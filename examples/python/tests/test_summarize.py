"""Tests for the pure summary logic (test-first core per Constitution C3)."""

import pytest

from csvsum.summarize import summarize_columns, summarize_csv


def test_numeric_column_stats():
    stats = summarize_columns(["price"], [["10"], ["20"], ["30"]])
    (col,) = stats
    assert col.numeric
    assert col.count == 3
    assert col.minimum == 10.0
    assert col.maximum == 30.0
    assert col.mean == pytest.approx(20.0)


def test_text_column_has_no_numeric_stats():
    stats = summarize_columns(["city"], [["Austin"], ["Boston"], ["10"]])
    (col,) = stats
    assert not col.numeric
    assert col.count == 3
    assert col.minimum is None and col.maximum is None and col.mean is None


def test_empty_cells_excluded_from_count_and_stats():
    stats = summarize_columns(["qty"], [["4"], [""], ["  "], ["8"]])
    (col,) = stats
    assert col.count == 2
    assert col.numeric
    assert col.mean == pytest.approx(6.0)


def test_ragged_rows_do_not_crash():
    stats = summarize_columns(["a", "b"], [["1", "2"], ["3"]])
    assert stats[1].count == 1  # missing cell in the short row is simply absent


def test_summarize_csv_reads_header_and_rows(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,score\nalice,90\nbob,80\n")
    by_name = {s.name: s for s in summarize_csv(csv_file)}
    assert not by_name["name"].numeric
    assert by_name["score"].mean == pytest.approx(85.0)


def test_summarize_csv_rejects_empty_file(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    with pytest.raises(ValueError, match="empty CSV"):
        summarize_csv(empty)
