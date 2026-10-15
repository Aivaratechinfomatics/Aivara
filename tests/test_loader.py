import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io

import pandas as pd

from ingestion.loader import load_csv, load_excel, load_file

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(name: str):
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return load_csv(f.read(), filename=name)


def test_clean_csv_loads():
    result = _load("clean.csv")
    assert result.success
    assert result.delimiter == ","
    assert list(result.dataframe.columns) == [
        "date",
        "region",
        "product",
        "revenue",
        "cost",
        "units",
    ]
    assert len(result.dataframe) == 7


def test_semicolon_delimited_detected():
    result = _load("semicolon.csv")
    assert result.success
    assert result.delimiter == ";"
    assert "sales" in result.dataframe.columns


def test_no_header_generates_column_names():
    result = _load("no_header.csv")
    assert result.success
    assert all(c.startswith("column_") for c in result.dataframe.columns)
    assert len(result.dataframe) == 4


def test_currency_formatted_column_parses():
    result = _load("currency.csv")
    assert result.success
    assert "revenue" in result.dataframe.columns
    # revenue column is still raw strings at load time; cleaning happens in
    # ingestion/cleaner.py, so just assert the load itself didn't crash and
    # produced the right shape.
    assert len(result.dataframe) == 4


def test_mixed_encoding_does_not_crash():
    result = _load("mixed_encoding.csv")
    assert result.success
    assert len(result.dataframe) == 3


def test_no_date_column_loads_fine():
    result = _load("no_date.csv")
    assert result.success
    assert "date" not in result.dataframe.columns


def test_garbage_bytes_never_raises():
    garbage = bytes([0xFF, 0xFE, 0x00, 0x01]) * 20
    result = load_csv(garbage, filename="garbage.csv")
    # Must not raise; success may be True or False depending on how pandas
    # interprets the bytes, but it must always return a LoadResult.
    assert result is not None


def test_load_excel_single_sheet():
    df_in = pd.DataFrame({"product": ["A", "B", "C"], "revenue": [100, 200, 300]})
    buf = io.BytesIO()
    df_in.to_excel(buf, index=False, engine="openpyxl")
    excel_bytes = buf.getvalue()

    result = load_excel(excel_bytes, filename="sample.xlsx")
    assert result.success
    assert result.delimiter == "excel"
    assert list(result.dataframe.columns) == ["product", "revenue"]
    assert len(result.dataframe) == 3


def test_load_excel_multi_sheet():
    df1 = pd.DataFrame({"month": ["Jan", "Feb"], "sales": [10, 20]})
    df2 = pd.DataFrame({"month": ["Mar", "Apr"], "sales": [30, 40]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="Q1", index=False)
        df2.to_excel(writer, sheet_name="Q2", index=False)
    excel_bytes = buf.getvalue()

    result = load_excel(excel_bytes, filename="quarterly.xlsx")
    assert result.success
    assert any("Workbook has 2 sheets" in note for note in result.notes)
    assert list(result.dataframe["sales"]) == [10, 20]


def test_load_file_routes_xlsx_and_csv():
    # Test CSV routing
    csv_bytes = b"a,b\n1,2\n"
    res_csv = load_file(csv_bytes, filename="test.csv")
    assert res_csv.success
    assert res_csv.delimiter == ","

    # Test XLSX routing
    buf = io.BytesIO()
    pd.DataFrame({"x": [1, 2]}).to_excel(buf, index=False, engine="openpyxl")
    res_xlsx = load_file(buf.getvalue(), filename="test.xlsx")
    assert res_xlsx.success
    assert res_xlsx.delimiter == "excel"
    assert "x" in res_xlsx.dataframe.columns


def test_load_empty_file_returns_clean_error():
    res_empty = load_file(b"", filename="empty.csv")
    assert not res_empty.success
    assert "empty" in res_empty.error.lower()

    res_spaces = load_csv(b"   \n\t  \n", filename="spaces.csv")
    assert not res_spaces.success
    assert "empty" in res_spaces.error.lower()


def test_load_oversized_file_rejected(monkeypatch):
    from config import MAX_UPLOAD_MB

    fake_huge_bytes = b"x" * ((MAX_UPLOAD_MB + 1) * 1024 * 1024)
    res = load_file(fake_huge_bytes, filename="large.csv")
    assert not res.success
    assert "exceeds maximum allowed size" in res.error


def test_load_exceeds_max_columns(monkeypatch):
    import config

    monkeypatch.setattr(config, "MAX_COLUMNS", 5)
    from ingestion import loader

    monkeypatch.setattr(loader, "MAX_COLUMNS", 5)

    cols = [f"c{i}" for i in range(10)]
    csv_text = ",".join(cols) + "\n" + ",".join(["1"] * 10) + "\n"
    res = load_csv(csv_text.encode("utf-8"), filename="wide.csv")
    assert not res.success
    assert "exceeds maximum column limit" in res.error


def test_duplicate_and_blank_column_headers():
    csv_text = "region,,revenue,revenue\nNorth,A,100,200\nSouth,B,300,400\n"
    res = load_csv(csv_text.encode("utf-8"), filename="dup.csv")
    assert res.success
    cols = list(res.dataframe.columns)
    assert cols[0] == "region"
    assert cols[1] == "column_2"
    assert cols[2] == "revenue"
    assert cols[3] == "revenue_2"
    assert any("Renamed duplicate column 'revenue' to 'revenue_2'" in n for n in res.notes)
    assert any("Assigned default name 'column_2' to blank column header" in n for n in res.notes)


def test_malformed_csv_bad_lines_counted_and_reported():
    csv_text = "a,b,c\n1,2,3\n1,2,3\n4,5,6,7,8,9\n10,11,12\n"
    res = load_csv(csv_text.encode("utf-8"), filename="bad_lines.csv")
    assert res.success
    assert len(res.dataframe) == 3
    assert any("row(s) skipped: malformed" in n for n in res.notes)


def test_loader_hypothesis_fuzzing():
    from hypothesis import given, settings
    from hypothesis import strategies as st

    @given(st.binary(min_size=1, max_size=500))
    @settings(max_examples=25, deadline=None)
    def _fuzz(b: bytes):
        res = load_file(b, filename="fuzz.csv")
        assert res is not None
        assert isinstance(res.success, bool)
        assert isinstance(res.notes, list)

    _fuzz()


def test_loader_delimiter_edge_cases():
    from ingestion.loader import _detect_delimiter

    delim, notes = _detect_delimiter("")
    assert delim == ","
    assert any("No sample lines available" in n for n in notes)

    delim2, notes2 = _detect_delimiter("singlewordwithoutdelimiters\nanotherline")
    assert delim2 == ","


def test_excel_empty_sheet_and_no_header():
    # Empty excel
    df_empty = pd.DataFrame()
    buf = io.BytesIO()
    df_empty.to_excel(buf, index=False, engine="openpyxl")
    res = load_excel(buf.getvalue(), filename="empty.xlsx")
    assert res.success
    assert res.dataframe.empty

    # Excel with numeric data only (no header)
    df_no_head = pd.DataFrame([[1, 2], [3, 4]])
    buf2 = io.BytesIO()
    df_no_head.to_excel(buf2, index=False, header=False, engine="openpyxl")
    res2 = load_excel(buf2.getvalue(), filename="no_head.xlsx")
    assert res2.success
    assert all(c.startswith("column_") for c in res2.dataframe.columns)


def test_excel_corrupted_bytes():
    res = load_excel(b"PK\x03\x04corrupted_zip_payload", filename="bad.xlsx")
    assert not res.success
    assert "Could not read Excel file" in res.error


def test_excel_max_rows_sampled(monkeypatch):
    import ingestion.loader as ldr

    monkeypatch.setattr(ldr, "MAX_ROWS_FULL_PROCESSING", 5)
    df = pd.DataFrame({"a": range(10)})
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    res = load_excel(buf.getvalue(), filename="sampled.xlsx")
    assert res.success
    assert len(res.dataframe) == 5
    assert any("sampled down" in n for n in res.notes)


def test_loader_internal_helpers_coverage():
    from ingestion.loader import (
        _find_best_header_row,
        _is_numeric_value,
        _looks_like_header,
        _value_shape,
    )

    # _is_numeric_value
    assert _is_numeric_value(123)
    assert _is_numeric_value(12.34)
    assert not _is_numeric_value(float("nan"))
    assert not _is_numeric_value("")
    assert _is_numeric_value("1,234.56")
    assert not _is_numeric_value("not_a_num")

    # _value_shape
    assert _value_shape(float("nan")) == "text"
    assert _value_shape(pd.Timestamp("2024-01-01")) == "date"
    assert _value_shape(42) == "numeric"
    assert _value_shape("42.5") == "numeric"
    assert _value_shape("2024-01-01") == "date"
    assert _value_shape("some_text") == "text"

    # _looks_like_header
    assert _looks_like_header([], [])
    assert _looks_like_header(["a", "b"], [])
    assert _looks_like_header(["a", "b"], [["x", "y"], ["z", "w"]])
    assert not _looks_like_header(["1", "2"], [["3", "4"], ["5", "6"]])
    assert _looks_like_header(["cat", "val"], [["A", "10"], ["B", "20"]])

    # _find_best_header_row
    assert _find_best_header_row([]) == (0, True)
    assert _find_best_header_row([["name", "val"], ["A", "10"], ["B", "20"]]) == (0, True)


def test_detect_encoding_fallback_to_latin1(monkeypatch):
    import ingestion.loader as ldr
    from ingestion.loader import _detect_encoding

    monkeypatch.setattr(ldr, "CANDIDATE_ENCODINGS", [])
    monkeypatch.setattr(ldr, "_cn_from_bytes", None)
    enc, notes = _detect_encoding(b"some bytes")
    assert enc == "latin-1"
    assert any("latin-1" in n for n in notes)


def test_loader_remaining_coverage_branches(monkeypatch):
    import ingestion.loader as ldr
    from ingestion.loader import _prune_trailing_summary_rows

    # 1. _prune_trailing_summary_rows with empty row near bottom
    df_tail = pd.DataFrame(
        {
            "a": ["Item 1", "Item 2", "Total", None, "Grand Total"],
            "b": [10, 20, 30, None, 60],
        }
    )
    pruned, pnotes = _prune_trailing_summary_rows(df_tail)
    assert len(pruned) == 2
    assert len(pnotes) >= 2

    # 2. CSV exceeds MAX_ROWS_FULL_PROCESSING
    monkeypatch.setattr(ldr, "MAX_ROWS_FULL_PROCESSING", 5)
    csv_10 = "val\n" + "\n".join(str(i) for i in range(10)) + "\n"
    res_sampled = ldr.load_csv(csv_10.encode("utf-8"), filename="sampled.csv")
    assert res_sampled.success
    assert len(res_sampled.dataframe) == 5
    assert any("sampled down" in n for n in res_sampled.notes)

    # 3. CSV with leading metadata rows (best_header_idx > 0)
    csv_metadata = (
        "Report Title: Sales\nGenerated: Today\nDate,Revenue\n2024-01-01,100\n2024-01-02,200\n"
    )
    res_meta = ldr.load_csv(csv_metadata.encode("utf-8"), filename="meta.csv")
    assert res_meta.success
    assert "Revenue" in res_meta.dataframe.columns
    assert any("Auto-detected table header at row 3" in n for n in res_meta.notes)


def test_loader_one_column_parsed_retry(monkeypatch):
    import ingestion.loader as ldr

    # Force delimiter detection to return wrong delimiter ";"
    monkeypatch.setattr(ldr, "_detect_delimiter", lambda sample: (";", []))
    csv_text = "a,b,c\n1,2,3\n4,5,6\n"
    res = ldr.load_csv(csv_text.encode("utf-8"), filename="test.csv")
    assert res.success
    assert len(res.dataframe.columns) == 3


def test_excel_with_leading_metadata_rows():
    import ingestion.loader as ldr

    df_meta = pd.DataFrame(
        [
            ["Report Title", "Sales Q1"],
            ["Generated by", "Admin"],
            ["region", "revenue"],
            ["North", 100],
            ["South", 200],
        ]
    )
    buf = io.BytesIO()
    df_meta.to_excel(buf, index=False, header=False, engine="openpyxl")
    res = ldr.load_excel(buf.getvalue(), filename="meta.xlsx")
    assert res.success
    assert "revenue" in res.dataframe.columns
    assert any("Auto-detected table header at row 3" in n for n in res.notes)


def test_load_file_empty_and_oversized(monkeypatch):
    import ingestion.loader as ldr

    res_empty = ldr.load_file(b"")
    assert not res_empty.success
    assert "empty (0 bytes)" in res_empty.error

    monkeypatch.setattr(ldr, "MAX_UPLOAD_MB", 0.00001)
    res_oversized = ldr.load_file(b"a" * 100, filename="big.csv")
    assert not res_oversized.success
    assert "exceeds maximum allowed size" in res_oversized.error


def test_load_excel_empty_and_oversized(monkeypatch):
    import ingestion.loader as ldr

    res_empty = ldr.load_excel(b"")
    assert not res_empty.success
    assert "empty (0 bytes)" in res_empty.error

    monkeypatch.setattr(ldr, "MAX_UPLOAD_MB", 0.00001)
    res_oversized = ldr.load_excel(b"a" * 100, filename="big.xlsx")
    assert not res_oversized.success
    assert "exceeds maximum allowed size" in res_oversized.error


def test_load_csv_exhaustion_failure(monkeypatch):
    import ingestion.loader as ldr

    def fake_read_csv(*args, **kwargs):
        raise ValueError("Corrupt CSV parsing explosion")

    monkeypatch.setattr(pd, "read_csv", fake_read_csv)
    res = ldr.load_csv(b"col1,col2\n1,2\n")
    assert not res.success
    assert "Failed to parse CSV after multiple attempts" in res.error


def test_find_best_header_row_and_shape_edge_cases():
    from ingestion.loader import _find_best_header_row, _looks_like_header

    # Leading empty/whitespace rows
    rows = [[], [None, ""], ["   ", ""], ["Name", "Value"], ["Item1", "10"]]
    best_idx, has_header = _find_best_header_row(rows)
    assert best_idx == 3
    assert has_header

    # Candidate with empty column_values in data_rows
    assert _looks_like_header(["A", "B", "C"], [["X"]])
