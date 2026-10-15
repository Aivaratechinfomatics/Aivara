"""
ui/upload_page.py — Handles CSV/Excel uploading, type inference review,
and manual schema overrides.
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
    classify_columns,
)
from ingestion.cleaner import clean_dataframe
from ingestion.loader import load_file
from insight.cache import clear_view_cache

ALL_ROLES = [ROLE_DATE, ROLE_METRIC, ROLE_DIMENSION, ROLE_ID, ROLE_TEXT]


def reset_dataset_state() -> None:
    """Clears all dataset-derived keys from session state so a new upload
    gets a completely clean slate."""
    keys_to_clear = [
        "dataset",
        "cleaned_df",
        "classifications",
        "overrides",
        "pipeline_result",
        "dataset_name",
        "_uploaded_filename",
        "_uploaded_file_hash",
        "_export_figures",
        "_export_figure_blobs",
        "_pptx_buffer",
        "schema_confirmed",
        "_load_notes",
        "_clean_messages",
        "_clean_report",
        "_view_insights",
    ]
    for k in keys_to_clear:
        st.session_state.pop(k, None)
    clear_view_cache()


def render_upload_page() -> bool:
    """Renders the upload UI. Returns True once a dataset is loaded and
    classified and ready for the dashboard tabs to use."""
    is_confirmed = bool(st.session_state.get("schema_confirmed"))
    df = st.session_state.get("dataset")

    # If dataset is already confirmed, hide the upload and schema sections from
    # the main area so the dashboard, scorecards, and charts appear at the top.
    if is_confirmed and df is not None:
        if st.sidebar.button("📂 Load New Dataset", key="btn_load_new_dataset"):
            reset_dataset_state()
            st.session_state["schema_confirmed"] = False
            st.rerun()

        with st.sidebar.expander("ℹ️ Ingestion & Schema Details", expanded=False):
            st.write(f"**File:** `{st.session_state.get('dataset_name')}`")
            st.write(f"**Rows:** {len(df):,}")
            st.write(f"**Columns:** {len(df.columns)}")
            for col_name, c in st.session_state.get("classifications", {}).items():
                st.caption(f"`{col_name}`: {c.role}")

        dataset_name = st.session_state.get("dataset_name", "Uploaded Dataset")
        st.caption(
            f"📁 Active Dataset: **{dataset_name}** ({len(df):,} rows, {len(df.columns)} columns)"
        )
        return True

    # If not confirmed yet, render the full upload form and schema review gate
    st.header("Upload your data")
    st.caption(
        "Your raw data never leaves this server — only small, aggregated "
        "summaries are ever sent to the AI insight layer."
    )

    uploaded = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx", "xls"])
    if uploaded is None:
        return "dataset" in st.session_state and is_confirmed

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
    saved_clean_report = st.session_state.get("_clean_report")
    load_notes = st.session_state.get("_load_notes", [])
    clean_messages = st.session_state.get("_clean_messages", [])

    with st.expander("📊 Data Quality & Ingestion Summary", expanded=False):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Rows Loaded", f"{len(df):,}")
        m2.metric("Columns", len(df.columns))
        m3.metric("Flagged Duplicates", getattr(saved_clean_report, "duplicate_rows_flagged", 0))
        m4.metric("Normalized Nulls", getattr(saved_clean_report, "total_nulls_found", 0))

        if saved_clean_report and (
            saved_clean_report.empty_rows_removed > 0
            or saved_clean_report.empty_columns_removed > 0
        ):
            st.caption(
                f"🧹 Dropped {saved_clean_report.empty_rows_removed} fully empty row(s) and {saved_clean_report.empty_columns_removed} spacer column(s)."
            )

        if saved_clean_report and getattr(saved_clean_report, "coercion_failures", None):
            st.warning("⚠️ Unparsed values during type coercion:")
            for c_fail, count in saved_clean_report.coercion_failures.items():
                st.write(
                    f"- **{c_fail}**: {count} cell(s) could not be parsed and were converted to empty/null."
                )

        if load_notes or clean_messages:
            st.write("##### Ingestion Activity Log")
            for note in load_notes:
                st.caption(f"ℹ️ {note}")
            for msg in clean_messages:
                st.caption(f"🧹 {msg}")

    with st.expander("⚙️ Detected Schema & Column Roles", expanded=True):
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

        if st.button(
            "Confirm schema and build dashboard", type="primary", key="confirm_schema_btn"
        ):
            final_classifications = apply_overrides(classifications, overrides)
            st.session_state["classifications"] = {c.name: c for c in final_classifications}
            st.session_state["schema_confirmed"] = True
            st.rerun()

    with st.expander("Preview raw data"):
        st.dataframe(df.head(50))

    return False
