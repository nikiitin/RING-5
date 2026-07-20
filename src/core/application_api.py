"""Application facade used by the web presentation layer."""

import logging
from collections.abc import Mapping, Sequence
from concurrent.futures import Future
from typing import Any, Literal, cast

import numpy as np
import pandas as pd

from src.core.models import (
    DatasetInfo,
    DatasetLineage,
    DatasetRevision,
    DatasetSnapshotInfo,
    DashboardSpec,
    DrillDownResult,
    JoinCardinality,
    JoinDiagnostics,
    LinkedSelectionSpec,
    PlotTransferMode,
    PlotTransferResult,
    SmallMultiplesSpec,
    ParseBatchResult,
    ScanFileResult,
    ScannedVariable,
    ScanResult,
    StatConfig,
)
from src.core.models.pattern_index_service import PatternIndexService
from src.core.models.data_models import (
    ColumnInfoResult,
    CsvPoolEntry,
    ParseVariableConfig,
    SavedConfigData,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.shaper_models import ShaperStepConfig
from src.core.models.history_models import OperationRecord
from src.core.models.parsing_models import StatParamValue
from src.core.models.plot_protocol import PlotDeserializer
from src.core.models.visualization import FigureConfig
from src.core.services.data_services.data_services_api import DataServicesAPI
from src.core.services.managers.managers_api import ManagersAPI
from src.core.services.services_impl import DefaultServicesAPI
from src.core.services.shapers.shapers_api import ShapersAPI
from src.core.services.visualization.drill_down_service import drill_down_rows
from src.core.services.visualization.small_multiples_service import (
    create_small_multiples_spec as build_small_multiples_spec,
)
from src.core.services.visualization.plot_transfer_service import copy_plot_content
from src.core.state.repository_state_manager import RepositoryStateManager
from src.parsing.framework.file_discovery import find_stats_files as _find_stats_files
from src.parsing.parser_protocol import SimulationParser
from src.parsing.registry import SimulatorInfo, SimulatorRegistry

logger = logging.getLogger(__name__)


class ApplicationAPI:
    """Coordinate parsers, domain services, and repository state for the UI."""

    # [impl->req~ring5.quality.application-facade~1]

    def __init__(
        self,
        plot_deserializer: PlotDeserializer | None = None,
        parser: SimulationParser | None = None,
    ) -> None:
        """
        Initialize the Application API.

        Args:
            plot_deserializer: Optional callable that converts a dict into
                a ``PlotProtocol`` instance.  Injected into the repository
                layer so that portfolio restoration never imports web-layer
                classes directly.
            parser: Optional simulator parser backend.  Defaults to the
                gem5 parser from the ``SimulatorRegistry``.
        """
        self.state_manager = RepositoryStateManager(plot_deserializer=plot_deserializer)

        self._services = DefaultServicesAPI(self.state_manager)

        self._parser: SimulationParser = parser or SimulatorRegistry.get_parser("gem5")

        # A facade may cancel only scan jobs that it submitted.
        self._pending_scan_futures: list[Future[ScanFileResult]] = []

        logger.info("Application API initialized")

    # ServicesAPI sub-API access (for UI components)

    @property
    def managers(self) -> ManagersAPI:
        """Access stateless data transformation operations."""
        return self._services.managers

    @property
    def data_services(self) -> DataServicesAPI:
        """Access data storage, retrieval, and domain entity management."""
        return self._services.data_services

    @property
    def shapers(self) -> ShapersAPI:
        """Access pipeline and shaper operations."""
        return self._services.shapers

    def load_data(self, csv_path: str) -> None:
        """
        Orchestrate loading data from a file path:
        1. Load via data services
        2. Persist via StateManager
        """
        # [impl->req~ring5.ingestion.csv-load~1]
        try:
            # 1. Operation: Load
            df = self._services.data_services.load_csv_file(csv_path)

            # 2. Persistence: Save
            self.state_manager.set_data(df, operation=f"Load CSV: {csv_path}")
            self.state_manager.set_processed_data(None)  # Reset derived state
            self.state_manager.set_csv_path(csv_path)

            logger.info(f"Loaded and registered data from {csv_path}")
        except Exception as e:
            logger.error(f"Failed to load data from {csv_path}: {e}")
            raise

    def load_from_pool(self, csv_path: str) -> None:
        """Load a dataset from the CSV pool."""
        # Using pure string path from pool
        self.load_data(csv_path)

    def get_current_view(self) -> dict[str, Any]:
        """Assemble the current data pipeline state for UI consumption."""
        return {
            "raw_data": self.state_manager.get_data(),
            "processed_data": self.state_manager.get_processed_data(),
            "config": self.state_manager.get_config(),
        }

    def reset_session(self) -> None:
        """Clear all session data."""
        self.state_manager.clear_data()
        self.state_manager.clear_all()

    # Named dataset workspace

    def add_dataset(
        self,
        name: str,
        data: pd.DataFrame,
        *,
        select: bool = True,
        replace: bool = False,
        operation: str = "Add dataset",
        source_datasets: tuple[str, ...] = (),
    ) -> DatasetInfo:
        """Retain a named dataset without replacing unrelated workspace data.

        Args:
            name: Human-readable session-unique name.
            data: Dataset to retain by defensive copy.
            select: Make this dataset the active source-data view.
            replace: Permit replacement of the same name.
            operation: Human-readable lineage operation.
            source_datasets: Named datasets used to produce this state.

        Returns:
            Metadata for the stored dataset.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Named workspace data must be a pandas DataFrame.")
        return self.state_manager.add_dataset(
            name,
            data,
            select=select,
            replace=replace,
            operation=operation,
            source_datasets=source_datasets,
        )

    def add_current_dataset(
        self,
        name: str,
        *,
        select: bool = True,
        replace: bool = False,
    ) -> DatasetInfo:
        """Retain the current source-data view under a name."""
        data = self.state_manager.get_data()
        if data is None:
            raise ValueError("No active data is available to retain.")
        selected = self.state_manager.selected_dataset_name()
        sources = (selected,) if selected is not None else ()
        return self.add_dataset(
            name,
            data,
            select=select,
            replace=replace,
            operation="Retain current dataset",
            source_datasets=sources,
        )

    def list_datasets(self) -> tuple[DatasetInfo, ...]:
        """Return retained dataset metadata in insertion order."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        return self.state_manager.list_datasets()

    def get_dataset(self, name: str | None = None) -> pd.DataFrame:
        """Return a defensive copy of a named or selected dataset."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        return self.state_manager.get_dataset(name)

    def select_dataset(self, name: str) -> pd.DataFrame:
        """Select a retained dataset as the active source-data view."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        return self.state_manager.select_dataset(name)

    def remove_dataset(self, name: str) -> None:
        """Remove one retained dataset while preserving every other dataset."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        self.state_manager.remove_dataset(name)

    def update_selected_dataset(
        self,
        data: pd.DataFrame,
        *,
        operation: str,
        source_datasets: tuple[str, ...] = (),
    ) -> None:
        """Replace the active data and snapshot it when a named dataset is selected."""
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Updated workspace data must be a pandas DataFrame.")
        self.state_manager.set_data(
            data,
            operation=operation,
            source_datasets=source_datasets,
        )

    def get_dataset_lineage(self, name: str | None = None) -> DatasetLineage:
        """Inspect immutable revisions and recovery state for a named dataset."""
        # [impl->req~ring5.data.lineage-undo-redo~1]
        return self.state_manager.get_dataset_lineage(name)

    def get_dataset_revision(self, revision_id: str) -> pd.DataFrame:
        """Return a defensive copy of an immutable dataset revision."""
        # [impl->req~ring5.data.lineage-undo-redo~1]
        return self.state_manager.get_dataset_revision(revision_id)

    def undo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Restore the preceding revision of a named dataset."""
        # [impl->req~ring5.data.lineage-undo-redo~1]
        return self.state_manager.undo_dataset(name)

    def redo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Reapply the most recently undone revision of a named dataset."""
        # [impl->req~ring5.data.lineage-undo-redo~1]
        return self.state_manager.redo_dataset(name)

    def restore_dataset_revision(self, revision_id: str) -> DatasetRevision:
        """Restore any retained intermediate revision by ID."""
        # [impl->req~ring5.data.lineage-undo-redo~1]
        return self.state_manager.restore_dataset_revision(revision_id)

    def list_dataset_snapshots(self) -> tuple[DatasetSnapshotInfo, ...]:
        """List reusable local dataset snapshots without loading their tables."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        return self.data_services.list_dataset_snapshots()

    def save_dataset_snapshot(
        self,
        name: str,
        dataset_name: str | None = None,
        *,
        overwrite: bool = False,
    ) -> DatasetSnapshotInfo:
        """Persist a named or active dataset for verified reuse in later sessions."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        selected = self.state_manager.selected_dataset_name()
        if dataset_name is not None:
            data = self.state_manager.get_dataset(dataset_name)
            source_name = dataset_name.strip()
        elif selected is not None:
            data = self.state_manager.get_dataset(selected)
            source_name = selected
        else:
            active = self.state_manager.get_data()
            if active is None:
                raise ValueError("No active or named dataset is available to snapshot.")
            data = active
            source_name = "active_data"
        return self.data_services.save_dataset_snapshot(
            name,
            data,
            source_dataset=source_name,
            overwrite=overwrite,
        )

    def load_dataset_snapshot(
        self,
        name: str,
        dataset_name: str | None = None,
        *,
        select: bool = True,
        replace: bool = False,
    ) -> DatasetInfo:
        """Verify a snapshot and retain its table in the named workspace."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        snapshot, data = self.data_services.load_dataset_snapshot(name)
        output_name = snapshot.source_dataset if dataset_name is None else dataset_name
        return self.add_dataset(
            output_name,
            data,
            select=select,
            replace=replace,
            operation=f"Load reusable snapshot: {snapshot.name}",
        )

    def delete_dataset_snapshot(self, name: str) -> None:
        """Delete one reusable local dataset snapshot."""
        self.data_services.delete_dataset_snapshot(name)

    def append_datasets(
        self,
        dataset_names: Sequence[str],
        output_name: str,
        *,
        join: Literal["outer", "inner"] = "outer",
        select: bool = True,
        replace: bool = False,
    ) -> pd.DataFrame:
        """Append retained datasets and store the result under a new name."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        frames = [self.state_manager.get_dataset(name) for name in dataset_names]
        result = self.managers.append_datasets(frames, join=join)
        self.add_dataset(
            output_name,
            result,
            select=select,
            replace=replace,
            operation=f"Append datasets ({join})",
            source_datasets=tuple(dataset_names),
        )
        return result.copy(deep=True)

    def join_datasets(
        self,
        left_name: str,
        right_name: str,
        output_name: str,
        on: Sequence[str],
        *,
        how: Literal["inner", "left", "right", "outer"] = "inner",
        suffixes: tuple[str, str] = ("_left", "_right"),
        select: bool = True,
        replace: bool = False,
    ) -> pd.DataFrame:
        """Join retained datasets and store the result under a new name."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        left = self.state_manager.get_dataset(left_name)
        right = self.state_manager.get_dataset(right_name)
        result = self.managers.join_datasets(
            left,
            right,
            on,
            how=how,
            suffixes=suffixes,
        )
        self.add_dataset(
            output_name,
            result,
            select=select,
            replace=replace,
            operation=f"Join datasets ({how}) on {', '.join(on)}",
            source_datasets=(left_name, right_name),
        )
        return result.copy(deep=True)

    def diagnose_join(
        self,
        left_name: str,
        right_name: str,
        on: Sequence[str],
        *,
        cardinality: JoinCardinality,
    ) -> JoinDiagnostics:
        """Diagnose named-dataset join keys without changing workspace data."""
        # [impl->req~ring5.data.validated-joins~1]
        left = self.state_manager.get_dataset(left_name)
        right = self.state_manager.get_dataset(right_name)
        return self.managers.diagnose_join(
            left,
            right,
            on,
            cardinality=cardinality,
        )

    def join_datasets_validated(
        self,
        left_name: str,
        right_name: str,
        output_name: str,
        on: Sequence[str],
        *,
        cardinality: JoinCardinality,
        how: Literal["inner", "left", "right", "outer"] = "inner",
        suffixes: tuple[str, str] = ("_left", "_right"),
        select: bool = True,
        replace: bool = False,
    ) -> tuple[pd.DataFrame, JoinDiagnostics]:
        """Validate cardinality, join named datasets, and retain the result."""
        # [impl->req~ring5.data.validated-joins~1]
        left = self.state_manager.get_dataset(left_name)
        right = self.state_manager.get_dataset(right_name)
        result, diagnostics = self.managers.validated_join(
            left,
            right,
            on,
            cardinality=cardinality,
            how=how,
            suffixes=suffixes,
        )
        self.add_dataset(
            output_name,
            result,
            select=select,
            replace=replace,
            operation=(f"Validated {cardinality.replace('_', '-')} {how} join on {', '.join(on)}"),
            source_datasets=(left_name, right_name),
        )
        return result.copy(deep=True), diagnostics

    def compare_datasets(
        self,
        baseline_name: str,
        candidate_name: str,
        key_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        directions: (
            Literal["higher", "lower"] | Mapping[str, Literal["higher", "lower"]]
        ) = "higher",
        thresholds: float | Mapping[str, float] = 0.0,
        threshold_mode: Literal["percentage", "absolute"] = "percentage",
    ) -> pd.DataFrame:
        """Compare two retained datasets without changing either dataset."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        baseline = self.state_manager.get_dataset(baseline_name)
        candidate = self.state_manager.get_dataset(candidate_name)
        return self.managers.compare(
            baseline,
            candidate,
            key_columns,
            metric_columns,
            directions=directions,
            thresholds=thresholds,
            threshold_mode=threshold_mode,
            baseline_name=baseline_name,
            candidate_name=candidate_name,
        )

    # Parsing & Scanning

    def find_stats_files(self, search_path: str, pattern: str = "stats.txt") -> list[str]:
        """Find statistics files recursively.

        Args:
            search_path: Root directory to inspect.
            pattern: Filename glob pattern.

        Returns:
            Matching paths in discovery order, or an empty list when the root
            is missing or contains no matches.
        """
        return _find_stats_files(search_path, pattern)

    def submit_parse_async(
        self,
        stats_path: str,
        stats_pattern: str,
        variables: Sequence[ParseVariableConfig | StatConfig],
        output_dir: str,
        strategy_type: str = "simple",
        scanned_vars: list[ScannedVariable] | list[ScannedVariableDict] | None = None,
    ) -> ParseBatchResult:
        """
        Submit parsing job to the service.

        Converts variable dictionaries to StatConfig objects.
        Repetition and regex expansion are handled by the parsing module.
        """
        # [impl->req~ring5.ingestion.output-aliases~1]
        stat_configs: list[StatConfig] = []
        for var in variables:
            if isinstance(var, dict):
                # Normalize type for consistency
                v_type = str(var.get("type", "scalar")).lower()

                # Aliases are part of the serialized parser-variable contract.
                source_name = str(var.get("name", ""))
                alias = var.get("alias")
                params: dict[str, StatParamValue] = cast(dict[str, StatParamValue], dict(var))
                is_regex = PatternIndexService.is_pattern_variable(source_name)
                output_name = str(alias) if alias else source_name

                if alias and not is_regex:
                    params["parsed_ids"] = [source_name]

                config = StatConfig(
                    name=output_name,
                    source_name=source_name if alias else None,
                    type=v_type,
                    repeat=int(var.get("repeat", 1)),
                    statistics_only=bool(
                        var.get("statistics_only", var.get("statisticsOnly", False))
                    ),
                    params=params,
                    is_regex=is_regex,
                    keep_indices=bool(var.get("keep_indices", var.get("keepIndices", False))),
                )
            elif hasattr(var, "name") and hasattr(var, "type") and not hasattr(var, "params"):
                # Accept scanned-variable objects from compatibility callers.
                config = StatConfig(
                    name=var.name,
                    type=var.type,
                    params={"entries": getattr(var, "entries", [])},
                    is_regex=PatternIndexService.is_pattern_variable(var.name),
                )
            else:
                config = var

            stat_configs.append(config)

        # Convert ScannedVariableDict to ScannedVariable if needed
        resolved_scanned: list[ScannedVariable] | None = None
        if scanned_vars is not None:
            resolved_scanned = [
                ScannedVariable.from_dict(sv) if isinstance(sv, dict) else sv for sv in scanned_vars
            ]

        return self._parser.submit_parse_async(
            stats_path, stats_pattern, stat_configs, output_dir, strategy_type, resolved_scanned
        )

    def finalize_parsing(
        self,
        output_dir: str,
        results: list[dict[str, Any]],
        strategy_type: str = "simple",
        var_names: list[str] | None = None,
    ) -> str | None:
        """Finalize parsing results into a CSV."""
        return self._parser.finalize_parsing(
            output_dir, results, strategy_type, var_names=var_names
        )

    def submit_scan_async(
        self, stats_path: str, stats_pattern: str = "stats.txt", limit: int = 5
    ) -> list[Future[ScanFileResult]]:
        """Submit scanning job. Each future resolves to a ``ScanFileResult``."""
        futures = self._parser.submit_scan_async(stats_path, stats_pattern, limit)
        # Accumulate (pruning settled futures) rather than replace: replacing
        # would orphan a still-running earlier batch from cancellation.
        self._pending_scan_futures = [f for f in self._pending_scan_futures if not f.done()] + list(
            futures
        )
        return futures

    def finalize_scan(self, results: list[ScanFileResult]) -> ScanResult:
        """Aggregate per-file scan results into a ``ScanResult``.

        Also releases this instance's settled scan-future references (their
        per-file payloads are large; aggregation is the natural release
        point).
        """
        self._pending_scan_futures = [f for f in self._pending_scan_futures if not f.done()]
        return self._parser.aggregate_scan_results(results)

    def get_parse_status(self) -> str:
        """Get current parsing status.

        Returns a static 'idle' status. Status tracking is handled
        at the UI layer via session state.
        """
        return "idle"

    def get_scanner_status(self) -> str:
        """Get current scanner status."""
        return "idle"

    # Shapers & Pipelines

    def apply_shapers(
        self, data: pd.DataFrame, pipeline_config: list[ShaperStepConfig]
    ) -> pd.DataFrame:
        """Apply a sequence of shapers to a DataFrame."""
        return self._services.shapers.process_pipeline(data, pipeline_config)

    # Configuration Management

    def save_configuration(
        self,
        name: str,
        description: str,
        shapers_config: list[ShaperStepConfig],
        csv_path: str | None = None,
    ) -> str:
        """Save current configuration to disk."""
        return self._services.data_services.save_configuration(
            name, description, shapers_config, csv_path
        )

    def load_configuration(self, config_path: str) -> SavedConfigData:
        """Load configuration from file."""
        return self._services.data_services.load_configuration(config_path)

    def load_csv_pool(self) -> list[CsvPoolEntry]:
        """List available CSV files in the pool."""
        return self._services.data_services.load_csv_pool()

    def load_saved_configs(self) -> list[SavedConfigEntry]:
        """List all saved configurations."""
        return self._services.data_services.load_saved_configs()

    def delete_configuration(self, config_path: str) -> bool:
        """Delete a configuration file."""
        return self._services.data_services.delete_configuration(config_path)

    def add_to_csv_pool(self, file_path: str) -> str:
        """Add a file to the CSV pool."""
        return self._services.data_services.add_to_csv_pool(file_path)

    def delete_from_pool(self, file_path: str) -> bool:
        """Delete a file from the CSV pool."""
        return self._services.data_services.delete_from_csv_pool(file_path)

    def delete_from_csv_pool(self, file_path: str) -> bool:
        """Alias for delete_from_pool."""
        return self.delete_from_pool(file_path)

    def load_csv_file(self, file_path: str) -> pd.DataFrame:
        """Load a CSV file directly returning DataFrame."""
        return self._services.data_services.load_csv_file(file_path)

    def get_column_info(self, df: pd.DataFrame | None) -> ColumnInfoResult:
        """Get summary information about DataFrame columns for UI."""
        if df is None:
            return ColumnInfoResult(
                total_columns=0,
                total_rows=0,
                numeric_columns=[],
                categorical_columns=[],
                columns=[],
            )

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

        return ColumnInfoResult(
            total_columns=len(df.columns),
            total_rows=len(df),
            numeric_columns=numeric_cols,
            categorical_columns=categorical_cols,
            columns=df.columns.tolist(),
        )

    # Visualization Config (Delegated to StateManager)

    def get_visualization_config(self, plot_id: int) -> "FigureConfig | None":
        """Retrieve the visualization config for a plot."""
        return self.state_manager.get_visualization_config(plot_id)

    def set_visualization_config(self, plot_id: int, config: FigureConfig) -> None:
        """Store the visualization config for a plot."""
        self.state_manager.set_visualization_config(plot_id, config)

    def remove_visualization_config(self, plot_id: int) -> None:
        """Remove the visualization config for a plot."""
        self.state_manager.remove_visualization_config(plot_id)

    def create_dashboard(
        self,
        plot_ids: Sequence[int],
        *,
        title: str = "",
        rows: int | None = None,
        columns: int = 2,
        width: int = 1200,
        height: int = 800,
        shared_xaxes: bool = False,
        shared_yaxes: bool = False,
        shared_legend: bool = True,
        x_title: str = "",
        y_title: str = "",
        panel_titles: Sequence[str] | None = None,
    ) -> DashboardSpec:
        # [impl->req~ring5.plots.multi-panel-dashboard~1]
        """Create a validated dashboard layout from registered plots.

        The returned specification is immutable and contains stable plot IDs,
        so both the web application and the headless API use the same layout
        contract.  Rendering remains live: a later plot edit is reflected the
        next time the dashboard is rendered.
        """
        ids = tuple(plot_ids)
        if any(isinstance(plot_id, bool) or not isinstance(plot_id, int) for plot_id in ids):
            raise ValueError("Dashboard plot IDs must be integers.")

        available = {plot.plot_id: plot for plot in self.state_manager.get_plots()}
        missing = [plot_id for plot_id in ids if plot_id not in available]
        if missing:
            missing_text = ", ".join(str(plot_id) for plot_id in missing)
            raise ValueError(f"Dashboard references unknown plot IDs: {missing_text}.")

        if columns < 1:
            raise ValueError("Dashboard columns must be at least 1.")
        effective_rows = rows if rows is not None else max(1, (len(ids) + columns - 1) // columns)
        titles = (
            tuple(str(value) for value in panel_titles)
            if panel_titles is not None
            else tuple(str(available[plot_id].name) for plot_id in ids)
        )
        return DashboardSpec(
            plot_ids=ids,
            rows=effective_rows,
            columns=columns,
            panel_titles=titles,
            title=title.strip(),
            width=width,
            height=height,
            shared_xaxes=shared_xaxes,
            shared_yaxes=shared_yaxes,
            shared_legend=shared_legend,
            x_title=x_title.strip(),
            y_title=y_title.strip(),
        )

    def create_small_multiples(
        self,
        plot_id: int,
        facet_columns: Sequence[str],
        *,
        columns: int = 3,
        order: Sequence[Any] | None = None,
        labels: Mapping[Any, str] | None = None,
        title: str | None = None,
        width: int = 1200,
        panel_height: int = 320,
        shared_xaxes: bool = True,
        shared_yaxes: bool = True,
        shared_legend: bool = True,
        x_title: str = "",
        y_title: str = "",
    ) -> SmallMultiplesSpec:
        # [impl->req~ring5.plots.small-multiples~1]
        """Resolve categorical facet panels for one registered plot."""
        available = {plot.plot_id: plot for plot in self.state_manager.get_plots()}
        plot = available.get(plot_id)
        if plot is None:
            raise ValueError(f"Small multiples references unknown plot ID: {plot_id}.")
        if plot.processed_data is None:
            raise ValueError(f"Plot '{plot.name}' has no processed data.")
        effective_title = str(plot.config.get("title", plot.name)) if title is None else title
        return build_small_multiples_spec(
            plot_id,
            plot.processed_data,
            facet_columns,
            columns=columns,
            order=order,
            labels=labels,
            title=effective_title,
            width=width,
            panel_height=panel_height,
            shared_xaxes=shared_xaxes,
            shared_yaxes=shared_yaxes,
            shared_legend=shared_legend,
            x_title=x_title,
            y_title=y_title,
        )

    def create_linked_selection(
        self,
        plot_ids: Sequence[int],
        *,
        axis: Literal["x", "y"] = "x",
        mode: Literal["highlight", "filter"] = "highlight",
    ) -> LinkedSelectionSpec:
        # [impl->req~ring5.plots.linked-selections~1]
        """Create a validated, non-mutating selection link for registered plots."""
        ids = tuple(plot_ids)
        available = {plot.plot_id for plot in self.state_manager.get_plots()}
        missing = [plot_id for plot_id in ids if plot_id not in available]
        if missing:
            raise ValueError(
                "Linked selection references unknown plot IDs: "
                + ", ".join(map(str, missing))
                + "."
            )
        return LinkedSelectionSpec(plot_ids=ids, axis=axis, mode=mode)

    def copy_plot_content(
        self,
        source_plot_id: int,
        target_plot_id: int,
        mode: PlotTransferMode,
        *,
        sections: Sequence[str] = (),
    ) -> PlotTransferResult:
        # [impl->req~ring5.plots.copy-settings-pipeline~1]
        """Copy validated configuration or pipeline content between live plots."""
        available = {plot.plot_id: plot for plot in self.state_manager.get_plots()}
        missing = [value for value in (source_plot_id, target_plot_id) if value not in available]
        if missing:
            raise ValueError(
                "Copy references unknown plot IDs: " + ", ".join(map(str, missing)) + "."
            )
        return copy_plot_content(
            available[source_plot_id],
            available[target_plot_id],
            mode,
            sections=sections,
        )

    def drill_down_plot(
        self,
        plot_id: int,
        filters: Mapping[str, Any],
    ) -> DrillDownResult:
        # [impl->req~ring5.plots.drill-down~1]
        """Resolve the private source rows represented by one registered plot point."""
        if isinstance(plot_id, bool) or not isinstance(plot_id, int):
            raise ValueError("Drill-down plot ID must be an integer.")
        plot = next(
            (
                candidate
                for candidate in self.state_manager.get_plots()
                if candidate.plot_id == plot_id
            ),
            None,
        )
        if plot is None:
            raise ValueError(f"Drill-down references unknown plot ID: {plot_id}.")
        source_data = plot.source_data if plot.source_data is not None else plot.processed_data
        if source_data is None:
            raise ValueError(f"Plot {plot_id} has no source data to inspect.")
        return drill_down_rows(plot_id, source_data, filters)

    # Previews (Delegated to StateManager)

    def set_preview(self, operation_name: str, data: pd.DataFrame) -> None:
        """Store a preview DataFrame for an operation."""
        # [impl->req~ring5.extension.data-manager~1]
        self.state_manager.set_preview(operation_name, data)

    def get_preview(self, operation_name: str) -> pd.DataFrame | None:
        """Retrieve a preview DataFrame for an operation."""
        return self.state_manager.get_preview(operation_name)

    def has_preview(self, operation_name: str) -> bool:
        """Check if a preview exists for an operation."""
        return self.state_manager.has_preview(operation_name)

    def clear_preview(self, operation_name: str) -> None:
        """Clear a preview for an operation."""
        self.state_manager.clear_preview(operation_name)

    # History (Delegated to StateManager)

    def add_manager_history_record(self, record: OperationRecord) -> None:
        """Record a manager operation in both manager and portfolio history."""
        self.state_manager.add_manager_history_record(record)
        self.state_manager.add_portfolio_history_record(record)

    def get_manager_history(self) -> list[OperationRecord]:
        """Get the rolling manager operation history (last 10)."""
        return self.state_manager.get_manager_history()

    def get_portfolio_history(self) -> list[OperationRecord]:
        """Get the full portfolio operation history."""
        return self.state_manager.get_portfolio_history()

    def remove_manager_history_record(self, record: OperationRecord) -> None:
        """Remove a specific record from both manager and portfolio history."""
        self.state_manager.remove_manager_history_record(record)
        self.state_manager.remove_portfolio_history_record(record)

    # Simulator Registry Facades (so web layer avoids parsing imports)

    @staticmethod
    def available_simulators() -> list[str]:
        """Return the list of registered simulator names."""
        return SimulatorRegistry.available_simulators()

    @staticmethod
    def available_simulator_info() -> list[SimulatorInfo]:
        """Return metadata for all registered simulators."""
        return SimulatorRegistry.available_simulator_info()

    @staticmethod
    def get_simulator_info(name: str) -> SimulatorInfo:
        """Return metadata for a specific simulator."""
        return SimulatorRegistry.get_info(name)

    def release_settled_scans(self) -> None:
        """Drop references to *completed* scan futures to free memory.

        This is memory cleanup only: it never cancels a running future. Use it
        after consuming scan results; use
        :meth:`cancel_pending_scans` only for an explicit user-initiated abort.
        """
        self._pending_scan_futures = [f for f in self._pending_scan_futures if not f.done()]

    def cancel_pending_scans(self) -> None:
        """Cancel scan futures submitted through this facade.

        Cancellation is handle-based and instance-scoped: only futures
        returned by this instance's ``submit_scan_async`` are affected. Use
        :meth:`release_settled_scans` for routine cleanup because it never
        cancels live work.
        """
        for future in self._pending_scan_futures:
            future.cancel()
        self._pending_scan_futures.clear()
