"""
ui/upload_page.py — upload flow: CSV upload -> load -> clean -> classify ->
show inferred schema with manual override controls -> stash results in
session state for the dashboard views to consume.
"""

from __future__ import annotations

import hashlib

import streamlit as st

from ingestion.classifier import (
    ROLE_DATE,
    ROLE_DIMENSION,
    ROLE_ID,
    ROLE_METRIC,
    ROLE_TEXT,
    ambiguous_columns,
    apply_overrides,
    build_llm_classification_payload,
    classify_columns,
)
from ingestion.cleaner import clean_dataframe
from ingestion.loader import load_file
from insight.cache import clear_view_cache
from insight.client import BudgetExhaustedError, classify_ambiguous_columns

ALL_ROLES = [ROLE_DATE, ROLE_METRIC, ROLE_DIMENSION, ROLE_ID, ROLE_TEXT]


def reset_dataset_state() -> None:
    """Clears all session-state caches, loaded dataframes, classifications,
    export figures, pptx deck buffers, and view insights so a new dataset
    operates with a completely clean slate."""
    keys_to_clear = [
        "dataset",
        "cleaned_df",
        "classifications",
        "_uploaded_filename",
        "_uploaded_file_hash",
        "dataset_name",
        "schema_confirmed",
        "overrides",
        "_export_figures",
        "_pptx_buffer",
        "_view_insights",
        "_load_notes",
        "_clean_messages",
        "_clean_report",
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)
    clear_view_cache()


def render_upload_page() -> bool:
    """Renders the upload UI. Returns True once a dataset is loaded and
    classified and ready for the dashboard tabs to use."""
    st.header("Upload your data")
    st.caption(
        "Your raw data never leaves this server — only small, aggregated "
        "summaries are ever sent to the AI insight layer."
    )

    uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])
    if uploaded is None:
        return "dataset" in st.session_state

    file_bytes = uploaded.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    if st.session_state.get("_uploaded_file_hash") != file_hash:
        reset_dataset_state()
        load_result = load_file(file_bytes, filename=uploaded.name)

        if not load_result.success:
            st.error(f"Could not read this file: {load_result.error}")
            return False

        cleaned_df, clean_report = clean_dataframe(load_result.dataframe)
        classifications = classify_columns(cleaned_df)

        st.session_state["dataset"] = cleaned_df
        st.session_state["classifications"] = {c.name: c for c in classifications}
        st.session_state["_uploaded_filename"] = uploaded.name
        st.session_state["_uploaded_file_hash"] = file_hash
        st.session_state["dataset_name"] = uploaded.name
        st.session_state["schema_confirmed"] = False
        st.session_state["_load_notes"] = load_result.notes
        st.session_state["_clean_messages"] = clean_report.messages
        st.session_state["_clean_report"] = clean_report

    df = st.session_state["dataset"]
    classifications = list(st.session_state["classifications"].values())

    # Data Quality Summary Panel
    clean_report = st.session_state.get("_clean_report")
    load_notes = st.session_state.get("_load_notes", [])
    clean_messages = st.session_state.get("_clean_messages", [])

    with st.expander("📊 Data Quality & Ingestion Summary", expanded=False):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rows Loaded", f"{len(df):,}")
        m2.metric("Columns", len(df.columns))
        m3.metric("Flagged Duplicates", getattr(clean_report, "duplicate_rows_flagged", 0))
        m4.metric("Normalized Nulls", getattr(clean_report, "total_nulls_found", 0))

        if clean_report and (
            clean_report.empty_rows_removed > 0 or clean_report.empty_columns_removed > 0
        ):
            st.caption(
                f"🧹 Dropped {clean_report.empty_rows_removed} fully empty row(s) and {clean_report.empty_columns_removed} spacer column(s)."
            )

        if clean_report and getattr(clean_report, "coercion_failures", None):
            st.warning("⚠️ Unparsed values during type coercion:")
            for c_fail, count in clean_report.coercion_failures.items():
                st.write(
                    f"- **{c_fail}**: {count} cell(s) could not be parsed and were converted to empty/null."
                )

        if load_notes or clean_messages:
            st.write("##### Ingestion Activity Log")
            for note in load_notes:
                st.caption(f"ℹ️ {note}")
            for msg in clean_messages:
                st.caption(f"🧹 {msg}")

    st.subheader("Detected schema")
    st.caption("Review and override any column's role below, then continue to the dashboard.")

    overrides = st.session_state.get("overrides", {})
    ambiguous = {c.name for c in ambiguous_columns(classifications)}

    for c in classifications:
        cols = st.columns([3, 2, 2, 3])
        cols[0].write(c.name)
        flag = " ⚠️ low confidence" if c.name in ambiguous else ""
        cols[1].write(f"{c.role}{flag}")
        cols[2].write(f"{c.confidence:.0%} confidence")
        current_role = overrides.get(c.name, c.role)
        new_role = cols[3].selectbox(
            "Override",
            ALL_ROLES,
            index=ALL_ROLES.index(current_role),
            key=f"override_{c.name}",
            label_visibility="collapsed",
        )
        if new_role != c.role:
            overrides[c.name] = new_role

    st.session_state["overrides"] = overrides

    if ambiguous and st.button(
        "✨ Auto-classify ambiguous columns with AI", key="auto_classify_ai_btn"
    ):
        ambiguous_objs = [c for c in classifications if c.name in ambiguous]
        payload = build_llm_classification_payload(df, ambiguous_objs)
        try:
            llm_results = classify_ambiguous_columns(payload)
            for item in llm_results:
                col_name = item.get("column_name")
                role = item.get("role")
                if col_name in ambiguous and role in ALL_ROLES:
                    overrides[col_name] = role
            st.session_state["overrides"] = overrides
            st.rerun()
        except BudgetExhaustedError:
            st.info("AI classification budget reached — keeping rule-based guesses.")
        except Exception as exc:
            st.warning(f"Could not run AI classification: {exc}")

    if st.button("Confirm schema and build dashboard", type="primary", key="confirm_schema_btn"):
        final_classifications = apply_overrides(classifications, overrides)
        st.session_state["classifications"] = {c.name: c for c in final_classifications}
        st.session_state["schema_confirmed"] = True

    with st.expander("Preview raw data"):
        st.dataframe(df.head(50))

    return bool(st.session_state.get("schema_confirmed"))
