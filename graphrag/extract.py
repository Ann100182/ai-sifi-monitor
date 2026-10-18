"""Phase 2 — extraction pipeline.

Reads parsed section JSONL from Phase 1, runs each section through Claude
Haiku 4.5 with tool_use, writes extraction results to disk, and reports
cost + token usage.

Prompt caching is used on the system prompt + tool schema (large, static)
to keep per-section cost low when running the full corpus.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from graphrag.config import HERE, PARSED_DIR
from graphrag.prompts import SYSTEM_PROMPT, build_user_message
from graphrag.schemas import extraction_tool_schema

# Load Anthropic key from graphrag/.env (user-created, gitignored)
load_dotenv(HERE / ".env")

HAIKU   = "claude-haiku-4-5-20251001"
SONNET  = "claude-sonnet-4-6"
MAX_INPUT_TOKENS_PER_CALL = 15_000       # chunk larger sections

EXTRACTED_DIR = HERE / "cache" / "extracted"
EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

# Sections where extraction quality matters most → Sonnet 4.6 (with caching).
# Everything else → Haiku 4.5 (no caching, cheaper).
SONNET_SECTIONS = {
    # Risk factors (10-K Item 1A, 20-F Item 3D, 10-Q interim risk updates)
    "item_1a", "item_3d", "part2_item1a",
    # MD&A (10-K Item 7, 10-Q Item 2, 20-F Item 5)
    "item_7", "part1_item2", "item_5",
    # Financial statements and notes (SPVs, debt, leases, commitments live here)
    "item_8_pointer", "item_8", "financial_statements_and_notes",
    "item_18",                       # 20-F equivalent
    "part1_item1",                   # 10-Q unaudited fs + notes
    # Related-party and compensation (DEF 14A)
    "related_party", "comp_disc_analysis",
}


def pick_model(section_id: str) -> str:
    return SONNET if section_id in SONNET_SECTIONS else HAIKU


# Pricing per million tokens
PRICES = {
    HAIKU:  {"in": 0.80, "creation": 1.00, "read": 0.08, "out": 4.00},
    SONNET: {"in": 3.00, "creation": 3.75, "read": 0.30, "out": 15.00},
}


@dataclass
class ModelStats:
    api_calls: int = 0
    uncached_input: int = 0
    cache_creation: int = 0
    cache_read: int = 0
    output: int = 0

    def cost(self, prices: dict) -> float:
        return (self.uncached_input * prices["in"]
                + self.cache_creation * prices["creation"]
                + self.cache_read * prices["read"]
                + self.output * prices["out"]) / 1_000_000


@dataclass
class ExtractionStats:
    sections_processed: int = 0
    sections_skipped: int = 0
    errors: int = 0
    by_model: dict = None

    def __post_init__(self):
        if self.by_model is None:
            self.by_model = {HAIKU: ModelStats(), SONNET: ModelStats()}

    def est_cost_usd(self) -> float:
        return sum(m.cost(PRICES[name]) for name, m in self.by_model.items())

    def summary(self) -> str:
        lines = [f"total cost ≈ ${self.est_cost_usd():.3f}  "
                 f"sections={self.sections_processed} skipped={self.sections_skipped} errors={self.errors}"]
        for name, m in self.by_model.items():
            model_label = "Haiku" if "haiku" in name else "Sonnet"
            total_in = m.uncached_input + m.cache_creation + m.cache_read
            hit = (m.cache_read / total_in * 100) if total_in else 0
            lines.append(
                f"  {model_label:<7} calls={m.api_calls:>3}  "
                f"in={m.uncached_input:>8,}  create={m.cache_creation:>7,}  "
                f"read={m.cache_read:>8,} ({hit:4.1f}% cache)  "
                f"out={m.output:>7,}  ${m.cost(PRICES[name]):.3f}"
            )
        return "\n".join(lines)


# ---------- Chunking ----------

def _chunk_text(text: str, max_tokens: int = MAX_INPUT_TOKENS_PER_CALL) -> list[str]:
    """Rough paragraph-based chunking. ~4 chars/token."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return [text]
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for p in paragraphs:
        plen = len(p) + 2
        if current_len + plen > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [p]
            current_len = plen
        else:
            current.append(p)
            current_len += plen
    if current:
        chunks.append("\n\n".join(current))
    return chunks


# ---------- Single-section extraction ----------

def extract_section(client: Anthropic, section: dict, model: str) -> tuple[dict, dict]:
    """Return (extraction_result, {model: usage_dict})."""
    chunks = _chunk_text(section["text"])
    merged = {"nodes": [], "edges": [], "notes": []}
    usage = {"calls": 0, "uncached_in": 0, "cache_creation": 0, "cache_read": 0, "out": 0}

    # Only mark cache_control for models that honor it (Sonnet works, Haiku ignores)
    sys_block = {"type": "text", "text": SYSTEM_PROMPT}
    if "sonnet" in model:
        sys_block["cache_control"] = {"type": "ephemeral"}

    for i, chunk in enumerate(chunks):
        user_msg = build_user_message(
            chunk,
            section["section_id"], section["section_name"],
            section["ticker"], section["form"], section["filing_date"], section["accession"],
        )
        resp = client.messages.create(
            model=model,
            max_tokens=4096,
            system=[sys_block],
            tools=[{
                "name": "extract_graph",
                "description": "Return the extracted knowledge-graph nodes and edges from the source text.",
                "input_schema": extraction_tool_schema(),
            }],
            tool_choice={"type": "tool", "name": "extract_graph"},
            messages=[{"role": "user", "content": user_msg}],
        )
        usage["calls"] += 1
        u = resp.usage
        usage["uncached_in"]   += u.input_tokens or 0
        usage["cache_creation"] += getattr(u, "cache_creation_input_tokens", 0) or 0
        usage["cache_read"]     += getattr(u, "cache_read_input_tokens", 0) or 0
        usage["out"]            += u.output_tokens or 0

        tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
        if tool_use:
            payload = tool_use.input
            merged["nodes"].extend(payload.get("nodes", []))
            merged["edges"].extend(payload.get("edges", []))
            if payload.get("notes"):
                merged["notes"].append(f"[chunk {i+1}/{len(chunks)}] {payload['notes']}")

    merged["notes"] = "\n".join(merged["notes"]) if merged["notes"] else None
    return merged, usage


# ---------- Per-filing + full-corpus orchestration ----------

def extract_filing(client: Anthropic, cik: str, accession: str,
                   stats: ExtractionStats) -> dict:
    """Extract all sections for one filing with per-section model routing."""
    sec_path = PARSED_DIR / cik / accession / "sections.jsonl"
    if not sec_path.exists():
        return {}
    sections = [json.loads(l) for l in sec_path.read_text().splitlines()]

    out_dir = EXTRACTED_DIR / cik / accession
    out_dir.mkdir(parents=True, exist_ok=True)

    by_section: dict[str, dict] = {}
    for sec in sections:
        if sec.get("token_estimate", 0) < 300:
            stats.sections_skipped += 1
            continue
        model = pick_model(sec["section_id"])
        try:
            result, usage = extract_section(client, sec, model=model)
        except Exception as e:
            print(f"  ! extract failed {sec['section_id']} ({model}): {str(e)[:120]}")
            stats.errors += 1
            continue
        by_section[sec["section_id"]] = result
        stats.sections_processed += 1
        m = stats.by_model[model]
        m.api_calls      += usage["calls"]
        m.uncached_input += usage["uncached_in"]
        m.cache_creation += usage["cache_creation"]
        m.cache_read     += usage["cache_read"]
        m.output         += usage["out"]

    (out_dir / "extracted.json").write_text(json.dumps(by_section, indent=2))
    return by_section


def extract_all(limit: int | None = None) -> ExtractionStats:
    """Walk every parsed filing, extract via hybrid routing, save."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. "
            "Run the key-setup command and ensure graphrag/.env exists."
        )
    client = Anthropic(api_key=api_key)
    stats = ExtractionStats()

    filings = sorted(PARSED_DIR.glob("*/*/sections.jsonl"))
    if limit:
        filings = filings[:limit]
    for i, path in enumerate(filings, 1):
        acc = path.parent.name
        cik = path.parent.parent.name
        print(f"[{i}/{len(filings)}] cik={cik} {acc}", flush=True)
        extract_filing(client, cik, acc, stats)
        if i % 5 == 0 or i == len(filings):
            print(f"\n{stats.summary()}\n", flush=True)
    return stats
