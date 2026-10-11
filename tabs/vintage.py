"""Tab 2: Vintage Analysis — $10K invested 5/10/15 years ago in top-N players."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from data.players import PLAYERS, tickers

INVEST = 10_000  # dollars per ticker per vintage


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch_history(tkrs: tuple[str, ...], years: int = 15) -> pd.DataFrame:
    """Return a wide DataFrame of adjusted close prices (columns = tickers)."""
    period = f"{years}y"
    df = yf.download(
        list(tkrs), period=period, progress=False, auto_adjust=True, group_by="ticker"
    )
    # Normalize to a flat (date x ticker) frame of adj close
    out = pd.DataFrame()
    for t in tkrs:
        try:
            if (t, "Close") in df.columns:
                out[t] = df[(t, "Close")]
            elif t in df.columns.get_level_values(0):
                out[t] = df[t]["Close"]
        except Exception:
            pass
    return out.dropna(how="all")


@st.cache_data(ttl=60 * 60, show_spinner=False)
def fetch_market_caps(tkrs: tuple[str, ...]) -> dict[str, float]:
    mcaps: dict[str, float] = {}
    for t in tkrs:
        try:
            info = yf.Ticker(t).info or {}
            mcaps[t] = info.get("marketCap") or 0
        except Exception:
            mcaps[t] = 0
    return mcaps


def _value_from_vintage(prices: pd.Series, years: int) -> tuple[float | None, float | None]:
    """Return (end_value, cagr) for $INVEST invested `years` ago in this ticker."""
    prices = prices.dropna()
    if prices.empty:
        return None, None
    cutoff = prices.index[-1] - pd.DateOffset(years=years)
    window = prices[prices.index >= cutoff]
    if len(window) < 2:
        return None, None
    start_px = window.iloc[0]
    end_px = window.iloc[-1]
    end_val = INVEST * (end_px / start_px)
    cagr = (end_px / start_px) ** (1 / years) - 1
    return float(end_val), float(cagr)


def _max_drawdown(series: pd.Series) -> float | None:
    if series.empty:
        return None
    peak = series.cummax()
    dd = (series / peak - 1).min()
    return float(dd)


def render():
    st.header("Vintage Analysis — $10K invested at 5 / 10 / 15 years ago")
    st.caption(
        "If you had put $10,000 into each of the top 10 AI SIFI players "
        "5, 10, or 15 years ago, what would you have today? "
        "Default is top 10 by market cap — override via the selector."
    )

    all_tkrs = tuple(tickers())

    with st.spinner("Loading market caps..."):
        mcaps = fetch_market_caps(all_tkrs)
    top10_default = [t for t, _ in sorted(mcaps.items(), key=lambda kv: -kv[1])[:10]]

    name_by_tkr = {p.ticker: p.name for p in PLAYERS}
    labels = {t: f"{t} — {name_by_tkr.get(t, t)}" for t in all_tkrs}

    chosen = st.multiselect(
        "Tickers to analyze",
        options=sorted(all_tkrs),
        default=top10_default,
        format_func=lambda t: labels[t],
        help="Default = top 10 by current market cap",
    )

    if not chosen:
        st.warning("Pick at least one ticker.")
        return

    with st.spinner(f"Loading 15 years of history for {len(chosen)} tickers..."):
        prices = fetch_history(tuple(chosen), years=15)

    if prices.empty:
        st.error("Could not load price history.")
        return

    # --- Vintage returns table ---
    rows = []
    for t in chosen:
        if t not in prices.columns:
            continue
        s = prices[t]
        v5, c5 = _value_from_vintage(s, 5)
        v10, c10 = _value_from_vintage(s, 10)
        v15, c15 = _value_from_vintage(s, 15)
        dd = _max_drawdown(s)
        rows.append({
            "Ticker": t,
            "Name": name_by_tkr.get(t, t),
            "5Y value": v5,
            "5Y CAGR": c5,
            "10Y value": v10,
            "10Y CAGR": c10,
            "15Y value": v15,
            "15Y CAGR": c15,
            "15Y Max DD": dd,
        })
    vdf = pd.DataFrame(rows)

    # --- Portfolio totals ---
    k = len(chosen)
    totals = {
        "5y total invested":  INVEST * k if vdf["5Y value"].notna().all() else None,
        "5y total value":     vdf["5Y value"].sum(skipna=True),
        "10y total invested": INVEST * vdf["10Y value"].notna().sum(),
        "10y total value":    vdf["10Y value"].sum(skipna=True),
        "15y total invested": INVEST * vdf["15Y value"].notna().sum(),
        "15y total value":    vdf["15Y value"].sum(skipna=True),
    }
    m1, m2, m3 = st.columns(3)
    for col, horizon in zip((m1, m2, m3), ("5y", "10y", "15y")):
        inv = totals[f"{horizon} total invested"]
        val = totals[f"{horizon} total value"]
        delta = (val - inv) if (inv and val) else None
        col.metric(
            f"${INVEST:,}/ticker × {k} tickers, {horizon}",
            f"${val:,.0f}" if val else "—",
            delta=f"${delta:,.0f}" if delta is not None else None,
        )

    # --- Formatted table ---
    disp = vdf.copy()
    for col in ("5Y value", "10Y value", "15Y value"):
        disp[col] = disp[col].map(lambda v: f"${v:,.0f}" if pd.notna(v) else "—")
    for col in ("5Y CAGR", "10Y CAGR", "15Y CAGR", "15Y Max DD"):
        disp[col] = disp[col].map(lambda v: f"{v*100:.1f}%" if pd.notna(v) else "—")
    st.subheader("Per-ticker vintage returns")
    st.dataframe(disp, use_container_width=True, hide_index=True)

    # --- Growth chart: $10K per ticker, normalized ---
    st.subheader("Growth of $10K per ticker over time")
    horizon = st.selectbox("Horizon", ["15y", "10y", "5y"], index=0)
    years = int(horizon.replace("y", ""))
    cutoff = prices.index.max() - pd.DateOffset(years=years)
    window = prices.loc[prices.index >= cutoff, chosen].dropna(how="all")
    if window.empty:
        st.info("Insufficient data for selected horizon.")
    else:
        normalized = window.apply(lambda col: INVEST * col / col.dropna().iloc[0])
        fig = px.line(
            normalized, x=normalized.index, y=normalized.columns,
            labels={"value": "Value ($)", "index": "Date", "variable": "Ticker"},
            title=f"Growth of ${INVEST:,} per ticker, {horizon} horizon",
        )
        fig.update_layout(height=500, legend_title=None)
        st.plotly_chart(fig, use_container_width=True)

    # --- CAGR bar chart ---
    st.subheader("CAGR comparison across vintages")
    cagr_long = vdf.melt(
        id_vars=["Ticker"],
        value_vars=["5Y CAGR", "10Y CAGR", "15Y CAGR"],
        var_name="Vintage", value_name="CAGR",
    ).dropna()
    if not cagr_long.empty:
        cagr_long["CAGR_pct"] = cagr_long["CAGR"] * 100
        fig2 = px.bar(
            cagr_long, x="Ticker", y="CAGR_pct", color="Vintage", barmode="group",
            labels={"CAGR_pct": "CAGR (%)"},
            title="Annualized return by vintage",
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
