"""DeriveColumn shaper — create one column from existing columns.

A single, composable derived-column step covering the arithmetic and text operations
figures need when building metrics from raw stats: row-sum of N columns, a ratio of two
columns, a column-scalar operation, a string concatenation, and a value recode. One
transform per shaper (atomic + composable); immutable (``copy()`` first).

NaN/zero conventions mirror the rest of RING-5: ``sum`` is NaN-skipping like
``DataFrame.sum(axis=1)`` (an all-NaN row → ``0.0``), and ``ratio``'s default
``zero_denominator="nan"`` matches ``ArithmeticService.apply_operation`` Division
(``s1 / s2.replace(0, np.nan)``).
"""

from typing import Any, cast, override

import pandas as pd

from src.core.common.dataframe_utils import concat_columns
from src.core.common.numerical_operations import (
    ArithmeticOperator,
    ZeroDenominatorPolicy,
    aggregate_rows,
    apply_binary,
    divide_columns,
)
from src.core.models.shaper_models import DeriveColumnShaperConfig, ShaperValue
from src.core.services.shapers.uni_df_shaper import UniDfShaper


class DeriveColumn(UniDfShaper):
    """Create/overwrite ``dest`` from ``sources`` via one of: sum, ratio, scalar, concat, map."""

    def __init__(self, params: dict[str, Any]) -> None:
        super().__init__(params)
        config = cast(DeriveColumnShaperConfig, self.params)
        self.dest: str = config["dest"]
        self.op: str = config["op"]
        self.sources: list[str] = config["sources"]
        self.scalar: float | None = config.get("scalar")
        self.scalar_op: str = config.get("scalar_op", "/")
        self.separator: str = config.get("separator", "_")
        self.mapping: dict[str, ShaperValue | None] = config.get("mapping", {})
        self.zero_denominator: str = config.get("zero_denominator", "nan")

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        super()._verify_preconditions(data_frame)
        missing = [c for c in self.sources if c not in data_frame.columns]
        if missing:
            raise ValueError(f"DeriveColumn: source columns not found: {missing}")
        return True

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        # [impl->req~ring5.shaping.derive-column~1]
        self._verify_preconditions(data_frame)
        result = data_frame.copy()

        if self.op == "sum":
            result[self.dest] = aggregate_rows(data_frame[self.sources], "sum")
        elif self.op == "concat":
            result[self.dest] = concat_columns(data_frame, self.sources, self.separator)
        elif self.op == "ratio":
            numerator, denominator = self.sources
            result[self.dest] = divide_columns(
                data_frame[numerator],
                data_frame[denominator],
                cast(ZeroDenominatorPolicy, self.zero_denominator),
            )
        elif self.op == "scalar":
            value = float(cast(float, self.scalar))
            result[self.dest] = apply_binary(
                data_frame[self.sources[0]], value, cast(ArithmeticOperator, self.scalar_op)
            )
        else:  # "map"
            result[self.dest] = result[self.sources[0]].map(self.mapping)

        return result
