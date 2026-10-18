"""Generate AI_SIFI_Monitor.pptx — showcase deck for the dashboard.

Run from project root:
    source .venv/bin/activate
    python docs/make_ppt.py

Writes docs/AI_SIFI_Monitor.pptx (16-widescreen slides, dark theme).
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

# ---- Dark SIFI palette ----
BG       = RGBColor(0x0A, 0x0E, 0x14)      # near-black navy
PANEL    = RGBColor(0x14, 0x18, 0x21)      # card background
BORDER   = RGBColor(0x1C, 0x22, 0x30)
TEXT     = RGBColor(0xE4, 0xE7, 0xEB)      # soft white
MUTED    = RGBColor(0x94, 0xA3, 0xB8)      # cool grey
PRIMARY  = RGBColor(0x4C, 0x9E, 0xFF)      # cyan-blue
CRITICAL = RGBColor(0xE7, 0x4C, 0x3C)
ELEVATED = RGBColor(0xF3, 0x9C, 0x12)
WATCH    = RGBColor(0xF1, 0xC4, 0x0F)
NORMAL   = RGBColor(0x2E, 0xCC, 0x71)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _add_bg(slide):
    r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, SLIDE_W, SLIDE_H)
    r.fill.solid(); r.fill.fore_color.rgb = BG
    r.line.fill.background()
    r.shadow.inherit = False
    return r


def _add_text(slide, left, top, width, height, text, *,
              size=18, bold=False, color=TEXT, align=PP_ALIGN.LEFT, font="Calibri"):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Emu(0)
    tf.margin_top = tf.margin_bottom = Emu(0)
    lines = text.split("\n") if isinstance(text, str) else text
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
    return tb


def _add_panel(slide, left, top, width, height, fill=PANEL):
    r = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    r.fill.solid(); r.fill.fore_color.rgb = fill
    r.line.color.rgb = BORDER; r.line.width = Pt(0.75)
    r.shadow.inherit = False
    r.adjustments[0] = 0.03
    return r


def _add_accent_bar(slide, top, color=PRIMARY):
    r = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.6), top, Inches(0.08), Inches(0.5))
    r.fill.solid(); r.fill.fore_color.rgb = color; r.line.fill.background()
    r.shadow.inherit = False
    return r


def _add_slide_number(slide, n, total):
    _add_text(slide, Inches(12.4), Inches(7.05), Inches(0.8), Inches(0.3),
              f"{n:02d} / {total:02d}", size=9, color=MUTED, align=PP_ALIGN.RIGHT)
    _add_text(slide, Inches(0.6), Inches(7.05), Inches(5), Inches(0.3),
              "AI SIFI Monitor", size=9, color=MUTED)


def _title_block(slide, idx, total, title, subtitle=None):
    _add_accent_bar(slide, Inches(0.55))
    _add_text(slide, Inches(0.85), Inches(0.4), Inches(12), Inches(0.7),
              title, size=28, bold=True, color=TEXT)
    if subtitle:
        _add_text(slide, Inches(0.85), Inches(1.05), Inches(12), Inches(0.5),
                  subtitle, size=14, color=MUTED)
    _add_slide_number(slide, idx, total)


# ---- Slide builders ----

def slide_title(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    # Accent dot
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.9), Inches(3.1), Inches(0.3), Inches(0.3))
    dot.fill.solid(); dot.fill.fore_color.rgb = PRIMARY; dot.line.fill.background()
    dot.shadow.inherit = False
    _add_text(s, Inches(1.4), Inches(2.95), Inches(10), Inches(0.6),
              "AI SIFI MONITOR", size=14, bold=True, color=PRIMARY)
    _add_text(s, Inches(0.9), Inches(3.6), Inches(11.5), Inches(1.3),
              "Where is the systemic risk in the AI buildout?",
              size=42, bold=True, color=TEXT)
    _add_text(s, Inches(0.9), Inches(4.75), Inches(11.5), Inches(1.2),
              "A surveillance framework for the 45 institutions whose simultaneous "
              "stress would re-rate the entire AI compute theme.",
              size=18, color=MUTED)
    _add_text(s, Inches(0.9), Inches(6.5), Inches(11.5), Inches(0.3),
              "github.com/Ann100182/ai-sifi-monitor",
              size=11, color=PRIMARY)
    _add_slide_number(s, 1, total)
    return s


def slide_problem(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 2, total,
                 "The question",
                 "What investors should be asking at today's concentration levels")
    # Big quote
    _add_panel(s, Inches(0.85), Inches(2.0), Inches(11.6), Inches(2.3))
    _add_text(s, Inches(1.2), Inches(2.2), Inches(11), Inches(0.4),
              "— Michael Cembalest, JPM 2026 Outlook", size=11, color=MUTED)
    _add_text(s, Inches(1.2), Inches(2.6), Inches(11), Inches(1.5),
              "\"When markets are highly concentrated and near all-time highs, "
              "the right question to ask is: what could go wrong.\"",
              size=22, bold=True, color=TEXT)
    # Three stats
    for i, (hdr, val, unit) in enumerate([
        ("Share of S&P 500 returns from 42 AI stocks", "65–75", "%"),
        ("Hyperscaler capex since ChatGPT launch", "$1.3", "T"),
        ("Tech capex contribution to US GDP growth", "40–45", "%"),
    ]):
        left = Inches(0.85 + i * 4.0)
        _add_panel(s, left, Inches(4.65), Inches(3.8), Inches(1.9))
        _add_text(s, left + Inches(0.25), Inches(4.9), Inches(3.5), Inches(0.5),
                  hdr, size=10, color=MUTED)
        _add_text(s, left + Inches(0.25), Inches(5.3), Inches(3.5), Inches(1.0),
                  f"{val}", size=40, bold=True, color=PRIMARY)
        _add_text(s, left + Inches(2.3), Inches(5.55), Inches(1), Inches(0.5),
                  unit, size=20, color=PRIMARY)


def slide_analogy(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 3, total,
                 "The 2008 analogy",
                 "Interlocking exposures that no single balance sheet makes visible")
    # Two columns
    for i, (title, color, bullets) in enumerate([
        ("PRE-2008 BANKS", MUTED, [
            "• AAA-rated MBS tranches circulated between banks",
            "• Off-balance-sheet SIVs held the risky layers",
            "• Monoline insurers backstopped the whole structure",
            "• Correlations spiked to 1.0 in the stress event",
            "• Recovery: ~5 years of recapitalization",
        ]),
        ("TODAY'S AI STACK", PRIMARY, [
            "• NVIDIA invests in neoclouds that rent GPUs back",
            "• Meta/Hyperion SPV holds $27B debt off-books",
            "• Oracle committed to deliver $60B/yr to OpenAI (not yet earned)",
            "• 4 semi + 4 hyperscalers = 20% of DM market cap",
            "• Recovery: 5–10 years to rebuild compute capacity",
        ]),
    ]):
        left = Inches(0.85 + i * 6.1)
        _add_panel(s, left, Inches(2.0), Inches(5.9), Inches(4.6))
        _add_text(s, left + Inches(0.4), Inches(2.25), Inches(5.5), Inches(0.4),
                  title, size=12, bold=True, color=color)
        _add_text(s, left + Inches(0.4), Inches(2.8), Inches(5.5), Inches(3.5),
                  "\n".join(bullets), size=14, color=TEXT)


def slide_wcgw(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 4, total,
                 "Four failure vectors",
                 "What Could Go Wrong — from Cembalest's JPM 2026 Outlook")
    specs = [
        ("1", "Monetization gap", CRITICAL,
         "Hyperscaler $1.3T capex vs. actual AI revenue. "
         "If ROI disappoints like Metaverse 2022, Mag 7 could halve."),
        ("2", "US power grid", ELEVATED,
         "25 GW of derated capacity added in 2024. OpenAI alone announced 30 GW of partnerships. "
         "Gas turbines on 3-7 year backlog."),
        ("3", "China scales the moat", WATCH,
         "Huawei Ascend 910C now 75%+ of China's AI chip production. "
         "EUV prototype targeted 2028-2030. One-to-three generations behind — but moving."),
        ("4", "Taiwan Strait", CRITICAL,
         "90% of leading-edge logic from TSMC. Taiwan imports 90% of energy; "
         "10-11 days of LNG storage. US onshoring ~30-35% by 2030."),
    ]
    for i, (num, title, color, body) in enumerate(specs):
        row, col = i // 2, i % 2
        left = Inches(0.85 + col * 6.1)
        top = Inches(1.95 + row * 2.4)
        _add_panel(s, left, top, Inches(5.9), Inches(2.2))
        # Number badge
        _add_text(s, left + Inches(0.35), top + Inches(0.25), Inches(0.6), Inches(0.6),
                  num, size=28, bold=True, color=color)
        _add_text(s, left + Inches(1.1), top + Inches(0.25), Inches(4.6), Inches(0.5),
                  title.upper(), size=14, bold=True, color=TEXT)
        _add_text(s, left + Inches(1.1), top + Inches(0.75), Inches(4.6), Inches(1.4),
                  body, size=11, color=MUTED)


def slide_stack(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 5, total,
                 "The 8-tier AI compute stack",
                 "Failure of a lower-tier node cascades up — power stalls everything")
    tiers = [
        ("8", "AI Software, Apps & Security", 10, "Palantir, ServiceNow, Palo Alto, Crowdstrike"),
        ("7", "Hyperscalers & Cloud", 7,  "Microsoft, Google, Amazon, Meta, Oracle, CoreWeave"),
        ("6", "AI Hardware & Networking", 4,  "Super Micro, Dell, Arista, HP"),
        ("5", "Semi Manufacturing", 1,  "TSMC — single point of failure for leading-edge"),
        ("4", "Semi Design", 7,  "NVIDIA, AMD, Broadcom, Micron, Intel"),
        ("3", "Semi Equipment & EDA", 2,  "ASML (EUV monopoly), Cadence"),
        ("2", "Grid & Electrical Capital Equipment", 6,  "GE Vernova, Eaton, Quanta, Trane"),
        ("1", "Power Generation (Utilities)", 8,  "Constellation, Vistra, NextEra, Entergy"),
    ]
    y = Inches(1.9)
    row_h = Inches(0.6)
    for i, (num, name, cnt, players) in enumerate(tiers):
        top = y + row_h * i
        _add_panel(s, Inches(0.85), top, Inches(11.6), Inches(0.52))
        _add_text(s, Inches(1.05), top + Inches(0.08), Inches(0.5), Inches(0.4),
                  f"T{num}", size=14, bold=True, color=PRIMARY)
        _add_text(s, Inches(1.7), Inches(0.08) + top, Inches(4.5), Inches(0.4),
                  name, size=13, bold=True, color=TEXT)
        _add_text(s, Inches(6.2), Inches(0.1) + top, Inches(0.6), Inches(0.4),
                  f"{cnt}", size=13, bold=True, color=PRIMARY)
        _add_text(s, Inches(6.8), Inches(0.12) + top, Inches(5.5), Inches(0.4),
                  players, size=11, color=MUTED)


def slide_universe(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 6, total,
                 "45-player universe at a glance",
                 "Status counts from the composite risk score")
    # Four status counts
    counts = [
        ("CRITICAL",  4,  CRITICAL,  "NVDA · TSM · ORCL · CRWV"),
        ("ELEVATED", 13,  ELEVATED,  "AVGO · ASML · AMD · INTC · GEV · META · AMZN · MSFT · MU · SMCI · TSLA · CEG · VST"),
        ("WATCH",    18,  WATCH,     "Semi + hyperscaler second rank"),
        ("NORMAL",   10,  NORMAL,    "Mid-tier utilities + security + NXP · HPQ · JCI · NI · PEG · IBM · PANW · FTNT · TT · EME"),
    ]
    for i, (lbl, n, color, who) in enumerate(counts):
        top = Inches(1.9 + i * 1.2)
        _add_panel(s, Inches(0.85), top, Inches(11.6), Inches(1.05))
        _add_text(s, Inches(1.1), top + Inches(0.2), Inches(1.5), Inches(0.6),
                  str(n), size=36, bold=True, color=color)
        _add_text(s, Inches(2.5), top + Inches(0.15), Inches(2.5), Inches(0.4),
                  lbl, size=12, bold=True, color=color)
        _add_text(s, Inches(2.5), top + Inches(0.55), Inches(9), Inches(0.45),
                  who, size=11, color=MUTED)


def slide_critical(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 7, total,
                 "4 critical nodes — where the cascade starts",
                 "")
    nodes = [
        ("NVDA", "NVIDIA", "Tier 4 — Semi Design",
         "Blackwell/Rubin roadmap owns inference. Vendor-financing circularity: invests in neoclouds that rent GPUs to its own customers."),
        ("TSM", "Taiwan Semiconductor", "Tier 5 — Semi Mfg",
         "Manufactures ~90% of leading-edge logic. Taiwan Strait risk + 10-day LNG storage + US onshoring gap through 2030."),
        ("ORCL", "Oracle", "Tier 7 — Hyperscalers",
         "Committed $60B/yr compute to OpenAI (not yet earned). Stock -35% since September, CDS +90bps. First hyperscaler to visibly lever up."),
        ("CRWV", "CoreWeave", "Tier 7 — Hyperscalers",
         "Pure-play neocloud, most levered to GPU rental rates. Stock -50% from June peak; H100 rental rates down 20-25% YoY."),
    ]
    for i, (tkr, name, tier, body) in enumerate(nodes):
        row, col = i // 2, i % 2
        left = Inches(0.85 + col * 6.1)
        top = Inches(1.95 + row * 2.4)
        _add_panel(s, left, top, Inches(5.9), Inches(2.2))
        # Red critical bar
        bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Inches(0.1), Inches(2.2))
        bar.fill.solid(); bar.fill.fore_color.rgb = CRITICAL; bar.line.fill.background()
        bar.shadow.inherit = False
        _add_text(s, left + Inches(0.35), top + Inches(0.2), Inches(2.5), Inches(0.5),
                  tkr, size=20, bold=True, color=TEXT, font="Consolas")
        _add_text(s, left + Inches(2.7), top + Inches(0.25), Inches(3), Inches(0.4),
                  tier, size=10, color=MUTED, align=PP_ALIGN.RIGHT)
        _add_text(s, left + Inches(0.35), top + Inches(0.75), Inches(5.3), Inches(0.4),
                  name, size=13, bold=True, color=TEXT)
        _add_text(s, left + Inches(0.35), top + Inches(1.15), Inches(5.3), Inches(1.0),
                  body, size=11, color=MUTED)


def slide_tab(prs, total, idx, tab_num, name, subtitle, highlights):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, idx, total,
                 f"Tab {tab_num}  ·  {name}",
                 subtitle)
    # Mock dashboard preview panel
    _add_panel(s, Inches(0.85), Inches(2.0), Inches(7.5), Inches(4.6), fill=RGBColor(0x0F, 0x13, 0x1A))
    _add_text(s, Inches(1.1), Inches(2.25), Inches(7), Inches(0.4),
              "[ live preview — see dashboard ]", size=11, color=MUTED)
    _add_text(s, Inches(1.1), Inches(3.3), Inches(7), Inches(2.5),
              f"{name.upper()}", size=36, bold=True, color=PRIMARY, align=PP_ALIGN.CENTER)
    _add_text(s, Inches(1.1), Inches(4.1), Inches(7), Inches(2.5),
              "localhost:8501", size=11, color=MUTED, align=PP_ALIGN.CENTER)
    # Highlights panel
    _add_panel(s, Inches(8.65), Inches(2.0), Inches(3.8), Inches(4.6))
    _add_text(s, Inches(8.9), Inches(2.25), Inches(3.4), Inches(0.4),
              "WHAT'S ON THIS TAB", size=10, bold=True, color=MUTED)
    _add_text(s, Inches(8.9), Inches(2.7), Inches(3.4), Inches(3.8),
              "\n\n".join([f"• {h}" for h in highlights]), size=12, color=TEXT)


def slide_methodology(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 12, total,
                 "Risk-scoring methodology",
                 "Composite of fundamental risk + news-flagged events")
    # Formula panel
    _add_panel(s, Inches(0.85), Inches(1.95), Inches(11.6), Inches(1.4))
    _add_text(s, Inches(1.1), Inches(2.15), Inches(11), Inches(0.4),
              "COMPOSITE RISK SCORE", size=11, bold=True, color=MUTED)
    _add_text(s, Inches(1.1), Inches(2.55), Inches(11), Inches(0.7),
              "= tier_severity × 0.4   +   leverage_bucket × 0.3   +   concentration × 0.2   +   news_severity × 0.1",
              size=15, bold=True, color=PRIMARY, font="Consolas")

    # Three columns of scoring inputs
    for i, (hdr, body) in enumerate([
        ("Tier severity (1-10)",
         "T5 Semi Mfg → 10\nT4 Design, T7 Hyperscalers → 8\nT3 Equip/EDA → 7\nT1 Utilities → 6\nT8 Apps → 5"),
        ("Leverage bucket",
         "ND/EBITDA from Yahoo Finance\nPlus SPV debt (manual, from 10-Ks)\n+2 if credit spread widening\n+2 if debt-funded capex surge"),
        ("News severity (per theme)",
         "Taiwan/TSMC: 3\nChina sanctions: 3\nUS power: 3\nOpenAI/vendor: 3\nSPV leverage: 2\nAI ROI skepticism: 2\n...11 themes total"),
    ]):
        left = Inches(0.85 + i * 4.0)
        _add_panel(s, left, Inches(3.6), Inches(3.8), Inches(3.0))
        _add_text(s, left + Inches(0.3), Inches(3.8), Inches(3.4), Inches(0.4),
                  hdr, size=12, bold=True, color=TEXT)
        _add_text(s, left + Inches(0.3), Inches(4.3), Inches(3.4), Inches(2.3),
                  body, size=11, color=MUTED, font="Consolas")


def slide_techstack(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 13, total,
                 "Tech stack",
                 "Zero API keys. Zero paid services. Entirely free-tier.")
    rows = [
        ("UI",            "Streamlit",   "Dark theme, native tabs, free, fast iteration"),
        ("Market data",   "yfinance",    "Prices + fundamentals, batched, no key"),
        ("News",          "feedparser",  "Bloomberg Markets/Tech + Google News per ticker"),
        ("Charts",        "Plotly",      "Interactive, dark-theme-aware, strip/bar/line"),
        ("Risk engine",   "Pandas + custom", "Keyword taxonomy + severity weights in data/risks.py"),
    ]
    y = Inches(2.1)
    for i, (layer, tool, why) in enumerate(rows):
        top = y + Inches(0.95) * i
        _add_panel(s, Inches(0.85), top, Inches(11.6), Inches(0.85))
        _add_text(s, Inches(1.1), top + Inches(0.2), Inches(2), Inches(0.5),
                  layer, size=11, bold=True, color=MUTED)
        _add_text(s, Inches(3.2), top + Inches(0.18), Inches(2.5), Inches(0.5),
                  tool, size=15, bold=True, color=PRIMARY, font="Consolas")
        _add_text(s, Inches(6.0), top + Inches(0.22), Inches(6.4), Inches(0.5),
                  why, size=12, color=TEXT)


def slide_roadmap(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _title_block(s, 14, total,
                 "Roadmap",
                 "Where this goes next")
    items = [
        ("SPV / off-balance-sheet debt tracker",
         "Scrape 10-K operating leases, RVGs, project-finance obligations (Hyperion template)"),
        ("Options skew monitor",
         "Tail-risk pricing for the 4 critical nodes — NVDA / TSM / ORCL / CRWV"),
        ("Capacity price feeds",
         "PJM / ERCOT auction prices as leading indicator for Tier 1 stress"),
        ("Credit spread integration",
         "5Y CDS deltas for ORCL / META / INTC"),
        ("Satellite imagery hooks",
         "Data center construction progress via Planet Labs / Umbra"),
        ("Export control scrapers",
         "Real-time BIS Entity List + Dutch export rulings"),
    ]
    for i, (title, body) in enumerate(items):
        row, col = i // 2, i % 2
        left = Inches(0.85 + col * 6.1)
        top = Inches(1.95 + row * 1.75)
        _add_panel(s, left, top, Inches(5.9), Inches(1.55))
        _add_text(s, left + Inches(0.3), top + Inches(0.2), Inches(5.5), Inches(0.5),
                  f"▸  {title}", size=13, bold=True, color=PRIMARY)
        _add_text(s, left + Inches(0.5), top + Inches(0.7), Inches(5.3), Inches(0.8),
                  body, size=11, color=MUTED)


def slide_close(prs, total):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _add_bg(s)
    _add_accent_bar(s, Inches(0.55))
    _add_text(s, Inches(0.85), Inches(0.4), Inches(12), Inches(0.7),
              "Thanks.", size=28, bold=True, color=TEXT)
    _add_text(s, Inches(0.9), Inches(2.5), Inches(11.5), Inches(0.8),
              "The dashboard, the thesis, and the source material.", size=22, color=TEXT)
    # Links panel
    _add_panel(s, Inches(0.85), Inches(3.8), Inches(11.6), Inches(2.6))
    _add_text(s, Inches(1.2), Inches(4.0), Inches(2.5), Inches(0.4),
              "REPO", size=11, bold=True, color=MUTED)
    _add_text(s, Inches(1.2), Inches(4.35), Inches(10), Inches(0.5),
              "github.com/Ann100182/ai-sifi-monitor", size=16, bold=True, color=PRIMARY, font="Consolas")
    _add_text(s, Inches(1.2), Inches(5.0), Inches(2.5), Inches(0.4),
              "SOURCES", size=11, bold=True, color=MUTED)
    _add_text(s, Inches(1.2), Inches(5.35), Inches(10), Inches(1.0),
              "Cembalest, M. — Smothering Heights (JPM 2026 Outlook, Jan 2026)\n"
              "Tyler, L. — Financing AI (Morgan Stanley, Mar 2026)",
              size=12, color=TEXT)
    _add_slide_number(s, total, total)


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    total = 15

    slide_title(prs, total)                   # 1
    slide_problem(prs, total)                 # 2
    slide_analogy(prs, total)                 # 3
    slide_wcgw(prs, total)                    # 4
    slide_stack(prs, total)                   # 5
    slide_universe(prs, total)                # 6
    slide_critical(prs, total)                # 7

    slide_tab(prs, total, 8, 1, "Portfolio Overview",
              "Risk × Investment Matrix for every player, sidebar tier browser",
              ["Sidebar tier nav with per-layer thesis",
               "Status badge: Critical / Elevated / Watch / Normal",
               "Risk /10 and Invest /10 progress bars",
               "One-line bull factor per player",
               "Expandable live Yahoo Finance fundamentals"])
    slide_tab(prs, total, 9, 2, "Vintage Analysis",
              "$10,000 invested 5 / 10 / 15 years ago in top-N by market cap",
              ["Default: top 10 by current market cap",
               "Per-ticker end value, CAGR, max drawdown",
               "Growth-of-$10K line chart, horizon selector",
               "Multiselect to override the default set"])
    slide_tab(prs, total, 10, 3, "News & Risk Monitor",
              "Bloomberg + Google News RSS tagged against 11-theme SIFI taxonomy",
              ["Per-ticker news from Google News (aggregates Bloomberg, WSJ, Reuters)",
               "Broad feeds: Bloomberg Markets, Tech, Opinion",
               "Severity-weighted re-ranking",
               "Flagged headlines with Critical/Watch markers"])
    slide_tab(prs, total, 11, 4, "Stack Comparison",
              "Intra-tier best/worst on return, FCF margin, leverage, valuation",
              ["Per-tier summary dashboard",
               "YTD dispersion strip plot by tier",
               "Expandable drilldown — concentrated tiers expanded by default",
               "Highlights intra-tier dispersion signal"])

    slide_methodology(prs, total)             # 12
    slide_techstack(prs, total)               # 13
    slide_roadmap(prs, total)                 # 14 — wait that's 14, close moves to 15

    # Oops, total should match — let me just add close
    slide_close(prs, total)                   # final = 14

    out = Path(__file__).parent / "AI_SIFI_Monitor.pptx"
    prs.save(out)
    print(f"wrote {out}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
