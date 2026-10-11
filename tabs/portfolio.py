"""Tab 1: Portfolio Overview — Risk × Investment Matrix with sidebar tier nav."""

from __future__ import annotations


import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

from data.players import PLAYERS, TIERS, status_from_risk, tickers
from data.styles import badge, bar, status_pill_row, tier_header
from data.tier_meta import TIER_META


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_fundamentals(tkrs: tuple[str, ...]) -> pd.DataFrame:
    """Pull per-ticker fundamentals + YTD return via yfinance."""
    rows = []
    for t in tkrs:
        info = {}
        try:
            info = yf.Ticker(t).info or {}
        except Exception as e:
            info = {"_error": str(e)}
        rows.append({
            "Ticker": t,
            "MarketCap": info.get("marketCap"),
            "P/E (fwd)": info.get("forwardPE"),
            "P/E (ttm)": info.get("trailingPE"),
            "FCF Margin": _safe_ratio(info.get("freeCashflow"), info.get("totalRevenue")),
            "Net Debt / EBITDA": _net_debt_to_ebitda(info),
            "52W Change %": _pct(info.get("52WeekChange")),
        })
    df = pd.DataFrame(rows)

    try:
        hist = yf.download(
            list(tkrs), period="ytd", progress=False, auto_adjust=True, group_by="ticker"
        )
        ytd = {}
        for t in tkrs:
            try:
                if t in hist.columns.get_level_values(0):
                    closes = hist[t]["Close"].dropna()
                    if len(closes) > 1:
                        ytd[t] = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
            except Exception:
                pass
        df["YTD %"] = df["Ticker"].map(ytd)
    except Exception:
        df["YTD %"] = None
    return df


def _safe_ratio(num, den):
    try:
        if num and den and den != 0:
            return num / den
    except Exception:
        return None
    return None


def _net_debt_to_ebitda(info: dict):
    try:
        total_debt = info.get("totalDebt") or 0
        cash = info.get("totalCash") or 0
        ebitda = info.get("ebitda")
        if ebitda and ebitda > 0:
            return (total_debt - cash) / ebitda
    except Exception:
        return None
    return None


def _pct(v):
    return v * 100 if v is not None else None


def _fmt_mcap(v):
    if pd.isna(v) or v is None:
        return "—"
    v = float(v)
    if v >= 1e12:
        return f"${v / 1e12:.2f}T"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    return f"${v / 1e6:.0f}M"


# ---------- Rendering ----------

def _render_matrix(players, funds_df: pd.DataFrame):
    """Render the Risk × Investment matrix as styled HTML rows."""
    st.markdown("### Risk × Investment Matrix")
    st.markdown(
        '<div class="sifi-row header">'
        '<div>Player</div><div>Ticker</div><div>Country</div><div>Status</div>'
        '<div>Risk /10</div><div>Invest /10</div><div>Top Bull Factor</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    # Sort by risk desc then invest desc
    rows = sorted(players, key=lambda p: (-p.risk_score, -p.invest_score))
    for p in rows:
        status, _ = status_from_risk(p.risk_score)
        html = (
            f'<div class="sifi-row">'
            f'  <div class="player">{p.name}</div>'
            f'  <div class="ticker">{p.ticker}</div>'
            f'  <div>{p.country}</div>'
            f'  <div>{badge(status)}</div>'
            f'  <div>{bar(p.risk_score, "risk")}</div>'
            f'  <div>{bar(p.invest_score, "invest")}</div>'
            f'  <div class="bull-factor">{p.bull_factor}</div>'
            f'</div>'
        )
        st.markdown(html, unsafe_allow_html=True)


def _render_tier_view(tier_num: int, funds_df: pd.DataFrame):
    meta = TIER_META[tier_num]
    tier_name = TIERS[tier_num]
    tier_players = [p for p in PLAYERS if p.tier == tier_num]

    st.markdown(
        tier_header("#4C9EFF", f"{tier_name}", meta["desc"]),
        unsafe_allow_html=True,
    )

    # Status counts
    statuses = [status_from_risk(p.risk_score)[0] for p in tier_players]
    c = statuses.count("CRITICAL")
    e = statuses.count("ELEVATED")
    w = statuses.count("WATCH")
    n = statuses.count("NORMAL")
    st.markdown(status_pill_row(c, e, w, n, len(tier_players)), unsafe_allow_html=True)

    _render_matrix(tier_players, funds_df)

    # Fundamentals detail for the tier
    with st.expander("Fundamentals detail (live Yahoo Finance)", expanded=False):
        sub = funds_df[funds_df["Ticker"].isin([p.ticker for p in tier_players])].copy()
        name_by = {p.ticker: p.name for p in tier_players}
        sub.insert(1, "Name", sub["Ticker"].map(name_by))
        sub["Market Cap"] = sub["MarketCap"].map(_fmt_mcap)
        sub["YTD %"] = sub["YTD %"].map(lambda v: f"{v:.1f}%" if pd.notna(v) else "—")
        sub["52W %"] = sub["52W Change %"].map(lambda v: f"{v:.1f}%" if pd.notna(v) else "—")
        sub["P/E (fwd)"] = sub["P/E (fwd)"].map(lambda v: f"{v:.1f}" if pd.notna(v) else "—")
        sub["FCF Margin"] = sub["FCF Margin"].map(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "—")
        sub["ND/EBITDA"] = sub["Net Debt / EBITDA"].map(lambda v: f"{v:.2f}x" if pd.notna(v) else "—")
        st.dataframe(
            sub[["Ticker", "Name", "Market Cap", "YTD %", "52W %",
                 "P/E (fwd)", "FCF Margin", "ND/EBITDA"]],
            use_container_width=True, hide_index=True,
        )


def _render_all_tiers(funds_df: pd.DataFrame):
    st.markdown(
        tier_header(
            "#4C9EFF",
            "All Tiers — 45 Players",
            "Aggregate view across the eight tiers of the AI compute stack. "
            "Status counts reflect composite risk scoring; the market-cap chart "
            "below quantifies concentration — a reminder that four semiscalers plus "
            "four hyperscalers now carry ~16% of global equity market capitalization.",
        ),
        unsafe_allow_html=True,
    )

    # Status counts across all
    all_statuses = [status_from_risk(p.risk_score)[0] for p in PLAYERS]
    c = all_statuses.count("CRITICAL")
    e = all_statuses.count("ELEVATED")
    w = all_statuses.count("WATCH")
    n = all_statuses.count("NORMAL")
    st.markdown(status_pill_row(c, e, w, n, len(PLAYERS)), unsafe_allow_html=True)

    # Tier concentration chart
    tier_agg = funds_df.copy()
    name_tier = {p.ticker: (p.tier, p.tier_name) for p in PLAYERS}
    tier_agg["Tier"] = tier_agg["Ticker"].map(lambda t: name_tier[t][0])
    tier_agg["Layer"] = tier_agg["Ticker"].map(lambda t: name_tier[t][1])
    tier_agg = (
        tier_agg.dropna(subset=["MarketCap"])
          .groupby(["Tier", "Layer"], as_index=False)["MarketCap"].sum()
          .sort_values("Tier")
    )
    if not tier_agg.empty:
        fig = px.bar(
            tier_agg, x="Layer", y="MarketCap", color="Tier",
            labels={"MarketCap": "Combined market cap (USD)"},
            title="Market cap concentration by tier",
            color_continuous_scale="Blues",
        )
        fig.update_layout(
            xaxis_tickangle=-30, showlegend=False, height=380,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E4E7EB",
        )
        st.plotly_chart(fig, use_container_width=True)

    _render_matrix(PLAYERS, funds_df)


def render(selected_tier: int | None):
    """Main entry — selected_tier is passed from the shared sidebar."""
    with st.spinner("Pulling fundamentals from Yahoo Finance..."):
        funds = fetch_fundamentals(tuple(tickers()))

    if selected_tier is None:
        _render_all_tiers(funds)
    else:
        _render_tier_view(selected_tier, funds)
