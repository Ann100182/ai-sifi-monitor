"""Per-tier descriptions and sidebar icons."""

TIER_META: dict[int, dict[str, str]] = {
    1: {
        "icon": "⚡",
        "short": "Power Gen",
        "desc": "Foundational constraint — US added just 25 GW in 2024 after derating. "
                "Data centers projected to drive 2/3 of load growth. "
                "If utilities can't deliver, every tier above stalls.",
    },
    2: {
        "icon": "🔌",
        "short": "Grid & Cap Eq",
        "desc": "Gas turbines, transformers, switchgear — 3-7 year lead times. "
                "Bottleneck between power generation and the data center shell.",
    },
    3: {
        "icon": "🔬",
        "short": "Semi Equip & EDA",
        "desc": "ASML EUV monopoly + Cadence/Synopsys EDA duopoly. "
                "Narrowest tier; irreplaceable in the <5nm cutting edge.",
    },
    4: {
        "icon": "🧠",
        "short": "Semi Design",
        "desc": "NVIDIA + the challengers. GPU/custom-silicon designers that own IP but "
                "depend entirely on TSMC manufacturing and HBM supply.",
    },
    5: {
        "icon": "🏭",
        "short": "Semi Mfg",
        "desc": "TSMC = single point of failure for leading-edge nodes. "
                "US onshoring may reach 30-35% self-sufficiency by 2030 — still highly reliant.",
    },
    6: {
        "icon": "💻",
        "short": "AI Hardware & Net",
        "desc": "Server integrators and networking gear. "
                "Where GPUs become usable systems; margin thin, concentration high.",
    },
    7: {
        "icon": "☁️",
        "short": "Hyperscalers",
        "desc": "Core demand engine — $1.3T capex since 2022. "
                "If AI monetization disappoints, FCF compresses and the whole stack re-rates. "
                "Oracle + Meta + CoreWeave carry the leverage.",
    },
    8: {
        "icon": "📱",
        "short": "AI Software & Apps",
        "desc": "The monetization layer. Palantir / Salesforce / ServiceNow lead on AI revenue traction; "
                "security vendors (PANW / CRWD / FTNT) are the defensive cut.",
    },
}
