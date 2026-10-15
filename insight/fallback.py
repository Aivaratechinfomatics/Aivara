"""
insight/fallback.py — Deterministic Template Fallback Generator (Phase 5 / Audit §5 / Audit 3.8).

Generates high-quality, grammatical 3-sentence insights directly from pre-computed facts
when the LLM is unconfigured, rate-limited, unreachable, schema-invalid, or hallucinating.
Runs 100% locally and offline without external network or API dependencies.
"""

from __future__ import annotations

from typing import Any


def generate_deterministic_fallback(facts_packet: dict[str, Any]) -> tuple[str, str, str]:
    """Builds a deterministic (headline, driver_explanation, suggested_action) tuple
    strictly from the pre-computed numbers in facts_packet.
    """
    analysis_type = facts_packet.get("analysis_type")

    # 1. Cross-sectional Snapshot
    if analysis_type == "snapshot":
        total_items = facts_packet.get("total_items", 0)
        entity_dim = facts_packet.get("entity_dimension", "items")
        primary_m = facts_packet.get("primary_metric", "Metric")
        total_val = facts_packet.get("total_value", 0.0)
        top_perf = facts_packet.get("top_performer")
        top_share = facts_packet.get("top_performer_share_pct")

        headline = f"Portfolio comprises {total_items:,} {entity_dim} totaling {total_val:,.2f} in {primary_m}."
        if top_perf and top_share is not None:
            driver = f"Leading {entity_dim} is '{top_perf}', generating {top_share:.1f}% of total {primary_m}."
            action = f"Optimize operations around '{top_perf}' while monitoring performance across remaining {entity_dim}."
        else:
            driver = "Performance is distributed evenly across the monitored portfolio."
            action = "Establish benchmark thresholds for key portfolio segments."
        return headline, driver, action

    # 2. Project Portfolio
    if analysis_type == "project":
        total_tasks = facts_packet.get("total_tasks", 0)
        comp_rate = facts_packet.get("completion_rate_pct", 0.0)
        completed = facts_packet.get("completed_tasks", 0)
        unstarted = facts_packet.get("unstarted_tasks", 0)

        headline = f"Project portfolio comprises {total_tasks:,} tasks with an overall completion rate of {comp_rate:.1f}%."
        driver = f"{completed:,} tasks are complete, with {unstarted:,} tasks remaining unstarted."
        action = (
            "Prioritize unstarted tasks and verify team capacity to avoid delivery bottlenecks."
        )
        return headline, driver, action

    # 3. Standard KPI / Trend
    kpi_name = facts_packet.get("kpi_name", "Primary Metric")
    unit = facts_packet.get("unit") or ""
    curr_val = facts_packet.get("current_value", 0.0)
    pct_chg = facts_packet.get("pct_change")
    period = facts_packet.get("period_label", "this period")

    prefix = unit if unit in ("$", "€", "£", "₹") else ""
    suffix = unit if unit not in ("$", "€", "£", "₹") else ""

    if pct_chg is not None:
        direction = "rose" if pct_chg > 0 else ("fell" if pct_chg < 0 else "remained flat")
        headline = (
            f"{kpi_name} {direction} to {prefix}{curr_val:,.2f}{suffix} ({pct_chg:+.1f}% {period})."
        )
    else:
        headline = f"{kpi_name} reached {prefix}{curr_val:,.2f}{suffix} for {period}."

    # Driver explanation
    top_pos = facts_packet.get("top_positive_drivers", [])
    top_neg = facts_packet.get("top_negative_drivers", [])

    if top_pos:
        p_driver = top_pos[0]
        cat = p_driver.get("category", "Top Category")
        pct = p_driver.get("contribution_pct", 0.0)
        driver = f"Positive movement was led by '{cat}' contributing {pct:.1f}% of the change."
        action = f"Scale successful initiatives in '{cat}' and assess sustainability across peer segments."
    elif top_neg:
        n_driver = top_neg[0]
        cat = n_driver.get("category", "Top Category")
        pct = n_driver.get("contribution_pct", 0.0)
        driver = f"Downside pressure was primarily driven by '{cat}' contributing {pct:.1f}% of the decrease."
        action = f"Investigate variance drivers in '{cat}' before the next review cycle."
    else:
        driver = f"{kpi_name} trends remained consistent across evaluated segments."
        action = f"Continue monitoring {kpi_name} against established baseline expectations."

    return headline, driver, action
