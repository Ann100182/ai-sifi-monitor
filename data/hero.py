"""Hero banner component — one per tab, with gradient background + stat chips."""

from __future__ import annotations

import streamlit as st

HERO_CSS = """
<style>
.sifi-hero {
    position: relative;
    padding: 1.6rem 2rem 1.5rem 2rem;
    border-radius: 14px;
    margin: 0 0 1.4rem 0;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 4px 24px rgba(0,0,0,0.35);
}
.sifi-hero-row { display: flex; align-items: center; gap: 1.4rem; }
.sifi-hero-icon {
    flex: 0 0 68px;
    height: 68px; width: 68px;
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    font-size: 2.4rem;
    background: rgba(255,255,255,0.12);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.18);
}
.sifi-hero-text { flex: 1; }
.sifi-hero-title {
    font-size: 1.65rem;
    font-weight: 700;
    color: #FFFFFF;
    margin: 0;
    letter-spacing: -0.01em;
    line-height: 1.15;
}
.sifi-hero-tagline {
    font-size: 0.95rem;
    color: rgba(255,255,255,0.86);
    margin-top: 0.35rem;
    line-height: 1.45;
    max-width: 920px;
}
.sifi-hero-stats {
    display: flex; gap: 0.6rem; flex-wrap: wrap;
    margin-top: 0.9rem;
}
.sifi-hero-chip {
    background: rgba(0,0,0,0.28);
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.78rem;
    color: rgba(255,255,255,0.95);
    border: 1px solid rgba(255,255,255,0.14);
    letter-spacing: 0.02em;
}
.sifi-hero-chip b { color: #FFFFFF; font-weight: 700; }

/* Gradient variants per tab theme */
.sifi-hero.portfolio {
    background: linear-gradient(135deg, #0b3d6e 0%, #1a7acc 55%, #2fa3e0 100%);
}
.sifi-hero.vintage {
    background: linear-gradient(135deg, #0f4b2e 0%, #1a8f54 55%, #26b474 100%);
}
.sifi-hero.news {
    background: linear-gradient(135deg, #5a2f05 0%, #c57a1a 55%, #e9a83a 100%);
}
.sifi-hero.stack {
    background: linear-gradient(135deg, #3a1f6a 0%, #6a3fb2 55%, #8f5fd8 100%);
}
.sifi-hero.exposureiq {
    background: linear-gradient(135deg, #4a0a0a 0%, #a6252d 50%, #d84a4a 100%);
}
</style>
"""


def _inject_once():
    if "_sifi_hero_css" not in st.session_state:
        st.markdown(HERO_CSS, unsafe_allow_html=True)
        st.session_state["_sifi_hero_css"] = True


def hero(
    *,
    theme: str,           # "portfolio" | "vintage" | "news" | "stack" | "exposureiq"
    icon: str,            # emoji
    title: str,
    tagline: str,
    chips: list[tuple[str, str]] | None = None,   # (label, value) pairs
):
    _inject_once()
    chip_html = ""
    if chips:
        chip_html = '<div class="sifi-hero-stats">'
        for label, value in chips:
            chip_html += f'<span class="sifi-hero-chip">{label} <b>{value}</b></span>'
        chip_html += '</div>'

    st.markdown(
        f"""<div class="sifi-hero {theme}">
            <div class="sifi-hero-row">
                <div class="sifi-hero-icon">{icon}</div>
                <div class="sifi-hero-text">
                    <h2 class="sifi-hero-title">{title}</h2>
                    <p class="sifi-hero-tagline">{tagline}</p>
                    {chip_html}
                </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )
