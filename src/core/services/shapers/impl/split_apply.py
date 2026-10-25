"""Apply independent pipelines to column groups and merge their results."""

import logging
from collections.abc import Mapping, Sequence
from typing import Any, cast, override

import pandas as pd

from src.core.models.shaper_models import (
    SplitApplyGroupConfig,
    SplitApplyShaperConfig,
)
from src.core.services.shapers.uni_df_shaper import UniDfShaper

logger = logging.getLogger(__name__)


class SplitApply(UniDfShaper):
    """Split a DataFrame by column groups, apply sub-pipelines, then merge.

    Each group receives the join columns plus its own numeric columns.
    Sub-pipelines are applied independently so that row-adding shapers
    (Mean) or row-modifying shapers (Normalize) only affect their own
    columns without cross-contamination.
    """

    def __init__(self, params: dict[str, Any]) -> None:
        """Initialize SplitApply shaper.

        Args:
            params: Dictionary containing:
                - joinColumns (List[str]): Columns shared across all groups,
                  used for merging results back together.
                - groups (List[Dict]): Each dict has:
                    - columns (List[str]): Numeric columns for this group.
                    - pipeline (List[Dict]): Shaper configs to apply.
        """
        super().__init__(params)
        config = cast(SplitApplyShaperConfig, self.params)
        self._join_columns: list[str] = config["joinColumns"]
        self._groups: list[SplitApplyGroupConfig] = config["groups"]
        self._params = self.params

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify all referenced columns exist in the DataFrame."""
        super()._verify_preconditions(data_frame)

        for col in self._join_columns:
            if col not in data_frame.columns:
                raise ValueError(
                    f"SplitApply: Join column '{col}' not found "
                    f"in DataFrame. Available: "
                    f"{list(data_frame.columns)}"
                )

        for idx, group in enumerate(self._groups):
            for col in group.get("columns", []):
                if col not in data_frame.columns:
                    raise ValueError(
                        f"SplitApply: Group {idx} column '{col}' " f"not found in DataFrame."
                    )

        return True

    @staticmethod
    def _apply_sub_pipeline(
        data: pd.DataFrame,
        pipeline: Sequence[Mapping[str, object]],
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame slice.

        The core pipeline engine owns admission and execution. The import is local
        because its factory registers SplitApply.

        Args:
            data: Input DataFrame (join columns + group columns).
            pipeline: List of shaper config dicts, each with a 'type' key.

        Returns:
            Transformed DataFrame.
        """
        # [impl->req~ring5.shaping.split-apply~1]
        from src.core.services.shapers.pipeline_service import PipelineService

        return PipelineService.process_pipeline(data.copy(), pipeline)

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Split data by groups, apply sub-pipelines, merge results.

        Algorithm:
            1. For each group, select joinColumns + group.columns
            2. Apply the group's sub-pipeline to the slice
            3. Merge all group results sequentially on joinColumns

        The first group's result becomes the base. Subsequent groups
        are merged (outer join) on the join columns, adding their
        own numeric columns without duplicating the categorical data.

        Args:
            data_frame: Input DataFrame.

        Returns:
            Merged DataFrame with all groups' transformations applied
            independently.
        """
        # [impl->req~ring5.shaping.split-apply~1]
        self._verify_preconditions(data_frame)

        # Also include any .sd columns that correspond to group columns
        group_results: list[pd.DataFrame] = []
        for idx, group in enumerate(self._groups):
            group_cols: list[str] = list(group.get("columns", []))
            pipeline: Sequence[Mapping[str, object]] = group.get("pipeline", [])

            # Include matching .sd columns automatically
            sd_cols: list[str] = [
                f"{col}.sd" for col in group_cols if f"{col}.sd" in data_frame.columns
            ]
            select_cols: list[str] = self._join_columns + group_cols + sd_cols

            # Slice the DataFrame to only this group's columns
            slice_df: pd.DataFrame = data_frame[select_cols].copy()

            # Apply sub-pipeline if any
            if pipeline:
                try:
                    slice_df = self._apply_sub_pipeline(slice_df, pipeline)
                except (KeyError, TypeError, ValueError, RuntimeError) as e:
                    raise ValueError(
                        f"SplitApply: Sub-pipeline failed for group "
                        f"{idx} (columns={group_cols}): {e}"
                    ) from e

            if len(self._groups) > 1 and slice_df.duplicated(self._join_columns).any():
                raise ValueError(
                    f"SplitApply: Group {idx} has duplicate join keys in "
                    f"{self._join_columns}; include every row-identifying column."
                )
            group_results.append(slice_df)

        # Merge results: start with first group, outer-join the rest
        merged: pd.DataFrame = group_results[0]
        for subsequent in group_results[1:]:
            merged = merged.merge(
                subsequent,
                on=self._join_columns,
                how="outer",
                validate="one_to_one",
            )

        return merged
