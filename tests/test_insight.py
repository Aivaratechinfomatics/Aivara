import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.kpis import KPIResult
from insight.client import _split_into_sentences
from insight.facts_builder import build_facts_packet


def test_split_into_sentences_handles_decimals_and_percentages():
    text = (
        "Revenue rose to $30,000.50 this week. "
        "North led with 81.8% of the gain. "
        "Investigate South's 9.1% decline before next review."
    )
    sentences = _split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Revenue rose to $30,000.50 this week."
    assert sentences[1] == "North led with 81.8% of the gain."
    assert sentences[2] == "Investigate South's 9.1% decline before next review."


def test_split_into_sentences_handles_numbered_list():
    text = (
        "1) Revenue rose by 15.5% this week.\n"
        "2) Enterprise segment drove 90.2% of the expansion.\n"
        "3) Prioritize mid-market retention calls."
    )
    sentences = _split_into_sentences(text)
    assert len(sentences) == 3
    assert "15.5%" in sentences[0]
    assert "90.2%" in sentences[1]
    assert "retention" in sentences[2]


def test_facts_builder_excludes_both_pos_and_neg_inf():
    kpi_pos = KPIResult("metric1", None, 100.0, 0.0, float("inf"), 100.0)
    packet_pos = build_facts_packet(kpi_pos, None, None, "test")
    assert packet_pos["pct_change"] is None

    kpi_neg = KPIResult("metric2", None, -50.0, 0.0, float("-inf"), -50.0)
    packet_neg = build_facts_packet(kpi_neg, None, None, "test")
    assert packet_neg["pct_change"] is None
