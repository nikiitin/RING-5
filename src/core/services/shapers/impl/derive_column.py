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

import numpy as np
import pandas as pd

from src.core.common.dataframe_utils import concat_columns
from src.core.models.shaper_models import DeriveColumnShaperConfig
from src.core.services.shapers.uni_df_shaper import UniDfShaper

_OPS = frozenset({"sum", "ratio", "scalar", "concat", "map"})
_SCALAR_OPS = frozenset({"+", "-", "*", "/"})


class DeriveColumn(UniDfShaper):
    """Create/overwrite ``dest`` from ``sources`` via one of: sum, ratio, scalar, concat, map."""

    def __init__(self, params: dict[str, Any]) -> None:
        config = cast(DeriveColumnShaperConfig, params)
        self.dest: str = config.get("dest", "")
        self.op: str = config.get("op", "")
        self.sources: list[str] = list(config.get("sources", []))
        self.scalar: float | None = config.get("scalar")
        self.scalar_op: str = config.get("scalar_op", "/")
        self.separator: str = config.get("separator", "_")
        self.mapping: dict[str, str] = dict(config.get("mapping", {}))
        self.zero_denominator: str = config.get("zero_denominator", "nan")
        super().__init__(params)

    @override
    def _verify_params(self) -> bool:
        super()._verify_params()
        if not self.dest:
            raise ValueError("DeriveColumn requires a 'dest' column name.")
        if self.op not in _OPS:
            raise ValueError(f"DeriveColumn 'op' must be one of {sorted(_OPS)}; got {self.op!r}.")
        if self.op in ("sum", "concat") and not self.sources:
            raise ValueError(f"DeriveColumn op '{self.op}' requires a non-empty 'sources' list.")
        if self.op == "ratio" and len(self.sources) != 2:
            raise ValueError("DeriveColumn op 'ratio' requires exactly two 'sources' [num, den].")
        if self.op in ("scalar", "map") and len(self.sources) != 1:
            raise ValueError(f"DeriveColumn op '{self.op}' requires exactly one 'sources' column.")
        if self.op == "scalar":
            if self.scalar is None:
                raise ValueError("DeriveColumn op 'scalar' requires a 'scalar' value.")
            if self.scalar_op not in _SCALAR_OPS:
                raise ValueError("DeriveColumn 'scalar_op' must be one of '+', '-', '*', '/'.")
        if self.op == "map" and not self.mapping:
            raise ValueError("DeriveColumn op 'map' requires a non-empty 'mapping'.")
        return True

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
            result[self.dest] = result[self.sources].sum(axis=1)
        elif self.op == "concat":
            result[self.dest] = concat_columns(result, self.sources, self.separator)
        elif self.op == "ratio":
            numerator, denominator = self.sources
            den = result[denominator]
            if self.zero_denominator == "nan":
                den = den.replace(0, np.nan)
            result[self.dest] = result[numerator] / den
        elif self.op == "scalar":
            col = result[self.sources[0]]
            value = float(cast(float, self.scalar))
            result[self.dest] = {
                "+": col + value,
                "-": col - value,
                "*": col * value,
                "/": col / value,
            }[self.scalar_op]
        else:  # "map"
            result[self.dest] = result[self.sources[0]].map(self.mapping)

        return result
