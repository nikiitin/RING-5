"""Stateless composition operations for named workspace datasets."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import pandas as pd
from pandas.errors import MergeError

from src.core.models.dataset_workspace_models import JoinCardinality, JoinDiagnostics

_JOIN_CARDINALITIES = frozenset({"one_to_one", "one_to_many", "many_to_one", "many_to_many"})


class DatasetWorkspaceService:
    """Join or append datasets without mutating their stored inputs."""

    @classmethod
    def append(
        cls,
        datasets: Sequence[pd.DataFrame],
        *,
        join: Literal["outer", "inner"] = "outer",
    ) -> pd.DataFrame:
        """Append two or more datasets by matching column names.

        Args:
            datasets: Ordered datasets to append.
            join: Keep the union or intersection of columns.

        Returns:
            A new DataFrame with a fresh range index.

        Raises:
            ValueError: Fewer than two datasets or an option is invalid.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        frames = list(datasets)
        if len(frames) < 2:
            raise ValueError("Appending requires at least two datasets.")
        if join not in ("outer", "inner"):
            raise ValueError("Append join must be 'outer' or 'inner'.")
        for index, frame in enumerate(frames, start=1):
            cls._validate_columns(frame, f"Dataset {index}")
        return pd.concat(frames, axis=0, ignore_index=True, join=join, sort=False).copy()

    @classmethod
    def join(
        cls,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: Sequence[str],
        *,
        how: Literal["inner", "left", "right", "outer"] = "inner",
        suffixes: tuple[str, str] = ("_left", "_right"),
    ) -> pd.DataFrame:
        """Join two datasets on shared key columns.

        Args:
            left: Left-side dataset.
            right: Right-side dataset.
            on: Shared key columns.
            how: Row-retention strategy.
            suffixes: Distinct suffixes for overlapping non-key columns.

        Returns:
            A newly allocated joined DataFrame.

        Raises:
            ValueError: Keys, columns, join mode, or suffixes are invalid.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        keys = cls._validate_join_inputs(left, right, on, how=how, suffixes=suffixes)
        try:
            return left.merge(
                right,
                how=how,
                on=keys,
                sort=False,
                suffixes=suffixes,
            ).copy()
        except (KeyError, MergeError, TypeError, ValueError) as exc:
            raise ValueError(f"Datasets cannot be joined: {exc}") from exc

    @classmethod
    def diagnose_join(
        cls,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: Sequence[str],
        *,
        cardinality: JoinCardinality,
    ) -> JoinDiagnostics:
        """Inspect duplicate keys, unmatched rows, and expected cardinality."""
        # [impl->req~ring5.data.validated-joins~1]
        keys = cls._validate_join_inputs(
            left,
            right,
            on,
            how="inner",
            suffixes=("_left", "_right"),
        )
        if cardinality not in _JOIN_CARDINALITIES:
            choices = ", ".join(sorted(_JOIN_CARDINALITIES))
            raise ValueError(f"Invalid join cardinality {cardinality!r}. Use {choices}.")

        left_duplicates = left.duplicated(keys, keep=False).to_numpy(dtype=bool)
        right_duplicates = right.duplicated(keys, keep=False).to_numpy(dtype=bool)
        left_groups = int(left.loc[left_duplicates, keys].drop_duplicates().shape[0])
        right_groups = int(right.loc[right_duplicates, keys].drop_duplicates().shape[0])
        left_duplicate_rows = int(left_duplicates.sum())
        right_duplicate_rows = int(right_duplicates.sum())
        cardinality_valid = {
            "one_to_one": left_duplicate_rows == 0 and right_duplicate_rows == 0,
            "one_to_many": left_duplicate_rows == 0,
            "many_to_one": right_duplicate_rows == 0,
            "many_to_many": True,
        }[cardinality]

        try:
            left_keys = left[keys].drop_duplicates()
            right_keys = right[keys].drop_duplicates()
            matched_key_count = len(left_keys.merge(right_keys, how="inner", on=keys, sort=False))
            left_unmatched = cls._unmatched_row_count(left, right_keys, keys)
            right_unmatched = cls._unmatched_row_count(right, left_keys, keys)
        except (KeyError, MergeError, TypeError, ValueError) as exc:
            raise ValueError(f"Join keys cannot be compared: {exc}") from exc

        return JoinDiagnostics(
            key_columns=tuple(keys),
            expected_cardinality=cardinality,
            cardinality_valid=cardinality_valid,
            left_rows=len(left),
            right_rows=len(right),
            left_duplicate_key_rows=left_duplicate_rows,
            right_duplicate_key_rows=right_duplicate_rows,
            left_duplicate_key_groups=left_groups,
            right_duplicate_key_groups=right_groups,
            left_unmatched_rows=left_unmatched,
            right_unmatched_rows=right_unmatched,
            matched_key_count=matched_key_count,
        )

    @classmethod
    def validated_join(
        cls,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: Sequence[str],
        *,
        cardinality: JoinCardinality,
        how: Literal["inner", "left", "right", "outer"] = "inner",
        suffixes: tuple[str, str] = ("_left", "_right"),
    ) -> tuple[pd.DataFrame, JoinDiagnostics]:
        """Join only when the explicitly selected key cardinality is satisfied."""
        # [impl->req~ring5.data.validated-joins~1]
        diagnostics = cls.diagnose_join(left, right, on, cardinality=cardinality)
        if not diagnostics.cardinality_valid:
            label = cardinality.replace("_", "-")
            raise ValueError(
                f"Expected a {label} join, but duplicate keys affect "
                f"{diagnostics.left_duplicate_key_rows} left rows in "
                f"{diagnostics.left_duplicate_key_groups} groups and "
                f"{diagnostics.right_duplicate_key_rows} right rows in "
                f"{diagnostics.right_duplicate_key_groups} groups."
            )
        return (
            cls.join(left, right, on, how=how, suffixes=suffixes),
            diagnostics,
        )

    @classmethod
    def _validate_join_inputs(
        cls,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: Sequence[str],
        *,
        how: str,
        suffixes: tuple[str, str],
    ) -> list[str]:
        cls._validate_columns(left, "Left dataset")
        cls._validate_columns(right, "Right dataset")
        keys = list(on)
        if not keys:
            raise ValueError("Joining requires at least one key column.")
        if any(not isinstance(column, str) or not column for column in keys):
            raise ValueError("Every join key must be a non-empty string.")
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate join keys are not allowed.")
        for label, frame in (("Left", left), ("Right", right)):
            missing = [column for column in keys if column not in frame.columns]
            if missing:
                raise ValueError(f"{label} dataset is missing join keys: {', '.join(missing)}.")
        if how not in ("inner", "left", "right", "outer"):
            raise ValueError("Join mode must be 'inner', 'left', 'right', or 'outer'.")
        if (
            not isinstance(suffixes, tuple)
            or len(suffixes) != 2
            or any(not isinstance(suffix, str) or not suffix for suffix in suffixes)
            or suffixes[0] == suffixes[1]
        ):
            raise ValueError("Join suffixes must be two distinct non-empty strings.")
        return keys

    @staticmethod
    def _unmatched_row_count(
        source: pd.DataFrame,
        other_keys: pd.DataFrame,
        keys: list[str],
    ) -> int:
        marker = "__ring5_join_match__"
        while marker in keys:
            marker = f"_{marker}"
        candidates = other_keys.assign(**{marker: True})
        probe = source[keys].merge(candidates, how="left", on=keys, sort=False)
        return int(probe[marker].isna().sum())

    @staticmethod
    def _validate_columns(data: pd.DataFrame, label: str) -> None:
        if any(not isinstance(column, str) or not column for column in data.columns):
            raise ValueError(f"{label} requires non-empty string column names.")
        if data.columns.duplicated().any():
            raise ValueError(f"{label} requires unique column names.")
