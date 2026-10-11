"""Shared CSS injection + HTML widgets for dark SIFI theme."""

CUSTOM_CSS = """
<style>
/* ---- Overall page polish ---- */
.block-container { padding-top: 1.5rem !important; }

/* ---- Sidebar polish ---- */
[data-testid="stSidebar"] {
    background: #0D1117 !important;
    border-right: 1px solid #1C2230;
}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #94A3B8 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
    margin-top: 1.5rem;
}
[data-testid="stSidebar"] .stRadio > label { font-size: 0.95rem; }
[data-testid="stSidebar"] [role="radiogroup"] label {
    padding: 0.5rem 0.7rem;
    border-radius: 8px;
    margin-bottom: 2px;
    transition: background 0.15s;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
    background: rgba(76,158,255,0.08);
}

/* ---- Status pill chips ---- */
.sifi-pill-row {
    display: flex; gap: 1.5rem; align-items: center;
    padding: 0.9rem 1.1rem;
    background: #141821;
    border: 1px solid #1C2230;
    border-radius: 10px;
    margin: 0.8rem 0 1.5rem 0;
}
.sifi-pill { display:flex; align-items:center; gap:0.5rem; font-size:0.95rem; }
.sifi-pill .count { font-size: 1.3rem; font-weight: 700; }
.sifi-pill .label { color:#94A3B8; font-size: 0.85rem; letter-spacing: 0.02em; }
.sifi-pill .total { color:#64748B; margin-left:auto; font-size: 0.85rem; }

/* ---- Tier header ---- */
.sifi-tier-header { display:flex; align-items:center; gap:0.6rem; margin-top:0.5rem; }
.sifi-tier-header .dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: #4C9EFF; box-shadow: 0 0 10px #4C9EFF;
}
.sifi-tier-header h1 { font-size: 1.8rem; margin: 0 !important; }

/* ---- Status badges (inside tables) ---- */
.badge {
    display:inline-block; padding: 2px 10px; border-radius: 4px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em;
}
.badge-critical { background: rgba(231,76,60,0.15); color: #E74C3C; border: 1px solid rgba(231,76,60,0.4); }
.badge-elevated { background: rgba(243,156,18,0.15); color: #F39C12; border: 1px solid rgba(243,156,18,0.4); }
.badge-watch    { background: rgba(241,196,15,0.15); color: #F1C40F; border: 1px solid rgba(241,196,15,0.4); }
.badge-normal   { background: rgba(46,204,113,0.15); color: #2ECC71; border: 1px solid rgba(46,204,113,0.4); }

/* ---- Risk/Invest row ---- */
.sifi-row {
    display: grid;
    grid-template-columns: 2fr 0.7fr 0.6fr 1fr 2fr 2fr 2.2fr;
    gap: 0.8rem; align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #1C2230;
}
.sifi-row:hover { background: rgba(76,158,255,0.04); }
.sifi-row.header {
    color: #94A3B8; font-size: 0.78rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase;
    border-bottom: 1px solid #2A3140;
    background: #0F131A;
}
.sifi-row .ticker { color:#64748B; font-family: ui-monospace, Menlo, monospace; font-size: 0.85rem; }
.sifi-row .player { font-weight: 600; }

/* ---- Progress bars ---- */
.sifi-bar {
    position: relative;
    height: 6px; background: #1C2230; border-radius: 3px;
    display: flex; align-items: center;
}
.sifi-bar-fill { height: 6px; border-radius: 3px; }
.sifi-bar-val {
    margin-left: 0.6rem; font-weight: 700;
    font-family: ui-monospace, Menlo, monospace;
}

.bull-factor { color: #94A3B8; font-size: 0.9rem; }
</style>
"""


def badge(status: str) -> str:
    cls = {
        "CRITICAL": "badge-critical",
        "ELEVATED": "badge-elevated",
        "WATCH": "badge-watch",
        "NORMAL": "badge-normal",
    }.get(status, "badge-normal")
    return f'<span class="badge {cls}">{status}</span>'


def _bar_color(value: int, kind: str) -> str:
    """Color intensifies with score. Risk bars shade red; invest bars shade blue."""
    if kind == "risk":
        if value >= 9: return "#E74C3C"
        if value >= 7: return "#F39C12"
        if value >= 5: return "#F1C40F"
        return "#2ECC71"
    # invest
    return "#4C9EFF"


def bar(value: int, kind: str = "risk", max_value: int = 10) -> str:
    pct = max(0, min(100, value / max_value * 100))
    color = _bar_color(value, kind)
    return (
        f'<div style="display:flex;align-items:center;">'
        f'  <div class="sifi-bar" style="flex:1;">'
        f'    <div class="sifi-bar-fill" style="width:{pct:.0f}%;background:{color};"></div>'
        f'  </div>'
        f'  <span class="sifi-bar-val" style="color:{color};">{value}</span>'
        f'</div>'
    )


def tier_header(dot_color: str, title: str, subtitle: str) -> str:
    return (
        f'<div class="sifi-tier-header">'
        f'  <span class="dot" style="background:{dot_color};box-shadow:0 0 10px {dot_color};"></span>'
        f'  <h1>{title}</h1>'
        f'</div>'
        f'<p style="color:#94A3B8; font-size: 1rem; margin-top:0.5rem; max-width:900px;">{subtitle}</p>'
    )


def status_pill_row(critical: int, elevated: int, watch: int, normal: int, total: int) -> str:
    return f"""
<div class="sifi-pill-row">
  <div class="sifi-pill">
    <span style="color:#E74C3C;">⚠</span>
    <span class="count" style="color:#E74C3C;">{critical}</span>
    <span class="label">Critical</span>
  </div>
  <div class="sifi-pill">
    <span style="color:#F39C12;">↗</span>
    <span class="count" style="color:#F39C12;">{elevated}</span>
    <span class="label">Elevated</span>
  </div>
  <div class="sifi-pill">
    <span style="color:#F1C40F;">👁</span>
    <span class="count" style="color:#F1C40F;">{watch}</span>
    <span class="label">Watch</span>
  </div>
  <div class="sifi-pill">
    <span style="color:#2ECC71;">✓</span>
    <span class="count" style="color:#2ECC71;">{normal}</span>
    <span class="label">Normal</span>
  </div>
  <div class="sifi-pill total">{total} total players</div>
</div>
"""
