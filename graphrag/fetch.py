"""EDGAR fetcher — pulls filing index and primary documents to local cache.

For each company:
  1. GET submissions.json → list of recent filings
  2. Filter by FORMS_IN + fiscal year range (FY_START..FY_END)
  3. For each matching filing, download the primary document (HTML)
  4. Cache raw to RAW_DIR/{cik}/{accession}/primary.html + meta.json

All HTTP is rate-limited to stay under SEC's 10 req/s policy.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.request import Request, urlopen

from tqdm import tqdm

from graphrag.config import (
    FORMS_IN, FY_END, FY_START, RAW_DIR,
    SEC_REQUEST_DELAY_SEC, SEC_USER_AGENT, UNIVERSE,
)


@dataclass
class FilingRef:
    cik: str
    ticker: str
    accession: str          # e.g., "0001326801-25-000012"
    accession_nodash: str   # e.g., "000132680125000012" — used in URL paths
    form: str
    filing_date: str        # YYYY-MM-DD
    report_date: str        # fiscal period end
    primary_doc: str        # filename of primary document
    primary_url: str        # fully-qualified URL
    size_bytes: int | None = None


# ---------- HTTP helpers ----------

def _get(url: str, as_json: bool = False, timeout: int = 30):
    req = Request(url, headers={"User-Agent": SEC_USER_AGENT})
    with urlopen(req, timeout=timeout) as r:
        data = r.read()
    time.sleep(SEC_REQUEST_DELAY_SEC)
    return json.loads(data) if as_json else data


# ---------- Submission index ----------

def list_filings_for(ticker: str, cik: str) -> list[FilingRef]:
    """Return all filings matching FORMS_IN within [FY_START, FY_END]."""
    sub = _get(f"https://data.sec.gov/submissions/CIK{cik}.json", as_json=True)
    recent = sub.get("filings", {}).get("recent", {})
    out: list[FilingRef] = []
    for i, form in enumerate(recent.get("form", [])):
        if form not in FORMS_IN:
            continue
        date = recent["filingDate"][i]
        y = int(date[:4]) if date else 0
        if not (FY_START <= y <= FY_END):
            continue
        acc = recent["accessionNumber"][i]
        acc_nodash = acc.replace("-", "")
        primary = recent.get("primaryDocument", [""])[i]
        out.append(FilingRef(
            cik=cik,
            ticker=ticker,
            accession=acc,
            accession_nodash=acc_nodash,
            form=form,
            filing_date=date,
            report_date=recent.get("reportDate", [""])[i] or "",
            primary_doc=primary,
            primary_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_nodash}/{primary}",
        ))
    return out


# ---------- Fetch + cache ----------

def _dest_dir(ref: FilingRef) -> Path:
    d = RAW_DIR / ref.cik / ref.accession
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch_filing(ref: FilingRef, overwrite: bool = False) -> Path:
    """Download primary document + write meta.json. Returns path to primary doc."""
    dest = _dest_dir(ref)
    primary_path = dest / "primary.html"
    meta_path = dest / "meta.json"
    if primary_path.exists() and meta_path.exists() and not overwrite:
        return primary_path
    try:
        body = _get(ref.primary_url)
        primary_path.write_bytes(body)
        ref.size_bytes = len(body)
    except Exception as e:
        meta_path.write_text(json.dumps({**asdict(ref), "_fetch_error": str(e)}, indent=2))
        return primary_path
    meta_path.write_text(json.dumps(asdict(ref), indent=2))
    return primary_path


def fetch_all_universe(limit_per_company: int | None = None, overwrite: bool = False) -> dict:
    """Fetch every in-scope filing for every company in UNIVERSE.

    Returns summary: {ticker: {form: count}}.
    """
    summary: dict[str, dict[str, int]] = {}
    for row in UNIVERSE:
        ticker, cik = row["ticker"], row["cik"]
        print(f"\n== {ticker} (CIK {cik}) · {row['name']} ==")
        try:
            refs = list_filings_for(ticker, cik)
        except Exception as e:
            print(f"  ! listing failed: {e}")
            summary[ticker] = {"_error": 1}
            continue
        if limit_per_company:
            refs = refs[:limit_per_company]
        counts: dict[str, int] = {}
        for ref in tqdm(refs, desc=f"  {ticker}", unit="filing"):
            try:
                fetch_filing(ref, overwrite=overwrite)
                counts[ref.form] = counts.get(ref.form, 0) + 1
            except Exception as e:
                counts["_err:" + ref.form] = counts.get("_err:" + ref.form, 0) + 1
                print(f"  ! {ref.accession} {ref.form}: {e}")
        summary[ticker] = counts
        print(f"  → {sum(counts.values())} filings cached")
    return summary
