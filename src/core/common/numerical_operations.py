"""Value-only arithmetic shared by manager and shaper orchestration."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

ArithmeticOperator = Literal["+", "-", "*", "/"]
AggregationMethod = Literal["sum", "mean"]
ZeroDenominatorPolicy = Literal["nan", "propagate"]


def apply_binary(
    left: pd.Series, right: pd.Series | float, operator: ArithmeticOperator
) -> pd.Series:
    # [impl->req~ring5.data.arithmetic~1]
    # [impl->req~ring5.shaping.derive-column~1]
    """Apply elementwise arithmetic without changing either operand.

    Missing operands propagate. Division is raw pandas division, including
    infinite results for a nonzero numerator divided by zero.
    """
    match operator:
        case "+":
            return left + right
        case "-":
            return left - right
        case "*":
            return left * right
        case "/":
            return left / right
    raise ValueError(f"Unknown arithmetic operator: {operator}")


def aggregate_rows(values: pd.DataFrame, operation: AggregationMethod) -> pd.Series:
    # [impl->req~ring5.data.numeric-mixer~1]
    # [impl->req~ring5.shaping.derive-column~1]
    """Aggregate nonmissing values in each row without changing the frame.

    An all-missing row sums to zero and has an unknown arithmetic mean.
    """
    match operation:
        case "sum":
            return values.sum(axis=1)
        case "mean":
            return values.mean(axis=1)
    raise ValueError(f"Unknown row aggregation: {operation}")


def divide_columns(
    numerator: pd.Series,
    denominator: pd.Series,
    zero_denominator: ZeroDenominatorPolicy = "nan",
) -> pd.Series:
    # [impl->req~ring5.data.arithmetic~1]
    # [impl->req~ring5.shaping.derive-column~1]
    """Divide columns, masking zero denominators only for the ``nan`` policy."""
    match zero_denominator:
        case "nan":
            denominator = denominator.replace(0, np.nan)
        case "propagate":
            pass
        case _:
            raise ValueError("zero_denominator must be 'nan' or 'propagate'.")
    return apply_binary(numerator, denominator, "/")
