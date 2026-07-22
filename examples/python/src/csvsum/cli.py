"""CLI entry point: summarize a CSV, optionally persist the run to SQLite."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from csvsum.db import apply_migrations, connect, record_run
from csvsum.summarize import ColumnStats, summarize_csv


def format_stats(stats: list[ColumnStats]) -> str:
    """Render column stats as an aligned text table."""
    lines = [f"{'column':<20} {'count':>6}  {'min':>10} {'max':>10} {'mean':>10}"]
    for s in stats:
        if s.numeric:
            lines.append(
                f"{s.name:<20} {s.count:>6}  {s.minimum:>10.4g} {s.maximum:>10.4g} {s.mean:>10.4g}"
            )
        else:
            lines.append(f"{s.name:<20} {s.count:>6}  {'(text)':>10} {'':>10} {'':>10}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="csvsum", description=__doc__)
    parser.add_argument("csv_path", type=Path, help="CSV file with a header row")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="SQLite file to record this run in (created/migrated as needed)",
    )
    args = parser.parse_args(argv)

    try:
        stats = summarize_csv(args.csv_path)
    except (OSError, ValueError) as exc:
        print(f"csvsum: {exc}", file=sys.stderr)
        return 1

    print(format_stats(stats))

    if args.db is not None:
        con = connect(args.db)
        try:
            apply_migrations(con)
            run_id = record_run(con, str(args.csv_path), stats)
        finally:
            con.close()
        print(f"\nrecorded run {run_id} in {args.db}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
