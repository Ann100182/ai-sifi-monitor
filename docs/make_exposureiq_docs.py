"""Generate the ExposureIQ Word documents.

    docs/ExposureIQ_Architecture.docx   — stack + architecture write-up
    docs/ExposureIQ_Demo_Script.docx    — 3-minute demo script
    docs/exposureiq_architecture.png    — architecture diagram (embedded in the first)

Run:
    source .venv/bin/activate
    pip install python-docx matplotlib
    python docs/make_exposureiq_docs.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

HERE = Path(__file__).parent
ROOT = HERE.parent
BANNER = ROOT / "assets" / "exposureiq_banner.png"
DIAGRAM = HERE / "exposureiq_architecture.png"

NAVY = "#0F1B2D"
SLATE = "#334155"
GOLD = "#C9A46A"
TEAL = "#2B6F7E"
LIGHT = "#F1F5F9"

NAVY_RGB = RGBColor(0x0F, 0x1B, 0x2D)
GREY_RGB = RGBColor(0x64, 0x74, 0x8B)


# ---------------------------------------------------------------- diagram

def draw_architecture(path: Path):
    fig, ax = plt.subplots(figsize=(13, 6.6), dpi=200)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6.6)
    ax.axis("off")

    def box(x, y, w, h, title, sub="", fc=NAVY, tc="white"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=fc, ec="none"))
        ax.text(x + w / 2, y + h * (0.62 if sub else 0.5), title, ha="center", va="center",
                color=tc, fontsize=10.5, fontweight="bold")
        if sub:
            ax.text(x + w / 2, y + h * 0.3, sub, ha="center", va="center",
                    color=tc, fontsize=7.8, alpha=0.9)

    def arrow(x1, y1, x2, y2, color=SLATE):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13,
                                     color=color, lw=1.4, shrinkA=2, shrinkB=2))

    def band(y, h, label):
        ax.add_patch(FancyBboxPatch((0.1, y), 12.8, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                    fc=LIGHT, ec="none"))
        ax.text(0.3, y + h - 0.22, label, ha="left", va="center", color=SLATE,
                fontsize=9, fontweight="bold")

    # ---- Build-time band
    band(3.55, 2.9, "BUILD TIME  ·  one-off, ~15 h, ~\\$35")
    y, h, w = 4.15, 1.0, 1.75
    xs = [0.35, 2.35, 4.35, 6.35, 8.35]
    box(xs[0], y, w, h, "SEC EDGAR", "147 filings · 12 filers\n10-K/10-Q/20-F/DEF 14A", fc=SLATE)
    box(xs[1], y, w, h, "Fetch + Parse", "fetch.py · parse.py\nItem 1A, MD&A, Notes …")
    box(xs[2], y, w, h, "Extract", "Claude Sonnet 4.6 +\nHaiku 4.5 → JSON", fc=GOLD, tc=NAVY)
    box(xs[3], y, w, h, "Canonicalize", "aliases → names\ndrop unquoted nodes")
    for a, b in zip(xs[:3], xs[1:4]):
        arrow(a + w, y + h / 2, b, y + h / 2)

    # stores
    box(10.5, 4.85, 2.2, 0.95, "Kuzu graph", "4,084 nodes · 3,583 edges", fc=TEAL)
    box(10.5, 3.75, 2.2, 0.95, "Chroma index", "25,090 chunks · bge-small", fc=TEAL)
    arrow(xs[3] + w, y + h / 2 + 0.15, 10.5, 5.32)
    # parsed sections → embeddings (local)
    ax.add_patch(FancyArrowPatch((xs[1] + w / 2, y), (10.5, 4.2), arrowstyle="-|>",
                                 mutation_scale=13, color=SLATE, lw=1.2, ls="--",
                                 connectionstyle="arc3,rad=0.18", shrinkA=2, shrinkB=2))
    ax.text(6.2, 3.93, "sections embedded locally (sentence-transformers, no API)",
            ha="center", va="center", fontsize=7.6, color=SLATE, style="italic")

    # ---- Query-time band
    band(0.15, 3.1, "QUERY TIME  ·  LangGraph state machine, ~\\$0.02–\\$0.13 / question")
    qy, qh = 1.0, 1.0
    box(0.35, qy, 1.75, qh, "Question", "Streamlit\nExposureIQ tab", fc=SLATE)
    box(2.5, qy, 1.85, qh, "classify", "GRAPH · VECTOR · HYBRID\nSIMPLE · MULTIHOP", fc=GOLD, tc=NAVY)
    box(4.85, 1.75, 2.1, 0.95, "graph_search", "LLM → Cypher → Kuzu\n+1 self-repair round", fc=GOLD, tc=NAVY)
    box(4.85, 0.35, 2.1, 0.95, "vector_search", "ticker-filtered Chroma\n+ backlog (RPO) probe")
    box(7.55, qy, 2.1, qh, "synthesize", "Sonnet 4.6 · Opus 4.7\nfor MULTIHOP", fc=GOLD, tc=NAVY)
    box(10.2, qy, 2.5, qh, "Cited answer", "[E1]… evidence · Cypher\ncost + pipeline trace", fc=SLATE)
    arrow(2.1, qy + qh / 2, 2.5, qy + qh / 2)
    arrow(4.35, qy + qh / 2 + 0.15, 4.85, 2.2)
    arrow(4.35, qy + qh / 2 - 0.15, 4.85, 0.85)
    arrow(6.95, 2.2, 7.55, qy + qh / 2 + 0.15)
    arrow(6.95, 0.85, 7.55, qy + qh / 2 - 0.15)
    arrow(9.65, qy + qh / 2, 10.2, qy + qh / 2)
    ax.text(5.9, 1.52, "parallel when hybrid / multihop", ha="center", va="center",
            fontsize=7.4, color=SLATE, style="italic")


    # legend
    for i, (c, lbl) in enumerate([(GOLD, "Claude call"), (NAVY, "local code"),
                                  (TEAL, "data store"), (SLATE, "input / output")]):
        ax.add_patch(FancyBboxPatch((7.9 + i * 1.25, 6.38), 0.18, 0.14,
                                    boxstyle="round,pad=0.01", fc=c, ec="none"))
        ax.text(8.13 + i * 1.25, 6.45, lbl, va="center", fontsize=7.6, color=SLATE)

    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- docx helpers

def base_document() -> Document:
    doc = Document()
    sec = doc.sections[0]
    sec.left_margin = sec.right_margin = Inches(0.9)
    sec.top_margin = sec.bottom_margin = Inches(0.8)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        st = doc.styles[name]
        st.font.name = "Calibri"
        st.font.size = Pt(size)
        st.font.color.rgb = NAVY_RGB
    return doc


def shade(cell, hex_fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def table(doc, header: list[str], rows: list[list[str]], widths: list[float] | None = None):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        r.font.size = Pt(9.5)
        shade(c, "0F1B2D")
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            # **bold** prefix support: "**Label** rest"
            if val.startswith("**") and "**" in val[2:]:
                end = val.index("**", 2)
                p.add_run(val[2:end]).bold = True
                p.add_run(val[end + 2:])
            else:
                p.add_run(val)
            for r in p.runs:
                r.font.size = Pt(9.5)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return t


def bullets(doc, items: list[str]):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        if it.startswith("**") and "**" in it[2:]:
            end = it.index("**", 2)
            p.add_run(it[2:end]).bold = True
            p.add_run(it[end + 2:])
        else:
            p.add_run(it)


def para(doc, text: str, italic=False, color=None, size=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = italic
    if color:
        r.font.color.rgb = color
    if size:
        r.font.size = Pt(size)
    return p


# ---------------------------------------------------------------- architecture doc

def build_architecture_doc(path: Path):
    doc = base_document()
    if BANNER.exists():
        doc.add_picture(str(BANNER), width=Inches(6.7))

    title = doc.add_heading("ExposureIQ — Stack and Architecture", level=0)
    title.runs[0].font.color.rgb = NAVY_RGB
    para(doc, "GraphRAG over SEC filings for the AI SIFI Monitor  ·  github.com/Ann100182/ai-sifi-monitor",
         italic=True, color=GREY_RGB)

    doc.add_heading("1. Summary", level=1)
    para(doc,
         "ExposureIQ answers natural-language questions about hidden exposures in the AI compute "
         "buildout. It reads 147 SEC filings from 12 cloud and AI-infrastructure companies, uses "
         "Claude to extract structured facts (off-balance-sheet vehicles, investments, capex "
         "commitments, risk factors and hidden-risk signals) into a knowledge graph, and pairs that "
         "graph with a vector index of the filing text. A LangGraph state machine routes each "
         "question to graph search, vector search or both, then writes an answer in which every "
         "claim cites a specific filing.")
    para(doc,
         "The thesis it serves: the AI buildout carries interlocking obligations (SPV debt, "
         "investor ⇄ customer ⇄ supplier loops, equity that returns as revenue) that no single "
         "balance sheet shows. Those signals live in the notes, risk factors and MD&A, which is "
         "exactly where ExposureIQ looks.")

    doc.add_heading("2. Architecture", level=1)
    doc.add_picture(str(DIAGRAM), width=Inches(6.7))
    cap = para(doc, "Figure 1. Build-time pipeline (top) and query-time LangGraph flow (bottom).",
               italic=True, color=GREY_RGB, size=9)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(doc,
         "The system has two halves. The build-time pipeline runs once (about 15 hours and $35 of "
         "Claude calls) and produces two local stores: a Kuzu property graph and a Chroma vector "
         "index. The query-time engine is a four-node LangGraph state machine that reads those "
         "stores and calls Claude two to four times per question.")

    doc.add_heading("3. Technology stack", level=1)
    table(doc, ["Layer", "Technology", "Why this choice"], [
        ["**Source data**", "SEC EDGAR (10-K, 10-Q, 20-F, DEF 14A, ARS)",
         "Audited, public and citable; notes and risk factors hold the off-balance-sheet detail"],
        ["**Ingestion**", "requests, BeautifulSoup, lxml",
         "Rate-limited EDGAR fetch (<10 req/s); section-aware HTML parsing"],
        ["**Extraction**", "Claude Sonnet 4.6 + Claude Haiku 4.5, Pydantic schemas",
         "Sonnet for risk-critical sections (~65%), Haiku for the rest; JSON validated against the schema"],
        ["**Graph store**", "Kuzu 0.11 (embedded, Cypher)",
         "pip-installable, no Docker or Java; replaced Neo4j for a zero-footprint laptop setup"],
        ["**Vector store**", "Chroma 1.5 (persistent, cosine)", "Local, metadata filters by ticker and form"],
        ["**Embeddings**", "BAAI/bge-small-en-v1.5 via sentence-transformers (Apple MPS)",
         "Runs locally; no second API key; ~15 min to embed 25k chunks"],
        ["**Orchestration**", "LangGraph 0.6", "Explicit state machine, parallel fan-out, reducer-merged state"],
        ["**Reasoning**", "Claude Sonnet 4.6 (default), Claude Opus 4.7 (multi-hop)",
         "Quality-first query path; Opus only where multi-entity reasoning needs it"],
        ["**UI**", "Streamlit (tab 5 of the AI SIFI Monitor)", "Same app as the market dashboards; no new service"],
        ["**Runtime**", "Python 3, local laptop", "Only secret: ANTHROPIC_API_KEY"],
    ], widths=[1.2, 2.4, 3.1])

    doc.add_heading("4. Input data", level=1)
    table(doc, ["Dimension", "Scope"], [
        ["**Companies (12)**", "Microsoft, Amazon, Alphabet, Oracle, Meta, IBM, Salesforce, Adobe, "
                               "NVIDIA, ASML, CoreWeave, Broadcom"],
        ["**Roles**", "Hyperscalers, a neocloud (CoreWeave), SaaS consumers, the GPU supplier, "
                      "custom silicon, lithography (foreign filer)"],
        ["**Forms**", "10-K, 10-Q, 20-F, DEF 14A, ARS (8-K / 6-K / S-1 deferred)"],
        ["**Period**", "Fiscal 2024 – 2026"],
        ["**Volume**", "147 filings, ~10M raw tokens, ~650 MB of HTML"],
        ["**Sections used**", "Item 1A risk factors, Item 7 MD&A, financial statements and notes, "
                              "related-party transactions, compensation discussion"],
    ], widths=[1.5, 5.2])

    doc.add_heading("5. Build pipeline", level=1)
    table(doc, ["Stage", "Module", "What it does", "Output"], [
        ["1. Fetch", "fetch.py", "Pulls filing indexes and primary documents from EDGAR", "cache/raw (HTML)"],
        ["2. Parse", "parse.py", "Splits each filing into named sections with offsets",
         "cache/parsed (sections.jsonl)"],
        ["3. Extract", "extract.py, prompts.py, schemas.py",
         "Claude reads each section and returns typed nodes, edges and hidden-risk signals with "
         "verbatim quotes", "cache/extracted (JSON)"],
        ["4. Canonicalize", "canonicalize.py", "Maps aliases (AWS → Amazon, Facebook → Meta)", "—"],
        ["5. Graph load", "graph_load.py",
         "Dedupes nodes, drops nodes without a real quote, writes 7 node tables and 13 edge tables",
         "cache/kuzu"],
        ["6. Vector load", "vector_load.py", "Chunks sections and embeds them locally", "cache/chroma"],
    ], widths=[1.0, 1.5, 2.9, 1.3])
    para(doc,
         "The repo ships the parsed sections and the extracted JSON (51 MB), so anyone who clones "
         "it runs only stages 5 and 6: about 15 minutes, no API cost.")

    doc.add_heading("6. Knowledge graph schema", level=1)
    table(doc, ["Element", "Values"], [
        ["**Node types (7)**", "Company, AILab (OpenAI, Anthropic, xAI, Mistral, Cohere, Perplexity, "
                               "Databricks), CapexCommitment, OffBalanceEntity, Investment, "
                               "RiskFactor, HiddenRiskSignal"],
        ["**Edge types (13)**", "SELLS_COMPUTE_TO, BUYS_COMPUTE_FROM, INVESTED_IN, COMMITTED_CAPEX, "
                                "SPONSORS, BENEFITS, CITES_RISK, HAS_RISK_SIGNAL, CIRCULAR_WITH, "
                                "ROUND_TRIPS_WITH, NAMES_COUNTERPARTY, SUPPLIES, DEPENDS_ON"],
        ["**Hidden-risk types (8)**", "HIDDEN_LEVERAGE, CIRCULARITY, REVENUE_ROUNDTRIP, CAPEX_ROI_GAP, "
                                      "EXECUTION_RISK, COST_OPACITY, CUSTOMER_CONCENTRATION, "
                                      "SUPPLIER_CONCENTRATION; severity 1–5 (5 = could trigger a cascade)"],
        ["**Provenance**", "Every node keeps a list of cik:accession references and a verbatim quote"],
        ["**Size**", "4,084 nodes, 3,583 edges, 1,631 unique hidden-risk signals"],
    ], widths=[1.6, 5.1])

    doc.add_heading("7. Query engine", level=1)
    para(doc, "graphrag/query.py compiles a LangGraph StateGraph with four nodes:")
    table(doc, ["Node", "Role", "Model"], [
        ["**classify**", "Chooses GRAPH, VECTOR or HYBRID retrieval and rates the question SIMPLE or "
                         "MULTIHOP", "Sonnet 4.6"],
        ["**graph_search**", "Writes 1–3 Cypher queries against the schema and runs them on Kuzu. "
                             "Failed queries go back to the model once with the Kuzu error. Each row "
                             "resolves to a ticker, form and filing date.", "Sonnet 4.6"],
        ["**vector_search**", "Embeds the question, searches Chroma filtered to the companies it "
                              "names, and for multi-hop questions adds each company's latest backlog "
                              "(RPO) figures via exact-text match", "Local"],
        ["**synthesize**", "Writes a cited answer from the evidence only; flags hidden-risk "
                           "patterns; says \"insufficient evidence\" rather than guessing; labels "
                           "inferred links as inference", "Sonnet 4.6, or Opus 4.7 if MULTIHOP"],
    ], widths=[1.3, 4.1, 1.3])
    bullets(doc, [
        "**Parallel retrieval.** Hybrid and multi-hop questions fan out to both retrievers in the "
        "same LangGraph superstep; synthesize runs once when both finish.",
        "**Cost tracking.** Every Claude call is recorded with model, tokens, cost and latency and "
        "shown in the UI.",
        "**Read-only graph.** Kuzu opens read-only, so the app and the CLI can query at the same time.",
    ])

    doc.add_heading("8. Design decisions", level=1)
    table(doc, ["Decision", "Rationale"], [
        ["**Graph + vector, not either alone**",
         "Vector search finds similar text; the graph answers structural questions (who sponsors "
         "which SPV, who invests in whom) and traverses counterparty webs."],
        ["**Grounding filter at load**",
         "Nodes without a real verbatim quote are dropped. This removed a hallucinated Salesforce "
         "\"Hyperion\" that had overwritten Meta's real $27B Hyperion JV with Blue Owl."],
        ["**Inference is labelled, never asserted**",
         "Filers often omit counterparty names. Oracle never names OpenAI; its backlog rising from "
         "$138B to $638B in FY26 is cited as consistent with the reported deal, marked as inference."],
        ["**Model routing by complexity**",
         "Sonnet handles routing and simple answers; Opus is reserved for multi-hop synthesis, where "
         "it earns its cost."],
        ["**Local embeddings and an embedded graph**",
         "No Docker, Java or second API key; the whole system runs on a laptop."],
    ], widths=[2.0, 4.7])

    doc.add_heading("9. Cost and performance", level=1)
    table(doc, ["Item", "Figure"], [
        ["One-off extraction", "$35.21 (Haiku $10.80, Sonnet $24.41), ~14 hours, 147 filings"],
        ["Index build", "~17 minutes locally, $0"],
        ["Simple question", "~$0.02, ~15 seconds"],
        ["Multi-hop question", "~$0.06–$0.13, 25–40 seconds"],
    ], widths=[2.0, 4.7])

    doc.add_heading("10. Limitations and roadmap", level=1)
    bullets(doc, [
        "**Extraction errors.** Graph facts come from an LLM; answers still need a human read.",
        "**Filings only.** Undisclosed relationships appear only as labelled inference. Next: news "
        "as a separate, clearly labelled evidence tier.",
        "**Dropped edges.** About 700 extracted edges fall outside the schema's allowed type pairs; "
        "widening the schema would recover them.",
        "**Snapshot corpus.** Re-run the pipeline to add new filings; 8-K, 6-K and S-1 are next.",
        "**Evaluation.** A question set with graded answers and citations is planned.",
    ])

    doc.save(path)


# ---------------------------------------------------------------- demo script

SCENES = [
    ("0:00 – 0:20", "The idea",
     "ExposureIQ banner at the top of the tab.",
     "The AI buildout is financed in ways balance sheets don't show: data-center SPVs, "
     "investors who are also customers, contracts for capacity that doesn't exist yet. Those "
     "details sit in the footnotes of SEC filings. ExposureIQ reads the footnotes so you don't "
     "have to."),
    ("0:20 – 0:45", "The input data",
     "Scroll to the starter questions. Optionally flash the repo's graphrag/cache/parsed folder.",
     "The input is 147 SEC filings — 10-Ks, 10-Qs, 20-Fs and proxies — from twelve companies at "
     "the center of AI compute: the hyperscalers, CoreWeave, NVIDIA, Broadcom and ASML, fiscal "
     "2024 through 2026. I focused on the sections where the risk hides: risk factors, MD&A, "
     "and the notes to the financial statements."),
    ("0:45 – 1:15", "What I built",
     "Show the architecture diagram (Figure 1 of the architecture doc) or describe it over the tab.",
     "Claude read every section and pulled out structured facts — off-balance-sheet vehicles, "
     "investments, capex commitments and eight types of hidden-risk signal — each with a verbatim "
     "quote. That became a knowledge graph of about four thousand nodes, next to a vector index of "
     "the filing text. At question time a LangGraph pipeline decides whether to query the graph, "
     "the text, or both in parallel, then writes an answer where every claim cites a filing."),
    ("1:15 – 1:50", "Demo 1 — a structural question",
     "Click \"Which SPVs does Meta sponsor?\". Point at the answer table, then open the Evidence "
     "panel and the Cypher.",
     "First, a structural question: which SPVs does Meta sponsor? This one goes to the graph. At "
     "the top is Hyperion — Meta's twenty-seven-billion-dollar data-center joint venture with Blue "
     "Owl — plus over a hundred billion dollars of leases that haven't started yet. Every row "
     "links back to the filing and the query that found it. That cost about two cents."),
    ("1:50 – 2:35", "Demo 2 — a multi-hop question",
     "Switch to the second browser tab where \"Trace the OpenAI counterparty web…\" has already "
     "run. Scroll to the Oracle section, then open the Pipeline trace.",
     "Now a harder one: trace the OpenAI web across Microsoft, Oracle and CoreWeave. This is "
     "multi-hop, so it searches the graph and the text in parallel and hands the answer to Opus. "
     "Microsoft's thirteen-billion-dollar stake goes out; a two-hundred-fifty-billion-dollar Azure "
     "commitment comes back. CoreWeave's OpenAI contract is backed by debt where OpenAI holds a "
     "lien. And Oracle never names OpenAI in any filing — so the answer cites Oracle's backlog "
     "jumping from 138 to 638 billion dollars, and labels the link as inference, not disclosure."),
    ("2:35 – 3:00", "Close",
     "Pipeline trace visible, then the GitHub repo page.",
     "Simple questions cost about two cents and complex ones about ten to thirteen. The whole thing "
     "runs on a laptop, and the repo includes the extracted data, so anyone can rebuild it in "
     "fifteen minutes. Next I'm adding news as a separate evidence source for the deals that "
     "filings won't name. Thanks for watching."),
]

PREP = [
    "Start the app: source .venv/bin/activate && streamlit run app.py, then open "
    "http://localhost:8501 → ExposureIQ.",
    "Warm up: ask any question once before recording; the first query loads the embedding model.",
    "Use two browser tabs (each is its own session). In tab A, run \"Which SPVs does Meta "
    "sponsor?\". In tab B, run \"Trace the OpenAI counterparty web across Microsoft, Oracle, and "
    "CoreWeave.\" The multi-hop answer takes ~40 seconds, so have it ready before you hit record.",
    "Have the architecture diagram (docs/exposureiq_architecture.png) open in a third tab or window.",
    "Turn on Do Not Disturb; record the full browser window so the URL bar shows localhost.",
    "Pace: about 140 words per minute. The spoken script is ~370 words (about 2:40), leaving ~20 seconds for clicks and pauses.",
]

BACKUP = [
    "\"Which companies have the most severe customer concentration risk signals?\" — Broadcom's "
    "largest customer is 32% of revenue and rising; NVIDIA's top three direct customers are 54%.",
    "\"What hidden-leverage signals above severity 4 appear in the latest 10-Ks?\"",
]


def build_demo_script(path: Path):
    doc = base_document()
    title = doc.add_heading("ExposureIQ — 3-Minute Demo Script", level=0)
    title.runs[0].font.color.rgb = NAVY_RGB
    para(doc, "Audience: investors, analysts, hiring managers and portfolio reviewers  ·  "
              "Length: 3:00  ·  Pace: ~140 words/min", italic=True, color=GREY_RGB)

    doc.add_heading("Before you record", level=1)
    for i, p in enumerate(PREP, 1):
        doc.add_paragraph(p, style="List Number")

    doc.add_heading("Arc", level=1)
    para(doc, "Idea → input data → what I built → two live questions → close. Spend most of the "
              "time on the two demos; the Oracle inference moment is the payoff, so don't rush it.")

    doc.add_heading("Script", level=1)
    for time, name, show, say in SCENES:
        h = doc.add_heading(f"{time}   {name}", level=2)
        p = doc.add_paragraph()
        r = p.add_run("Show: ")
        r.bold = True
        r.font.color.rgb = GREY_RGB
        p.add_run(show).italic = True
        p = doc.add_paragraph()
        r = p.add_run("Say: ")
        r.bold = True
        r.font.color.rgb = NAVY_RGB
        p.add_run(f"“{say}”")

    doc.add_heading("Backup questions", level=1)
    para(doc, "If a live answer is slow or weak, switch to one of these (both tested):")
    bullets(doc, BACKUP)

    doc.add_heading("Numbers to have at hand", level=1)
    table(doc, ["Fact", "Value"], [
        ["Filings / companies / years", "147 / 12 / FY2024–2026"],
        ["Graph", "4,084 nodes, 3,583 edges, 1,631 hidden-risk signals"],
        ["One-off extraction cost", "$35 (about 14 hours)"],
        ["Cost per question", "~$0.02 simple, ~$0.06–$0.13 multi-hop"],
        ["Meta Hyperion JV", "$27B, with Blue Owl"],
        ["Oracle backlog (RPO)", "$138B (May 2025) → $638B (May 2026) → $664B (Aug 2026)"],
        ["Microsoft ↔ OpenAI", "$13B funding commitment; $250B incremental Azure contract"],
    ], widths=[2.4, 4.3])

    doc.save(path)


def main():
    draw_architecture(DIAGRAM)
    build_architecture_doc(HERE / "ExposureIQ_Architecture.docx")
    build_demo_script(HERE / "ExposureIQ_Demo_Script.docx")
    spoken = sum(len(s[3].split()) for s in SCENES)
    print(f"wrote {DIAGRAM.name}, ExposureIQ_Architecture.docx, ExposureIQ_Demo_Script.docx "
          f"(spoken words: {spoken})")


if __name__ == "__main__":
    main()
