"""Interactive CLI browser for Phase 2 extracted output.

Run:
    source .venv/bin/activate
    python -m graphrag.scripts.inspect

Features:
  1. List filings by company
  2. Drill into a specific filing (summary + nodes + hidden-risk signals w/ quotes)
  3. Browse hidden-risk signals globally, sortable by severity + filter by type
  4. Search by counterparty name across all extractions
  5. Export a filing's extraction to markdown
"""

from __future__ import annotations

import json
import textwrap
from collections import defaultdict
from pathlib import Path

from graphrag.config import PARSED_DIR, UNIVERSE

EXTRACTED = Path(__file__).parent.parent / "cache" / "extracted"

# ANSI colors for terminal (fall back cleanly if not supported)
C = {"reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
     "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
     "blue": "\033[34m", "mag": "\033[35m", "cyan": "\033[36m"}

CIK_TO_TICKER = {u["cik"]: u["ticker"] for u in UNIVERSE}
CIK_TO_NAME = {u["cik"]: u["name"] for u in UNIVERSE}

SEVERITY_COLOR = {5: C["red"], 4: C["red"], 3: C["yellow"], 2: C["cyan"], 1: C["dim"]}


def _is_dict_node(n) -> bool:
    return isinstance(n, dict) and "type" in n


def _ok_nodes(result: dict) -> list:
    nodes = result.get("nodes", [])
    return [n for n in nodes if _is_dict_node(n)] if isinstance(nodes, list) else []


def _ok_edges(result: dict) -> list:
    edges = result.get("edges", [])
    return [e for e in edges if isinstance(e, dict)] if isinstance(edges, list) else []


def load_all():
    """Return {(ticker, accession): {meta, sections}}  — all extracted filings."""
    out = {}
    for ex in sorted(EXTRACTED.glob("*/*/extracted.json")):
        cik = ex.parent.parent.name
        acc = ex.parent.name
        ticker = CIK_TO_TICKER.get(cik, cik)
        meta_path = Path(f"graphrag/cache/raw/{cik}/{acc}/meta.json")
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        sections = json.loads(ex.read_text())
        out[(ticker, acc)] = {"meta": meta, "sections": sections, "cik": cik}
    return out


def _header(text: str):
    print(f"\n{C['bold']}{C['cyan']}{'═'*72}{C['reset']}")
    print(f"{C['bold']}{text}{C['reset']}")
    print(f"{C['bold']}{C['cyan']}{'═'*72}{C['reset']}\n")


def _subhead(text: str):
    print(f"\n{C['bold']}{C['blue']}── {text}{C['reset']}")


def menu_main(all_filings: dict):
    while True:
        _header("AI SIFI Monitor — Extracted Graph Browser")
        n_filings = len(all_filings)
        n_tickers = len({t for (t, _) in all_filings})
        n_signals = sum(1 for d in all_filings.values() for s in d["sections"].values()
                        for n in _ok_nodes(s) if n.get("type") == "hidden_risk_signal")
        n_edges = sum(len(_ok_edges(s)) for d in all_filings.values() for s in d["sections"].values())
        print(f"  {n_tickers} companies  ·  {n_filings} filings  ·  {n_signals:,} hidden-risk signals  ·  {n_edges:,} edges\n")
        print(f"  {C['bold']}1{C['reset']}  List filings by company")
        print(f"  {C['bold']}2{C['reset']}  View a specific filing")
        print(f"  {C['bold']}3{C['reset']}  Browse hidden-risk signals (by severity)")
        print(f"  {C['bold']}4{C['reset']}  Search by counterparty name")
        print(f"  {C['bold']}5{C['reset']}  Show circularity + revenue-roundtrip signals")
        print(f"  {C['bold']}6{C['reset']}  Export a filing to markdown")
        print(f"  {C['bold']}q{C['reset']}  Quit\n")
        choice = input(f"{C['bold']}choose › {C['reset']}").strip().lower()
        if choice == "q": return
        actions = {"1": act_list, "2": act_view_filing, "3": act_browse_signals,
                   "4": act_search, "5": act_circularity, "6": act_export}
        fn = actions.get(choice)
        if fn: fn(all_filings)


def act_list(all_filings: dict):
    _subhead("Filings by company")
    by_ticker = defaultdict(list)
    for (ticker, acc), d in all_filings.items():
        by_ticker[ticker].append((d["meta"].get("filing_date", "?"), d["meta"].get("form", "?"), acc))
    for ticker in sorted(by_ticker):
        print(f"\n  {C['bold']}{ticker}{C['reset']}  ({CIK_TO_NAME.get(next(u['cik'] for u in UNIVERSE if u['ticker']==ticker), '')})")
        for date, form, acc in sorted(by_ticker[ticker], reverse=True):
            # Count signals in this filing
            d = all_filings[(ticker, acc)]
            n_sig = sum(1 for s in d["sections"].values() for n in _ok_nodes(s) if n.get("type") == "hidden_risk_signal")
            print(f"    {date}  {form:<10} {acc}  — {n_sig} risk signals")
    input(f"\n{C['dim']}[enter to continue]{C['reset']}")


def act_view_filing(all_filings: dict):
    _subhead("View a filing")
    ticker = input(f"ticker (e.g. NVDA, META): ").strip().upper()
    matches = sorted([k for k in all_filings if k[0] == ticker], key=lambda k: all_filings[k]["meta"].get("filing_date", ""), reverse=True)
    if not matches:
        print(f"{C['red']}no filings for {ticker}{C['reset']}")
        return
    print(f"\n  {ticker} filings (most recent first):")
    for i, (_, acc) in enumerate(matches[:15], 1):
        m = all_filings[(ticker, acc)]["meta"]
        print(f"    {i:>2}  {m.get('filing_date','?'):<12} {m.get('form','?'):<10} {acc}")
    try:
        idx = int(input(f"\npick # › ").strip()) - 1
    except Exception:
        return
    if not (0 <= idx < len(matches)): return
    key = matches[idx]
    _render_filing(all_filings[key], ticker, key[1])


def _render_filing(d: dict, ticker: str, acc: str):
    meta = d["meta"]
    _header(f"{ticker}  ·  {meta.get('form')}  ·  filed {meta.get('filing_date')}")

    # Per-section summary
    print(f"{C['bold']}Sections extracted:{C['reset']}  {len(d['sections'])}\n")
    print(f"  {'section':<36}{'nodes':>7}{'edges':>7}{'signals':>9}")
    print(f"  {'-'*36}{'-'*7}{'-'*7}{'-'*9}")
    for sid, result in d["sections"].items():
        nodes = _ok_nodes(result)
        edges = _ok_edges(result)
        sigs = sum(1 for n in nodes if n.get("type") == "hidden_risk_signal")
        print(f"  {sid:<36}{len(nodes):>7}{len(edges):>7}{sigs:>9}")

    # All hidden-risk signals in this filing, sorted by severity desc
    all_sigs = []
    for sid, result in d["sections"].items():
        for n in _ok_nodes(result):
            if n.get("type") == "hidden_risk_signal":
                f = n.get("fields") if isinstance(n.get("fields"), dict) else {}
                all_sigs.append((sid, n, f))
    all_sigs.sort(key=lambda x: -int(x[2].get("severity") or 0))

    if all_sigs:
        _subhead(f"Hidden risk signals ({len(all_sigs)}) — highest severity first")
        for sid, n, f in all_sigs:
            sev = int(f.get("severity") or 0)
            color = SEVERITY_COLOR.get(sev, C["reset"])
            rtype = f.get("risk_type", "?")
            cp = f.get("named_counterparties", []) or []
            num = f.get("numeric_signal") or {}
            num_str = ""
            if isinstance(num, dict):
                if num.get("amount_usd"):
                    v = num["amount_usd"]
                    num_str = f"${v/1e9:.1f}B" if v >= 1e9 else f"${v/1e6:.0f}M"
                elif num.get("pct_of_revenue"):
                    num_str = f"{num['pct_of_revenue']*100:.0f}% of rev"
            print(f"\n  {color}[sev {sev}]{C['reset']}  {C['bold']}{rtype}{C['reset']}  "
                  f"{C['dim']}({sid}){C['reset']}  {num_str}")
            if cp:
                print(f"    counterparties: {', '.join(cp[:6])}")
            quote = (f.get("verbatim_quote") or "")[:400]
            if quote:
                for line in textwrap.wrap(quote, width=68):
                    print(f"    {C['dim']}“{line}”{C['reset']}")
    input(f"\n{C['dim']}[enter to continue]{C['reset']}")


def act_browse_signals(all_filings: dict):
    _subhead("All hidden-risk signals, filterable")
    print(f"  risk types: HIDDEN_LEVERAGE, CIRCULARITY, REVENUE_ROUNDTRIP,")
    print(f"              CAPEX_ROI_GAP, EXECUTION_RISK, COST_OPACITY,")
    print(f"              CUSTOMER_CONCENTRATION, SUPPLIER_CONCENTRATION, OTHER")
    rtype = input(f"\nfilter by risk_type (blank = all): ").strip().upper() or None
    min_sev = input(f"min severity 1-5 (blank = 3): ").strip() or "3"
    try: min_sev = int(min_sev)
    except: min_sev = 3

    results = []
    for (ticker, acc), d in all_filings.items():
        for sid, section in d["sections"].items():
            for n in _ok_nodes(section):
                if n.get("type") != "hidden_risk_signal": continue
                f = n.get("fields") if isinstance(n.get("fields"), dict) else {}
                if rtype and f.get("risk_type") != rtype: continue
                sev = int(f.get("severity") or 0)
                if sev < min_sev: continue
                results.append((ticker, acc, sid, sev, f))
    results.sort(key=lambda r: -r[3])
    print(f"\n{len(results)} signals matching\n")
    for ticker, acc, sid, sev, f in results[:40]:
        color = SEVERITY_COLOR.get(sev, "")
        q = (f.get("verbatim_quote") or "")[:140]
        print(f"  {color}[sev {sev}]{C['reset']}  {C['bold']}{ticker}{C['reset']} "
              f"{f.get('risk_type', '?'):<22} ({sid}) — {C['dim']}\"{q}...\"{C['reset']}")
    if len(results) > 40:
        print(f"\n  ... and {len(results) - 40} more")
    input(f"\n{C['dim']}[enter to continue]{C['reset']}")


def act_search(all_filings: dict):
    _subhead("Search by counterparty name (case-insensitive substring)")
    needle = input("counterparty: ").strip().lower()
    if not needle: return
    hits = []
    for (ticker, acc), d in all_filings.items():
        for sid, section in d["sections"].items():
            for n in _ok_nodes(section):
                if n.get("type") != "hidden_risk_signal": continue
                f = n.get("fields") if isinstance(n.get("fields"), dict) else {}
                cps = [str(c).lower() for c in (f.get("named_counterparties") or [])]
                if any(needle in c for c in cps):
                    hits.append((ticker, acc, sid, int(f.get("severity") or 0), f))
    hits.sort(key=lambda r: -r[3])
    print(f"\n{len(hits)} signals naming '{needle}'\n")
    for ticker, acc, sid, sev, f in hits[:30]:
        color = SEVERITY_COLOR.get(sev, "")
        q = (f.get("verbatim_quote") or "")[:160]
        print(f"  {color}[sev {sev}]{C['reset']}  {C['bold']}{ticker}{C['reset']} "
              f"{f.get('risk_type', '?'):<22}")
        print(f"    cps: {', '.join(f.get('named_counterparties') or [])[:80]}")
        print(f"    {C['dim']}\"{q}...\"{C['reset']}\n")
    input(f"{C['dim']}[enter to continue]{C['reset']}")


def act_circularity(all_filings: dict):
    _subhead("CIRCULARITY and REVENUE_ROUNDTRIP signals — the SIFI core")
    for target in ("CIRCULARITY", "REVENUE_ROUNDTRIP"):
        print(f"\n{C['bold']}{C['red']}{target}{C['reset']}")
        count = 0
        for (ticker, acc), d in all_filings.items():
            for sid, section in d["sections"].items():
                for n in _ok_nodes(section):
                    if n.get("type") != "hidden_risk_signal": continue
                    f = n.get("fields") if isinstance(n.get("fields"), dict) else {}
                    if f.get("risk_type") != target: continue
                    sev = int(f.get("severity") or 0)
                    if sev < 3: continue
                    count += 1
                    if count > 20: continue
                    cps = f.get("named_counterparties") or []
                    q = (f.get("verbatim_quote") or "")[:200]
                    print(f"\n  {SEVERITY_COLOR.get(sev, '')}[sev {sev}]{C['reset']} "
                          f"{C['bold']}{ticker}{C['reset']}  cps={cps[:5]}")
                    print(f"    {C['dim']}\"{q}...\"{C['reset']}")
        if count > 20:
            print(f"\n  ... +{count - 20} more {target} signals")
    input(f"\n{C['dim']}[enter to continue]{C['reset']}")


def act_export(all_filings: dict):
    _subhead("Export a filing to markdown")
    ticker = input("ticker: ").strip().upper()
    matches = sorted([k for k in all_filings if k[0] == ticker],
                     key=lambda k: all_filings[k]["meta"].get("filing_date", ""), reverse=True)
    if not matches:
        print(f"{C['red']}no filings{C['reset']}")
        return
    for i, (_, acc) in enumerate(matches[:10], 1):
        m = all_filings[(ticker, acc)]["meta"]
        print(f"  {i}  {m.get('filing_date')} {m.get('form')}  {acc}")
    idx = int(input("pick # › ").strip()) - 1
    key = matches[idx]
    d = all_filings[key]
    out_path = Path(f"graphrag/cache/{ticker}_{key[1]}.md")
    with out_path.open("w") as fh:
        fh.write(f"# {ticker} · {d['meta'].get('form')} · {d['meta'].get('filing_date')}\n\n")
        for sid, section in d["sections"].items():
            fh.write(f"\n## {sid}\n\n")
            for n in _ok_nodes(section):
                if n.get("type") == "hidden_risk_signal":
                    f = n.get("fields") if isinstance(n.get("fields"), dict) else {}
                    fh.write(f"- **[sev {f.get('severity')}] {f.get('risk_type')}** — "
                             f"cps: {f.get('named_counterparties')} — "
                             f"\"{(f.get('verbatim_quote') or '')[:400]}\"\n")
    print(f"{C['green']}wrote {out_path}{C['reset']}")
    input(f"\n{C['dim']}[enter to continue]{C['reset']}")


if __name__ == "__main__":
    all_filings = load_all()
    try:
        menu_main(all_filings)
    except (KeyboardInterrupt, EOFError):
        print()
