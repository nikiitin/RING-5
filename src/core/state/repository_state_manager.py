"""Repository-backed implementation of the application state contract."""

from __future__ import annotations

import logging
import threading
from contextlib import ExitStack, contextmanager
from functools import wraps
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Concatenate, ParamSpec, TypeVar

from src.core.common.plot_render_state import PlotRenderBinding
from src.core.models.preview_models import PreviewContext

import pandas as pd

from src.core.models.dataset_workspace_models import (
    DatasetInfo,
    DatasetInputIdentity,
    DatasetLineage,
    DatasetRevision,
)
from src.core.models.plot_protocol import PlotProtocol
from src.core.models.portfolio_models import PortfolioData, RestoreReport
from src.core.models.data_models import (
    CsvPoolEntry,
    ParseVariableConfig,
    SavedConfigEntry,
    ScannedVariableDict,
)
from src.core.models.history_models import OperationRecord
from src.core.models.plot_protocol import PlotDeserializer
from src.core.models.visualization.figure_config import FigureConfig
from src.core.state.repositories.plot_repository import PlotRetirement
from src.core.state.repositories.session_repository import SessionRepository

logger: logging.Logger = logging.getLogger(__name__)


_P = ParamSpec("_P")
_R = TypeVar("_R")


def _state_write(
    method: Callable[Concatenate[RepositoryStateManager, _P], _R],
) -> Callable[Concatenate[RepositoryStateManager, _P], _R]:
    """Serialize state publication, without locking numerical work in services."""

    @wraps(method)
    def guarded(self: RepositoryStateManager, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        with self.transaction():
            try:
                return method(self, *args, **kwargs)
            finally:
                self._workspace_version += 1

    return guarded


def _selection_revision(state: RepositoryStateManager) -> tuple[str | None, str | None]:
    selected = state.selected_dataset_name()
    revision = state.get_dataset_lineage(selected).current_revision_id if selected else None
    return selected, revision


def _source_write(
    method: Callable[Concatenate[RepositoryStateManager, _P], _R],
) -> Callable[Concatenate[RepositoryStateManager, _P], _R]:
    """Publish a source change and advance its monotonic preview guard."""
    named_operations = {
        "add_dataset",
        "select_dataset",
        "remove_dataset",
        "undo_dataset",
        "redo_dataset",
        "restore_dataset_revision",
    }

    @wraps(method)
    def guarded(self: RepositoryStateManager, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        with self.transaction():
            selection = _selection_revision(self) if method.__name__ in named_operations else None
            csv_path = self.get_csv_path() if method.__name__ == "set_csv_path" else None
            try:
                return method(self, *args, **kwargs)
            finally:
                self._workspace_version += 1
                # A failed operation may already have published part of its state.
                # Old previews must not retain authority after that publication.
                unchanged_selection = selection is not None and selection == _selection_revision(
                    self
                )
                unchanged_path = (
                    method.__name__ == "set_csv_path" and csv_path == self.get_csv_path()
                )
                if not unchanged_selection and not unchanged_path:
                    self._source_version += 1

    return guarded


@contextmanager
def _retire_plot_binding(binding: PlotRenderBinding[Any]) -> Iterator[None]:
    """Retire one binding with the preceding body/cleanup exception still active."""
    try:
        yield
    finally:
        binding.dispose()


class RepositoryStateManager:
    """Delegate application state operations to a session repository."""

    def __init__(self, plot_deserializer: PlotDeserializer | None = None) -> None:
        """Initialize the repository layer.

        Args:
            plot_deserializer: Optional callable that converts a dict into
                a ``PlotProtocol`` instance.  Forwarded to SessionRepository
                so portfolio restoration never imports web-layer classes.
        """
        # [impl->req~ring5.workspace.session-isolation~1]
        self._transaction_lock = threading.RLock()
        self._transaction_context = threading.local()
        self._source_version = 0
        self._workspace_version = 0
        self._plot_deserializer = plot_deserializer
        self._session_repo = SessionRepository(plot_deserializer=plot_deserializer)

    @contextmanager
    def transaction(self) -> Iterator[None]:
        """Publish atomically, then retire removed bindings after the outer lock exits.

        Cleanup failures propagate after committed state; remaining callbacks still run.
        """
        with ExitStack() as cleanup:
            retired: list[PlotRenderBinding[Any]] = []
            try:
                with self._transaction_lock:
                    depth = getattr(self._transaction_context, "depth", 0)
                    if depth == 0:
                        self._transaction_context.retirements = []
                    self._transaction_context.depth = depth + 1
                    try:
                        yield
                    finally:
                        self._transaction_context.depth = depth
                        if depth == 0:
                            pending = self._transaction_context.retirements
                            self._transaction_context.retirements = []
                            live = {id(plot) for plot in self.get_plots()}
                            seen: set[int] = set()
                            for retirement in pending:
                                if id(retirement.plot) in live or id(retirement.binding) in seen:
                                    continue
                                seen.add(id(retirement.binding))
                                binding = retirement.detach()
                                if binding is not None:
                                    retired.append(binding)
            finally:
                # Register only after both ownership locks exit. The outer stack
                # receives body failures and preserves them in the cleanup chain.
                for binding in reversed(retired):
                    cleanup.enter_context(_retire_plot_binding(binding))

    def _queue_retirements(self, retirements: tuple[PlotRetirement, ...]) -> None:
        """Record exact bindings for the surrounding publication transaction."""
        self._transaction_context.retirements.extend(retirements)

    def get_source_version(self) -> int:
        """Return the version advanced by source publication or selection."""
        with self._transaction_lock:
            return self._source_version

    @_state_write
    def initialize(self) -> None:
        """Re-initialize the session to clean defaults.

        Useful for resetting state without constructing a new instance.
        """
        clears_source = not self._session_repo.data_repo.has_data()
        try:
            self._session_repo.initialize_session()
        finally:
            if clears_source:
                self._source_version += 1

    # ==================== Data Management ====================

    def get_data(self) -> pd.DataFrame | None:
        """Return the current source data."""
        return self._session_repo.data_repo.get_data()

    def set_data(
        self,
        data: pd.DataFrame | None,
        on_change: Callable[[], None] | None = None,
        *,
        operation: str = "Update dataset",
        source_datasets: tuple[str, ...] = (),
    ) -> None:
        """Store source data, then invoke a callback after releasing the publication lock.

        Raises:
            ValueError: A callback is supplied inside an explicit state transaction.
        """
        transaction_depth: int = getattr(self._transaction_context, "depth", 0)
        if on_change is not None and transaction_depth > 0:
            raise ValueError(
                "State-change callbacks must run after the surrounding transaction exits."
            )
        # Copy + enforce configuration-column dtypes via the shared ingestion
        # helper, so fresh loads and portfolio restores agree on dtypes.
        if data is not None:
            data = self._session_repo.enforce_config_dtypes(data)

        with self._transaction_lock:
            try:
                self._session_repo.data_repo.set_data(
                    data,
                    operation=operation,
                    source_datasets=source_datasets,
                )
            finally:
                self._source_version += 1
                self._workspace_version += 1
        # Foreign callbacks may wait on work that publishes more session state.
        # Run them only after the source version is committed and the lock released.
        if on_change is not None:
            on_change()

    def get_processed_data(self) -> pd.DataFrame | None:
        """Return the current processed data."""
        return self._session_repo.data_repo.get_processed_data()

    @_state_write
    def set_processed_data(self, data: pd.DataFrame | None) -> None:
        """Store processed data."""
        self._session_repo.data_repo.set_processed_data(data)

    def has_data(self) -> bool:
        """Whether source data is available."""
        return self._session_repo.data_repo.has_data()

    @_source_write
    def clear_data(self) -> None:
        """Clear data, plots, and temporary files owned by the session."""
        # [impl->req~ring5.workspace.reset~1]
        temp_dir = self._session_repo.config_repo.get_temp_dir()
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.warning(f"STATE: Cleanup failed for {temp_dir}: {e}")

        self._session_repo.data_repo.clear_data()
        self._session_repo.config_repo.set_csv_path("")
        self._session_repo.config_repo.set_temp_dir("")
        self._queue_retirements(self._session_repo.plot_repo.clear_plots())
        self._session_repo.plot_repo.set_plot_counter(0)
        self._session_repo.plot_repo.set_current_plot_id(None)

    @_source_write
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
        """Retain a named dataset after applying shared dtype rules."""
        normalized = self._session_repo.enforce_config_dtypes(data)
        return self._session_repo.data_repo.add_dataset(
            name,
            normalized,
            select=select,
            replace=replace,
            operation=operation,
            source_datasets=source_datasets,
        )

    def list_datasets(self) -> tuple[DatasetInfo, ...]:
        """Return retained dataset metadata in insertion order."""
        return self._session_repo.data_repo.list_datasets()

    def get_dataset(self, name: str | None = None) -> pd.DataFrame:
        """Return a defensive copy of a named or selected dataset."""
        return self._session_repo.data_repo.get_dataset(name)

    @_source_write
    def select_dataset(self, name: str) -> pd.DataFrame:
        """Select a retained dataset as the active source data."""
        return self._session_repo.data_repo.select_dataset(name)

    @_source_write
    def remove_dataset(self, name: str) -> None:
        """Remove one retained dataset without changing unrelated data."""
        self._session_repo.data_repo.remove_dataset(name)

    def selected_dataset_name(self) -> str | None:
        """Return the selected retained dataset name."""
        return self._session_repo.data_repo.selected_dataset_name()

    def get_dataset_input_identity(self, name: str | None = None) -> DatasetInputIdentity:
        """Return the current input identity without copying revision history."""
        return self._session_repo.data_repo.get_dataset_input_identity(name)

    def get_dataset_lineage(self, name: str | None = None) -> DatasetLineage:
        """Return revision metadata and recovery capabilities for a dataset."""
        return self._session_repo.data_repo.get_dataset_lineage(name)

    def get_dataset_revision(self, revision_id: str) -> pd.DataFrame:
        """Return a defensive copy of a retained revision snapshot."""
        return self._session_repo.data_repo.get_dataset_revision(revision_id)

    @_source_write
    def undo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Restore the preceding revision of a named dataset."""
        return self._session_repo.data_repo.undo_dataset(name)

    @_source_write
    def redo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Reapply the most recently undone dataset revision."""
        return self._session_repo.data_repo.redo_dataset(name)

    @_source_write
    def restore_dataset_revision(self, revision_id: str) -> DatasetRevision:
        """Restore an arbitrary retained dataset revision."""
        return self._session_repo.data_repo.restore_dataset_revision(revision_id)

    # ==================== Config & Parser ====================

    def get_config(self) -> dict[str, Any]:
        """Return the application configuration."""
        return self._session_repo.config_repo.get_config()

    @_state_write
    def set_config(self, config: dict[str, Any]) -> None:
        """Replace the application configuration."""
        self._session_repo.config_repo.set_config(config)

    @_state_write
    def update_config(self, key: str, value: object) -> None:
        """Set one application configuration value."""
        self._session_repo.config_repo.update_config(key, value)

    def get_temp_dir(self) -> str | None:
        """Return the active temporary directory."""
        return self._session_repo.config_repo.get_temp_dir()

    @_state_write
    def set_temp_dir(self, path: str) -> None:
        """Set the active temporary directory."""
        self._session_repo.config_repo.set_temp_dir(path)

    def get_csv_path(self) -> str | None:
        """Return the active CSV path."""
        return self._session_repo.config_repo.get_csv_path()

    @_source_write
    def set_csv_path(self, path: str) -> None:
        """Set the active CSV path."""
        self._session_repo.config_repo.set_csv_path(path)

    def get_csv_pool(self) -> list[CsvPoolEntry]:
        """Return saved CSV-pool entries."""
        return self._session_repo.config_repo.get_csv_pool()

    @_state_write
    def set_csv_pool(self, pool: list[CsvPoolEntry]) -> None:
        """Replace saved CSV-pool entries."""
        self._session_repo.config_repo.set_csv_pool(pool)

    def get_saved_configs(self) -> list[SavedConfigEntry]:
        """Return saved application configurations."""
        return self._session_repo.config_repo.get_saved_configs()

    @_state_write
    def set_saved_configs(self, configs: list[SavedConfigEntry]) -> None:
        """Replace saved application configurations."""
        self._session_repo.config_repo.set_saved_configs(configs)

    def is_using_parser(self) -> bool:
        """Whether the parser is the active data source."""
        return self._session_repo.parser_repo.is_using_parser()

    @_state_write
    def set_use_parser(self, use: bool) -> None:
        """Select whether the parser is the active data source."""
        self._session_repo.parser_repo.set_using_parser(use)

    def get_parse_variables(self) -> list[ParseVariableConfig]:
        """Return variables selected for parsing."""
        return self._session_repo.parser_repo.get_parse_variables()

    @_state_write
    def set_parse_variables(self, variables: list[ParseVariableConfig]) -> None:
        """Replace variables selected for parsing."""
        self._session_repo.parser_repo.set_parse_variables(variables)

    def get_stats_path(self) -> str:
        """Return the simulator-statistics search path."""
        return self._session_repo.parser_repo.get_stats_path()

    @_state_write
    def set_stats_path(self, path: str) -> None:
        """Set the simulator-statistics search path."""
        self._session_repo.parser_repo.set_stats_path(path)

    def get_stats_pattern(self) -> str:
        """Return the statistics filename pattern."""
        return self._session_repo.parser_repo.get_stats_pattern()

    @_state_write
    def set_stats_pattern(self, pattern: str) -> None:
        """Set the statistics filename pattern."""
        self._session_repo.parser_repo.set_stats_pattern(pattern)

    def get_scanned_variables(self) -> list[ScannedVariableDict]:
        """Return variables found by the latest scan."""
        return self._session_repo.parser_repo.get_scanned_variables()

    @_state_write
    def set_scanned_variables(self, variables: list[ScannedVariableDict]) -> None:
        """Replace variables found by the latest scan."""
        self._session_repo.parser_repo.set_scanned_variables(variables)

    def get_parser_strategy(self) -> str:
        """Return the selected parser strategy."""
        return self._session_repo.parser_repo.get_parser_strategy()

    @_state_write
    def set_parser_strategy(self, strategy: str) -> None:
        """Set the parser strategy."""
        self._session_repo.parser_repo.set_parser_strategy(strategy)

    def get_simulator(self) -> str:
        """Return the selected simulator backend."""
        return self._session_repo.parser_repo.get_simulator()

    @_state_write
    def set_simulator(self, simulator: str) -> None:
        """Set the simulator backend."""
        self._session_repo.parser_repo.set_simulator(simulator)

    # ==================== Plots ====================

    def get_plots(self) -> list[PlotProtocol]:
        """Return registered plots."""
        return self._session_repo.plot_repo.get_plots()

    @_state_write
    def set_plots(self, plots: list[PlotProtocol]) -> None:
        """Replace registered plots."""
        self._queue_retirements(self._session_repo.plot_repo.set_plots(plots))

    @_state_write
    def add_plot(self, plot_obj: PlotProtocol) -> None:
        """Register a plot."""
        self._session_repo.plot_repo.add_plot(plot_obj)

    def get_plot_counter(self) -> int:
        """Return the latest allocated plot identifier."""
        return self._session_repo.plot_repo.get_plot_counter()

    @_state_write
    def set_plot_counter(self, counter: int) -> None:
        """Set the latest allocated plot identifier."""
        self._session_repo.plot_repo.set_plot_counter(counter)

    @_state_write
    def start_next_plot_id(self) -> int:
        """Allocate and return the next plot identifier."""
        return self._session_repo.plot_repo.increment_plot_counter()

    def get_current_plot_id(self) -> int | None:
        """Return the selected plot identifier."""
        return self._session_repo.plot_repo.get_current_plot_id()

    @_state_write
    def set_current_plot_id(self, plot_id: int | None) -> None:
        """Set the selected plot identifier."""
        self._session_repo.plot_repo.set_current_plot_id(plot_id)

    # ==================== Visualization ====================

    def get_visualization_config(self, plot_id: int) -> FigureConfig | None:
        """Return the figure configuration for a plot."""
        return self._session_repo.visualization_repo.get_config(plot_id)

    @_state_write
    def set_visualization_config(self, plot_id: int, config: FigureConfig) -> None:
        """Store the figure configuration for a plot."""
        self._session_repo.visualization_repo.set_config(plot_id, config)

    @_state_write
    def remove_visualization_config(self, plot_id: int) -> None:
        """Remove the figure configuration for a plot."""
        self._session_repo.visualization_repo.remove_config(plot_id)

    # ==================== Previews ====================

    @_state_write
    def set_preview(
        self, operation_name: str, data: pd.DataFrame, *, context: PreviewContext
    ) -> None:
        """Store preview data for an operation."""
        self._session_repo.preview_repo.set_preview(operation_name, data, context=context)

    def get_preview_context(self, operation_name: str) -> PreviewContext | None:
        """Return a defensive copy of a preview's retained source and options."""
        return self._session_repo.preview_repo.get_preview_context(operation_name)

    def get_preview(self, operation_name: str) -> pd.DataFrame | None:
        """Return preview data for an operation."""
        return self._session_repo.preview_repo.get_preview(operation_name)

    def has_preview(self, operation_name: str) -> bool:
        """Whether preview data exists for an operation."""
        return self._session_repo.preview_repo.has_preview(operation_name)

    @_state_write
    def clear_preview(self, operation_name: str) -> None:
        """Remove preview data for an operation."""
        self._session_repo.preview_repo.clear_preview(operation_name)

    # ==================== History ====================

    @_state_write
    def add_manager_history_record(self, record: OperationRecord) -> None:
        """Append a data-manager history record."""
        self._session_repo.history_repo.add_manager_record(record)

    def get_manager_history(self) -> list[OperationRecord]:
        """Return data-manager history records."""
        return self._session_repo.history_repo.get_manager_history()

    @_state_write
    def add_portfolio_history_record(self, record: OperationRecord) -> None:
        """Append a portfolio history record."""
        self._session_repo.history_repo.add_portfolio_record(record)

    def get_portfolio_history(self) -> list[OperationRecord]:
        """Return portfolio history records."""
        return self._session_repo.history_repo.get_portfolio_history()

    @_state_write
    def remove_manager_history_record(self, record: OperationRecord) -> None:
        """Remove a data-manager history record."""
        self._session_repo.history_repo.remove_manager_record(record)

    @_state_write
    def remove_portfolio_history_record(self, record: OperationRecord) -> None:
        """Remove a portfolio history record."""
        self._session_repo.history_repo.remove_portfolio_record(record)

    # ==================== Session ======================================

    @_source_write
    def clear_all(self) -> None:
        """Reset all session repositories."""
        self._queue_retirements(self._session_repo.clear_all())

    def restore_session(self, portfolio_data: PortfolioData) -> RestoreReport:
        # [impl->req~ring5.portfolio.restore~1]
        """Prepare a replacement workspace, then publish it atomically.

        Typed table decoding and injected deserializers run outside the state lock.
        Preparation exceptions retain the current repositories. Reported per-item
        failures remain best-effort, and successful publication replaces other
        workspace settings. A concurrent state-manager write aborts replacement.

        Args:
            portfolio_data: Verified portfolio snapshot to restore.

        Returns:
            Report describing data and plots restored or skipped.

        Raises:
            ValueError: Called inside a transaction, preparation input is invalid,
                or the workspace changes while the replacement is prepared.
        """
        transaction_depth: int = getattr(self._transaction_context, "depth", 0)
        if transaction_depth > 0:
            raise ValueError("Prepare portfolio restores outside a surrounding state transaction.")
        with self._transaction_lock:
            expected_version = self._workspace_version
            factory = self._plot_deserializer
        admitted: list[PlotRetirement] = []

        def deserialize(payload: dict[str, Any]) -> PlotProtocol | None:
            if factory is None:
                return None
            plot = factory(payload)
            if plot is not None:
                admitted.append(PlotRetirement.capture(plot))
            return plot

        candidate = SessionRepository(
            plot_deserializer=deserialize if factory is not None else None
        )
        published = False
        try:
            report = candidate.restore_from_portfolio(portfolio_data)
            with self.transaction():
                if self._workspace_version != expected_version:
                    raise ValueError(
                        "Workspace changed while restoring; review and retry the restore."
                    )
                self._queue_retirements(
                    self._session_repo.plot_repo.removed_bindings(candidate.plot_repo.get_plots())
                )
                self._session_repo = candidate
                self._source_version += 1
                self._workspace_version += 1
                published = True
            return report
        finally:
            if not published:
                with self.transaction():
                    self._queue_retirements(tuple(admitted))
