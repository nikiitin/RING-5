"""Stateless composition operations for named workspace datasets."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import pandas as pd
from pandas.errors import MergeError


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

    @staticmethod
    def _validate_columns(data: pd.DataFrame, label: str) -> None:
        if any(not isinstance(column, str) or not column for column in data.columns):
            raise ValueError(f"{label} requires non-empty string column names.")
        if data.columns.duplicated().any():
            raise ValueError(f"{label} requires unique column names.")
