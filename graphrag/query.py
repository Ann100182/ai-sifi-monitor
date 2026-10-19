"""Phase 4 — LangGraph query orchestrator.

State machine:

    START → classify ─┬─► graph_search  ─┐
                      │   (Cypher/Kuzu)  ├─► synthesize → END
                      └─► vector_search ─┘
                          (Chroma)

  classify       Sonnet 4.6 picks strategy (GRAPH / VECTOR / HYBRID) and
                 complexity (SIMPLE / MULTIHOP).
  graph_search   Sonnet 4.6 writes Cypher; rows carry provenance → ticker/form/date.
  vector_search  bge-small embeddings over Chroma, ticker-filtered when names appear.
  synthesize     Sonnet 4.6 by default; Opus 4.7 for MULTIHOP questions.

HYBRID fans out to both retrievers in the same LangGraph superstep (parallel),
and synthesize runs once after both finish.

Public entry:
  answer(question: str, verbose: bool = False) -> QueryResult
"""

from __future__ import annotations

import json
import operator
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Annotated, Literal, TypedDict

import chromadb
import kuzu
from anthropic import Anthropic
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from sentence_transformers import SentenceTransformer

from graphrag.config import HERE, PARSED_DIR, UNIVERSE

load_dotenv(HERE / ".env")

SONNET = "claude-sonnet-4-6"
OPUS   = "claude-opus-4-7"

# $ per 1M tokens (input, output)
PRICING = {
    SONNET: (3.0, 15.0),
    OPUS:   (5.0, 25.0),
}

DB_PATH = HERE / "cache" / "kuzu"
CHROMA_PATH = HERE / "cache" / "chroma"
COLLECTION_NAME = "sec_sections"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

CIK_TO_TICKER = {u["cik"]: u["ticker"] for u in UNIVERSE}

# Company name variants → ticker, for Chroma ticker filtering
_NAME_TO_TICKER = {
    "microsoft": "MSFT", "msft": "MSFT",
    "amazon": "AMZN", "aws": "AMZN", "amzn": "AMZN",
    "alphabet": "GOOGL", "google": "GOOGL", "googl": "GOOGL",
    "oracle": "ORCL", "orcl": "ORCL",
    "meta": "META", "facebook": "META",
    "ibm": "IBM",
    "salesforce": "CRM", "crm": "CRM",
    "adobe": "ADBE", "adbe": "ADBE",
    "nvidia": "NVDA", "nvda": "NVDA",
    "asml": "ASML",
    "coreweave": "CRWV", "crwv": "CRWV",
    "broadcom": "AVGO", "avgo": "AVGO",
}


def detect_tickers(question: str) -> list[str]:
    """Return canonical tickers mentioned in the question (whole-word, case-insensitive)."""
    q = question.lower()
    hits = []
    for name, ticker in _NAME_TO_TICKER.items():
        if re.search(rf"\b{re.escape(name)}\b", q) and ticker not in hits:
            hits.append(ticker)
    return hits


# ---------- Singletons ----------

_db = None; _conn = None; _coll = None; _embedder = None; _client = None


def _kuzu():
    global _db, _conn
    if _conn is None:
        # read_only lets the Streamlit app and the CLI query the graph at the same time
        _db = kuzu.Database(str(DB_PATH), read_only=True)
        _conn = kuzu.Connection(_db)
    return _conn


def _chroma():
    global _coll
    if _coll is None:
        c = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _coll = c.get_collection(COLLECTION_NAME)
    return _coll


def _embed():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
        try:
            import torch
            if torch.backends.mps.is_available():
                _embedder = _embedder.to("mps")
        except Exception:
            pass
    return _embedder


def _anthropic():
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


@lru_cache(maxsize=1)
def _filing_index() -> dict[str, dict]:
    """accession → {ticker, form, filing_date}, read from the first line of each
    parsed sections.jsonl. Used to give graph evidence a citable filing header."""
    idx: dict[str, dict] = {}
    for f in PARSED_DIR.glob("*/*/sections.jsonl"):
        with f.open() as fh:
            line = fh.readline()
        try:
            rec = json.loads(line)
        except Exception:
            continue
        idx[f.parent.name] = {
            "ticker": rec.get("ticker") or CIK_TO_TICKER.get(f.parent.parent.name, ""),
            "form": rec.get("form", ""),
            "filing_date": rec.get("filing_date", ""),
        }
    return idx


# ---------- Result shapes ----------

@dataclass
class EvidenceChunk:
    source: Literal["graph", "vector"]
    ticker: str
    filing_date: str
    form: str
    section_id: str
    text: str
    accession: str
    extra: dict = field(default_factory=dict)   # tier-specific metadata


@dataclass
class LLMCall:
    step: str
    model: str
    input_tokens: int
    output_tokens: int
    seconds: float

    @property
    def cost_usd(self) -> float:
        pin, pout = PRICING.get(self.model, PRICING[SONNET])
        return (self.input_tokens * pin + self.output_tokens * pout) / 1_000_000


@dataclass
class QueryResult:
    question: str
    answer: str
    evidence: list[EvidenceChunk]
    strategy: str                               # "graph", "vector", or "hybrid"
    complexity: str                             # "simple" or "multihop"
    model_used: str                             # synthesis model
    cost_usd: float                             # all LLM calls in the run
    calls: list[LLMCall] = field(default_factory=list)
    seconds: float = 0.0
    sections: list[str] = field(default_factory=list)   # target section groups, [] = any


class QueryState(TypedDict, total=False):
    question: str
    strategy: str
    complexity: str
    sections: list[str]                             # classifier's target section groups
    graph_evidence: list[EvidenceChunk]
    vector_evidence: list[EvidenceChunk]
    evidence: list[EvidenceChunk]
    answer: str
    model_used: str
    calls: Annotated[list[LLMCall], operator.add]   # parallel branches append safely
    verbose: bool


def _call(step: str, model: str, max_tokens: int, messages: list[dict],
          system: str | None = None) -> tuple[str, LLMCall]:
    t0 = time.time()
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    msg = _anthropic().messages.create(**kwargs)
    text = "\n".join(b.text for b in msg.content if b.type == "text").strip()
    call = LLMCall(step=step, model=model,
                   input_tokens=msg.usage.input_tokens or 0,
                   output_tokens=msg.usage.output_tokens or 0,
                   seconds=time.time() - t0)
    return text, call


def _log(state: QueryState, msg: str):
    if state.get("verbose"):
        print(msg)


# ---------- Node: classify ----------

CLASSIFY_PROMPT = """Classify this question about SEC-filing-extracted data about 12 AI/cloud companies.

Question: {q}

Line 1 — exactly ONE retrieval strategy:
- GRAPH: structural question about relationships, counterparties, counts, or specific extracted facts (SPVs, investments, risk signals, capex commitments). Examples: "which SPVs does Meta sponsor", "list circularity signals above severity 4", "who are NVIDIA's investees".
- VECTOR: semantic/narrative question. Examples: "what does Oracle say about OpenAI concentration", "how does ASML describe its China exposure", "explain Meta's capex outlook".
- HYBRID: needs both relational traversal AND narrative context. Examples: "trace the OpenAI-Oracle-CoreWeave-NVIDIA dependency and summarize each company's disclosure", "compare how Microsoft and Oracle describe their OpenAI relationships".

Line 2 — exactly ONE complexity:
- SIMPLE: one company or one fact pattern; a direct lookup or summary.
- MULTIHOP: chains relationships across 3+ entities, compares several companies, or requires reasoning across multiple filings/years.

Line 3 — the filing sections most likely to contain the answer, as `SECTIONS: ` followed by one or two of:
- MDA: management's discussion — outlook, guidance, capex plans, results drivers, liquidity, backlog
- RISK: risk factors — dependencies, suppliers, competition, regulation, export controls, concentration risk
- NOTES: financial statements and notes — leases, VIEs, investments, debt, commitments, accounting policies, useful lives
- BUSINESS: business description — products, strategy, customers, segments
- GOVERNANCE: proxy — compensation, directors, ownership, related-party transactions
- ANY: no particular section
Example: `SECTIONS: MDA, NOTES`

Line 4 — a one-sentence rationale."""

# Classifier section groups → section_id values across 10-K, 10-Q and 20-F.
# 10-Qs are mostly unsplit ("FULL"), so they're reached by the unfiltered query.
SECTION_GROUPS = {
    "MDA":        ["item_7", "item_7a", "part1_item2", "item_5"],
    "RISK":       ["item_1a", "part2_item1a", "item_3d"],
    "NOTES":      ["financial_statements_and_notes", "part1_item1", "item_8_pointer", "item_15"],
    "BUSINESS":   ["item_1"],
    "GOVERNANCE": ["comp_disc_analysis", "director_comp", "beneficial_owners", "related_party"],
}


def classify_node(state: QueryState) -> dict:
    text, call = _call("classify", SONNET, 200,
                       [{"role": "user", "content": CLASSIFY_PROMPT.format(q=state["question"])}])
    lines = [l.strip().upper() for l in text.splitlines() if l.strip()]
    first = lines[0] if lines else ""
    second = lines[1] if len(lines) > 1 else ""
    strategy = "graph" if first.startswith("GRAPH") else "hybrid" if first.startswith("HYBRID") else "vector"
    complexity = "multihop" if "MULTIHOP" in second or "MULTI-HOP" in second else "simple"
    m = re.search(r"SECTIONS:\s*([A-Z ,]+)", text.upper())
    sections = [s for s in re.findall(r"[A-Z]+", m.group(1)) if s in SECTION_GROUPS][:2] if m else []
    _log(state, f"[classify] strategy={strategy} complexity={complexity} sections={sections or 'ANY'}")
    return {"strategy": strategy, "complexity": complexity, "sections": sections, "calls": [call]}


def route_retrieval(state: QueryState) -> list[str]:
    s = state["strategy"]
    if state.get("complexity") == "multihop":
        # Multi-entity questions: the graph often covers some entities but not all,
        # so always back it with filing text.
        return ["graph_search", "vector_search"]
    if s == "graph":
        return ["graph_search"]
    if s == "vector":
        return ["vector_search"]
    return ["graph_search", "vector_search"]


# ---------- Node: graph_search ----------

GRAPH_TOOL_SYSTEM = """You translate a natural-language question into Kuzu Cypher queries over this schema.

NODE TABLES:
  Company(name, ticker, aliases, role, provenance)
  AILab(name, aliases, private, known_backers, provenance)
  CapexCommitment(name, filer, amount_usd, duration_yrs, start_fy, counterparty, purpose, verbatim_quote, provenance)
  OffBalanceEntity(name, entity_type, sponsor, co_owner, beneficiary, debt_stack_usd, residual_value_guarantee, term_yrs, purpose, verbatim_quote, provenance)
  Investment(name, investor, target, amount_usd, equity_pct, round, disclosed_date, verbatim_quote, provenance)
  RiskFactor(name, filer, category, severity, verbatim_quote, provenance)
  HiddenRiskSignal(name, filer, risk_type, severity, amount_usd, pct_of_revenue, duration_yrs, numeric_note, verbatim_quote, provenance)

RISK_TYPE values: HIDDEN_LEVERAGE, CIRCULARITY, REVENUE_ROUNDTRIP, CAPEX_ROI_GAP, EXECUTION_RISK, COST_OPACITY, CUSTOMER_CONCENTRATION, SUPPLIER_CONCENTRATION, OTHER

EDGE TABLES (predicate: allowed FROM → TO):
  SELLS_COMPUTE_TO: Company→AILab, Company→Company
  BUYS_COMPUTE_FROM: Company→Company
  INVESTED_IN: Company→AILab, Company→Company
  COMMITTED_CAPEX: Company→Company, Company→AILab, Company→CapexCommitment
  SPONSORS: Company→OffBalanceEntity
  BENEFITS: OffBalanceEntity→Company
  CITES_RISK: Company→RiskFactor
  HAS_RISK_SIGNAL: Company→HiddenRiskSignal
  CIRCULAR_WITH, ROUND_TRIPS_WITH, SUPPLIES, DEPENDS_ON: Company→Company, Company→AILab
  NAMES_COUNTERPARTY: RiskFactor/HiddenRiskSignal → Company/AILab

Canonical company names (Company.name, and the filer/sponsor/investor string properties): Microsoft, Amazon, Alphabet, Oracle, Meta, IBM, Salesforce, Adobe, NVIDIA, ASML, CoreWeave, Broadcom
AI Labs (AILab.name): OpenAI, Anthropic, xAI, Mistral, Cohere, Perplexity, Databricks

Rules:
- RETURN the whole fact node (e.g. `RETURN c.name, s`), not just scalar properties — the node carries provenance used for citations.
- Prefer filtering the string properties (filer, sponsor, investor, target, counterparty) over edge traversal for "which X does <company> have"; use edges for counterparty webs.
- For fuzzy name matching use `lower(x.name) CONTAINS 'openai'`.
- This is Kuzu, not Neo4j: use `label(r)` / `label(n)` (there is no `type()` or `labels()`); multi-type edges are written `[r:A|B]`; don't reuse a variable for two different node tables.
- Always end each query with `LIMIT 25`. Order by severity or amount_usd DESC when ranking.

Return 1-3 Cypher queries as a JSON array of strings only — no prose."""


def _parse_json_array(raw: str) -> list[str]:
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    return [q for q in arr if isinstance(q, str)]


def _row_to_evidence(row: list, col_names: list[str], cypher: str) -> EvidenceChunk:
    parts: list[str] = []
    prov: list[str] = []
    for i, v in enumerate(row):
        label = col_names[i] if i < len(col_names) else f"c{i}"
        if isinstance(v, dict):                     # node or rel
            if not prov and v.get("provenance"):
                prov = list(v["provenance"])
            node_label = v.get("_label", "")
            fields = [f"{k}={val!r}" for k, val in v.items()
                      if val not in (None, "", 0, 0.0, [], False)
                      and k not in ("provenance", "_id", "_label", "_src", "_dst")]
            parts.append(f"{node_label}({', '.join(fields)})" if node_label else ", ".join(fields))
        elif label.endswith("provenance") and isinstance(v, list):
            prov = prov or list(v)
        else:
            parts.append(f"{label}={v!r}")

    # Provenance entries are "cik:accession". Cite the most recent filing.
    idx = _filing_index()
    filings = []
    for p in prov:
        cik, _, acc = p.partition(":")
        meta = idx.get(acc, {})
        filings.append({"cik": cik, "accession": acc,
                        "ticker": meta.get("ticker") or CIK_TO_TICKER.get(cik, ""),
                        "form": meta.get("form", ""),
                        "filing_date": meta.get("filing_date", "")})
    filings.sort(key=lambda f: f["filing_date"], reverse=True)
    top = filings[0] if filings else {}
    return EvidenceChunk(
        source="graph", ticker=top.get("ticker", ""), filing_date=top.get("filing_date", ""),
        form=top.get("form", ""), section_id="(graph)", text=" · ".join(parts),
        accession=top.get("accession", ""),
        extra={"cypher": cypher, "all_filings": filings},
    )


def _run_cypher(q: str, limit: int) -> list[EvidenceChunk]:
    result = _kuzu().execute(q)
    col_names = result.get_column_names()
    out = []
    while result.has_next() and len(out) < limit:
        out.append(_row_to_evidence(result.get_next(), col_names, q))
    return out


def graph_search_node(state: QueryState, max_results_per_query: int = 25) -> dict:
    question = state["question"]
    raw, call = _call("graph_search", SONNET, 1200,
                      [{"role": "user", "content": f"Question: {question}\n\nReturn Cypher as JSON array."}],
                      system=GRAPH_TOOL_SYSTEM)
    calls = [call]
    queries = _parse_json_array(raw)[:3]
    _log(state, f"[graph] {len(queries)} cypher queries")

    evidence: list[EvidenceChunk] = []
    failed: list[tuple[str, str]] = []
    for q in queries:
        try:
            rows = _run_cypher(q, max_results_per_query)
            evidence.extend(rows)
            _log(state, f"[graph]   {len(rows)} rows ← {q[:90]}")
        except Exception as e:
            _log(state, f"[graph]   ERROR {str(e)[:120]}")
            failed.append((q, str(e)[:400]))

    # One self-repair round: hand Kuzu's errors back to the model.
    if failed:
        errs = "\n\n".join(f"QUERY: {q}\nERROR: {err}" for q, err in failed)
        raw, call = _call("cypher_repair", SONNET, 1200,
                          [{"role": "user", "content":
                            f"Question: {question}\n\nThese Kuzu Cypher queries failed:\n\n{errs}\n\n"
                            "Rewrite them so they run on Kuzu, respecting the allowed FROM → TO "
                            "pairs for each edge table. Return a JSON array of strings only."}],
                          system=GRAPH_TOOL_SYSTEM)
        calls.append(call)
        for q in _parse_json_array(raw)[:len(failed)]:
            try:
                rows = _run_cypher(q, max_results_per_query)
                evidence.extend(rows)
                _log(state, f"[graph]   repaired: {len(rows)} rows ← {q[:80]}")
            except Exception as e:
                _log(state, f"[graph]   repair failed: {str(e)[:120]}")
    return {"graph_evidence": evidence, "calls": calls}


# ---------- Node: vector_search ----------

_BACKLOG_PHRASES = ["emaining performance obligation", "RPO"]   # case-sensitive $contains


def _pack_backlog(coll, ticker: str, evidence: list[EvidenceChunk], n: int = 2):
    """Append the latest chunks that state a dollar backlog (RPO) figure for `ticker`."""
    try:
        r = coll.get(where={"ticker": ticker},
                     where_document={"$or": [{"$contains": p} for p in _BACKLOG_PHRASES]},
                     include=["documents", "metadatas"], limit=300)
    except Exception:
        return
    pat = re.compile(r"(remaining performance obligations?|RPO)[^.]{0,120}\$\s?[\d,.]+\s?(billion|million)", re.I)
    rows = []
    for md, doc in zip(r["metadatas"], r["documents"]):
        m = pat.search(doc)
        if m:
            start = max(0, m.start() - 300)    # centre the excerpt on the figure
            rows.append((md, doc[start:start + 1200]))
    rows.sort(key=lambda x: x[0].get("filing_date", ""), reverse=True)
    for md, text in rows[:n]:
        evidence.append(EvidenceChunk(
            source="vector", ticker=md.get("ticker", ""),
            filing_date=md.get("filing_date", ""), form=md.get("form", ""),
            section_id=md.get("section_id", ""), text=text,
            accession=md.get("accession", ""),
            extra={"chunk_idx": md.get("chunk_idx"), "probe": "backlog"},
        ))

def vector_search_node(state: QueryState, k: int = 8) -> dict:
    """If the question names companies, pull ticker-filtered results first, then
    supplement with un-filtered results so broader context isn't lost."""
    question = state["question"]
    coll = _chroma()
    qv = _embed().encode([question], convert_to_numpy=True, normalize_embeddings=True)[0].tolist()
    tickers = detect_tickers(question)
    include = ["documents", "metadatas", "distances"]
    evidence: list[EvidenceChunk] = []

    def _pack(result):
        for doc, md, dist in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
            evidence.append(EvidenceChunk(
                source="vector", ticker=md.get("ticker", ""),
                filing_date=md.get("filing_date", ""), form=md.get("form", ""),
                section_id=md.get("section_id", ""), text=doc[:1200],
                accession=md.get("accession", ""),
                extra={"distance": float(dist), "chunk_idx": md.get("chunk_idx")},
            ))

    # Section-targeted pass: half the budget goes to the sections the classifier
    # picked (e.g. MD&A for outlook questions), so boilerplate-heavy sections like
    # proxy compensation tables can't crowd out the answer.
    section_ids = [sid for g in state.get("sections") or [] for sid in SECTION_GROUPS[g]]

    def _query(n, where=None):
        try:
            _pack(coll.query(query_embeddings=[qv], n_results=n, where=where, include=include))
        except Exception:
            pass   # e.g. no chunks match the filter

    if section_ids:
        in_sections = {"section_id": {"$in": section_ids}}
        if tickers:
            for t in tickers:
                _query(max(2, (k // 2) // len(tickers)), {"$and": [{"ticker": t}, in_sections]})
        else:
            _query(k // 2, in_sections)

    if tickers:
        per_ticker = max(2, (k // 2 if section_ids else k) // len(tickers))
        for t in tickers:
            _query(per_ticker, {"ticker": t})
        if state.get("complexity") == "multihop":
            # Filings often omit counterparty names (e.g. Oracle never names OpenAI;
            # the deal shows up only as an RPO surge). Probe each named company's
            # backlog figures (exact-text match) so unnamed commitments can be cited.
            for t in tickers:
                _pack_backlog(coll, t, evidence)
        _query(max(3, k - len(evidence)))
    else:
        _query(max(3, k - len(evidence)))

    def _dedupe(items):
        seen, out = set(), []
        for e in items:
            key = (e.accession, e.section_id, e.extra.get("chunk_idx"))
            if key not in seen:
                seen.add(key)
                out.append(e)
        return out

    deduped = _dedupe(evidence)
    # Passes overlap (e.g. ASML has only two sections), so top up to k with fresh chunks.
    if len(deduped) < k:
        evidence = []
        if tickers:
            for t in tickers:
                _query(k * 2, {"ticker": t})
        else:
            _query(k * 2)
        deduped = _dedupe(deduped + evidence)[:max(k, len(deduped))]
    _log(state, f"[vector] {len(deduped)} chunks (ticker filter: {tickers or 'none'}; "
                f"sections: {state.get('sections') or 'any'})")
    return {"vector_evidence": deduped}


# ---------- Node: synthesize ----------

SYNTHESIS_SYSTEM = """You are a specialist research analyst using the AI SIFI Monitor knowledge graph.
You answer questions about 12 AI/cloud companies (Microsoft, Amazon, Alphabet, Oracle, Meta, IBM, Salesforce, Adobe, NVIDIA, ASML, CoreWeave, Broadcom) using evidence from their SEC filings 2024-2026.

Your answer is only as good as its grounding. Readers act on it, and every statement must be traceable to a filing.

Grounding rules:
1. Every factual statement comes from the EVIDENCE below and carries a citation [E1], [E2]... Do not use background knowledge about the companies, their products, suppliers, deals, history or accounting changes — even when it is well known, and even with a caveat. Do not add "general knowledge", "publicly known" or "outside the evidence" sections.
2. Report figures as the evidence states them. Unit conversions (millions → billions), rounding and simple sums or ratios of cited figures are fine; show what you combined.
3. Do not attribute purposes, motives or causes the filing does not state (e.g. don't say restricted cash is "for covenants" or capex is "AI-driven" unless the evidence says so). Interpretation is allowed only when it is built on cited facts and marked "(inference)".
4. If the evidence does not answer the question, say "insufficient evidence", summarise what the evidence does show, and name what is missing. Do not fill the gap.
5. Graph evidence comes from LLM extraction and can contain errors; where a graph fact conflicts with filing text (vector evidence), trust the filing text and note the conflict.
6. Filers often omit counterparty names. If the evidence shows an unnamed large commitment (e.g. a surge in remaining performance obligations, "a customer", "certain large contracts") that plausibly corresponds to a relationship in the question, cite it and mark the link as inference — e.g. "Oracle does not name OpenAI, but RPO rose from $X to $Y [E7], consistent with the reported OpenAI contract (inference, not disclosed)." Never present an inferred counterparty as disclosed.

Style:
7. Prefer short, structured answers (bullets, tables) over long prose. Do not pad.
8. Call out hidden-risk patterns (hidden leverage, circularity, revenue roundtripping, capex ROI gap, cost opacity, execution risk, concentration) when the cited evidence shows them; mark any pattern that goes beyond what the filing states as (inference)."""


def _format_evidence(evidence: list[EvidenceChunk]) -> str:
    lines = []
    for i, e in enumerate(evidence, 1):
        hdr = " ".join(x for x in (e.ticker, e.form, e.filing_date) if x)
        if e.source == "graph":
            lines.append(f"[E{i}] (graph{' · ' + hdr if hdr else ''}) {e.text}")
        else:
            lines.append(f"[E{i}] (vector · {hdr} · {e.section_id})\n{e.text}")
    return "\n\n".join(lines)


def synthesize_node(state: QueryState) -> dict:
    evidence = (state.get("graph_evidence") or []) + (state.get("vector_evidence") or [])
    model = OPUS if state.get("complexity") == "multihop" else SONNET
    _log(state, f"[synthesize] {len(evidence)} evidence chunks → {model}")
    text, call = _call("synthesize", model, 4096,
                       [{"role": "user", "content":
                         f"Question: {state['question']}\n\n"
                         f"Evidence:\n{_format_evidence(evidence)}\n\nAnswer:"}],
                       system=SYNTHESIS_SYSTEM)
    return {"answer": text, "evidence": evidence, "model_used": model, "calls": [call]}


# ---------- Graph assembly ----------

def build_graph():
    g = StateGraph(QueryState)
    g.add_node("classify", classify_node)
    g.add_node("graph_search", graph_search_node)
    g.add_node("vector_search", vector_search_node)
    g.add_node("synthesize", synthesize_node)
    g.add_edge(START, "classify")
    g.add_conditional_edges("classify", route_retrieval, ["graph_search", "vector_search"])
    g.add_edge("graph_search", "synthesize")
    g.add_edge("vector_search", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


_app = None


def _graph_app():
    global _app
    if _app is None:
        _app = build_graph()
    return _app


# ---------- Public entry ----------

def answer(question: str, verbose: bool = False) -> QueryResult:
    t0 = time.time()
    final = _graph_app().invoke({"question": question, "calls": [], "verbose": verbose})
    calls: list[LLMCall] = final.get("calls", [])
    return QueryResult(
        question=question,
        answer=final.get("answer", ""),
        evidence=final.get("evidence", []),
        strategy=final.get("strategy", ""),
        complexity=final.get("complexity", ""),
        model_used=final.get("model_used", ""),
        cost_usd=sum(c.cost_usd for c in calls),
        calls=calls,
        seconds=time.time() - t0,
        sections=final.get("sections", []),
    )
