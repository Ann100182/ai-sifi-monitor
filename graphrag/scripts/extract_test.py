"""Phase 2 test — extract ONE filing (NVDA FY2026 10-K) to validate quality.

Expected cost: ~$0.20-0.40. Run:
    source .venv/bin/activate
    python -m graphrag.scripts.extract_test
"""

from __future__ import annotations

import json
import os
from collections import Counter

from anthropic import Anthropic
from dotenv import load_dotenv

from graphrag.config import HERE
from graphrag.extract import ExtractionStats, extract_filing

load_dotenv(HERE / ".env")

# NVDA FY2026 10-K
CIK = "0001045810"
ACCESSION = "0001045810-26-000021"


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in graphrag/.env")
        print("   Run the key-setup command first.")
        return
    print(f"✓ API key loaded (starts with {api_key[:12]}...)")

    client = Anthropic(api_key=api_key)
    stats = ExtractionStats()
    print(f"\nExtracting NVDA FY2026 10-K (cik={CIK}, accession={ACCESSION})...\n")

    by_section = extract_filing(client, CIK, ACCESSION, stats)

    # Summarize
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Sections processed:    {stats.sections_processed}")
    print(f"Sections skipped:      {stats.sections_skipped}")
    print(f"API calls:             {stats.api_calls}")
    print(f"Input tokens (fresh):  {stats.uncached_input_tokens:,}")
    print(f"Cache creation tokens: {stats.cache_creation_tokens:,}  (1.25x price)")
    print(f"Cache read tokens:     {stats.cache_read_tokens:,}  (0.10x price)")
    print(f"Cache hit rate:        {stats.cache_hit_rate()*100:.1f}%")
    print(f"Output tokens:         {stats.output_tokens:,}")
    print(f"Est. cost:             ${stats.est_cost_usd():.4f}")
    print(f"Errors:                {stats.errors}")

    # Node type counts across the whole filing
    node_types = Counter()
    edge_predicates = Counter()
    hidden_risks = Counter()
    for section_id, result in by_section.items():
        for n in result.get("nodes", []):
            node_types[n.get("type", "?")] += 1
            if n.get("type") == "hidden_risk_signal":
                rtype = n.get("fields", {}).get("risk_type", "UNKNOWN")
                hidden_risks[rtype] += 1
        for e in result.get("edges", []):
            edge_predicates[e.get("predicate", "?")] += 1

    print(f"\n--- NODE TYPES ---")
    for t, n in node_types.most_common():
        print(f"  {t:<24} {n}")
    print(f"\n--- EDGE PREDICATES ---")
    for p, n in edge_predicates.most_common():
        print(f"  {p:<24} {n}")
    print(f"\n--- HIDDEN RISK SIGNALS BY TYPE ---")
    for t, n in hidden_risks.most_common():
        print(f"  {t:<28} {n}")

    # Show 3 examples of hidden_risk_signal with verbatim quotes
    print(f"\n--- HIDDEN RISK SIGNAL EXAMPLES ---\n")
    shown = 0
    for section_id, result in by_section.items():
        for n in result.get("nodes", []):
            if n.get("type") == "hidden_risk_signal" and shown < 3:
                shown += 1
                f = n.get("fields", {})
                print(f"[{shown}] Section: {section_id}")
                print(f"    risk_type:  {f.get('risk_type')}")
                print(f"    severity:   {f.get('severity')}")
                print(f"    counterparties: {f.get('named_counterparties')}")
                num = f.get("numeric_signal") or {}
                if num:
                    print(f"    numeric_signal: {num}")
                quote = (f.get("verbatim_quote") or "")[:400]
                print(f"    verbatim:   {quote!r}")
                print()


if __name__ == "__main__":
    main()
