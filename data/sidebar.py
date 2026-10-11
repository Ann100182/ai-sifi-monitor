"""Shared left sidebar — tier navigation reused across tabs."""

from __future__ import annotations

import streamlit as st

from data.players import TIERS, by_tier
from data.tier_meta import TIER_META

ALL_TIERS = "📊 All Tiers"


def tier_selector(key: str = "tier_nav") -> int | None:
    """Render sidebar tier picker. Returns tier number (1-8) or None for 'All'."""
    with st.sidebar:
        st.markdown(
            "<div style='padding: 0.5rem 0; margin-bottom: 1rem; "
            "border-bottom: 1px solid #1C2230;'>"
            "<div style='font-size: 1.3rem; font-weight: 700; "
            "color: #4C9EFF; letter-spacing: 0.05em;'>AI SIFI</div>"
            "<div style='font-size: 0.8rem; color: #94A3B8;'>Systemic Risk Monitor</div>"
            "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("##### TIERS")
        counts = {t: len(ps) for t, ps in by_tier().items()}
        tier_order = list(TIERS.keys())
        label_to_tier: dict[str, int | None] = {ALL_TIERS: None}
        labels = [ALL_TIERS]
        for t in tier_order:
            lbl = f"{TIER_META[t]['icon']}  {TIER_META[t]['short']}  ({counts[t]})"
            labels.append(lbl)
            label_to_tier[lbl] = t

        chosen = st.radio(
            "tier selector",
            labels,
            index=0,
            label_visibility="collapsed",
            key=key,
        )
        st.markdown(
            "<div style='position: fixed; bottom: 1.5rem; font-size: 0.75rem; "
            "color: #64748B;'>Data: Yahoo Finance · RSS<br/>Thesis: Cembalest JPM 2026</div>",
            unsafe_allow_html=True,
        )
        return label_to_tier.get(chosen)
