"""Phase 3 — build Kuzu graph + Chroma vector index.

Run:
    source .venv/bin/activate
    python -m graphrag.scripts.phase3_build

~5-15 min: canonicalization + graph load fast, embeddings dominate.
"""

from __future__ import annotations

import time

from graphrag.graph_load import load_all as load_graph
from graphrag.vector_load import load_all as load_vectors


def main():
    print("━" * 60)
    print("  PHASE 3 — Load Kuzu graph + Chroma vector index")
    print("━" * 60)

    t0 = time.time()
    print("\n[1/2] Graph (Kuzu)")
    print("─" * 60)
    load_graph()

    print("\n[2/2] Vector embeddings (Chroma + bge-small)")
    print("─" * 60)
    load_vectors()

    dt = time.time() - t0
    print(f"\n✓ Phase 3 complete in {dt/60:.1f} min")


if __name__ == "__main__":
    main()
