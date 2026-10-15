import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from ingestion.cleaner import clean_dataframe


def test_percent_columns_scaled_properly():
    df = pd.DataFrame({"growth": ["45%", "50%", "12%"]})
    cleaned_df, report = clean_dataframe(df)
    assert pd.api.types.is_numeric_dtype(cleaned_df["growth"])
    # 45% should be 0.45, not 45
    assert abs(cleaned_df["growth"].iloc[0] - 0.45) < 1e-6
    assert abs(cleaned_df["growth"].iloc[1] - 0.50) < 1e-6
    assert abs(cleaned_df["growth"].iloc[2] - 0.12) < 1e-6


def test_null_placeholders_normalized():
    tokens = [
        "",
        "na",
        "n/a",
        "N/A",
        "NaN",
        "NAN",
        "None",
        "none",
        "NULL",
        "null",
        "-",
        "--",
        "Valid",
    ]
    df = pd.DataFrame({"category": tokens, "val": range(len(tokens))})
    cleaned_df, report = clean_dataframe(df)
    assert "category" in cleaned_df
    assert cleaned_df["category"].iloc[:-1].isna().all()
    assert cleaned_df["category"].iloc[-1] == "Valid"


def test_partial_coercion_reports_failure_count():
    # 9 numbers, 1 stray text -> 90% clean, should coerce and report 1 unparsed value
    vals = ["10", "20", "30", "40", "50", "60", "70", "80", "90", "corrupted"]
    df = pd.DataFrame({"revenue": vals})
    cleaned_df, report = clean_dataframe(df)
    assert pd.api.types.is_numeric_dtype(cleaned_df["revenue"])
    assert any("could not be parsed and are now empty" in m for m in report.messages)


def test_compact_date_format_coerced_to_datetime_not_numeric():
    dates = ["20240101", "20240102", "20240103", "20240104"]
    df = pd.DataFrame({"date_col": dates, "revenue": ["100", "200", "300", "400"]})
    cleaned_df, report = clean_dataframe(df)
    assert pd.api.types.is_datetime64_any_dtype(cleaned_df["date_col"])
    assert pd.api.types.is_numeric_dtype(cleaned_df["revenue"])


def test_broader_null_placeholders_and_total_count():
    tokens = ["nil", "n.a.", "n/d", "-", "--", "Valid1", "Valid2"]
    df = pd.DataFrame({"col": tokens, "id": range(len(tokens))})
    cleaned_df, report = clean_dataframe(df)
    assert report.total_nulls_found == 5
    assert cleaned_df["col"].iloc[:5].isna().all()
    assert list(cleaned_df["col"].iloc[5:]) == ["Valid1", "Valid2"]


def test_coercion_failures_dict_populated():
    vals = ["100", "200", "300", "400", "500", "600", "700", "800", "900", "error_val"]
    dates = [
        "2024-01-01",
        "2024-01-02",
        "2024-01-03",
        "2024-01-04",
        "2024-01-05",
        "2024-01-06",
        "2024-01-07",
        "2024-01-08",
        "2024-01-09",
        "not_a_date",
    ]
    df = pd.DataFrame({"rev": vals, "dt": dates})
    cleaned_df, report = clean_dataframe(df)
    assert report.coercion_failures.get("rev") == 1
    assert report.coercion_failures.get("dt") == 1
    assert pd.api.types.is_numeric_dtype(cleaned_df["rev"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned_df["dt"])


def test_cleaner_empty_rows_and_spacer_columns():
    df = pd.DataFrame(
        {
            "a": [1, None, 2, None],
            "Unnamed: 1": [None, None, None, None],
            "b": [10, None, 20, None],
        }
    )
    cleaned_df, report = clean_dataframe(df)
    assert report.empty_columns_removed == 1
    assert report.empty_rows_removed == 2
    assert "Unnamed: 1" not in cleaned_df.columns
    assert len(cleaned_df) == 2


def test_cleaner_duplicate_flagging():
    df = pd.DataFrame({"a": [1, 2, 1], "b": ["x", "y", "x"]})
    cleaned_df, report = clean_dataframe(df)
    assert report.duplicate_rows_flagged == 1
    assert "_is_duplicate" in cleaned_df.columns
    assert list(cleaned_df["_is_duplicate"]) == [False, False, True]


def test_cleaner_parens_negative_and_currency():
    df = pd.DataFrame({"cost": ["(1,500.50)", "$2,000", "₹500", "€100"]})
    cleaned_df, report = clean_dataframe(df)
    assert pd.api.types.is_numeric_dtype(cleaned_df["cost"])
    assert cleaned_df["cost"].iloc[0] == -1500.50
    assert cleaned_df["cost"].iloc[1] == 2000.0
    assert cleaned_df["cost"].iloc[2] == 500.0
    assert cleaned_df["cost"].iloc[3] == 100.0


def test_cleaner_wide_matrix_detection_and_unpivot():
    from ingestion.cleaner import detect_wide_matrix, unpivot_matrix_table

    df = pd.DataFrame(
        {
            "Region": ["North", "South"],
            "Jan 2024": [100, 200],
            "Feb 2024": [110, 210],
            "Mar 2024": [120, 220],
            "Apr 2024": [130, 230],
        }
    )
    is_wide, id_cols, date_cols = detect_wide_matrix(df)
    assert is_wide
    assert id_cols == ["Region"]
    assert len(date_cols) == 4

    unpivoted = unpivot_matrix_table(df, id_cols, date_cols, var_name="month", value_name="sales")
    assert len(unpivoted) == 8
    assert "month" in unpivoted.columns
    assert "sales" in unpivoted.columns
    assert pd.api.types.is_numeric_dtype(unpivoted["sales"])


def test_cleaner_numeric_coerce_edge_cases():
    from ingestion.cleaner import _try_numeric_coerce

    # Already numeric
    s_num = pd.Series([1, 2, 3])
    conv, did, unparsed = _try_numeric_coerce(s_num)
    assert not did
    assert unparsed == 0

    # All null/empty string series
    s_empty = pd.Series(["", "  ", None])
    conv, did, unparsed = _try_numeric_coerce(s_empty)
    assert not did

    # Date pattern > 80%
    s_date = pd.Series(["2024-01-01", "2024-01-02", "2024-01-03", "not_date"])
    conv, did, unparsed = _try_numeric_coerce(s_date)
    assert not did


def test_cleaner_wide_matrix_edge_cases():
    from ingestion.cleaner import detect_wide_matrix

    # Empty df
    assert detect_wide_matrix(pd.DataFrame()) == (False, [], [])

    # Too few columns
    df_few = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert detect_wide_matrix(df_few) == (False, [], [])


def test_cleaner_remaining_branches():
    from ingestion.cleaner import _try_numeric_coerce, detect_wide_matrix

    # _try_numeric_coerce with unparseable percent symbol alone
    assert _try_numeric_coerce(pd.Series(["%", "%"]))[1] is False

    # detect_wide_matrix with valid datetime strings as column names
    df = pd.DataFrame(
        {
            "id": [1, 2],
            "2024-01-01": [10, 20],
            "2024-02-01": [15, 25],
            "2024-03-01": [20, 30],
            "2024-04-01": [25, 35],
        }
    )
    is_wide, id_cols, date_cols = detect_wide_matrix(df)
    assert is_wide
    assert len(date_cols) == 4


def test_cleaner_all_remaining_branches():
    from ingestion.cleaner import _try_numeric_coerce, clean_dataframe, detect_wide_matrix

    # 1. Float percent ValueError (line 70-71)
    res, did, unparsed = _try_numeric_coerce(pd.Series(["foo%"]))
    assert not did

    # 2. String column that becomes entirely null after normalization is dropped as empty
    df_null_str = pd.DataFrame({"col": ["na", "none", "null"], "id": [1, 2, 3]})
    cdf, rep = clean_dataframe(df_null_str)
    assert "col" not in cdf.columns
    assert rep.empty_columns_removed == 1

    # 3. Wide matrix with MM/DD/YYYY columns (hitting line 226-228)
    df_mmdd = pd.DataFrame(
        {
            "id": [1, 2],
            "01/15/2024": [10, 20],
            "02/15/2024": [15, 25],
            "03/15/2024": [20, 30],
        }
    )
    is_w, ids, dts = detect_wide_matrix(df_mmdd)
    assert is_w
    assert len(dts) == 3

    # 4. Wide matrix with non-numeric date columns (hitting line 242)
    df_non_num = pd.DataFrame(
        {
            "id": [1, 2],
            "Jan 2024": ["a", "b"],
            "Feb 2024": ["c", "d"],
            "Mar 2024": ["e", "f"],
        }
    )
    is_w2, _, _ = detect_wide_matrix(df_non_num)
    assert not is_w2
