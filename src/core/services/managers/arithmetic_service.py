"""
Arithmetic Service - Column-Based Mathematical Operations.

Provides utilities for performing arithmetic transformations on DataFrame
columns: division, sum, subtraction, multiplication, and multi-column
merge with standard deviation propagation. Used to create derived
metrics from base statistics.
"""

from collections import Counter

import numpy as np
import pandas as pd

from src.core.common.dataframe_utils import concat_columns
from src.core.common.distribution_metadata import (
    inspect_distribution_layouts,
    preserve_distribution_layouts,
)
from src.core.common.numerical_operations import aggregate_rows, apply_binary, divide_columns
from src.core.models.arithmetic_models import ArithmeticOperation, MixerOperation


def _missing_values(values: pd.Series) -> pd.Series:
    """Include numerical NaNs independently of a dtype's missing-value mask."""
    missing = values.isna()
    comparable = values.mask(missing, 0)
    return missing | comparable.ne(comparable).fillna(True)


def _sd_magnitude(values: pd.Series, present: pd.Series) -> pd.Series:
    """Return magnitudes for contributing measurements without squaring SDs."""
    values = values.mask(_missing_values(values), np.nan).infer_objects()
    magnitude = pd.Series(np.hypot(0.0, values), index=values.index)
    return magnitude.where(present, 0.0)


class ArithmeticService:
    """Service for arithmetic column operations and multi-column merging."""

    @staticmethod
    def list_operators() -> list[str]:
        """Return the list of supported binary arithmetic operators."""
        return [operation.value for operation in ArithmeticOperation]

    @staticmethod
    def apply_operation(
        df: pd.DataFrame, operation: str, src1: str, src2: str, dest: str
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        # [impl->req~ring5.data.arithmetic~1]
        # [impl->req~ring5.quality.immutable-data~1]
        inspect_distribution_layouts(df)
        result = df.copy()

        s1 = result[src1]
        s2 = result[src2]

        try:
            op = ArithmeticOperation(operation)
        except ValueError as exc:
            raise ValueError(f"Unknown operation: {operation}") from exc
        if op == ArithmeticOperation.DIVISION:
            result[dest] = divide_columns(s1, s2)
        elif op == ArithmeticOperation.SUM:
            result[dest] = apply_binary(s1, s2, "+")
        elif op == ArithmeticOperation.SUBTRACTION:
            result[dest] = apply_binary(s1, s2, "-")
        elif op == ArithmeticOperation.MULTIPLICATION:
            result[dest] = apply_binary(s1, s2, "*")
        else:
            raise ValueError(f"Unsupported arithmetic operation: {op}")

        return preserve_distribution_layouts(df, result, invalidated_columns=(dest,))

    @staticmethod
    def apply_mixer(
        df: pd.DataFrame,
        dest_col: str,
        source_cols: list[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into a destination column with SD propagation.

        Supports Sum, Mean, and Concatenate operations.
        For numeric operations, automatically propagates standard deviation
        columns with the canonical .sd suffix. Missing source values are skipped;
        unknown SDs of contributing values remain unknown. Mean SDs use each
        row's nonmissing source count. Repeated selections use correlated weights;
        an undefined estimate keeps its uncertainty missing.

        Args:
            df: Source DataFrame.
            dest_col: Name of the new merged column.
            source_cols: List of columns to merge.
            operation: One of 'Sum', 'Mean', or 'Concatenate'.
            separator: Separator string for concatenation.

        Returns:
            New DataFrame with the merged column added.

        Raises:
            ValueError: If the operation is not supported.
        """
        # [impl->req~ring5.data.configuration-mixer~1]
        # [impl->req~ring5.data.error-propagation~2]
        # [impl->req~ring5.data.numeric-mixer~1]
        try:
            op = MixerOperation(operation)
        except ValueError as exc:
            raise ValueError(f"Unknown mixer operation: {operation}") from exc
        if not source_cols:
            raise ValueError("At least one source column must be selected.")

        inspect_distribution_layouts(df)
        result = df.copy()
        invalidated = [dest_col]
        source_values = df[source_cols]

        if op == MixerOperation.SUM:
            result[dest_col] = aggregate_rows(source_values, "sum")
        elif op == MixerOperation.MEAN:
            result[dest_col] = aggregate_rows(source_values, "mean")
        elif op == MixerOperation.CONCATENATE:
            result[dest_col] = concat_columns(df, source_cols, separator)
        else:
            raise ValueError(f"Unsupported mixer operation: {op}")

        if op in (MixerOperation.SUM, MixerOperation.MEAN):
            deviation = ArithmeticService._mixer_deviation(df, source_cols, result[dest_col], op)
            if deviation is not None:
                result[f"{dest_col}.sd"] = deviation
                invalidated.append(f"{dest_col}.sd")

        return preserve_distribution_layouts(df, result, invalidated_columns=invalidated)

    @staticmethod
    def _mixer_deviation(
        frame: pd.DataFrame,
        source_cols: list[str],
        estimate: pd.Series,
        operation: MixerOperation,
    ) -> pd.Series | None:
        # [impl->req~ring5.data.error-propagation~2]
        """Combine distinct-source SDs with correlated repeated-source weights.

        Row scaling avoids intermediate overflow and premature underflow. Two streaming
        passes keep memory proportional to the row count, not the column count.
        """
        multiplicities = Counter(source_cols)
        companions = [col for col in multiplicities if f"{col}.sd" in frame.columns]
        if not companions:
            return None

        scale = pd.Series(0.0, index=frame.index)
        unknown = pd.Series(False, index=frame.index)
        infinite = pd.Series(False, index=frame.index)
        count = pd.Series(0, index=frame.index, dtype="int64")
        for col, weight in multiplicities.items():
            present = ~_missing_values(frame[col])
            if operation == MixerOperation.MEAN:
                count = count + present.astype("int64") * weight
            if f"{col}.sd" in frame.columns:
                magnitude = _sd_magnitude(frame[f"{col}.sd"], present)
                unknown = unknown | _missing_values(magnitude)
                infinite = infinite | magnitude.eq(np.inf).fillna(False)
                scale = pd.Series(np.fmax(scale, magnitude), index=frame.index)

        undefined = _missing_values(estimate)
        active = ~(unknown | infinite | undefined)
        safe_scale = scale.where(active & scale.ne(0), 1.0)
        normalized = pd.Series(0.0, index=frame.index)
        for col in companions:
            magnitude = _sd_magnitude(frame[f"{col}.sd"], ~_missing_values(frame[col]))
            component = (magnitude / safe_scale).where(active, 0.0)
            normalized = pd.Series(
                np.hypot(normalized, component * multiplicities[col]), index=frame.index
            )
        if operation == MixerOperation.MEAN:
            normalized = normalized / count.where(count.ne(0))
        deviation = safe_scale * normalized
        return deviation.mask(infinite, np.inf).mask(unknown | undefined)

    @staticmethod
    def validate_merge_inputs(
        df: pd.DataFrame,
        columns: list[str],
        operation: str,
        new_column_name: str,
    ) -> list[str]:
        """Validate inputs for the column mixer.

        Args:
            df: The DataFrame to validate against.
            columns: Source columns to merge.
            operation: The merge operation name.
            new_column_name: Desired name for the result column.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []

        if not columns:
            errors.append("At least one column must be selected")
        elif len(columns) < 2:
            errors.append("At least two columns must be selected for merging")

        missing = [col for col in columns if col not in df.columns]
        if missing:
            errors.append(f"Columns not found in DataFrame: {', '.join(missing)}")

        valid_ops = [op.value for op in MixerOperation]
        if operation not in valid_ops:
            errors.append(f"Invalid operation: '{operation}'. Valid: {', '.join(valid_ops)}")

        if not new_column_name:
            errors.append("New column name cannot be empty")
        elif new_column_name in df.columns:
            errors.append(f"Column '{new_column_name}' already exists in DataFrame")

        return errors
