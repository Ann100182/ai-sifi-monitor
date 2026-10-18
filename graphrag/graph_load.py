"""Load extracted nodes + edges into Kuzu (embedded Cypher graph DB).

Kuzu schema:
  Node tables  — one per node type (Company, AILab, CapexCommitment, …)
  Edge tables  — one per predicate (SELLS_COMPUTE_TO, INVESTED_IN, …)

Dedupe strategy:
  Nodes are keyed on (type, canonical_name). Same key across filings merges;
  fiscal_year + provenance accumulate as list properties.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import kuzu

from graphrag.canonicalize import canonical, canonicalize_in_list
from graphrag.config import HERE

DB_PATH = HERE / "cache" / "kuzu"
EXTRACTED = HERE / "cache" / "extracted"

NODE_TYPES = [
    "Company", "AILab", "CapexCommitment", "OffBalanceEntity",
    "Investment", "RiskFactor", "HiddenRiskSignal",
]

# Edge tables: (predicate, source_types, target_types)
# Kuzu requires edge tables to list specific (from, to) type pairs
EDGE_TABLES = {
    "SELLS_COMPUTE_TO":   [("Company", "AILab"), ("Company", "Company")],
    "BUYS_COMPUTE_FROM":  [("Company", "Company")],
    "INVESTED_IN":        [("Company", "AILab"), ("Company", "Company")],
    "COMMITTED_CAPEX":    [("Company", "Company"), ("Company", "AILab"), ("Company", "CapexCommitment")],
    "SPONSORS":           [("Company", "OffBalanceEntity")],
    "BENEFITS":           [("OffBalanceEntity", "Company")],
    "CITES_RISK":         [("Company", "RiskFactor")],
    "HAS_RISK_SIGNAL":    [("Company", "HiddenRiskSignal")],
    "CIRCULAR_WITH":      [("Company", "Company"), ("Company", "AILab")],
    "ROUND_TRIPS_WITH":   [("Company", "Company"), ("Company", "AILab")],
    "NAMES_COUNTERPARTY": [("RiskFactor", "Company"), ("RiskFactor", "AILab"),
                           ("HiddenRiskSignal", "Company"), ("HiddenRiskSignal", "AILab")],
    "SUPPLIES":           [("Company", "Company"), ("Company", "AILab")],
    "DEPENDS_ON":         [("Company", "Company"), ("Company", "AILab")],
}


# Type name capitalization for Kuzu
TYPE_MAP = {
    "company": "Company", "ailab": "AILab",
    "capex_commitment": "CapexCommitment", "off_balance_entity": "OffBalanceEntity",
    "investment": "Investment", "risk_factor": "RiskFactor",
    "hidden_risk_signal": "HiddenRiskSignal",
}


def _f(v) -> float:
    """Robust float coercion. LLM sometimes puts explanatory strings in numeric slots."""
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _i(v) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _s(v) -> str:
    """String coercion — flatten lists/dicts to repr if non-string."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    try:
        return str(v)
    except Exception:
        return ""


def _b(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "yes", "y", "1")
    return bool(v)


def _init_schema(conn):
    """Create node + edge tables. Idempotent — drops first if present."""
    # Clean reset for development; comment out for incremental loads
    for t in NODE_TYPES:
        try:
            conn.execute(f"DROP TABLE {t}")
        except Exception:
            pass

    conn.execute("""
        CREATE NODE TABLE Company(
            name STRING PRIMARY KEY,
            ticker STRING,
            aliases STRING[],
            role STRING,
            provenance STRING[]
        )
    """)
    conn.execute("""
        CREATE NODE TABLE AILab(
            name STRING PRIMARY KEY,
            aliases STRING[],
            private BOOLEAN,
            known_backers STRING[],
            provenance STRING[]
        )
    """)
    conn.execute("""
        CREATE NODE TABLE CapexCommitment(
            name STRING PRIMARY KEY,
            filer STRING,
            amount_usd DOUBLE,
            duration_yrs INT64,
            start_fy INT64,
            counterparty STRING,
            purpose STRING,
            verbatim_quote STRING,
            provenance STRING[]
        )
    """)
    conn.execute("""
        CREATE NODE TABLE OffBalanceEntity(
            name STRING PRIMARY KEY,
            entity_type STRING,
            sponsor STRING,
            co_owner STRING,
            beneficiary STRING,
            debt_stack_usd DOUBLE,
            residual_value_guarantee BOOLEAN,
            term_yrs INT64,
            purpose STRING,
            verbatim_quote STRING,
            provenance STRING[]
        )
    """)
    conn.execute("""
        CREATE NODE TABLE Investment(
            name STRING PRIMARY KEY,
            investor STRING,
            target STRING,
            amount_usd DOUBLE,
            equity_pct DOUBLE,
            round STRING,
            disclosed_date STRING,
            verbatim_quote STRING,
            provenance STRING[]
        )
    """)
    conn.execute("""
        CREATE NODE TABLE RiskFactor(
            name STRING PRIMARY KEY,
            filer STRING,
            category STRING,
            severity INT64,
            verbatim_quote STRING,
            provenance STRING[]
        )
    """)
    conn.execute("""
        CREATE NODE TABLE HiddenRiskSignal(
            name STRING PRIMARY KEY,
            filer STRING,
            risk_type STRING,
            severity INT64,
            amount_usd DOUBLE,
            pct_of_revenue DOUBLE,
            duration_yrs INT64,
            numeric_note STRING,
            verbatim_quote STRING,
            provenance STRING[]
        )
    """)

    for predicate, pairs in EDGE_TABLES.items():
        # Drop existing
        try: conn.execute(f"DROP TABLE {predicate}")
        except Exception: pass
        pair_sql = ", ".join(f"FROM {s} TO {t}" for s, t in pairs)
        conn.execute(f"CREATE REL TABLE {predicate}({pair_sql})")


_UNGROUNDED_QUOTES = ("no specific reference", "no direct reference", "not found in provided text")


def _is_grounded(ntype: str, fields: dict) -> bool:
    """Synthetic nodes must carry a real verbatim quote. The extractor occasionally
    invents an entity with an empty / 'No specific reference found' quote; left in,
    such a node can win a name collision and overwrite a real one (e.g. a phantom
    Salesforce 'Hyperion' masking Meta's Blue Owl JV)."""
    if ntype in ("Company", "AILab"):
        return True
    f = fields if isinstance(fields, dict) else {}
    q = _s(f.get("verbatim_quote")).strip().lower()
    return bool(q) and not any(m in q for m in _UNGROUNDED_QUOTES)


def _canonical_node_key(ntype: str, raw_name: str) -> str:
    """Nodes that denote entities get canonicalized; synthetic nodes (commitment,
    risk, etc.) use the raw name because they're per-filing artifacts."""
    if ntype in ("Company", "AILab"):
        return canonical(raw_name) if raw_name else "Unknown"
    return raw_name or "Unknown"


def _node_props(ntype: str, name: str, fields: dict, provenance: str) -> dict:
    """Convert extracted fields to typed properties the Kuzu schema expects."""
    f = fields if isinstance(fields, dict) else {}
    base = {"name": name, "provenance": [provenance]}
    if ntype == "Company":
        return {**base,
                "ticker": _s(f.get("ticker")),
                "aliases": [a for a in (f.get("aliases") or []) if isinstance(a, str)],
                "role": _s(f.get("role"))}
    if ntype == "AILab":
        return {**base,
                "aliases": [a for a in (f.get("aliases") or []) if isinstance(a, str)],
                "private": _b(f.get("private", True)),
                "known_backers": canonicalize_in_list(f.get("known_backers") or [])}
    if ntype == "CapexCommitment":
        return {**base,
                "filer": canonical(_s(f.get("filer"))),
                "amount_usd": _f(f.get("amount_usd")),
                "duration_yrs": _i(f.get("duration_yrs")),
                "start_fy": _i(f.get("start_fy")),
                "counterparty": canonical(_s(f.get("counterparty"))),
                "purpose": _s(f.get("purpose")),
                "verbatim_quote": _s(f.get("verbatim_quote"))[:1000]}
    if ntype == "OffBalanceEntity":
        return {**base,
                "entity_type": _s(f.get("entity_type")) or "other",
                "sponsor": canonical(_s(f.get("sponsor"))),
                "co_owner": canonical(_s(f.get("co_owner"))),
                "beneficiary": canonical(_s(f.get("beneficiary"))),
                "debt_stack_usd": _f(f.get("debt_stack_usd")),
                "residual_value_guarantee": _b(f.get("residual_value_guarantee")),
                "term_yrs": _i(f.get("term_yrs")),
                "purpose": _s(f.get("purpose")),
                "verbatim_quote": _s(f.get("verbatim_quote"))[:1000]}
    if ntype == "Investment":
        return {**base,
                "investor": canonical(_s(f.get("investor"))),
                "target": canonical(_s(f.get("target"))),
                "amount_usd": _f(f.get("amount_usd")),
                "equity_pct": _f(f.get("equity_pct")),
                "round": _s(f.get("round")),
                "disclosed_date": _s(f.get("disclosed_date")),
                "verbatim_quote": _s(f.get("verbatim_quote"))[:1000]}
    if ntype == "RiskFactor":
        return {**base,
                "filer": canonical(_s(f.get("filer"))),
                "category": _s(f.get("category")),
                "severity": _i(f.get("severity") or 3),
                "verbatim_quote": _s(f.get("verbatim_quote"))[:1500]}
    if ntype == "HiddenRiskSignal":
        num = f.get("numeric_signal") if isinstance(f.get("numeric_signal"), dict) else {}
        return {**base,
                "filer": canonical(_s(f.get("filer"))),
                "risk_type": _s(f.get("risk_type")) or "OTHER",
                "severity": _i(f.get("severity") or 3),
                "amount_usd": _f(num.get("amount_usd")),
                "pct_of_revenue": _f(num.get("pct_of_revenue")),
                "duration_yrs": _i(num.get("duration_yrs")),
                "numeric_note": _s(num.get("note")),
                "verbatim_quote": _s(f.get("verbatim_quote"))[:1500]}
    return base


def _upsert_node(conn, ntype: str, props: dict):
    """MERGE-style insert using Kuzu Cypher. Appends provenance if node exists."""
    name = props["name"]
    # Does it exist? (param name must not collide with node variable `n`)
    check = conn.execute(
        f"MATCH (node:{ntype} {{name: $nm}}) RETURN node.provenance AS p",
        {"nm": name},
    )
    row = check.get_next() if check.has_next() else None
    if row:
        existing = row[0] or []
        new_prov = list(set(list(existing) + props["provenance"]))
        conn.execute(
            f"MATCH (node:{ntype} {{name: $nm}}) SET node.provenance = $p",
            {"nm": name, "p": new_prov},
        )
    else:
        cols = list(props.keys())
        placeholders = ", ".join(f"{c}: ${c}" for c in cols)
        conn.execute(f"CREATE (node:{ntype} {{{placeholders}}})", props)


def _add_edge(conn, predicate: str, src_type: str, src_name: str,
              tgt_type: str, tgt_name: str):
    """Create edge if both endpoints exist. Silently skip missing endpoints."""
    try:
        conn.execute(
            f"MATCH (src:{src_type} {{name: $sn}}), (tgt:{tgt_type} {{name: $tn}}) "
            f"CREATE (src)-[:{predicate}]->(tgt)",
            {"sn": src_name, "tn": tgt_name},
        )
    except Exception:
        pass  # missing endpoint or schema mismatch — skip


def load_all():
    """Walk every extracted.json, dedupe + canonicalize, load into Kuzu."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Clean slate for development reloads (Kuzu may store as file or directory)
    import shutil
    if DB_PATH.exists():
        if DB_PATH.is_dir():
            shutil.rmtree(DB_PATH)
        else:
            DB_PATH.unlink()
    # Also remove sidecar files Kuzu may create
    for sidecar in DB_PATH.parent.glob(f"{DB_PATH.name}.*"):
        sidecar.unlink()

    db = kuzu.Database(str(DB_PATH))
    conn = kuzu.Connection(db)
    print("initializing schema...")
    _init_schema(conn)

    # First pass: collect all nodes with provenance
    nodes_by_key: dict[tuple, dict] = {}
    edges: list[tuple] = []

    files = sorted(EXTRACTED.glob("*/*/extracted.json"))
    print(f"scanning {len(files)} extracted files...")
    skipped_edges = 0
    skipped_ungrounded = 0
    for ex in files:
        cik = ex.parent.parent.name
        acc = ex.parent.name
        data = json.loads(ex.read_text())
        provenance = f"{cik}:{acc}"
        for sid, result in data.items():
            if not isinstance(result, dict):
                continue
            nodes_raw = result.get("nodes") or []
            if not isinstance(nodes_raw, list):
                continue
            # Build an in-section name resolution map so edges can find nodes
            section_resolution: dict[tuple, tuple] = {}
            for n in nodes_raw:
                if not isinstance(n, dict):
                    continue
                raw_type = n.get("type", "").lower()
                ntype = TYPE_MAP.get(raw_type)
                if not ntype:
                    continue
                if not _is_grounded(ntype, n.get("fields")):
                    skipped_ungrounded += 1
                    continue
                raw_name = n.get("name") or ""
                canon = _canonical_node_key(ntype, raw_name)
                key = (ntype, canon)
                props = _node_props(ntype, canon, n.get("fields") or {}, provenance)
                if key in nodes_by_key:
                    # merge provenance
                    existing = nodes_by_key[key]
                    existing["provenance"] = list(set(existing["provenance"] + props["provenance"]))
                else:
                    nodes_by_key[key] = props
                # Record mapping for edges within this section
                section_resolution[(raw_type, raw_name)] = (ntype, canon)

            edges_raw = result.get("edges") or []
            if not isinstance(edges_raw, list):
                continue
            for e in edges_raw:
                if not isinstance(e, dict):
                    continue
                predicate = e.get("predicate")
                if predicate not in EDGE_TABLES:
                    skipped_edges += 1
                    continue
                src_raw_type = (e.get("source_type") or "").lower()
                tgt_raw_type = (e.get("target_type") or "").lower()
                src_raw = e.get("source_name") or ""
                tgt_raw = e.get("target_name") or ""
                src = section_resolution.get((src_raw_type, src_raw))
                tgt = section_resolution.get((tgt_raw_type, tgt_raw))
                if not src:
                    # Fallback: canonicalize by inferring type from map
                    nt = TYPE_MAP.get(src_raw_type)
                    if nt: src = (nt, _canonical_node_key(nt, src_raw))
                if not tgt:
                    nt = TYPE_MAP.get(tgt_raw_type)
                    if nt: tgt = (nt, _canonical_node_key(nt, tgt_raw))
                if src and tgt:
                    edges.append((predicate, src[0], src[1], tgt[0], tgt[1]))

    print(f"collected {len(nodes_by_key)} unique nodes, {len(edges)} edges "
          f"({skipped_edges} edges skipped — unknown predicate; "
          f"{skipped_ungrounded} ungrounded nodes dropped)")

    # Insert nodes
    print("loading nodes...")
    by_type_count = defaultdict(int)
    for (ntype, _), props in nodes_by_key.items():
        _upsert_node(conn, ntype, props)
        by_type_count[ntype] += 1
    for t, c in sorted(by_type_count.items(), key=lambda x: -x[1]):
        print(f"  {t:<22}{c:>5}")

    # Insert edges
    print("loading edges...")
    edges_inserted = 0
    edges_skipped = 0
    for pred, st, sn, tt, tn in edges:
        if (st, tt) not in EDGE_TABLES[pred]:
            edges_skipped += 1
            continue
        _add_edge(conn, pred, st, sn, tt, tn)
        edges_inserted += 1
    print(f"  inserted {edges_inserted} edges; {edges_skipped} skipped (schema mismatch)")

    return conn
