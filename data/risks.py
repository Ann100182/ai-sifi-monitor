"""
Risk taxonomy for the AI SIFI thesis.

Themes drawn from Cembalest's JPM 2026 Outlook WCGW analysis
and the Morgan Stanley financing podcast.

Each theme has a severity weight (1-3) and keyword triggers. Severity reflects
cascade potential: Taiwan Strait (3) > GPU depreciation (1).
"""

# Each key = short theme name. severity: 1 (watch), 2 (concern), 3 (acute).
RISK_THEMES: dict[str, dict] = {
    "Taiwan / TSMC concentration": {
        "severity": 3,
        "keywords": ["taiwan", "tsmc", "strait", "blockade", "pla ", "xi jinping",
                     "reunification", "arizona fab"],
    },
    "China sanctions / export controls": {
        "severity": 3,
        "keywords": ["sanction", "export control", "h200", "h20", "huawei", "smic",
                     "chip ban", "entity list", "ascend", "cambricon"],
    },
    "US power grid constraints": {
        "severity": 3,
        "keywords": ["power grid", "pjm", "ercot", "interconnection", "turbine delay",
                     "transformer shortage", "capacity auction", "data center power",
                     "grid connection", "rate hike"],
    },
    "GPU oversupply / depreciation": {
        "severity": 2,
        "keywords": ["gpu rental", "depreciation", "oversupply", "overcapacity",
                     "coreweave stock", "neocloud", "a100 price"],
    },
    "OpenAI / vendor concentration": {
        "severity": 3,
        "keywords": ["openai", "altman", "circular", "vendor financing",
                     "openai revenue", "stargate"],
    },
    "SPV / off-balance-sheet leverage": {
        "severity": 2,
        "keywords": ["spv", "special purpose", "blue owl", "hyperion", "triple net",
                     "project finance", "credit downgrade", "credit spread widening"],
    },
    "Rare earths / critical minerals": {
        "severity": 2,
        "keywords": ["rare earth", "neodymium", "praseodymium", "gallium",
                     "germanium", "mp materials", "export embargo"],
    },
    "Helium / water / cooling supply": {
        "severity": 1,
        "keywords": ["helium shortage", "water scarcity", "cooling capacity",
                     "iran helium"],
    },
    "AI ROI skepticism": {
        "severity": 2,
        "keywords": ["mit nanda", "95%", "zero return", "pilot phase",
                     "ai disappointment", "productivity gap", "metaverse moment"],
    },
    "Regulatory / antitrust": {
        "severity": 1,
        "keywords": ["antitrust", "ftc ", "doj ", "cma", "european commission",
                     "monopoly", "break up", "regulator"],
    },
    "Nuclear / SMR delays": {
        "severity": 1,
        "keywords": ["smr delay", "small modular reactor", "nuclear restart",
                     "three mile island", "palisades"],
    },
}


def score_headline(text: str) -> dict[str, int]:
    """Return {theme: severity_weight} for themes triggered by this headline."""
    t = text.lower()
    hits: dict[str, int] = {}
    for theme, cfg in RISK_THEMES.items():
        for kw in cfg["keywords"]:
            if kw in t:
                hits[theme] = cfg["severity"]
                break
    return hits
