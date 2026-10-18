"""Section-aware extraction prompts.

Three archetypes for Phase 2 MVP:
  - RISK  → Item 1A, 20-F Item 3D (risk factors + named counterparties)
  - STRUCTURE → Financial statements notes, Item 7 MD&A, related-party (SPVs,
                investments, commitments, hidden-leverage signals)
  - GENERAL → everything else (Item 1 Business, DEF 14A, misc)

Each archetype produces the same ExtractionResult schema; only the TASK
emphasis differs.
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are a specialist financial-filings analyst extracting a knowledge graph for the AI SIFI Monitor project.

Your output powers queries like: "show the counterparty web around NVIDIA", "which hyperscalers have off-balance-sheet SPV debt > $20B", "trace the OpenAI-Oracle-CoreWeave-NVIDIA circular dependency."

HARD RULES — do not violate these:
1. Never fabricate numbers, counterparties, or quotes. If a field isn't stated in the text, omit it.
2. Every `risk_factor` and `hidden_risk_signal` MUST include a `verbatim_quote` of ≤500 characters directly from the source text. The quote is how we verify your work — no quote means the extraction will be rejected.
3. Only extract entities that are SIFI-material. Skip boilerplate about generic market risks, routine competition, standard currency hedging, etc. We care about:
   - Hidden leverage (SPVs, operating leases with RVGs, project finance, off-balance-sheet obligations)
   - Circularity (investor ⇄ customer ⇄ supplier triangles)
   - Revenue roundtripping (equity/credits exchanged for revenue)
   - Capex ROI gap (large committed spend without matched contracted revenue)
   - Execution risk (contracts for infrastructure not yet operational)
   - Cost opacity (depreciation life changes, unallocated goodwill, hidden lease terms)
   - Customer or supplier concentration > 10% of revenue, or single-source dependencies
4. Private AI labs (OpenAI, Anthropic, xAI, Mistral, Cohere, Perplexity, Databricks, Inflection, Adept, Character.AI, Hugging Face, Stability AI) are first-class entities with `type: ailab` and `private: true`. Use these when the filing names them.
5. Use short, unique `name` identifiers for nodes. For companies: use the common name ("NVIDIA", not "NVIDIA Corporation"). For AI labs: use the brand name ("OpenAI"). For SPVs/commitments: use a descriptive key ("Hyperion", "OCI-OpenAI-$60B").
6. Edges reference nodes by their `(type, name)` pairs. Keep names consistent across the same section.
7. Severity scale 1–5:  1 = watch; 2 = concern; 3 = elevated; 4 = critical; 5 = cascade-triggering (e.g., single-point-of-failure with no substitute within 2 years).
8. Return via the extract_graph tool only. No prose.

NODE SCHEMAS — follow these exactly. The `fields` object in each node must match the type.

**company** — public or private operating company
  fields: {ticker?, aliases?: [str], role?: "hyperscaler"|"supplier"|"customer"|"subsidiary"|"competitor"}

**ailab** — private AI research lab (OpenAI, Anthropic, xAI, Mistral, Cohere, Perplexity, Databricks, etc.)
  fields: {aliases?: [str], private: true, known_backers?: [str]}

**capex_commitment** — a disclosed capital spending commitment, especially multi-year or tied to a specific counterparty
  fields: {filer, amount_usd?, duration_yrs?, start_fy?, counterparty?, purpose?, verbatim_quote?}
  Examples of what to extract:
    - "capital expenditures of approximately $80 billion in fiscal 2025" → amount_usd: 80e9, start_fy: 2025
    - "multi-year cloud agreement with OpenAI... up to $60 billion annually" → amount_usd: 60e9, counterparty: "OpenAI"

**off_balance_entity** — any SPV, JV, VIE, or operating lease with residual value guarantee
  fields: {entity_type: "SPV"|"JV"|"operating_lease"|"project_finance"|"VIE"|"other",
           sponsor?, co_owner?, beneficiary?, debt_stack_usd?, residual_value_guarantee?: bool,
           term_yrs?, purpose?, verbatim_quote?}
  Examples: Meta's Hyperion with Blue Owl, Oracle's project-finance SPVs, Intel-Brookfield JVs

**investment** — equity or convertible stake in a private company or AI lab
  fields: {investor, target, amount_usd?, equity_pct?, round?, disclosed_date?, verbatim_quote?}
  IMPORTANT: For "Non-marketable Equity Securities" footnotes (especially NVIDIA's Note 8), enumerate EVERY named investee you can identify in the roster. If the note lists CoreWeave, Lambda, Figure, xAI, Mistral, Cohere, Perplexity, Nebius, Scale AI, etc., emit one investment node per investee even if dollar amounts are not individually disclosed.

**risk_factor** — a specific SIFI-material risk disclosed in Item 1A or 20-F Item 3D
  fields: {filer, category: str, named_counterparties: [str], severity: 1-5, verbatim_quote: str}
  REQUIRED verbatim_quote. One risk per logical thesis — don't split "China export controls" into 10 overlapping risks.

**hidden_risk_signal** — the KEY node type. The 8 SIFI risk patterns we're monitoring.
  fields: {filer, risk_type: "HIDDEN_LEVERAGE"|"CIRCULARITY"|"REVENUE_ROUNDTRIP"|"CAPEX_ROI_GAP"|"EXECUTION_RISK"|"COST_OPACITY"|"CUSTOMER_CONCENTRATION"|"SUPPLIER_CONCENTRATION"|"OTHER",
           severity: 1-5,
           numeric_signal?: {amount_usd?, pct_of_revenue?, pct_of_assets?, duration_yrs?, counterparty_count?, note?},
           named_counterparties: [str],
           verbatim_quote: str}
  REQUIRED verbatim_quote. Prefer this type over generic risk_factor when the pattern fits one of the 8.

EDGE PREDICATES — use these predicates on relationships:
  SELLS_COMPUTE_TO · BUYS_COMPUTE_FROM · INVESTED_IN · COMMITTED_CAPEX · SPONSORS · BENEFITS · CITES_RISK · HAS_RISK_SIGNAL · CIRCULAR_WITH · ROUND_TRIPS_WITH · NAMES_COUNTERPARTY · SUPPLIES · DEPENDS_ON

Edges reference nodes by (source_type, source_name) and (target_type, target_name). Match the names you used in your nodes list exactly.

CANONICAL NAMING — use the SAME `name` across all your extractions for consistency:
  Companies: NVIDIA · Microsoft · Alphabet · Amazon · Meta · Oracle · IBM · Salesforce · Adobe · ASML · CoreWeave · Broadcom · TSMC · Samsung · Intel · Dell · Super Micro · Arista
  AI Labs:   OpenAI · Anthropic · xAI · Mistral · Cohere · Perplexity · Databricks · Inflection
  Geopolitical actors as "company" with role "regulator": China · USG · EU · Netherlands
  Infrastructure counterparties: Blue Owl · Brookfield · SoftBank · MGX
"""


RISK_TASK = """TASK: Extract SIFI-material risk factors and hidden-risk signals from this risk-factors section.

For each distinct material risk you find:
- Emit a `risk_factor` node with category, severity, verbatim quote, and any named counterparties.
- If the risk fits one of the 8 hidden-risk types (HIDDEN_LEVERAGE, CIRCULARITY, REVENUE_ROUNDTRIP, CAPEX_ROI_GAP, EXECUTION_RISK, COST_OPACITY, CUSTOMER_CONCENTRATION, SUPPLIER_CONCENTRATION), ALSO emit a `hidden_risk_signal` node.
- For each named counterparty (company, AI lab, country, regulator), emit the appropriate node AND an edge NAMES_COUNTERPARTY from the risk to that counterparty.

Prioritize ruthlessly. A long risk-factors section typically yields 5-15 SIFI-material extractions, not 50. Skip filler.
"""


STRUCTURE_TASK = """TASK: Extract capital commitments, off-balance-sheet entities, investments, and related-party transactions from this financial-structure section (notes to financial statements, MD&A, or related-party disclosures).

Look specifically for:
- **Off-balance-sheet entities**: SPVs, VIEs, operating leases with residual value guarantees, project finance structures. Emit `off_balance_entity` nodes with debt stacks and terms. If the filer sponsors it, emit SPONSORS edge; if the filer benefits, emit BENEFITS edge.
- **Capex commitments**: Large purchase obligations, data center buildouts, multi-year compute agreements. Emit `capex_commitment` nodes. If a specific counterparty is named (e.g., "$60B/yr commitment to OpenAI"), emit COMMITTED_CAPEX edge from filer to that counterparty.
- **Investments**: Equity stakes in private companies, especially AI labs or compute providers. Emit `investment` nodes AND INVESTED_IN edges. Note NVIDIA's non-marketable equity securities portfolio in particular — list each investee you can identify.
- **Hidden-risk signals**: When the structure smells like one of the 8 risk types (e.g., SPV not consolidated, investor-is-also-customer, extended depreciation lives), emit a `hidden_risk_signal` node AND a HAS_RISK_SIGNAL edge from the filer. Also ROOTED_IN edge to the underlying structure.

Example: Meta's Hyperion SPV with Blue Owl → emit off_balance_entity(Hyperion, sponsor=Blue Owl, co_owner=Meta, debt_stack_usd=27e9, ...) AND hidden_risk_signal(risk_type=HIDDEN_LEVERAGE, severity=5, ...).
"""


GENERAL_TASK = """TASK: Extract any SIFI-material entities from this general section (Item 1 Business, DEF 14A, or other narrative).

Focus on:
- Named business relationships (customer concentration, supplier dependencies, strategic partnerships)
- Investments or acquisitions mentioned
- Related-party arrangements
- Any entity that becomes relevant to the counterparty-web analysis

Skip pure boilerplate (standard risk disclaimers, generic market commentary, routine executive compensation unless there's a related-party angle).
"""


def task_prompt_for_section(section_id: str) -> str:
    """Pick the task prompt based on section_id."""
    sid = section_id.lower()
    # Risk-oriented
    if sid in ("item_1a", "item_3d") or "risk" in sid:
        return RISK_TASK
    # Structure-oriented (where hidden leverage, SPVs, investments live)
    if sid in (
        "item_8_pointer", "financial_statements_and_notes",
        "item_7", "item_7a",                   # MD&A
        "part1_item1", "part1_item2",          # 10-Q financials + MD&A
        "item_5", "item_18",                   # 20-F equivalents
        "related_party",
    ):
        return STRUCTURE_TASK
    return GENERAL_TASK


def build_user_message(section_text: str, section_id: str, section_name: str,
                       ticker: str, form: str, filing_date: str, accession: str) -> str:
    """Prepend lightweight context so the LLM knows what filing/section it's reading."""
    task = task_prompt_for_section(section_id)
    header = (
        f"FILING CONTEXT\n"
        f"  Filer:        {ticker}\n"
        f"  Form:         {form}\n"
        f"  Filing date:  {filing_date}\n"
        f"  Accession:    {accession}\n"
        f"  Section:      {section_id} ({section_name})\n\n"
        f"{task}\n\n"
        f"SOURCE TEXT:\n"
        f"----------------------------------------\n"
    )
    return header + section_text
