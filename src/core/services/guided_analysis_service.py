"""Workspace-derived guidance without presentation-layer dependencies."""

from __future__ import annotations

import pandas as pd

from src.core.models.guided_analysis_models import (
    GuidedAnalysisProgress,
    GuidedAnalysisStage,
    GuidedAnalysisStageId,
)


class GuidedAnalysisService:
    """Assess the five milestones of a complete comparison workflow."""

    _DEFINITIONS: tuple[tuple[GuidedAnalysisStageId, str, str, str, str], ...] = (
        (
            "source",
            "Choose a source",
            "Load simulator output or review and accept a tabular import.",
            "Choose data source",
            "Data Source",
        ),
        (
            "validation",
            "Validate the data",
            "Check that the accepted table is structurally ready for analysis.",
            "Review data quality",
            "Data Managers",
        ),
        (
            "comparison",
            "Set up a comparison",
            "Choose baseline, candidate, alignment keys, metrics, and tolerances.",
            "Configure comparison",
            "Data Managers",
        ),
        (
            "visualization",
            "Build a visualization",
            "Create and render a plot from the comparison-ready workspace.",
            "Create visualization",
            "Manage Plots",
        ),
        (
            "export",
            "Export the result",
            "Download the rendered figure in the format required by its destination.",
            "Open export controls",
            "Manage Plots",
        ),
    )

    @classmethod
    def assess(
        cls,
        data: pd.DataFrame | None,
        *,
        comparison_ready: bool,
        plot_count: int,
        rendered_plot_count: int,
        exported: bool = False,
    ) -> GuidedAnalysisProgress:
        """Return ordered guidance inferred from current workspace evidence.

        Args:
            data: Active source table, if one is loaded.
            comparison_ready: Whether a comparison result or history entry exists.
            plot_count: Number of plots in the workspace.
            rendered_plot_count: Number of plots with a generated figure.
            exported: Whether this workflow has initiated a figure download.

        Returns:
            Immutable stage statuses and the first incomplete milestone.

        Raises:
            TypeError: Inputs use unsupported types.
            ValueError: Plot counts are negative or inconsistent.
        """
        # [impl->req~ring5.workspace.guided-analysis~1]
        if data is not None and not isinstance(data, pd.DataFrame):
            raise TypeError("Guided analysis data must be a pandas DataFrame or None.")
        for flag_name, flag_value in (
            ("comparison_ready", comparison_ready),
            ("exported", exported),
        ):
            if not isinstance(flag_value, bool):
                raise TypeError(f"{flag_name} must be a boolean.")
        for count_name, count_value in (
            ("plot_count", plot_count),
            ("rendered_plot_count", rendered_plot_count),
        ):
            if isinstance(count_value, bool) or not isinstance(count_value, int):
                raise TypeError(f"{count_name} must be an integer.")
            if count_value < 0:
                raise ValueError(f"{count_name} cannot be negative.")
        if rendered_plot_count > plot_count:
            raise ValueError("rendered_plot_count cannot exceed plot_count.")

        source_ready = data is not None and not data.empty
        validation_ready, validation_detail = cls._validation_status(data)
        comparison_complete = validation_ready and comparison_ready
        visualization_complete = comparison_complete and rendered_plot_count > 0
        checks = (
            source_ready,
            validation_ready,
            comparison_complete,
            visualization_complete,
            visualization_complete and exported,
        )
        details = (
            (
                f"{len(data):,} rows and {len(data.columns):,} columns are loaded."
                if source_ready and data is not None
                else "No source data is loaded."
            ),
            validation_detail,
            (
                "A comparison result is available."
                if comparison_ready
                else "No baseline-to-candidate comparison has been completed."
            ),
            (
                f"{rendered_plot_count} of {plot_count} plots have a rendered figure."
                if plot_count
                else "No visualization has been created."
            ),
            (
                "A figure download has been initiated."
                if exported and rendered_plot_count
                else "No figure download has been initiated in this guided run."
            ),
        )
        first_incomplete = next((index for index, ready in enumerate(checks) if not ready), None)
        stages = tuple(
            GuidedAnalysisStage(
                stage_id=definition[0],
                title=definition[1],
                description=definition[2],
                status=(
                    "complete"
                    if checks[index]
                    else "current" if index == first_incomplete else "blocked"
                ),
                detail=details[index],
                action_label=definition[3],
                destination=definition[4],
            )
            for index, definition in enumerate(cls._DEFINITIONS)
        )
        completed = sum(checks)
        current = stages[first_incomplete].stage_id if first_incomplete is not None else None
        return GuidedAnalysisProgress(
            stages=stages,
            completed_stages=completed,
            total_stages=len(stages),
            percent_complete=round(completed * 100 / len(stages)),
            current_stage=current,
            complete=first_incomplete is None,
        )

    @staticmethod
    def _validation_status(data: pd.DataFrame | None) -> tuple[bool, str]:
        """Check bounded structural conditions needed by downstream analysis."""
        if data is None or data.empty:
            return False, "Load data before validating it."
        columns = list(data.columns)
        if any(not isinstance(column, str) or not column.strip() for column in columns):
            return False, "Every column needs a non-empty text name."
        if len(columns) != len(set(columns)):
            return False, "Column names must be unique."
        numeric_columns = list(data.select_dtypes(include="number").columns)
        if not numeric_columns:
            return False, "At least one numeric metric is required for comparison and plotting."
        return (
            True,
            f"Structure is valid and {len(numeric_columns)} numeric metric"
            f"{'s are' if len(numeric_columns) != 1 else ' is'} available.",
        )
