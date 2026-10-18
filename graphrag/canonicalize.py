"""Canonicalize entity names across extracted output.

The extractor used both tickers and legal names depending on which the
filing used ("MSFT" vs "Microsoft", "AVGO" vs "Broadcom"). This module
maps every alias to a single canonical name per entity so the graph
dedupes correctly.
"""

from __future__ import annotations

import re
from functools import lru_cache

from graphrag.config import UNIVERSE

# ---------- Canonical name tables ----------

# Universe companies: canonical = legal name (short form), map tickers + variants
_UNIVERSE_CANON = {
    "MSFT":     "Microsoft",
    "AMZN":     "Amazon",
    "GOOGL":    "Alphabet",
    "GOOG":     "Alphabet",
    "ORCL":     "Oracle",
    "META":     "Meta",
    "IBM":      "IBM",
    "CRM":      "Salesforce",
    "ADBE":     "Adobe",
    "NVDA":     "NVIDIA",
    "ASML":     "ASML",
    "CRWV":     "CoreWeave",
    "AVGO":     "Broadcom",
}

# Known expansions / common variants → canonical
_EXPANSIONS = {
    "microsoft corporation": "Microsoft",
    "microsoft corp": "Microsoft",
    "amazon.com, inc.": "Amazon",
    "amazon.com inc": "Amazon",
    "amazon web services": "Amazon",
    "aws": "Amazon",
    "alphabet inc": "Alphabet",
    "alphabet inc.": "Alphabet",
    "google": "Alphabet",
    "google llc": "Alphabet",
    "oracle corporation": "Oracle",
    "oracle corp": "Oracle",
    "meta platforms": "Meta",
    "meta platforms, inc.": "Meta",
    "meta platforms inc": "Meta",
    "facebook": "Meta",
    "international business machines": "IBM",
    "ibm corporation": "IBM",
    "salesforce.com": "Salesforce",
    "salesforce, inc.": "Salesforce",
    "salesforce inc": "Salesforce",
    "adobe inc": "Adobe",
    "adobe systems": "Adobe",
    "nvidia corporation": "NVIDIA",
    "nvidia corp": "NVIDIA",
    "asml holding n.v.": "ASML",
    "asml holding nv": "ASML",
    "asml holding": "ASML",
    "asml nv": "ASML",
    "asml": "ASML",
    "coreweave, inc.": "CoreWeave",
    "coreweave inc": "CoreWeave",
    "broadcom inc.": "Broadcom",
    "broadcom inc": "Broadcom",
    # Non-universe but SIFI-adjacent
    "tsmc": "TSMC",
    "taiwan semiconductor manufacturing": "TSMC",
    "taiwan semiconductor manufacturing company": "TSMC",
    "intel corporation": "Intel",
    "intel corp": "Intel",
    "amd": "AMD",
    "advanced micro devices": "AMD",
    "advanced micro devices, inc.": "AMD",
    "samsung electronics": "Samsung",
    "samsung": "Samsung",
    "dell technologies": "Dell",
    "super micro computer": "Super Micro",
    "arista networks": "Arista",
    "hp inc": "HP",
    "hewlett packard enterprise": "HPE",
    "qualcomm": "Qualcomm",
    "micron technology": "Micron",
    "cadence design systems": "Cadence",
    "synopsys": "Synopsys",
    # Private AI labs
    "openai": "OpenAI",
    "openai llc": "OpenAI",
    "openai, inc.": "OpenAI",
    "openai inc": "OpenAI",
    "anthropic": "Anthropic",
    "anthropic pbc": "Anthropic",
    "anthropic, pbc": "Anthropic",
    "mistral ai": "Mistral",
    "mistral": "Mistral",
    "xai": "xAI",
    "x.ai": "xAI",
    "x ai": "xAI",
    "cohere": "Cohere",
    "perplexity": "Perplexity",
    "perplexity ai": "Perplexity",
    "databricks": "Databricks",
    "inflection ai": "Inflection",
    "inflection": "Inflection",
    "character ai": "Character.AI",
    "character.ai": "Character.AI",
    "huggingface": "Hugging Face",
    "hugging face": "Hugging Face",
    "stability ai": "Stability AI",
    # Common infrastructure counterparties
    "blue owl capital": "Blue Owl",
    "blue owl": "Blue Owl",
    "brookfield": "Brookfield",
    "brookfield infrastructure": "Brookfield",
    "softbank": "SoftBank",
    "mgx": "MGX",
    "lambda": "Lambda",
    "lambda labs": "Lambda",
    "nebius": "Nebius",
    "nebius group": "Nebius",
    "scale ai": "Scale AI",
    "figure ai": "Figure AI",
    "figure": "Figure AI",
    # Regulators / geopolitical actors
    "united states government": "USG",
    "u.s. government": "USG",
    "usg": "USG",
    "u.s.g.": "USG",
    "u.s. department of commerce": "US BIS",
    "department of commerce": "US BIS",
    "bureau of industry and security": "US BIS",
    "european union": "EU",
    "european commission": "EU",
    "people's republic of china": "China",
    "prc": "China",
    "china": "China",
    "netherlands": "Netherlands",
    "taiwan": "Taiwan",
    "republic of china": "Taiwan",
    "irs": "IRS",
    "internal revenue service": "IRS",
}

# Build reverse map: universe aliases + expansions all → canonical
_CANON_MAP: dict[str, str] = {}
for k, v in _UNIVERSE_CANON.items():
    _CANON_MAP[k.lower()] = v
    _CANON_MAP[v.lower()] = v
for k, v in _EXPANSIONS.items():
    _CANON_MAP[k.lower()] = v
# Also map any UNIVERSE legal-name variants
for u in UNIVERSE:
    _CANON_MAP[u["ticker"].lower()] = _UNIVERSE_CANON[u["ticker"]]
    _CANON_MAP[u["name"].lower()] = _UNIVERSE_CANON[u["ticker"]]


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation/whitespace, collapse spaces."""
    if not name:
        return ""
    s = name.lower().strip()
    # Collapse multiple whitespace
    s = re.sub(r"\s+", " ", s)
    # Drop trailing/leading quotes, commas, periods
    s = s.strip(" '\"`,.")
    return s


@lru_cache(maxsize=10_000)
def canonical(name: str) -> str:
    """Return canonical name for an entity. Preserves original if no mapping found."""
    if not name:
        return name
    norm = _normalize(name)
    if norm in _CANON_MAP:
        return _CANON_MAP[norm]
    # Try with internal commas removed (e.g. "openai, inc" → "openai inc")
    nocomma = norm.replace(",", "")
    nocomma = re.sub(r"\s+", " ", nocomma).strip()
    if nocomma in _CANON_MAP:
        return _CANON_MAP[nocomma]
    # Try stripping common suffixes (operate on the no-comma form so
    # "openai, inc." → "openai inc" → "openai" → OpenAI)
    for suffix in [" inc.", " inc", " llc", " corp.", " corp", " corporation",
                   " plc", " ltd", " ltd.", " ag", " nv", " n.v.", " sa", " s.a.",
                   " pbc", " company", " co.", " holdings", " holding"]:
        if nocomma.endswith(suffix):
            trimmed = nocomma[: -len(suffix)].strip()
            if trimmed in _CANON_MAP:
                return _CANON_MAP[trimmed]
    # Fallback: title-case the raw input
    return name.strip() if name else name


def canonicalize_in_list(names: list) -> list:
    """Apply canonical() to each item, dedupe preserving order."""
    if not names:
        return []
    seen = set()
    out = []
    for n in names:
        if not isinstance(n, str):
            continue
        c = canonical(n)
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out
