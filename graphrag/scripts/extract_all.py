"""Full Phase 2 extraction run.

Processes every parsed filing with hybrid Haiku/Sonnet routing.
Expected: ~15-20 min runtime, ~$18-25 total cost.

Run:
    source .venv/bin/activate
    python -m graphrag.scripts.extract_all
"""

from __future__ import annotations

import os
import time
from collections import Counter

from graphrag.config import HERE
from graphrag.extract import EXTRACTED_DIR, extract_all

from dotenv import load_dotenv
load_dotenv(HERE / ".env")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ ANTHROPIC_API_KEY not set"); return
    print(f"✓ API key loaded")

    t0 = time.time()
    stats = extract_all()
    dt = time.time() - t0

    print(f"\n{'='*70}")
    print(f"FULL EXTRACTION COMPLETE in {dt/60:.1f} min")
    print(f"{'='*70}")
    print(stats.summary())
    print()

    # Scan extracted dir and tally node/edge counts
    import json
    from pathlib import Path
    node_types, edge_preds, hidden_risks = Counter(), Counter(), Counter()
    file_count = 0
    for ex in EXTRACTED_DIR.glob("*/*/extracted.json"):
        file_count += 1
        data = json.loads(ex.read_text())
        for sid, result in data.items():
            for n in result.get("nodes", []):
                node_types[n.get("type", "?")] += 1
                if n.get("type") == "hidden_risk_signal":
                    rt = n.get("fields", {}).get("risk_type", "UNKNOWN")
                    hidden_risks[rt] += 1
            for e in result.get("edges", []):
                edge_preds[e.get("predicate", "?")] += 1

    print(f"Extracted artifact files: {file_count}")
    print(f"\n--- NODE TYPES ---")
    for t, n in node_types.most_common():
        print(f"  {t:<22} {n}")
    print(f"\n--- EDGE PREDICATES ---")
    for p, n in edge_preds.most_common():
        print(f"  {p:<22} {n}")
    print(f"\n--- HIDDEN RISK SIGNALS BY TYPE ---")
    for t, n in hidden_risks.most_common():
        print(f"  {t:<26} {n}")


if __name__ == "__main__":
    main()
