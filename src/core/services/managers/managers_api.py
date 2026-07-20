"""
Managers API Protocol -- Interface for data transformation managers.

Defines the contract for stateless data transformation operations used by
the data-manager UI components: arithmetic operations, outlier removal,
and seed reduction.
"""

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, runtime_checkable

import pandas as pd

from src.core.models.dataset_workspace_models import JoinCardinality, JoinDiagnostics
from src.core.models.quality_models import DataQualityReport
from src.core.models.schema_contract_models import DatasetSchemaContract, SchemaValidationReport
from src.core.models.semantic_metadata_models import DatasetSemantics


@runtime_checkable
class ManagersAPI(Protocol):
    """Protocol for stateless data transformation operations.

    Groups arithmetic, outlier removal, reduction, and column-merge
    operations used by the data-manager UI components.
    """

    # [impl->req~ring5.extension.data-manager~1]

    # -- Arithmetic (Preprocessor) --

    def list_operators(self) -> list[str]:
        """Return supported binary arithmetic operators."""
        raise NotImplementedError

    def apply_operation(
        self,
        df: pd.DataFrame,
        operation: str,
        src1: str,
        src2: str,
        dest: str,
    ) -> pd.DataFrame:
        """Apply arithmetic operation between two columns."""
        raise NotImplementedError

    # -- Mixer (Multi-column merge) --

    def apply_mixer(
        self,
        df: pd.DataFrame,
        dest_col: str,
        source_cols: list[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> pd.DataFrame:
        """Merge multiple columns into one with SD propagation."""
        raise NotImplementedError

    def validate_merge_inputs(
        self,
        df: pd.DataFrame,
        columns: list[str],
        operation: str,
        new_column_name: str,
    ) -> list[str]:
        """Validate inputs for merge/mixer operations."""
        raise NotImplementedError

    # -- Outlier Removal --

    def remove_outliers(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: list[str],
    ) -> pd.DataFrame:
        """Remove statistical outliers based on Q3 threshold."""
        raise NotImplementedError

    def validate_outlier_inputs(
        self,
        df: pd.DataFrame,
        outlier_col: str,
        group_by_cols: list[str],
    ) -> list[str]:
        """Validate inputs for outlier removal."""
        raise NotImplementedError

    # -- Seeds Reduction --

    def reduce_seeds(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str],
        statistic_cols: list[str],
    ) -> pd.DataFrame:
        """Aggregate data across random seeds (mean + stdev)."""
        raise NotImplementedError

    def validate_seeds_reducer_inputs(
        self,
        df: pd.DataFrame,
        categorical_cols: list[str],
        statistic_cols: list[str],
    ) -> list[str]:
        """Validate inputs for seeds reduction."""
        raise NotImplementedError

    # -- Baseline comparison --

    def compare(
        self,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        key_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        directions: (
            Literal["higher", "lower"] | Mapping[str, Literal["higher", "lower"]]
        ) = "higher",
        thresholds: float | Mapping[str, float] = 0.0,
        threshold_mode: Literal["percentage", "absolute"] = "percentage",
        baseline_name: str = "baseline",
        candidate_name: str = "candidate",
    ) -> pd.DataFrame:
        """Compare aligned baseline and candidate metrics.

        Args:
            baseline: Reference measurements with unique alignment keys.
            candidate: Measurements evaluated against the reference.
            key_columns: Columns identifying corresponding rows.
            metric_columns: Numeric columns to compare.
            directions: Global or per-metric optimization direction.
            thresholds: Global or per-metric non-negative tolerance.
            threshold_mode: Interpret tolerances as percentages or absolute values.
            baseline_name: Label stored with reference values.
            candidate_name: Label stored with candidate values.

        Returns:
            Long-form comparison rows with changes and outcomes.
        """
        raise NotImplementedError

    def compare_statistics(
        self,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        group_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        confidence_level: float = 0.95,
        alpha: float = 0.05,
        bootstrap_samples: int = 2_000,
        random_seed: int = 0,
        minimum_sample_size: int = 5,
    ) -> pd.DataFrame:
        """Calculate repeated-sample comparison statistics.

        Args:
            baseline: Reference observations.
            candidate: Candidate observations.
            group_columns: Columns defining independent comparison groups.
            metric_columns: Numeric measurements to compare.
            confidence_level: Two-sided confidence level.
            alpha: Significance threshold for the Welch test.
            bootstrap_samples: Number of deterministic resamples.
            random_seed: Seed used for resampling.
            minimum_sample_size: Per-side count below which warnings are emitted.

        Returns:
            Long-form statistical comparison rows.
        """
        raise NotImplementedError

    def annotate_comparison(
        self,
        comparison: pd.DataFrame,
        *,
        label_columns: Sequence[str] | None = None,
        change_mode: Literal["threshold", "percentage", "absolute"] = "threshold",
    ) -> pd.DataFrame:
        """Prepare accessible plot annotations for comparison rows.

        Args:
            comparison: Long-form threshold comparison result.
            label_columns: Columns combined with the metric for point labels.
            change_mode: Change measurement to expose for plotting.

        Returns:
            A new DataFrame with annotation labels, text, symbols, and colors.
        """
        raise NotImplementedError

    def profile_data(
        self,
        data: pd.DataFrame,
        *,
        expected_types: (
            Mapping[str, Literal["numeric", "integer", "boolean", "datetime", "string"]] | None
        ) = None,
    ) -> DataQualityReport:
        """Calculate dataset and per-column quality measurements.

        Args:
            data: Dataset to inspect without mutation.
            expected_types: Optional column-to-type expectations.

        Returns:
            Immutable quality report with an ordered column profile.
        """
        raise NotImplementedError

    def infer_schema_contract(
        self,
        data: pd.DataFrame,
        *,
        name: str = "dataset",
    ) -> DatasetSchemaContract:
        """Infer editable type and nullability rules from a dataset."""
        raise NotImplementedError

    def validate_schema(
        self,
        data: pd.DataFrame,
        contract: DatasetSchemaContract,
    ) -> SchemaValidationReport:
        """Validate a dataset against an explicit schema contract."""
        raise NotImplementedError

    def attach_semantics(
        self,
        data: pd.DataFrame,
        semantics: DatasetSemantics,
    ) -> pd.DataFrame:
        """Return a copy retaining validated semantic labels and units."""
        raise NotImplementedError

    def inspect_semantics(self, data: pd.DataFrame) -> DatasetSemantics:
        """Return ordered semantic metadata retained by a dataset."""
        raise NotImplementedError

    def convert_unit(
        self,
        data: pd.DataFrame,
        column: str,
        target_unit: str,
    ) -> pd.DataFrame:
        """Convert one numeric column between compatible declared units."""
        raise NotImplementedError

    def supported_units(self) -> tuple[str, ...]:
        """Return canonical units accepted by semantic conversion."""
        raise NotImplementedError

    def append_datasets(
        self,
        datasets: Sequence[pd.DataFrame],
        *,
        join: Literal["outer", "inner"] = "outer",
    ) -> pd.DataFrame:
        """Append datasets by the union or intersection of columns.

        Args:
            datasets: Ordered datasets to append.
            join: Keep the column union or intersection.

        Returns:
            A new DataFrame with a fresh range index.
        """
        raise NotImplementedError

    def join_datasets(
        self,
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
        """
        raise NotImplementedError

    def diagnose_join(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: Sequence[str],
        *,
        cardinality: JoinCardinality,
    ) -> JoinDiagnostics:
        """Diagnose key duplication, unmatched rows, and cardinality."""
        raise NotImplementedError

    def validated_join(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        on: Sequence[str],
        *,
        cardinality: JoinCardinality,
        how: Literal["inner", "left", "right", "outer"] = "inner",
        suffixes: tuple[str, str] = ("_left", "_right"),
    ) -> tuple[pd.DataFrame, JoinDiagnostics]:
        """Join only when the explicit key cardinality is satisfied."""
        raise NotImplementedError
