"""ExposureIQ evaluation — faithfulness and relevance, graded by Claude.

For each question in questions.jsonl:
  1. Run the full LangGraph pipeline (graphrag.query.answer).
  2. A judge model splits the answer into factual claims and checks each one
     against the evidence the pipeline retrieved:
        SUPPORTED   — evidence states or directly entails it
        PARTIAL     — mostly supported, but a figure/detail is off or overstated
        UNSUPPORTED — not in the evidence, or contradicted by it
     and rates relevance 1-5 (does the answer address the question?).

Metrics:
  faithfulness (strict)  = SUPPORTED / all claims
  faithfulness (lenient) = (SUPPORTED + 0.5 * PARTIAL) / all claims
  relevance              = % of answers rated >= 4, plus mean score

Run:
    source .venv/bin/activate
    python -m graphrag.eval.run_eval              # all questions
    python -m graphrag.eval.run_eval --limit 3    # smoke test
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from graphrag.query import PRICING, _anthropic, _format_evidence, answer

HERE = Path(__file__).parent
QUESTIONS = HERE / "questions.jsonl"
RESULTS = HERE / "results"

JUDGE_MODEL = "claude-opus-4-7"

JUDGE_SYSTEM = """You are a strict evaluator of retrieval-augmented answers about SEC filings.
You judge ONLY against the evidence provided — not against your own knowledge of the companies."""

JUDGE_PROMPT = """QUESTION:
{question}

EVIDENCE (what the system retrieved; the answer cites these as [E#]):
{evidence}

ANSWER:
{answer}

Tasks:

1. Extract every factual claim in the ANSWER: figures, dates, entities, relationships, and
   characterizations attributed to the filings. Split compound sentences into atomic claims.
   Do NOT extract: headings, statements that evidence is missing or insufficient, generic
   framing, or recommendations.
   For claims the answer explicitly labels as inference, judge whether the facts the inference
   rests on are supported; if they are and the label is present, mark the claim SUPPORTED.
   Claims the answer explicitly flags as coming from outside the evidence ("general knowledge")
   are still UNSUPPORTED.

2. Give each claim a verdict:
   SUPPORTED   — the evidence states it or directly entails it
   PARTIAL     — mostly supported, but a number, date or detail is off or overstated
   UNSUPPORTED — not in the evidence, or contradicted by it

3. Rate RELEVANCE 1-5: does the answer address the question that was asked?
   5 = fully answers it; 4 = answers it with minor gaps; 3 = partially; 2 = mostly off-target;
   1 = does not address it. If the evidence genuinely lacks the answer, a clear
   "insufficient evidence" response that explains what is missing scores 4.

Return ONLY a JSON object, no prose:
{{"claims": [{{"claim": "...", "verdict": "SUPPORTED|PARTIAL|UNSUPPORTED", "evidence": "E3", "note": "short reason if not SUPPORTED"}}],
  "relevance": 1-5, "relevance_reason": "one sentence"}}"""


def judge(question: str, evidence_text: str, answer_text: str) -> tuple[dict, float]:
    prompt = JUDGE_PROMPT.format(question=question, evidence=evidence_text, answer=answer_text)
    last_err = None
    for _ in range(2):
        msg = _anthropic().messages.create(
            model=JUDGE_MODEL, max_tokens=8000, system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        pin, pout = PRICING[JUDGE_MODEL]
        cost = (msg.usage.input_tokens * pin + msg.usage.output_tokens * pout) / 1_000_000
        text = "".join(b.text for b in msg.content if b.type == "text")
        m = re.search(r"\{.*\}", text, re.S)
        try:
            return json.loads(m.group(0)), cost
        except Exception as e:
            last_err = e
    raise RuntimeError(f"judge returned unparseable JSON: {last_err}")


def score(verdict: dict) -> dict:
    claims = verdict.get("claims", [])
    n = len(claims)
    s = sum(c.get("verdict") == "SUPPORTED" for c in claims)
    p = sum(c.get("verdict") == "PARTIAL" for c in claims)
    u = sum(c.get("verdict") == "UNSUPPORTED" for c in claims)
    return {"claims": n, "supported": s, "partial": p, "unsupported": u,
            "relevance": int(verdict.get("relevance", 0))}


def summarize(rows: list[dict]) -> str:
    def agg(rs):
        n = sum(r["score"]["claims"] for r in rs)
        s = sum(r["score"]["supported"] for r in rs)
        p = sum(r["score"]["partial"] for r in rs)
        rel = [r["score"]["relevance"] for r in rs]
        return {
            "questions": len(rs), "claims": n,
            "faith_strict": s / n if n else 0.0,
            "faith_lenient": (s + 0.5 * p) / n if n else 0.0,
            "rel_pct": sum(x >= 4 for x in rel) / len(rel) if rel else 0.0,
            "rel_mean": sum(rel) / len(rel) if rel else 0.0,
        }

    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    lines = ["| Slice | Questions | Claims | Faithfulness (strict) | Faithfulness (lenient) | "
             "Relevance (≥4/5) | Mean relevance |",
             "|---|---|---|---|---|---|---|"]
    for name, rs in [("**All**", rows)] + sorted(by_cat.items()):
        a = agg(rs)
        lines.append(f"| {name} | {a['questions']} | {a['claims']} | {a['faith_strict']:.1%} | "
                     f"{a['faith_lenient']:.1%} | {a['rel_pct']:.0%} | {a['rel_mean']:.2f} |")

    cost_ans = sum(r["answer_cost"] for r in rows)
    cost_judge = sum(r["judge_cost"] for r in rows)
    lines += ["", f"Answer cost ${cost_ans:.2f} · judge cost ${cost_judge:.2f} · "
                  f"judge model {JUDGE_MODEL}", "", "Per question:", "",
              "| id | category | claims | supported | partial | unsupported | relevance |",
              "|---|---|---|---|---|---|---|"]
    for r in rows:
        sc = r["score"]
        lines.append(f"| {r['id']} | {r['category']} | {sc['claims']} | {sc['supported']} | "
                     f"{sc['partial']} | {sc['unsupported']} | {sc['relevance']} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    qs = [json.loads(l) for l in QUESTIONS.read_text().splitlines() if l.strip()]
    if args.limit:
        qs = qs[:args.limit]

    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_jsonl = RESULTS / f"eval_{stamp}.jsonl"

    rows: list[dict] = []
    pool = ThreadPoolExecutor(max_workers=4)
    pending = []
    t0 = time.time()
    # Answers run sequentially (shared Kuzu connection); judging runs in parallel.
    for i, q in enumerate(qs, 1):
        try:
            res = answer(q["question"])
        except Exception as e:
            print(f"[{i}/{len(qs)}] {q['id']} ANSWER FAILED: {e}")
            continue
        ev = _format_evidence(res.evidence)
        print(f"[{i}/{len(qs)}] {q['id']} answered ({res.strategy}/{res.complexity}, "
              f"${res.cost_usd:.3f}, {res.seconds:.0f}s)")
        pending.append((q, res, ev, pool.submit(judge, q["question"], ev, res.answer)))

    for q, res, ev, fut in pending:
        try:
            verdict, jcost = fut.result()
        except Exception as e:
            print(f"{q['id']} JUDGE FAILED: {e}")
            continue
        row = {**q, "strategy": res.strategy, "complexity": res.complexity,
               "model": res.model_used, "answer": res.answer, "evidence": ev,
               "verdict": verdict, "score": score(verdict),
               "answer_cost": res.cost_usd, "judge_cost": jcost}
        rows.append(row)
        with out_jsonl.open("a") as fh:
            fh.write(json.dumps(row) + "\n")

    summary = summarize(rows)
    (RESULTS / f"eval_{stamp}_summary.md").write_text(
        f"# ExposureIQ eval — {stamp}\n\n{summary}\n")
    print("\n" + summary)
    print(f"\n{len(rows)} questions in {(time.time() - t0) / 60:.1f} min → {out_jsonl}")


if __name__ == "__main__":
    main()
