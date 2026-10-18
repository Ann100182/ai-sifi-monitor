"""Pydantic schemas for GraphRAG extraction output.

Shape:
  ExtractionResult = { nodes: list[Node], edges: list[Edge] }

The LLM returns one ExtractionResult per section. Nodes carry provenance;
edges reference nodes by `(type, name)` tuples that we canonicalize later.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


# ---------- Shared sub-schemas ----------

class Provenance(BaseModel):
    accession: str
    cik: str
    ticker: str
    form: str
    filing_date: str              # YYYY-MM-DD
    fiscal_year: int              # inferred from filing_date
    section_id: str               # e.g. "item_1a"
    section_name: str
    verbatim_quote: Optional[str] = Field(
        default=None,
        description="Exact quote from the filing, max ~500 chars. Omit if not applicable.",
    )


class NumericSignal(BaseModel):
    """Any numeric magnitude the risk/commitment attaches to."""
    amount_usd: Optional[float] = None
    pct_of_revenue: Optional[float] = None
    pct_of_assets: Optional[float] = None
    duration_yrs: Optional[int] = None
    counterparty_count: Optional[int] = None
    note: Optional[str] = Field(default=None, description="Free text if the number needs context")


RISK_TYPES = Literal[
    "HIDDEN_LEVERAGE",
    "CIRCULARITY",
    "REVENUE_ROUNDTRIP",
    "CAPEX_ROI_GAP",
    "EXECUTION_RISK",
    "COST_OPACITY",
    "CUSTOMER_CONCENTRATION",
    "SUPPLIER_CONCENTRATION",
    "OTHER",
]


# ---------- Node types (discriminated by `type`) ----------

class CompanyNode(BaseModel):
    type: Literal["company"]
    name: str
    ticker: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    role: Optional[str] = Field(default=None, description="e.g. 'hyperscaler', 'supplier', 'customer', 'subsidiary'")


class AILabNode(BaseModel):
    type: Literal["ailab"]
    name: str
    aliases: list[str] = Field(default_factory=list)
    private: bool = True
    known_backers: list[str] = Field(default_factory=list, description="Company names known to have invested")


class CapexCommitmentNode(BaseModel):
    type: Literal["capex_commitment"]
    filer: str                                     # ticker or legal name of the filing company
    amount_usd: Optional[float] = None
    duration_yrs: Optional[int] = None
    start_fy: Optional[int] = None
    counterparty: Optional[str] = None             # whom the capex is directed toward
    purpose: Optional[str] = None                  # e.g. "data_center_buildout"
    verbatim_quote: Optional[str] = None


class OffBalanceEntityNode(BaseModel):
    type: Literal["off_balance_entity"]
    name: str                                      # e.g. "Hyperion"
    entity_type: Literal["SPV", "JV", "operating_lease", "project_finance", "VIE", "other"]
    sponsor: Optional[str] = None
    co_owner: Optional[str] = None
    beneficiary: Optional[str] = None
    debt_stack_usd: Optional[float] = None
    residual_value_guarantee: Optional[bool] = None
    term_yrs: Optional[int] = None
    purpose: Optional[str] = None
    verbatim_quote: Optional[str] = None


class InvestmentNode(BaseModel):
    type: Literal["investment"]
    investor: str                                  # usually the filer
    target: str                                    # Company or AILab name
    amount_usd: Optional[float] = None
    equity_pct: Optional[float] = None
    round: Optional[str] = None                    # "Series B", "preferred", "convertible"
    disclosed_date: Optional[str] = None           # YYYY-MM or YYYY
    verbatim_quote: Optional[str] = None


class RiskFactorNode(BaseModel):
    type: Literal["risk_factor"]
    filer: str
    category: str                                  # free-text theme, e.g. "customer_concentration"
    named_counterparties: list[str] = Field(default_factory=list)
    severity: int = Field(ge=1, le=5, description="1=watch, 5=cascade-triggering")
    verbatim_quote: str                            # required for risk factors


class HiddenRiskSignalNode(BaseModel):
    type: Literal["hidden_risk_signal"]
    filer: str
    risk_type: RISK_TYPES
    severity: int = Field(ge=1, le=5)
    numeric_signal: Optional[NumericSignal] = None
    named_counterparties: list[str] = Field(default_factory=list)
    verbatim_quote: str                            # required — THIS is the QA mechanism


# Discriminated union over all node types
Node = Annotated[
    Union[
        CompanyNode, AILabNode, CapexCommitmentNode, OffBalanceEntityNode,
        InvestmentNode, RiskFactorNode, HiddenRiskSignalNode,
    ],
    Field(discriminator="type"),
]


# ---------- Edge types ----------

EDGE_PREDICATES = Literal[
    "SELLS_COMPUTE_TO",
    "BUYS_COMPUTE_FROM",
    "INVESTED_IN",
    "COMMITTED_CAPEX",
    "SPONSORS",
    "BENEFITS",
    "CITES_RISK",
    "HAS_RISK_SIGNAL",
    "CIRCULAR_WITH",
    "ROUND_TRIPS_WITH",
    "NAMES_COUNTERPARTY",
    "SUPPLIES",
    "DEPENDS_ON",
]


class Edge(BaseModel):
    predicate: EDGE_PREDICATES
    source_type: Literal["company", "ailab", "capex_commitment", "off_balance_entity",
                         "investment", "risk_factor", "hidden_risk_signal"]
    source_name: str
    target_type: Literal["company", "ailab", "capex_commitment", "off_balance_entity",
                         "investment", "risk_factor", "hidden_risk_signal"]
    target_name: str
    properties: dict = Field(default_factory=dict,
                             description="Edge properties like {amount_usd, pct, period}")


# ---------- Top-level extraction result ----------

class ExtractionResult(BaseModel):
    """What the LLM returns per section."""
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
    notes: Optional[str] = Field(
        default=None,
        description="Any observations the extractor wants to flag but can't typify, "
                    "e.g. 'section was mostly boilerplate; low signal'.",
    )


# ---------- JSON Schema export for Claude tool_use ----------

def extraction_tool_schema() -> dict:
    """JSON Schema compatible with Anthropic tool_use.input_schema.

    Kept minimal — detailed per-node-type guidance lives in the SYSTEM_PROMPT
    (which is cacheable). The schema here is just structural shape.
    """
    return {
        "type": "object",
        "properties": {
            "nodes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["company", "ailab", "capex_commitment",
                                     "off_balance_entity", "investment",
                                     "risk_factor", "hidden_risk_signal"],
                        },
                        "name": {"type": "string"},
                        "fields": {"type": "object"},
                    },
                    "required": ["type", "name", "fields"],
                },
            },
            "edges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "predicate": {
                            "type": "string",
                            "enum": list(EDGE_PREDICATES.__args__),
                        },
                        "source_type": {"type": "string"},
                        "source_name": {"type": "string"},
                        "target_type": {"type": "string"},
                        "target_name": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                    "required": ["predicate", "source_type", "source_name", "target_type", "target_name"],
                },
            },
            "notes": {"type": "string"},
        },
        "required": ["nodes", "edges"],
    }
