"""
AI SIFI Monitor — 45-player universe.

Sourced from:
- JP Morgan 2026 Outlook (Michael Cembalest): 42-stock AI universe
- Semiscaler foundation: ASML, TSMC
- Neocloud leveraged node: CoreWeave

Organized into 8 tiers matching the AI infrastructure stack. Tier 1 = foundational
(power), Tier 8 = application layer. Failure of a lower-tier node cascades up.

Risk score (1-10): cascade potential if this player fails or stresses, incorporating
tier severity, leverage, concentration, and news exposure. Hand-tuned from Cembalest
WCGW analysis.

Invest score (1-10): risk-adjusted opportunity — moat strength + growth runway +
valuation. Not a buy recommendation; a relative ranking within the SIFI universe.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    ticker: str
    name: str
    tier: int
    tier_name: str
    country: str
    risk_score: int        # 1-10, higher = more cascade risk
    invest_score: int      # 1-10, higher = better risk-adjusted opportunity
    bull_factor: str       # one-line thesis
    rationale: str         # SIFI role


TIERS = {
    1: "Power Generation (Utilities)",
    2: "Grid & Electrical Capital Equipment",
    3: "Semi Equipment & EDA",
    4: "Semi Design",
    5: "Semi Manufacturing",
    6: "AI Hardware & Networking",
    7: "Hyperscalers & Cloud",
    8: "AI Software, Apps & Security",
}


PLAYERS: list[Player] = [
    # Tier 1 — Power Generation (8)
    Player("NRG",   "NRG Energy",                1, TIERS[1], "USA", 6, 7, "PJM capacity price surge",      "Retail + generation; PJM capacity exposure"),
    Player("VST",   "Vistra",                    1, TIERS[1], "USA", 7, 8, "Direct hyperscaler PPAs",       "Nuclear + gas; direct hyperscaler PPAs"),
    Player("NEE",   "NextEra Energy",            1, TIERS[1], "USA", 5, 7, "Largest US renewables buildout","Largest US renewables; data center demand"),
    Player("CEG",   "Constellation Energy",      1, TIERS[1], "USA", 7, 9, "Three Mile Island restart",     "Microsoft TMI restart; nuclear PPAs"),
    Player("SO",    "Southern Company",          1, TIERS[1], "USA", 5, 6, "Vogtle nuclear completion",     "SE US; Vogtle AP1000 fleet"),
    Player("PEG",   "Public Service Enterprise", 1, TIERS[1], "USA", 4, 6, "NJ nuclear fleet",              "NJ nuclear + T&D"),
    Player("ETR",   "Entergy",                   1, TIERS[1], "USA", 6, 7, "Meta Hyperion power supplier",  "LA/MS/TX; Meta Hyperion data center"),
    Player("NI",    "NiSource",                  1, TIERS[1], "USA", 4, 5, "Midwest gas + electric",        "Gas + electric midwestern utility"),

    # Tier 2 — Grid & Electrical Capital Equipment (6)
    Player("ETN",   "Eaton",                     2, TIERS[2], "USA", 5, 8, "Switchgear backlog",            "Power management for data centers"),
    Player("GEV",   "GE Vernova",                2, TIERS[2], "USA", 7, 9, "Gas turbine 7yr backlog",       "Gas turbines; HV equipment"),
    Player("TT",    "Trane Technologies",        2, TIERS[2], "USA", 4, 7, "Data center cooling demand",    "Data center cooling systems"),
    Player("JCI",   "Johnson Controls",          2, TIERS[2], "USA", 4, 6, "HVAC + building controls",      "HVAC + building controls"),
    Player("PWR",   "Quanta Services",           2, TIERS[2], "USA", 5, 8, "Transformer bottleneck play",   "T&D construction"),
    Player("EME",   "EMCOR",                     2, TIERS[2], "USA", 4, 7, "Mech/electrical contractor",    "Mechanical/electrical construction"),

    # Tier 3 — Semi Equipment & EDA (2)
    Player("ASML",  "ASML Holding",              3, TIERS[3], "NLD", 8, 8, "EUV lithography monopoly",      "EUV monopoly; irreplaceable <5nm"),
    Player("CDNS",  "Cadence Design",            3, TIERS[3], "USA", 5, 8, "EDA duopoly with Synopsys",     "EDA; chip design software"),

    # Tier 4 — Semi Design (7)
    Player("NVDA",  "NVIDIA",                    4, TIERS[4], "USA", 9, 9, "Blackwell/Rubin GPU monopoly",  "GPU incumbent; cascade center"),
    Player("AMD",   "Advanced Micro Devices",    4, TIERS[4], "USA", 7, 8, "MI300/MI400 accelerators",      "Challenger GPU + CPU share"),
    Player("AVGO",  "Broadcom",                  4, TIERS[4], "USA", 7, 8, "Hyperscaler custom silicon",    "Custom ASICs + networking"),
    Player("QCOM",  "Qualcomm",                  4, TIERS[4], "USA", 5, 6, "Edge AI inference leader",      "Mobile + edge AI"),
    Player("INTC",  "Intel",                     4, TIERS[4], "USA", 8, 5, "US foundry comeback bet",       "US govt equity stake; foundry bet"),
    Player("NXPI",  "NXP Semiconductors",        4, TIERS[4], "NLD", 4, 6, "Auto + industrial chips",       "Auto + industrial semis"),
    Player("MU",    "Micron Technology",         4, TIERS[4], "USA", 7, 8, "HBM is binding constraint",     "HBM memory — AI compute bottleneck"),

    # Tier 5 — Semi Manufacturing (1)
    Player("TSM",   "Taiwan Semiconductor",      5, TIERS[5], "TWN", 10, 9, "Irreplaceable leading-edge",   "Single point of failure for <5nm"),

    # Tier 6 — AI Hardware & Networking (4)
    Player("SMCI",  "Super Micro Computer",      6, TIERS[6], "USA", 8, 7, "GPU server integrator",         "GPU server integrator; audit history"),
    Player("DELL",  "Dell Technologies",         6, TIERS[6], "USA", 6, 7, "AI server backlog growth",      "Enterprise AI server channel"),
    Player("HPQ",   "HP Inc",                    6, TIERS[6], "USA", 4, 5, "AI PC refresh cycle",           "PCs + print; AI PC narrative"),
    Player("ANET",  "Arista Networks",           6, TIERS[6], "USA", 6, 8, "AI data center networking",     "AI DC networking; MSFT/META wins"),

    # Tier 7 — Hyperscalers & Cloud (7)
    Player("MSFT",  "Microsoft",                 7, TIERS[7], "USA", 7, 8, "M365 Copilot monetization",     "Azure + OpenAI; AI revenue discloser"),
    Player("GOOGL", "Alphabet",                  7, TIERS[7], "USA", 6, 8, "TPU v7 cost advantage",         "GCP + TPUs + Gemini; vertical stack"),
    Player("AMZN",  "Amazon",                    7, TIERS[7], "USA", 7, 8, "AWS AI revenue acceleration",   "AWS + Trainium/Inferentia"),
    Player("META",  "Meta Platforms",            7, TIERS[7], "USA", 7, 9, "Llama ecosystem + ad margins",  "70% capex/rev; Hyperion SPV debt"),
    Player("ORCL",  "Oracle",                    7, TIERS[7], "USA", 9, 6, "OCI capacity expansion",        "OpenAI $60B commitment; levered"),
    Player("IBM",   "IBM",                       7, TIERS[7], "USA", 4, 6, "Hybrid cloud + Red Hat",        "watsonx + Red Hat"),
    Player("CRWV",  "CoreWeave",                 7, TIERS[7], "USA", 9, 7, "Pure-play AI compute",          "Most levered neocloud; GPU rental"),

    # Tier 8 — AI Software, Apps & Security (10)
    Player("PLTR",  "Palantir",                  8, TIERS[8], "USA", 6, 8, "Gov + commercial AI deployment","Gov + commercial AI; high valuation"),
    Player("CRM",   "Salesforce",                8, TIERS[8], "USA", 5, 7, "Agentforce monetization",       "Agentforce; enterprise SaaS AI"),
    Player("NOW",   "ServiceNow",                8, TIERS[8], "USA", 5, 8, "Workflow AI leader",            "Workflow AI; strong revenue traction"),
    Player("ADBE",  "Adobe",                     8, TIERS[8], "USA", 5, 6, "Firefly + creative AI",         "Firefly; creative AI monetization"),
    Player("AAPL",  "Apple",                     8, TIERS[8], "USA", 5, 7, "2.2B active devices",           "On-device AI; TSMC largest customer"),
    Player("TSLA",  "Tesla",                     8, TIERS[8], "USA", 8, 7, "FSD + Dojo + Optimus",          "FSD + Dojo; valuation stretched"),
    Player("UBER",  "Uber",                      8, TIERS[8], "USA", 5, 7, "AV platform + ML dispatch",     "ML dispatch; AV platform"),
    Player("PANW",  "Palo Alto Networks",        8, TIERS[8], "USA", 4, 7, "Platform consolidation",        "Security platform consolidation"),
    Player("CRWD",  "CrowdStrike",               8, TIERS[8], "USA", 5, 8, "AI SOC leader",                 "Endpoint + AI SOC"),
    Player("FTNT",  "Fortinet",                  8, TIERS[8], "USA", 4, 6, "Network security",              "Network security appliances"),
]


def by_tier() -> dict[int, list[Player]]:
    """Return players grouped by tier."""
    out: dict[int, list[Player]] = {t: [] for t in TIERS}
    for p in PLAYERS:
        out[p.tier].append(p)
    return out


def tickers() -> list[str]:
    return [p.ticker for p in PLAYERS]


def status_from_risk(score: int) -> tuple[str, str]:
    """Map risk score to (status_label, color_hex)."""
    if score >= 9:
        return "CRITICAL", "#E74C3C"
    if score >= 7:
        return "ELEVATED", "#F39C12"
    if score >= 5:
        return "WATCH", "#F1C40F"
    return "NORMAL", "#2ECC71"


assert len(PLAYERS) == 45, f"expected 45 players, got {len(PLAYERS)}"
