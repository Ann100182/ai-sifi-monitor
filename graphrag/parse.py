"""Section-aware parser — turns raw SEC HTML into section-tagged JSONL.

Design:
  1. Load HTML, strip script/style/XBRL inline tags
  2. Flatten to plain text with paragraph breaks preserved
  3. Detect section boundaries via regex patterns per form type
  4. Emit one JSON record per section:
     {ticker, cik, accession, form, filing_date, section_id, section_name,
      text, token_estimate}

Form-specific section maps live in SECTIONS_* below. These are patterns
that match the section HEADERS; everything until the next match is the
section body.

Not every filing cleanly matches these patterns. For filings where no
sections are found, we emit a single "FULL" section containing the entire
text — the extraction LLM in Phase 2 can still work on it.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from tqdm import tqdm

from graphrag.config import PARSED_DIR, RAW_DIR

# BeautifulSoup chatters about XBRL-first filings; we parse as HTML intentionally.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ---------- Section detection patterns ----------

# Patterns are tuples: (section_id, section_name, regex)
# Regex matches the HEADING line only.

SECTIONS_10K: list[tuple[str, str, re.Pattern]] = [
    ("item_1",   "Business",                   re.compile(r"^\s*item\s*1\.?\s*(business)?\s*$", re.I|re.M)),
    ("item_1a",  "Risk Factors",               re.compile(r"^\s*item\s*1a\.?\s*(risk\s*factors)?\s*$", re.I|re.M)),
    ("item_1b",  "Unresolved Staff Comments",  re.compile(r"^\s*item\s*1b\.?\s*(unresolved\s*staff\s*comments)?\s*$", re.I|re.M)),
    ("item_2",   "Properties",                 re.compile(r"^\s*item\s*2\.?\s*(properties)?\s*$", re.I|re.M)),
    ("item_3",   "Legal Proceedings",          re.compile(r"^\s*item\s*3\.?\s*(legal\s*proceedings)?\s*$", re.I|re.M)),
    ("item_7",   "MD&A",                       re.compile(r"^\s*item\s*7\.?\s*(management'?s?\s*discussion\s*and\s*analysis.*)?\s*$", re.I|re.M)),
    ("item_7a",  "Market Risk",                re.compile(r"^\s*item\s*7a\.?\s*(quantitative\s*and\s*qualitative.*)?\s*$", re.I|re.M)),
    ("item_8_pointer", "Item 8 pointer",       re.compile(r"^\s*item\s*8\.?\s*(financial\s*statements.*)?\s*$", re.I|re.M)),
    ("item_9a",  "Controls & Procedures",      re.compile(r"^\s*item\s*9a\.?\s*(controls?\s*and\s*procedures)?\s*$", re.I|re.M)),
    ("item_15",  "Exhibits",                   re.compile(r"^\s*item\s*15\.?\s*(exhibits.*)?\s*$", re.I|re.M)),
    # The real financial statements usually live AFTER Item 15 in Part IV.
    # Anchor on "Consolidated Balance Sheets" / "Report of Independent" markers.
    ("financial_statements_and_notes", "Financial Statements & Notes",
     re.compile(r"^\s*(consolidated\s*balance\s*sheets?|report\s*of\s*independent\s*registered\s*public\s*accounting\s*firm)\s*$", re.I|re.M)),
]

SECTIONS_10Q: list[tuple[str, str, re.Pattern]] = [
    ("part1_item1", "Financial Statements",    re.compile(r"^\s*part\s*i\s*[-:.\s]*item\s*1\.?\s*(financial\s*statements)?\s*$", re.I|re.M)),
    ("part1_item2", "MD&A",                    re.compile(r"^\s*part\s*i\s*[-:.\s]*item\s*2\.?\s*(management'?s?.*)?\s*$", re.I|re.M)),
    ("part1_item3", "Market Risk",             re.compile(r"^\s*part\s*i\s*[-:.\s]*item\s*3\.?\s*(quantitative.*)?\s*$", re.I|re.M)),
    ("part1_item4", "Controls",                re.compile(r"^\s*part\s*i\s*[-:.\s]*item\s*4\.?\s*(controls?.*)?\s*$", re.I|re.M)),
    ("part2_item1a","Risk Factors (interim)",  re.compile(r"^\s*part\s*ii\s*[-:.\s]*item\s*1a\.?\s*(risk\s*factors)?\s*$", re.I|re.M)),
    ("part2_item5", "Other",                   re.compile(r"^\s*part\s*ii\s*[-:.\s]*item\s*5\.?\s*(other.*)?\s*$", re.I|re.M)),
]

SECTIONS_20F: list[tuple[str, str, re.Pattern]] = [
    ("item_3",   "Key Information",            re.compile(r"^\s*item\s*3\.?\s*(key\s*information)?\s*$", re.I|re.M)),
    ("item_3d",  "Risk Factors (20-F)",        re.compile(r"^\s*(item\s*3d\.?|d\.?\s*risk\s*factors)\s*$", re.I|re.M)),
    ("item_4",   "Information on the Company", re.compile(r"^\s*item\s*4\.?\s*(information\s*on\s*the\s*company)?\s*$", re.I|re.M)),
    ("item_5",   "Operating & Financial Review", re.compile(r"^\s*item\s*5\.?\s*(operating\s*and\s*financial.*)?\s*$", re.I|re.M)),
    ("item_7",   "Major Shareholders & Related", re.compile(r"^\s*item\s*7\.?\s*(major\s*shareholders.*)?\s*$", re.I|re.M)),
    ("item_11",  "Market Risk Disclosures",    re.compile(r"^\s*item\s*11\.?\s*(quantitative.*)?\s*$", re.I|re.M)),
    ("item_18",  "Financial Statements",       re.compile(r"^\s*item\s*18\.?\s*(financial\s*statements)?\s*$", re.I|re.M)),
]

SECTIONS_DEF14A: list[tuple[str, str, re.Pattern]] = [
    ("comp_disc_analysis", "Compensation Discussion & Analysis",
     re.compile(r"^\s*(compensation\s*discussion\s*(and|&)\s*analysis)\s*$", re.I|re.M)),
    ("related_party",      "Related Party Transactions",
     re.compile(r"^\s*(certain\s*)?(relationships?\s*and\s*)?related\s*(party|person)\s*(transactions)?\s*$", re.I|re.M)),
    ("director_comp",      "Director Compensation",
     re.compile(r"^\s*director\s*compensation\s*$", re.I|re.M)),
    ("beneficial_owners",  "Beneficial Owners",
     re.compile(r"^\s*(security\s*ownership\s*of\s*)?(certain\s*)?beneficial\s*own(ers|ership)\s*$", re.I|re.M)),
]

SECTION_MAPS = {
    "10-K": SECTIONS_10K,       "10-K/A": SECTIONS_10K,
    "10-Q": SECTIONS_10Q,       "10-Q/A": SECTIONS_10Q,
    "20-F": SECTIONS_20F,       "20-F/A": SECTIONS_20F,
    "DEF 14A": SECTIONS_DEF14A,
}


# ---------- Text extraction ----------

def html_to_text(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "lxml")
    # Kill script, style, and inline XBRL tags
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Collapse <br> and </p> as line breaks
    text = soup.get_text("\n", strip=False)
    # Normalize whitespace: collapse runs of blank lines, strip trailing spaces
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------- Section splitting ----------

@dataclass
class Section:
    ticker: str
    cik: str
    accession: str
    form: str
    filing_date: str
    section_id: str
    section_name: str
    char_offset: int        # start offset in cleaned text
    text: str
    token_estimate: int     # rough: chars / 4


def _estimate_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def split_sections(text: str, form: str) -> list[tuple[str, str, int, str]]:
    """Return list of (section_id, section_name, offset, body).

    Algorithm:
      1. Find ALL header matches across patterns, sort by offset.
      2. Collapse runs of same-section_id matches (page footers repeat).
      3. For each distinct section run, body = text from run start → next
         distinct section's start.
      4. Dedup by section_id keeping the LARGEST body (handles TOC-vs-real).
    """
    patterns = SECTION_MAPS.get(form, [])
    if not patterns:
        return [("FULL", "Full document", 0, text)]

    found: list[tuple[int, str, str]] = []
    for sid, sname, pat in patterns:
        for m in pat.finditer(text):
            found.append((m.start(), sid, sname))
    if not found:
        return [("FULL", "Full document", 0, text)]
    found.sort(key=lambda t: t[0])

    # Collapse runs of same section_id (e.g., page-footer repeats)
    runs: list[tuple[str, str, int]] = []
    for off, sid, sname in found:
        if runs and runs[-1][0] == sid:
            continue  # same section still running
        runs.append((sid, sname, off))

    # Build sections: each run's body is until the NEXT run's offset
    sections: list[tuple[str, str, int, str]] = []
    for i, (sid, sname, off) in enumerate(runs):
        end = runs[i + 1][2] if i + 1 < len(runs) else len(text)
        body = text[off:end].strip()
        if len(body) < 200:
            continue
        sections.append((sid, sname, off, body))
    if not sections:
        return [("FULL", "Full document", 0, text)]

    # Final dedup by section_id (TOC + real body may both survive the run
    # collapse if they're separated by other sections) — keep the largest.
    by_id: dict[str, tuple[str, str, int, str]] = {}
    for sid, sname, off, body in sections:
        existing = by_id.get(sid)
        if existing is None or len(body) > len(existing[3]):
            by_id[sid] = (sid, sname, off, body)
    return sorted(by_id.values(), key=lambda t: t[2])


# ---------- Per-filing orchestration ----------

def parse_filing(cik_dir: Path, accession_dir: Path) -> list[Section]:
    meta_path = accession_dir / "meta.json"
    primary_path = accession_dir / "primary.html"
    if not meta_path.exists() or not primary_path.exists():
        return []
    meta = json.loads(meta_path.read_text())
    # Skip PDFs — ARS is usually a PDF (annual report glossy format); 10-K has the content
    if meta.get("primary_doc", "").lower().endswith(".pdf"):
        return []
    html = primary_path.read_bytes()
    text = html_to_text(html)
    secs = split_sections(text, meta["form"])
    return [
        Section(
            ticker=meta["ticker"], cik=meta["cik"], accession=meta["accession"],
            form=meta["form"], filing_date=meta["filing_date"],
            section_id=sid, section_name=sname, char_offset=off,
            text=body, token_estimate=_estimate_tokens(body),
        )
        for sid, sname, off, body in secs
    ]


def parse_all() -> dict:
    summary: dict[str, dict] = {}
    paths = list(RAW_DIR.glob("*/*/primary.html"))
    for primary in tqdm(paths, desc="parsing", unit="filing"):
        acc_dir = primary.parent
        cik_dir = acc_dir.parent
        try:
            secs = parse_filing(cik_dir, acc_dir)
        except Exception as e:
            summary.setdefault(cik_dir.name, {}).setdefault("_err", 0)
            summary[cik_dir.name]["_err"] += 1
            continue
        if not secs:
            continue
        # Write JSONL
        out_dir = PARSED_DIR / cik_dir.name / acc_dir.name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "sections.jsonl"
        with out_path.open("w") as fh:
            for s in secs:
                fh.write(json.dumps(asdict(s)) + "\n")
        summary.setdefault(secs[0].ticker, {}).setdefault("filings", 0)
        summary[secs[0].ticker]["filings"] += 1
        summary[secs[0].ticker].setdefault("sections", 0)
        summary[secs[0].ticker]["sections"] += len(secs)
        summary[secs[0].ticker].setdefault("tokens", 0)
        summary[secs[0].ticker]["tokens"] += sum(s.token_estimate for s in secs)
    return summary
