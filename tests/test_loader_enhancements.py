import pandas as pd
import pytest
from ingestion.loader import _prune_trailing_summary_rows, load_csv
from ingestion.cleaner import detect_wide_matrix, unpivot_matrix_table


def test_prune_trailing_summary_rows_removes_total_row():
    df = pd.DataFrame({
        "Product": ["Widgets", "Gadgets", "Gizmos", "Total"],
        "Sales": [100, 200, 300, 600],
        "Units": [10, 20, 30, 60],
    })
    pruned_df, notes = _prune_trailing_summary_rows(df)
    assert len(pruned_df) == 3
    assert list(pruned_df["Product"]) == ["Widgets", "Gadgets", "Gizmos"]
    assert any("Pruned trailing summary/footer row" in n for n in notes)


def test_prune_trailing_summary_rows_preserves_clean_data():
    df = pd.DataFrame({
        "Product": ["Widgets", "Gadgets", "Gizmos"],
        "Sales": [100, 200, 300],
    })
    pruned_df, notes = _prune_trailing_summary_rows(df)
    assert len(pruned_df) == 3
    assert notes == []


def test_detect_wide_matrix_identifies_monthly_columns():
    df = pd.DataFrame({
        "Region": ["North", "South", "East", "West"],
        "Jan 2024": [10, 20, 30, 40],
        "Feb 2024": [12, 22, 32, 42],
        "Mar 2024": [15, 25, 35, 45],
        "Apr 2024": [18, 28, 38, 48],
    })
    is_wide, id_cols, date_cols = detect_wide_matrix(df)
    assert is_wide is True
    assert "Region" in id_cols
    assert len(date_cols) == 4

    unpivoted = unpivot_matrix_table(df, id_cols, date_cols)
    assert len(unpivoted) == 16
    assert set(unpivoted.columns) == {"Region", "period", "value"}
    assert unpivoted["value"].sum() == (10+20+30+40 + 12+22+32+42 + 15+25+35+45 + 18+28+38+48)


def test_load_csv_with_trailing_grand_total():
    csv_text = (
        "Category,Revenue\n"
        "Electronics,500\n"
        "Apparel,300\n"
        "Books,200\n"
        "Grand Total,1000\n"
    )
    res = load_csv(csv_text.encode("utf-8"))
    assert res.success is True
    assert len(res.dataframe) == 3
    assert "Grand Total" not in res.dataframe["Category"].values
