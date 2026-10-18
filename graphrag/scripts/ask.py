"""Simple CLI to test the Phase 4 query engine.

Run:
    source .venv/bin/activate
    python -m graphrag.scripts.ask "trace the OpenAI counterparty web"
    python -m graphrag.scripts.ask "which SPVs does Meta sponsor"
    python -m graphrag.scripts.ask "what does Oracle say about OpenAI concentration"
"""

from __future__ import annotations
import sys

from graphrag.query import answer


def main():
    if len(sys.argv) < 2:
        print("usage: python -m graphrag.scripts.ask \"your question\"")
        return
    q = " ".join(sys.argv[1:])
    print(f"\nQ: {q}\n")
    print("─" * 70)
    r = answer(q, verbose=True)
    print(f"─" * 70)
    print(f"\n{r.answer}\n")
    print(f"─" * 70)
    print(f"strategy: {r.strategy}/{r.complexity}  ·  model: {r.model_used}  ·  "
          f"cost: ${r.cost_usd:.4f}  ·  evidence chunks: {len(r.evidence)}  ·  {r.seconds:.1f}s")
    for c in r.calls:
        print(f"  {c.step:13} {c.model:18} in={c.input_tokens:6} out={c.output_tokens:5} "
              f"${c.cost_usd:.4f}  {c.seconds:.1f}s")
    print()


if __name__ == "__main__":
    main()
