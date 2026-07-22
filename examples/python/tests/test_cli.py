"""End-to-end CLI tests: summarize a real file, persist to a real SQLite db."""

import sqlite3

from csvsum.cli import main

CSV = "item,price\nwidget,2.50\ngadget,7.50\n"


def test_cli_prints_summary(tmp_path, capsys):
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text(CSV)
    assert main([str(csv_file)]) == 0
    out = capsys.readouterr().out
    assert "item" in out and "(text)" in out
    assert "price" in out and "7.5" in out


def test_cli_persists_run_with_db_flag(tmp_path, capsys):
    csv_file = tmp_path / "sales.csv"
    csv_file.write_text(CSV)
    db_file = tmp_path / "runs.db"
    assert main([str(csv_file), "--db", str(db_file)]) == 0
    assert "recorded run 1" in capsys.readouterr().out

    con = sqlite3.connect(db_file)
    assert con.execute("SELECT count(*) FROM runs").fetchone()[0] == 1
    assert con.execute("SELECT count(*) FROM column_stats").fetchone()[0] == 2
    con.close()


def test_cli_missing_file_fails_cleanly(tmp_path, capsys):
    assert main([str(tmp_path / "nope.csv")]) == 1
    assert "csvsum:" in capsys.readouterr().err
