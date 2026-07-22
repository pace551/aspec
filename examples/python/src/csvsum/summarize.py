"""Pure summary logic: per-column statistics for CSV data. No I/O here."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ColumnStats:
    """Statistics for one CSV column."""

    name: str
    count: int  # non-empty values
    numeric: bool  # every non-empty value parsed as a number
    minimum: float | None
    maximum: float | None
    mean: float | None


def summarize_columns(header: list[str], rows: list[list[str]]) -> list[ColumnStats]:
    """Compute per-column stats. A column is numeric iff all non-empty cells parse."""
    stats: list[ColumnStats] = []
    for idx, name in enumerate(header):
        cells = [row[idx].strip() for row in rows if idx < len(row)]
        values = [c for c in cells if c]
        numbers: list[float] | None = []
        for cell in values:
            try:
                numbers.append(float(cell))
            except ValueError:
                numbers = None
                break
        if numbers:  # numeric column with at least one value
            stats.append(
                ColumnStats(
                    name=name,
                    count=len(values),
                    numeric=True,
                    minimum=min(numbers),
                    maximum=max(numbers),
                    mean=sum(numbers) / len(numbers),
                )
            )
        else:
            stats.append(
                ColumnStats(
                    name=name,
                    count=len(values),
                    numeric=False,
                    minimum=None,
                    maximum=None,
                    mean=None,
                )
            )
    return stats


def summarize_csv(path: Path) -> list[ColumnStats]:
    """Read a CSV file (first row = header) and summarize its columns."""
    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"{path}: empty CSV (no header row)") from None
        rows = list(reader)
    return summarize_columns(header, rows)
