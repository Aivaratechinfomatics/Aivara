"""
app.py — Main Streamlit application entry point.

Coordinates:
- Security & reverse-proxy authentication enforcement
- Sidebar settings and budget tracking
- Ingestion, schema review, and data quality display
- Typed analytics pipeline execution
- Boardroom executive takeaways
- Table-driven tab dispatch with per-tab error boundaries
- Pure PPTX export assembly and presentation download
"""

from __future__ import annotations

import streamlit as st

import config
from analytics.pipeline import PipelineResult, run_pipeline
from config import mask_secret
from export.deck_assembly import assemble_deck_inputs
from export.pptx_builder import build_deck
from insight.budget import get_status
from ui.auth import enforce_authentication
from ui.tabs import render_tab_registry
from ui.upload_page import render_upload_page

st.set_page_config(page_title=config.APP_TITLE, layout="wide")


def render_sidebar() -> tuple[str, bool]:
    """Render application branding, secret settings, and daily LLM budget."""
    st.sidebar.title(config.APP_TITLE)
    st.sidebar.caption("Local analytics, AI-narrated. Your raw data never leaves this server.")

    with st.sidebar.expander("Settings", expanded=False):
        key_display = (
            mask_secret(config.OPENROUTER_API_KEY) if config.OPENROUTER_API_KEY else "not set"
        )
        st.write(f"OpenRouter API key: `{key_display}`")
        st.caption(
            "Set OPENROUTER_API_KEY as an environment variable — never entered or logged here."
        )
        model = st.text_input("Model", value=config.DEFAULT_MODEL)
        allow_paid = st.toggle("Allow paid models", value=config.ALLOW_PAID_MODELS_DEFAULT)
        st.caption(
            "Free-tier `:free` models only by default unless 'Allow paid models' is enabled. "
            "[OpenRouter privacy docs](https://openrouter.ai/docs)"
        )

        status = get_status()
        st.progress(
            min(1.0, status.calls_made_today / max(1, status.daily_budget)),
            text=f"LLM calls today: {status.calls_made_today}/{status.daily_budget}",
        )
        st.caption(f"Aivara v{config.__version__} ({config.AIVARA_ENV})")

    return model, allow_paid


def render_export_button(pipeline_result: PipelineResult | dict) -> None:
    """Render export preparation button and PPTX download trigger."""
    st.sidebar.divider()
    if st.sidebar.button("Prepare PPTX export", key="prepare_pptx_btn"):
        figures = st.session_state.get("_export_figures", {})
        deck_inputs = assemble_deck_inputs(
            pipeline_result=pipeline_result,
            dataset_name=st.session_state.get("dataset_name", "uploaded.csv"),
            figures=figures,
        )

        try:
            buffer = build_deck(deck_inputs)
            st.session_state["_pptx_buffer"] = buffer.getvalue()
        except Exception as exc:  # noqa: BLE001 - surface friendly error, never crash app
            st.sidebar.error(f"Could not build the PPTX: {exc}")

    if "_pptx_buffer" in st.session_state:
        ds_name = st.session_state.get("dataset_name", "report").rsplit(".", 1)[0]
        st.sidebar.download_button(
            label="Download PPTX Deck",
            data=st.session_state["_pptx_buffer"],
            file_name=f"{ds_name}_aivara_deck.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            key="pptx_download_btn",
        )


def main() -> None:
    """Streamlined application controller: auth -> ingestion -> pipeline -> tabs -> export."""
    # 1. Enforce authentication boundary (halts execution if unauthorized)
    enforce_authentication()

    # 2. Sidebar controls
    model, allow_paid = render_sidebar()

    # 3. Ingestion & upload gate
    ready = render_upload_page()
    if not ready:
        return

    # 4. Typed analytics pipeline execution
    pipeline_result = run_pipeline()

    # 5. Boardroom Executive Takeaways Banner
    takeaways = pipeline_result.get("executive_takeaways", [])
    if takeaways:
        with st.expander("🎯 Boardroom Executive Takeaways", expanded=True):
            for t in takeaways:
                st.markdown(f"- {t}")

    # 6. Table-driven tab dispatch with error boundaries
    render_tab_registry(pipeline_result, model, allow_paid)

    # 7. Presentation export
    render_export_button(pipeline_result)


if __name__ == "__main__":
    main()
