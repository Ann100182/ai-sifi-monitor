"""GraphRAG config — locked scope per project memory 2026-10-17."""

from __future__ import annotations
from pathlib import Path

# ---- 12-company universe (cloud peers + supply-chain anchors) ----
UNIVERSE: list[dict] = [
    # ticker, cik (10-digit), legal_name,                          role in universe
    {"ticker": "MSFT",  "cik": "0000789019", "name": "Microsoft Corporation",         "role": "hyperscaler"},
    {"ticker": "AMZN",  "cik": "0001018724", "name": "Amazon.com, Inc.",              "role": "hyperscaler"},
    {"ticker": "GOOGL", "cik": "0001652044", "name": "Alphabet Inc.",                 "role": "hyperscaler"},
    {"ticker": "ORCL",  "cik": "0001341439", "name": "Oracle Corporation",            "role": "hyperscaler"},
    {"ticker": "META",  "cik": "0001326801", "name": "Meta Platforms, Inc.",          "role": "internal_consumer"},
    {"ticker": "IBM",   "cik": "0000051143", "name": "International Business Machines","role": "hyperscaler_legacy"},
    {"ticker": "CRM",   "cik": "0001108524", "name": "Salesforce, Inc.",              "role": "saas_consumer"},
    {"ticker": "ADBE",  "cik": "0000796343", "name": "Adobe Inc.",                    "role": "saas_consumer"},
    {"ticker": "NVDA",  "cik": "0001045810", "name": "NVIDIA Corporation",            "role": "supplier_center"},
    {"ticker": "ASML",  "cik": "0000937966", "name": "ASML Holding N.V.",             "role": "foreign_filer"},
    {"ticker": "CRWV",  "cik": "0001769628", "name": "CoreWeave, Inc.",               "role": "neocloud"},
    {"ticker": "AVGO",  "cik": "0001730168", "name": "Broadcom Inc.",                 "role": "custom_silicon"},
]

# ---- Forms in / out ----
FORMS_IN: set[str] = {
    "10-K",   "10-K/A",
    "10-Q",   "10-Q/A",
    "20-F",   "20-F/A",
    "DEF 14A",
    "ARS",
}
FORMS_OUT: set[str] = {"8-K", "6-K", "S-1", "S-1/A", "424B"}  # deferred to Phase 2

# ---- Timeline ----
FY_START = 2024
FY_END   = 2026

# ---- SEC EDGAR access ----
# SEC requires a User-Agent with a contact email. Change the email if you re-use this.
SEC_USER_AGENT = "AI SIFI Monitor research@ai-sifi.local"
SEC_REQUEST_DELAY_SEC = 0.11   # stay under SEC's 10 req/sec limit

# ---- Local paths ----
HERE       = Path(__file__).parent
CACHE_DIR  = HERE / "cache"
RAW_DIR    = CACHE_DIR / "raw"       # cache/raw/{cik}/{accession}/
PARSED_DIR = CACHE_DIR / "parsed"    # cache/parsed/{cik}/{accession}/
RAW_DIR.mkdir(parents=True, exist_ok=True)
PARSED_DIR.mkdir(parents=True, exist_ok=True)
