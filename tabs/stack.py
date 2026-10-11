"""Tab 4: Stack Comparison — intra-tier best/worst across the 8-tier AI infra chain."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from data.players import PLAYERS, TIERS, tickers
from tabs.portfolio import fetch_fundamentals, _fmt_mcap


def _best_worst(df: pd.DataFrame, col: str, higher_better: bool = True) -> tuple[str, str]:
    s = df[["Ticker", col]].dropna()
    if s.empty:
        return "—", "—"
    s = s.sort_values(col, ascending=not higher_better)
    best = s.iloc[0]
    worst = s.iloc[-1]
    return (
        f"{best['Ticker']} ({_fmt_cell(col, best[col])})",
        f"{worst['Ticker']} ({_fmt_cell(col, worst[col])})",
    )


def _fmt_cell(col: str, v) -> str:
    if pd.isna(v):
        return "—"
    if col in ("YTD %", "52W Change %", "FCF Margin"):
        pct = v * 100 if col == "FCF Margin" else v
        return f"{pct:.1f}%"
    if col == "P/E (fwd)":
        return f"{v:.1f}"
    if col == "Net Debt / EBITDA":
        return f"{v:.2f}x"
    return f"{v:.2f}"


def render():
    st.header("Stack Comparison — Best & Worst per AI Infrastructure Tier")
    st.caption(
        "For each of the 8 interlocking tiers, who's leading and who's lagging on return, "
        "profitability, leverage, and valuation. "
        "Within-tier dispersion matters: a struggling player in a concentrated tier "
        "(like Semi Manufacturing) is a different risk than a laggard in a crowded one."
    )

    with st.spinner("Loading fundamentals..."):
        funds = fetch_fundamentals(tuple(tickers()))

    base = pd.DataFrame([
        {"Ticker": p.ticker, "Name": p.name, "Tier": p.tier,
         "Layer": p.tier_name, "Rationale": p.rationale}
        for p in PLAYERS
    ])
    df = base.merge(funds, on="Ticker", how="left")

    # --- Tier summary dashboard ---
    st.subheader("Tier summary — concentration and health")
    rows = []
    for tier_num, tier_name in TIERS.items():
        sub = df[df["Tier"] == tier_num]
        if sub.empty:
            continue
        best_ytd, worst_ytd = _best_worst(sub, "YTD %", higher_better=True)
        best_fcf, worst_fcf = _best_worst(sub, "FCF Margin", higher_better=True)
        best_lev, worst_lev = _best_worst(sub, "Net Debt / EBITDA", higher_better=False)
        best_pe, worst_pe = _best_worst(sub, "P/E (fwd)", higher_better=False)
        rows.append({
            "Tier": tier_num,
            "Layer": tier_name,
            "Players": len(sub),
            "Combined Mcap": _fmt_mcap(sub["MarketCap"].sum(skipna=True)),
            "Median YTD": f"{sub['YTD %'].median():.1f}%" if sub["YTD %"].notna().any() else "—",
            "Best YTD": best_ytd,
            "Worst YTD": worst_ytd,
            "Best FCF margin": best_fcf,
            "Worst FCF margin": worst_fcf,
            "Lowest leverage": best_lev,
            "Highest leverage": worst_lev,
            "Cheapest (fwd P/E)": best_pe,
            "Priciest (fwd P/E)": worst_pe,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # --- Tier dispersion chart ---
    st.subheader("Within-tier dispersion: YTD return by player")
    plot_df = df.dropna(subset=["YTD %"]).copy()
    if not plot_df.empty:
        fig = px.strip(
            plot_df, x="Layer", y="YTD %", color="Layer", hover_data=["Ticker", "Name"],
            title="YTD % dispersion by tier (hover for ticker)",
        )
        fig.update_traces(marker=dict(size=14, opacity=0.85))
        fig.update_layout(
            xaxis_tickangle=-30, showlegend=False, height=500,
            yaxis_title="YTD %", xaxis_title=None,
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- Per-tier drilldown ---
    st.subheader("Per-tier drilldown")
    for tier_num, tier_name in TIERS.items():
        sub = df[df["Tier"] == tier_num].copy()
        if sub.empty:
            continue
        with st.expander(
            f"**Tier {tier_num} — {tier_name}** · {len(sub)} players · "
            f"combined {_fmt_mcap(sub['MarketCap'].sum(skipna=True))}",
            expanded=(tier_num in (5, 7)),  # expand concentrated tiers by default
        ):
            disp = sub[["Ticker", "Name", "MarketCap", "YTD %", "P/E (fwd)",
                        "FCF Margin", "Net Debt / EBITDA", "Rationale"]].copy()
            disp["MarketCap"] = disp["MarketCap"].map(_fmt_mcap)
            disp["YTD %"] = disp["YTD %"].map(
                lambda v: f"{v:.1f}%" if pd.notna(v) else "—")
            disp["P/E (fwd)"] = disp["P/E (fwd)"].map(
                lambda v: f"{v:.1f}" if pd.notna(v) else "—")
            disp["FCF Margin"] = disp["FCF Margin"].map(
                lambda v: f"{v*100:.1f}%" if pd.notna(v) else "—")
            disp["Net Debt / EBITDA"] = disp["Net Debt / EBITDA"].map(
                lambda v: f"{v:.2f}x" if pd.notna(v) else "—")
            st.dataframe(disp, use_container_width=True, hide_index=True)
