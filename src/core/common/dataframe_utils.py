"""Small, UI-free DataFrame helpers shared across core services.

Lives in Layer A's common language so both the shapers (``DeriveColumn``) and the managers
(``ArithmeticService``) use one implementation and cannot drift.
"""

from __future__ import annotations

import pandas as pd


def concat_columns(frame: pd.DataFrame, columns: list[str], separator: str) -> pd.Series:
    """Row-wise string join of ``columns`` with ``separator`` — NaN-safe.

    NaN/NA cells render as empty strings instead of crashing the join (under pandas 3 a
    plain ``astype(str)`` leaves NA as a float and ``str.join`` then raises ``TypeError``).
    For all-present string inputs this matches the historical
    ``frame[columns].astype(str).agg(sep.join, axis=1)`` value-for-value.
    """
    return frame[columns].astype("string").fillna("").agg(separator.join, axis=1)
