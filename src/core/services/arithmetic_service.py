"""
Arithmetic Service - Column-Based Mathematical Operations.

Provides utilities for performing arithmetic transformations on DataFrame
columns: division, sum, subtraction, multiplication. Used to create derived
metrics from base statistics.
"""

from typing import Any, List

import numpy as np
import pandas as pd


class ArithmeticService:
    """Service for basic arithmetic column operations."""

    @staticmethod
    def list_operators() -> List[str]:
        return ["Division", "Sum", "Subtraction", "Multiplication"]

    @staticmethod
    def apply_operation(
        df: pd.DataFrame, operation: str, src1: str, src2: str, dest: str
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        result = df.copy()

        s1 = result[src1]
        s2 = result[src2]

        op = operation.lower()
        if op in ["division", "divide", "/"]:
            result[dest] = s1 / s2.replace(0, np.nan)
        elif op in ["sum", "add", "+"]:
            result[dest] = s1 + s2
        elif op in ["subtraction", "subtract", "minus", "-"]:
            result[dest] = s1 - s2
        elif op in ["multiplication", "multiply", "*"]:
            result[dest] = s1 * s2
        else:
            raise ValueError(f"Unknown operation: {operation}")

        return result

    @staticmethod
    def merge_columns(
        df: pd.DataFrame, source_cols: List[str], operation: str, dest_col: str, **kwargs: Any
    ) -> pd.DataFrame:
        """Merge multiple columns using an operation (Sum, Mean, Concatenate, etc)."""
        result = df.copy()

        if not source_cols:
            return result

        op = operation.lower()
        if op == "sum":
            result[dest_col] = result[source_cols].sum(axis=1)
            # SD propagation for sum: sqrt(sum(sd^2))
            sd_cols = [f"{c}.sd" for c in source_cols if f"{c}.sd" in result.columns]
            if len(sd_cols) == len(source_cols):
                result[f"{dest_col}.sd"] = np.sqrt((result[sd_cols] ** 2).sum(axis=1))

        elif op == "mean":
            result[dest_col] = result[source_cols].mean(axis=1)
            # SD propagation for mean: sqrt(sum(sd^2)) / n
            sd_cols = [f"{c}.sd" for c in source_cols if f"{c}.sd" in result.columns]
            if len(sd_cols) == len(source_cols):
                result[f"{dest_col}.sd"] = np.sqrt((result[sd_cols] ** 2).sum(axis=1)) / len(
                    source_cols
                )

        elif op == "concatenate":
            sep = kwargs.get("separator", "-")
            result[dest_col] = result[source_cols].astype(str).agg(sep.join, axis=1)

        else:
            raise ValueError(f"Unsupported merge operation: {operation}")

        return result
