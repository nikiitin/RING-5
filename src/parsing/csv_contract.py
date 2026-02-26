"""
Backward-compatibility re-export.

The canonical location is ``src.core.models.csv_contract``.
This shim ensures existing ``from src.parsing.csv_contract import …``
statements keep working.
"""

from src.core.models.csv_contract import (  # noqa: F401
    CSV_DIALECT,
    CSV_ENCODING,
    MISSING_VALUE,
    validate_parser_csv,
)
