"""Apply independent pipelines to column groups and merge their results."""

import logging
from typing import Any, cast, override

import pandas as pd

from src.core.models.shaper_models import (
    ShaperStepConfig,
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
        config = cast(SplitApplyShaperConfig, params)
        self._join_columns: list[str] = config.get("joinColumns", [])
        self._groups: list[SplitApplyGroupConfig] = config.get("groups", [])
        self._params = params

        super().__init__(params)

    @override
    def _verify_params(self) -> bool:
        """Validate parameter structure."""
        super()._verify_params()

        if not self._join_columns:
            raise ValueError("SplitApply: 'joinColumns' must be a non-empty list.")
        if not isinstance(self._join_columns, list):
            raise TypeError("SplitApply: 'joinColumns' must be a list.")

        if not self._groups or len(self._groups) < 2:
            raise ValueError("SplitApply: 'groups' must contain at least 2 groups.")
        if len(self._groups) > 4:
            raise ValueError(
                "SplitApply: 'groups' must contain at most 4 groups " f"(got {len(self._groups)})."
            )

        # Validate each group
        all_group_cols: list[str] = []
        for idx, group in enumerate(self._groups):
            cols = group.get("columns", [])
            if not cols:
                raise ValueError(
                    f"SplitApply: Group {idx} must have a non-empty " f"'columns' list."
                )
            if not isinstance(cols, list):
                raise TypeError(f"SplitApply: Group {idx} 'columns' must be a list.")
            pipeline = group.get("pipeline", [])
            if not isinstance(pipeline, list):
                raise TypeError(f"SplitApply: Group {idx} 'pipeline' must be a list.")

            # Check for overlapping columns
            for col in cols:
                if col in all_group_cols:
                    raise ValueError(
                        f"SplitApply: Column '{col}' appears in "
                        f"multiple groups. Each column must belong "
                        f"to exactly one group."
                    )
                all_group_cols.append(col)

        return True

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
        pipeline: list[ShaperStepConfig],
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame slice.

        Uses ShaperFactory to create each shaper. This is intentionally
        a late import to avoid circular dependencies.

        Args:
            data: Input DataFrame (join columns + group columns).
            pipeline: List of shaper config dicts, each with a 'type' key.

        Returns:
            Transformed DataFrame.
        """
        # Late import to avoid circular dependency with factory
        from src.core.services.shapers.factory import ShaperFactory

        result: pd.DataFrame = data.copy()
        for step_cfg in pipeline:
            shaper_type = step_cfg.get("type")
            if not shaper_type:
                continue
            shaper = ShaperFactory.create_shaper(shaper_type, step_cfg)
            result = shaper(result)
        return result

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
        self._verify_preconditions(data_frame)

        # Also include any .sd columns that correspond to group columns
        group_results: list[pd.DataFrame] = []
        for idx, group in enumerate(self._groups):
            group_cols: list[str] = list(group.get("columns", []))
            pipeline: list[ShaperStepConfig] = group.get("pipeline", [])

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
                except Exception as e:
                    raise ValueError(
                        f"SplitApply: Sub-pipeline failed for group "
                        f"{idx} (columns={group_cols}): {e}"
                    ) from e

            group_results.append(slice_df)

        # Merge results: start with first group, outer-join the rest
        merged: pd.DataFrame = group_results[0]
        for subsequent in group_results[1:]:
            merged = merged.merge(
                subsequent,
                on=self._join_columns,
                how="outer",
            )

        return merged
