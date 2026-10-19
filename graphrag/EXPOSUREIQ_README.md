![ExposureIQ — See beyond the balance sheet](../assets/exposureiq_banner.png)

# ExposureIQ — GraphRAG over SEC filings

ExposureIQ is the 5th tab of the AI SIFI Monitor. It answers natural-language questions about **hidden exposures in the AI compute buildout** using a knowledge graph and vector index built from the SEC filings of 12 cloud and AI-infrastructure companies.

Balance sheets don't show the risks this project tracks. Those risks sit in the notes, risk factors and MD&A: off-balance-sheet SPVs, investor ⇄ customer ⇄ supplier loops, equity that comes back as revenue, and multi-year capex commitments without matched revenue. ExposureIQ pulls these out as structured facts and lets you query them with verbatim citations.

> **Example:** *"Trace the OpenAI counterparty web across Microsoft, Oracle, and CoreWeave."*
> The answer traces Microsoft's $13B equity-method stake and unconsolidated VIE, the $250B Azure commitment flowing back, CoreWeave's OpenAI contracts and its SPV debt secured by an OpenAI lien. Oracle never names OpenAI in its filings, so the answer cites Oracle's backlog jump (RPO $138B → $638B in FY26) and labels the link explicitly as *inference, not disclosed*.

---

## Coverage

| | |
|---|---|
| **Companies (12)** | MSFT, AMZN, GOOGL, ORCL, META, IBM, CRM, ADBE, NVDA, ASML, CRWV, AVGO |
| **Forms** | 10-K, 10-Q, 20-F, DEF 14A, ARS |
| **Period** | Fiscal 2024 – 2026 |
| **Filings indexed** | 147 |
| **Knowledge graph** | ~4,100 nodes · ~3,600 edges · ~1,600 unique hidden-risk signals |
| **Vector index** | ~22,000 filing chunks |

**Hidden-risk signal types:** `HIDDEN_LEVERAGE`, `CIRCULARITY`, `REVENUE_ROUNDTRIP`, `CAPEX_ROI_GAP`, `EXECUTION_RISK`, `COST_OPACITY`, `CUSTOMER_CONCENTRATION`, `SUPPLIER_CONCENTRATION`. Each signal has a 1–5 severity score, where 5 means the risk could trigger a cascade.

---

## How a question is answered

The query engine is a [LangGraph](https://github.com/langchain-ai/langgraph) state machine (`graphrag/query.py`):

```
START → classify ─┬─► graph_search  ─┐
                  │   (Cypher/Kuzu)  ├─► synthesize → END
                  └─► vector_search ─┘
                      (Chroma)
```

| Step | What it does | Model |
|---|---|---|
| **classify** | Picks a strategy: `GRAPH` (relationships and extracted facts), `VECTOR` (narrative) or `HYBRID`. Also rates complexity (`SIMPLE` or `MULTIHOP`) and names the filing sections likely to hold the answer: MD&A, risk factors, notes, business or governance. | Claude Sonnet 4.6 |
| **graph_search** | Writes 1–3 Cypher queries and runs them on Kuzu. If a query fails, the error goes back to the model for one repair attempt. Each row is traced to its source filing (ticker · form · date). | Claude Sonnet 4.6 |
| **vector_search** | Embeds the question locally (`BAAI/bge-small-en-v1.5`) and searches Chroma, filtered to the companies named in the question. Half the budget is restricted to the sections the classifier chose, mapped across forms (MD&A is `item_7` in a 10-K, `part1_item2` in a 10-Q, `item_5` in a 20-F), so proxy boilerplate can't crowd out the answer. Multi-hop questions also pull each company's latest backlog (RPO) figures, so commitments without a named counterparty can still be cited. | Local, no API cost |
| **synthesize** | Writes a cited answer (`[E1]`, `[E2]`…) using only the retrieved evidence. It flags hidden-risk patterns, says "insufficient evidence" instead of guessing, and labels inferred links as inference. | Sonnet 4.6, or **Opus 4.7** for `MULTIHOP` |

Multi-hop questions always run both retrievers **in parallel**, because the graph often covers some of the entities but not all of them.

**Typical cost and latency:** about $0.02 and 15 s for a simple question; $0.06–$0.18 and 25–40 s for a multi-hop one. The tab shows the cost of every LLM call.

---

## The tab

- **Starter questions:** one click runs the question.
- **Answer:** markdown with numbered evidence citations.
- **Metrics:** strategy, complexity, evidence count, total cost and latency, plus the LangGraph path the question took.
- **Pipeline trace:** every LLM call with its model, tokens, cost and duration.
- **Evidence panel:** graph facts (with the Cypher that produced them and every filing that supports them) and filing excerpts (ticker · form · date · section · similarity).

---

## How the data is built

```
EDGAR ──fetch──► raw HTML ──parse──► sections ──extract (Claude)──► nodes + edges ─┬─► Kuzu graph
                                         └──────────── embed (bge-small) ─────────┴─► Chroma index
```

| Stage | File | Notes |
|---|---|---|
| Fetch | `fetch.py` | SEC EDGAR, rate-limited below 10 requests/s |
| Parse | `parse.py` | Splits filings into Item 1A, Item 7 / MD&A, financial statements and notes, related-party and compensation sections |
| Extract | `extract.py`, `prompts.py`, `schemas.py` | Section-aware routing: Sonnet 4.6 for risk-critical sections, Haiku 4.5 for the rest. One-time cost about $35. |
| Canonicalize | `canonicalize.py` | Resolves name variants ("AWS" → Amazon, "Facebook" → Meta) |
| Graph load | `graph_load.py` | 7 node tables and 13 edge tables in Kuzu; drops nodes with no verbatim quote |
| Vector load | `vector_load.py` | Section chunks embedded locally into Chroma |

**Graph schema:** `Company`, `AILab` (OpenAI, Anthropic, xAI, Mistral, Cohere, Perplexity, Databricks), `CapexCommitment`, `OffBalanceEntity`, `Investment`, `RiskFactor`, `HiddenRiskSignal`. Edge types include `SELLS_COMPUTE_TO`, `INVESTED_IN`, `SPONSORS`, `CIRCULAR_WITH`, `ROUND_TRIPS_WITH`, `HAS_RISK_SIGNAL`, `NAMES_COUNTERPARTY`, `DEPENDS_ON` and more. Every node keeps its provenance (`cik:accession`) and verbatim quote.

---

## Running it

### Quick start (about 15 minutes, no extraction cost)

The repo includes the parsed filing sections (`graphrag/cache/parsed/`) and the Claude-extracted graph data (`graphrag/cache/extracted/`). You only build the local graph and search indexes from them.

```bash
git clone https://github.com/Ann100182/ai-sifi-monitor.git && cd ai-sifi-monitor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install anthropic langgraph kuzu chromadb sentence-transformers python-dotenv

echo "ANTHROPIC_API_KEY=sk-ant-..." > graphrag/.env

# Build the Kuzu graph and Chroma index locally (no API calls, about 15 minutes)
python -m graphrag.scripts.phase3_build
```

Then ask questions from the command line or in the app:

```bash
python -m graphrag.scripts.ask "Which SPVs does Meta sponsor?"
streamlit run app.py        # → ExposureIQ tab
```

The only key you need is `ANTHROPIC_API_KEY`, used at query time (about $0.02–$0.18 per question). Embeddings run locally. The first run downloads the ~130 MB `bge-small` embedding model.

### Full rebuild from EDGAR (optional)

To refresh the corpus or change the universe, re-run the whole pipeline:

```bash
pip install requests beautifulsoup4 lxml tqdm pydantic

# 1. Fetch and parse filings (no LLM cost, about 650 MB download)
python -c "from graphrag.fetch import fetch_all_universe; fetch_all_universe()"
python -c "from graphrag.parse import parse_all; parse_all()"

# 2. Extract the graph with Claude (about $35, several hours)
python -m graphrag.scripts.extract_all

# 3. Rebuild the indexes
python -m graphrag.scripts.phase3_build
```

---

## Evaluation

ExposureIQ is measured on a 26-question set (`graphrag/eval/questions.jsonl`): 8 graph, 11 text, 6 multi-hop and 1 out-of-scope question. Claude Opus 4.7 grades each answer:

- **Faithfulness:** the answer is split into individual factual claims, and each is checked against the evidence the pipeline retrieved. *Strict* counts only fully supported claims; *lenient* gives half credit to claims with a minor detail off.
- **Relevance:** a 1–5 rating of whether the answer addresses the question. The table reports the share scoring 4 or 5.

| Configuration | Claims | Faithfulness (strict) | Faithfulness (lenient) | Relevance (≥4/5) | Mean relevance |
|---|---|---|---|---|---|
| Original | 483 | 93.2% | 95.7% | 100% | 4.73 |
| + Grounding-only answer prompt | 482 | 97.1% | 98.1% | 92% | 4.65 |
| **+ Section-aware retrieval (current)** | **520** | **96.9%** | **98.0%** | **100%** | **4.81** |

What changed between runs:

1. **Grounding-only prompt.** Most early failures were the model adding outside knowledge. Forbidding it raised faithfulness, but exposed retrieval gaps: two questions now said "insufficient evidence" where the model used to fill in from memory.
2. **Section-aware retrieval** closed those gaps. "Meta's capex outlook" went from proxy compensation tables to four MD&A passages with explicit guidance.

The grader was audited by hand. Every figure in a "supported" claim was traced to the evidence, and every "unsupported" verdict was read. The grader leans slightly strict: in the current run, 2 of its 5 unsupported claims are true statements about which companies are covered.

Run it yourself (about 11 minutes, ~$4):

```bash
python -m graphrag.eval.run_eval            # writes graphrag/eval/results/eval_<timestamp>*.{jsonl,md}
```

**Caveats:** one run per configuration, 26 questions, and a judge from the same model family as the generator. Treat the numbers as indicative, not a benchmark.

---

## Limitations

- **Extraction can be wrong.** Graph facts come from LLM extraction over long filings. The answer-writing step is told to trust filing text over graph facts when they conflict, but answers still need a human read. For example, it can add up concentration percentages that don't add up.
- **Filings only.** Relationships a company doesn't disclose by name (for example, Oracle ↔ OpenAI) appear only as inference from aggregate figures.
- **Some relationships are dropped.** About 700 extracted edges don't fit the current schema's allowed entity-type pairs and are skipped at load.
- **The data is a snapshot.** The corpus is fixed at build time; re-run the pipeline to pick up new filings.

## Roadmap

- News-backed evidence for relationships the filings don't disclose, kept as a separate, clearly labelled evidence source
- A wider edge schema to recover the dropped relationships
- 8-K / 6-K / S-1 coverage
- An evaluation set for answer and citation accuracy
