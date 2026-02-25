"""
CSV Format Contract for RING-5 Parsers.

All simulator parsers MUST produce CSV files conforming to this contract.
The CSV is the "common language" between Layer A (Parsing) and Layer B (Core).

Format Rules:
    1. Header row is mandatory.
    2. Each row represents one dump interval (begin/end simpoint pair).
    3. Column names are variable names (hierarchical, dot-separated).
    4. Values are numeric (float) or string (for configuration variables).
    5. Missing values are represented as empty string.
    6. No simulator-specific metadata in the CSV — only data values.

Note:
    Simulator-specific column naming conventions (e.g., gem5 vector entries
    using ``..`` separator) are handled by each simulator's parser, NOT by
    this contract. This module defines only the generic CSV format.

Usage:
    Parsers should import constants from this module to ensure consistent
    formatting across all simulator implementations.

    Downstream services (core, web) should use ``validate_parser_csv``
    to verify parser output conforms to the contract.
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

MISSING_VALUE: str = ""
# Representation for missing/unavailable values in the CSV output.

CSV_ENCODING: str = "utf-8"
# Character encoding for all parser CSV output.

CSV_DIALECT: str = "excel"
# CSV dialect used for output files (Python csv module standard).


# ─── Validation ───────────────────────────────────────────────────────────────


def validate_parser_csv(path: Path) -> list[str]:
    """
    Validate that a CSV file conforms to the RING-5 parser contract.

    Args:
        path: Path to the CSV file to validate.

    Returns:
        List of validation warnings. Empty list means the file is valid.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is fundamentally invalid (no header, empty).
    """
    warnings: list[str] = []

    if not path.exists():
        raise FileNotFoundError(f"CSV file does not exist: {path}")

    with open(path, encoding=CSV_ENCODING, newline="") as f:
        reader = csv.reader(f)

        # 1. Header row is mandatory
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"CSV file is empty: {path}")

        if not header:
            raise ValueError(f"CSV file has empty header row: {path}")

        # 2. Check for duplicate column names
        seen: set[str] = set()
        for col in header:
            if col in seen:
                warnings.append(f"Duplicate column name: '{col}'")
            seen.add(col)

        # 3. Check column name format
        for col in header:
            if not col.strip():
                warnings.append("Empty column name found in header")
            if col != col.strip():
                warnings.append(f"Column name has leading/trailing whitespace: '{col}'")

        # 4. Verify data rows exist
        row_count = 0
        for row_idx, row in enumerate(reader, start=2):
            row_count += 1
            if len(row) != len(header):
                warnings.append(
                    f"Row {row_idx}: column count ({len(row)}) "
                    f"differs from header ({len(header)})"
                )

        if row_count == 0:
            warnings.append("CSV file has header but no data rows")

    return warnings
