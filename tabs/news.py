"""Tab 3: News & Risk Monitor — RSS-driven risk tagging that re-ranks the portfolio."""

from __future__ import annotations

import time
from datetime import datetime, timezone

import feedparser
import pandas as pd
import plotly.express as px
import streamlit as st

from data.players import PLAYERS, tickers
from data.risks import RISK_THEMES, score_headline

# Per-ticker: Google News RSS. Aggregates Bloomberg, WSJ, Reuters, FT, and the
# newswires. Keyed to ticker name + "stock" to narrow results.
GNEWS_RSS = (
    "https://news.google.com/rss/search?"
    "q={query}&hl=en-US&gl=US&ceid=US:en"
)

# Broad sector feeds — Bloomberg leads, with secondary sources for coverage breadth.
BROAD_FEEDS = [
    ("Bloomberg Markets",      "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg Technology",   "https://feeds.bloomberg.com/technology/news.rss"),
    ("Bloomberg Politics",     "https://feeds.bloomberg.com/politics/news.rss"),
    ("Bloomberg Opinion",      "https://feeds.bloomberg.com/opinion/news.rss"),
    # Fallback aggregators in case Bloomberg feeds are rate-limited or deprecated
    ("Google News — AI Infra", "https://news.google.com/rss/search?q=%22AI+infrastructure%22+OR+%22data+center%22+power+grid&hl=en-US&gl=US&ceid=US:en"),
    ("Google News — Taiwan/TSMC", "https://news.google.com/rss/search?q=TSMC+OR+Taiwan+semiconductor+export&hl=en-US&gl=US&ceid=US:en"),
]


@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_ticker_news(tkrs: tuple[str, ...], per_ticker: int = 5) -> pd.DataFrame:
    """Per-ticker news via Google News RSS — aggregates Bloomberg, WSJ, Reuters, FT."""
    from urllib.parse import quote_plus
    from data.players import PLAYERS as _P
    name_by = {p.ticker: p.name for p in _P}

    rows = []
    for t in tkrs:
        try:
            # Query combines name + ticker for recall; "-crypto" to drop noise
            query = quote_plus(f'"{name_by.get(t, t)}" OR {t} stock -crypto -meme')
            feed = feedparser.parse(GNEWS_RSS.format(query=query))
            for entry in feed.entries[:per_ticker]:
                # Google News titles include source: "Headline - Bloomberg"
                raw_title = entry.get("title", "")
                src = "Google News"
                if " - " in raw_title:
                    title, src = raw_title.rsplit(" - ", 1)
                else:
                    title = raw_title
                rows.append({
                    "Ticker": t,
                    "Source": src,
                    "Title": title,
                    "Link": entry.get("link", ""),
                    "Published": _parse_time(entry),
                    "Summary": entry.get("summary", "")[:400],
                })
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(ttl=60 * 30, show_spinner=False)
def fetch_broad_news(max_items: int = 30) -> pd.DataFrame:
    rows = []
    for name, url in BROAD_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items]:
                rows.append({
                    "Ticker": None,
                    "Source": name,
                    "Title": entry.get("title", ""),
                    "Link": entry.get("link", ""),
                    "Published": _parse_time(entry),
                    "Summary": entry.get("summary", "")[:400],
                })
        except Exception:
            continue
    return pd.DataFrame(rows)


def _parse_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        if entry.get(key):
            try:
                return datetime.fromtimestamp(time.mktime(entry[key]), tz=timezone.utc)
            except Exception:
                pass
    return None


def _tag_risks(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["RiskHits"] = df["Title"].fillna("").map(score_headline)
    df["RiskScore"] = df["RiskHits"].map(lambda d: sum(d.values()) if d else 0)
    df["Themes"] = df["RiskHits"].map(lambda d: ", ".join(d.keys()) if d else "")
    return df


def _per_ticker_risk(news_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate risk per ticker: total severity-weighted hits + themes seen."""
    df = news_df.dropna(subset=["Ticker"])
    if df.empty:
        return pd.DataFrame(columns=["Ticker", "News Count", "News Risk Score", "Themes"])
    agg = (
        df.groupby("Ticker")
          .agg(**{
              "News Count": ("Title", "count"),
              "News Risk Score": ("RiskScore", "sum"),
          })
          .reset_index()
    )
    themes = (
        df[df["Themes"] != ""]
          .groupby("Ticker")["Themes"]
          .apply(lambda s: ", ".join(sorted({x for row in s for x in row.split(", ")})))
          .reset_index()
    )
    return agg.merge(themes, on="Ticker", how="left").fillna({"Themes": ""})


def render():
    st.header("News & Risk Monitor")
    st.caption(
        "Live RSS from Yahoo Finance (per ticker) + Reuters/CNBC (broad). "
        "Headlines are tagged against the SIFI risk taxonomy; "
        "severity-weighted scores re-rank the portfolio by news-flagged risk."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        per_ticker = st.slider("Headlines per ticker", 3, 10, 5)
    with col2:
        if st.button("Refresh news (30-min cache)"):
            fetch_ticker_news.clear()
            fetch_broad_news.clear()

    with st.spinner("Pulling per-ticker news (this takes 30-60s on first load)..."):
        per_tkr_news = _tag_risks(fetch_ticker_news(tuple(tickers()), per_ticker=per_ticker))
    with st.spinner("Pulling broad sector news..."):
        broad_news = _tag_risks(fetch_broad_news())

    all_news = pd.concat([per_tkr_news, broad_news], ignore_index=True)

    # --- SIFI Risk Re-Ranking ---
    st.subheader("SIFI Risk Re-Ranking (news-driven)")
    st.caption(
        "News Risk Score = sum of severity weights across tagged themes in recent headlines. "
        "Higher = more cascade-risk mentions."
    )

    name_by_tkr = {p.ticker: p.name for p in PLAYERS}
    tier_by_tkr = {p.ticker: p.tier for p in PLAYERS}
    layer_by_tkr = {p.ticker: p.tier_name for p in PLAYERS}

    ranked = _per_ticker_risk(per_tkr_news)
    ranked["Name"] = ranked["Ticker"].map(name_by_tkr)
    ranked["Tier"] = ranked["Ticker"].map(tier_by_tkr)
    ranked["Layer"] = ranked["Ticker"].map(layer_by_tkr)
    ranked = ranked.sort_values("News Risk Score", ascending=False)

    # Metrics strip
    m1, m2, m3 = st.columns(3)
    m1.metric("Total headlines", len(all_news))
    m2.metric("Flagged headlines", int((all_news["RiskScore"] > 0).sum()))
    m3.metric("Themes active",
              int(sum(1 for theme in RISK_THEMES if
                      all_news["Themes"].str.contains(theme, na=False).any())))

    cols = ["Ticker", "Name", "Tier", "Layer", "News Count", "News Risk Score", "Themes"]
    st.dataframe(
        ranked[cols].head(20),
        use_container_width=True,
        hide_index=True,
    )

    # --- Theme breakdown chart ---
    st.subheader("Risk theme activity")
    theme_counts = {}
    for themes in all_news["Themes"]:
        if themes:
            for t in themes.split(", "):
                theme_counts[t] = theme_counts.get(t, 0) + 1
    if theme_counts:
        theme_df = pd.DataFrame(
            [{"Theme": k, "Mentions": v, "Severity": RISK_THEMES[k]["severity"]}
             for k, v in theme_counts.items() if k in RISK_THEMES]
        ).sort_values("Mentions", ascending=True)
        fig = px.bar(
            theme_df, x="Mentions", y="Theme", color="Severity", orientation="h",
            color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
            title="Risk themes cited in recent news",
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No risk themes triggered in current headlines.")

    # --- Flagged headlines ---
    st.subheader("Flagged headlines (highest severity first)")
    flagged = all_news[all_news["RiskScore"] > 0].sort_values(
        ["RiskScore", "Published"], ascending=[False, False]
    )
    if flagged.empty:
        st.info("No flagged headlines right now.")
    else:
        for _, row in flagged.head(25).iterrows():
            severity = row["RiskScore"]
            emoji = "🔴" if severity >= 3 else "🟡" if severity >= 2 else "🟢"
            ticker = f"**[{row['Ticker']}]** " if row["Ticker"] else ""
            when = row["Published"].strftime("%Y-%m-%d") if row["Published"] else ""
            st.markdown(
                f"{emoji} {ticker}[{row['Title']}]({row['Link']})  \n"
                f"<small>_{row['Source']} · {when} · Themes: {row['Themes']}_</small>",
                unsafe_allow_html=True,
            )

    # --- All headlines table (expandable) ---
    with st.expander(f"All {len(all_news)} headlines"):
        show = all_news[["Ticker", "Source", "Title", "Published", "Themes"]].copy()
        show["Published"] = show["Published"].map(
            lambda d: d.strftime("%Y-%m-%d %H:%M") if pd.notna(d) else ""
        )
        st.dataframe(show, use_container_width=True, hide_index=True, height=400)
