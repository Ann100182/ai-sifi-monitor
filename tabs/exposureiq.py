"""Tab 5 — ExposureIQ: GraphRAG Q&A over SEC filings.

Lives on top of graphrag/query.py (LangGraph query engine).
"""

from __future__ import annotations

import streamlit as st


def _try_import_query_engine():
    try:
        from graphrag.query import answer
        return answer, None
    except Exception as e:
        return None, str(e)


SUGGESTED_QUERIES = [
    "Which SPVs does Meta sponsor?",
    "Trace the OpenAI counterparty web across Microsoft, Oracle, and CoreWeave.",
    "What hidden-leverage signals above severity 4 appear in the latest 10-Ks?",
    "Which companies have the most severe customer concentration risk signals?",
    "List every NVIDIA investment disclosed across the past 3 years.",
    "Which companies have the largest capex ROI gap signals?",
]

_STEP_LABELS = {
    "classify": "Classify",
    "graph_search": "Graph → Cypher",
    "cypher_repair": "Cypher repair",
    "synthesize": "Synthesize",
}


def _pipeline_caption(result) -> str:
    """One-line view of the LangGraph path this question took."""
    if result.strategy == "hybrid" or result.complexity == "multihop":
        retrieval = "Graph ∥ Vector"
    else:
        retrieval = "Graph" if result.strategy == "graph" else "Vector"
    model = "Opus 4.7" if "opus" in result.model_used else "Sonnet 4.6"
    return f"Classify → {retrieval} → Synthesize ({model})"


def _citation_header(e) -> str:
    """Accepts an EvidenceChunk or a provenance dict from extra['all_filings']."""
    get = e.get if isinstance(e, dict) else lambda k: getattr(e, k, "")
    return " · ".join(x for x in (get("ticker"), get("form"), get("filing_date")) if x)


def _render_result(result):
    st.markdown("### Answer")
    st.markdown(result.answer)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Strategy", f"{result.strategy.upper()}")
    c2.metric("Complexity", result.complexity.upper())
    c3.metric("Evidence", len(result.evidence))
    c4.metric("Cost", f"${result.cost_usd:.4f}")
    c5.metric("Latency", f"{result.seconds:.0f}s")
    st.caption(f"LangGraph path: {_pipeline_caption(result)}")

    with st.expander("⚙️ Pipeline trace (every LLM call)"):
        st.dataframe(
            [{
                "Step": _STEP_LABELS.get(c.step, c.step),
                "Model": c.model,
                "Input tok": c.input_tokens,
                "Output tok": c.output_tokens,
                "Cost ($)": round(c.cost_usd, 4),
                "Seconds": round(c.seconds, 1),
            } for c in result.calls],
            hide_index=True, width="stretch",
        )

    graph_ev = [(i, e) for i, e in enumerate(result.evidence, 1) if e.source == "graph"]
    vector_ev = [(i, e) for i, e in enumerate(result.evidence, 1) if e.source == "vector"]

    with st.expander(f"📎 Evidence — {len(graph_ev)} graph facts · {len(vector_ev)} filing excerpts"):
        if graph_ev:
            st.markdown("**Knowledge graph facts**")
            for i, e in graph_ev:
                hdr = _citation_header(e)
                st.markdown(f"**[E{i}]** `graph`{' — ' + hdr if hdr else ''}")
                st.caption(e.text[:600])
                more = e.extra.get("all_filings") or []
                if len(more) > 1:
                    st.caption("Also in: " + ", ".join(
                        _citation_header(f) or f["accession"] for f in more[1:6]))
            cyphers = list(dict.fromkeys(e.extra.get("cypher") for _, e in graph_ev if e.extra.get("cypher")))
            if cyphers:
                st.markdown("**Cypher executed**")
                for q in cyphers:
                    st.code(q, language="cypher")
        if vector_ev:
            st.markdown("**Filing excerpts**")
            for i, e in vector_ev:
                dist = e.extra.get("distance")
                dist_str = f" · similarity={1 - dist:.2f}" if dist is not None else ""
                st.markdown(f"**[E{i}]** `vector` — {_citation_header(e)} · {e.section_id}{dist_str}")
                st.caption(e.text[:600])


def render():
    answer_fn, err = _try_import_query_engine()

    st.markdown("##### Suggested starter questions")
    cols = st.columns(3)
    for i, q in enumerate(SUGGESTED_QUERIES):
        with cols[i % 3]:
            if st.button(q, key=f"sug_{i}", width="stretch"):
                st.session_state["eiq_input"] = q
                st.session_state["eiq_autorun"] = True

    q = st.text_area(
        "Ask ExposureIQ about hidden exposures in the SEC filings:",
        key="eiq_input",
        height=90,
        placeholder="e.g., 'What off-balance-sheet entities does Meta sponsor?'",
    )

    col1, _ = st.columns([1, 5])
    with col1:
        go = st.button("🔎 Ask", type="primary", width="stretch")
    go = go or st.session_state.pop("eiq_autorun", False)

    if answer_fn is None:
        st.error(f"Query engine import failed: `{err[:300]}`")
        return

    if go and q.strip():
        with st.status("Running LangGraph pipeline…", expanded=False) as status:
            try:
                result = answer_fn(q.strip(), verbose=False)
            except Exception as e:
                status.update(label="Query failed", state="error")
                st.error(f"{type(e).__name__}: {str(e)[:400]}")
                return
            status.update(label=f"Done · {_pipeline_caption(result)}", state="complete")
        st.session_state["eiq_result"] = result

    # Persist the last answer across reruns (e.g. switching tabs / sidebar changes)
    result = st.session_state.get("eiq_result")
    if result is not None:
        if result.question != q.strip():
            st.caption(f"Showing last answer for: _{result.question}_")
        _render_result(result)
