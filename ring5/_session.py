"""Headless workspace for parsing, shaping, plotting, and portfolio replay."""

from __future__ import annotations

import copy
import shutil
import tempfile
import threading
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Literal, cast

import pandas as pd

from src.core.application_api import ApplicationAPI
from src.core.models import (
    DataQualityReport,
    DashboardSpec,
    DrillDownResult,
    DatasetInfo,
    DatasetLineage,
    DatasetRevision,
    DatasetSnapshotInfo,
    DatasetSchemaContract,
    JoinCardinality,
    JoinDiagnostics,
    LinkedSelectionSpec,
    PlotConfigurationComparison,
    PlotTransferMode,
    PlotTransferResult,
    SmallMultiplesSpec,
    RestoreReport,
    ScanResult,
    SchemaValidationReport,
    StatConfig,
)
from src.core.models.data_models import ParseVariableConfig
from src.core.models.shaper_models import ShaperStepConfig
from src.core.models.visualization.engine import EngineMode
from src.parsing.parser_protocol import SimulationParser
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory

from ring5 import _dashboard, _export, _parse, _render, _scan, _small_multiples
from ring5.errors import (
    ColumnNotFoundError,
    DataLoadError,
    DataValidationError,
    ParseError,
    PipelineError,
    PortfolioError,
    ScanError,
)
from ring5.figure_spec import FigureSpec
from ring5._plot_validation import validate_plot_config

PlotType = Literal[
    "bar",
    "box",
    "dual_axis_bar_dot",
    "ecdf",
    "grouped_bar",
    "grouped_stacked_bar",
    "heatmap",
    "histogram",
    "line",
    "scatter",
    "stacked_bar",
    "violin",
]

if TYPE_CHECKING:
    from ring5.data import Table


def _unwrap_table(data: "pd.DataFrame | Table") -> tuple[pd.DataFrame, bool]:
    """Return ``(DataFrame, was_table)`` — accept a ``ring5.Table`` or a raw frame.

    Lazy import of ``Table`` keeps ``ring5.data`` (pandas-heavy) off the import path until a
    Table is actually used, and avoids any import cycle.
    """
    from ring5.data import Table as _Table

    if isinstance(data, _Table):
        return data.frame, True
    return data, False


def _rewrap_table(frame: pd.DataFrame) -> "Table":
    """Wrap a DataFrame back into a ``ring5.Table`` (mirror of :func:`_unwrap_table`)."""
    from ring5.data import Table as _Table

    return _Table(frame)


def _remove_directory_when_settled(path: str, futures: list[Any]) -> None:
    """Remove *path* now, or after every still-running future settles."""
    pending = {id(future) for future in futures if not future.done()}
    if not pending:
        shutil.rmtree(path, ignore_errors=True)
        return

    lock = threading.Lock()

    def settled(future: Any) -> None:
        should_remove = False
        with lock:
            pending.discard(id(future))
            should_remove = not pending
        if should_remove:
            shutil.rmtree(path, ignore_errors=True)

    for future in futures:
        if id(future) in pending:
            future.add_done_callback(settled)


def available_plot_types() -> tuple[str, ...]:
    # [impl->req~ring5.api.registry-discovery~1]
    """Return the registered plot-type identifiers accepted by :class:`Session`.

    Returns:
        Plot types in their stable display order.
    """
    from src.web.pages.ui.plotting.plot_factory import PlotFactory

    return tuple(PlotFactory.get_available_plot_types())


def _resolve_plot_type(plot_type: str) -> str:
    """Normalize a plot identifier or display name and validate it."""
    from src.web.pages.ui.plotting.plot_factory import PlotFactory

    normalized = plot_type.strip().lower().replace("-", "_").replace(" ", "_")
    available = PlotFactory.get_available_plot_types()
    if normalized in available:
        return normalized

    for identifier, metadata in PlotFactory.get_plot_metadata().items():
        display_name = metadata["display_name"].lower().replace("-", "_").replace(" ", "_")
        if normalized == display_name:
            return identifier

    choices = ", ".join(available)
    raise DataValidationError(f"Unknown plot type {plot_type!r}. Available types: {choices}.")


class Session:
    # [impl->req~ring5.api.session~1]
    """A headless RING-5 workspace.

    Mirrors what one browser session of the web app can do — parse, shape,
    plot, render, export, snapshot — as plain method calls::

        with ring5.Session() as s:
            csv = s.parse("/sims", variables=["simTicks"]).csv_path
            df = s.load(csv)
            df = s.reduce_seeds(df, ["config_description_abbrev"], ["simTicks"])
            fig = s.plot("Bar Chart", data=df,
                         config={"x": "config_description_abbrev",
                                 "y": "simTicks"},
                         engine="matplotlib")
            s.export(fig, "out/simticks.pdf")

    The full :class:`ApplicationAPI` remains available as ``session.api``
    (history, previews, CSV pool, saved configs, …).
    """

    def __init__(self, *, parser: SimulationParser | None = None) -> None:
        # Headless portfolio restores need the web composition root's plot deserializer.
        self.api = ApplicationAPI(plot_deserializer=PlotFactory.from_dict, parser=parser)
        # Temporary parse output is removed when the session closes.
        self._owned_tmpdirs: list[str] = []
        self._parse_jobs: list[_parse.ParseJob] = []

    # lifecycle
    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        # [impl->req~ring5.api.session~1]
        # [impl->req~ring5.quality.async-ownership~1]
        """Release this session's pending work (process pools stay up)."""
        self.api.cancel_pending_scans()
        for job in self._parse_jobs:
            job.cancel()
        for tmp in self._owned_tmpdirs:
            jobs = [job for job in self._parse_jobs if job.output_dir == tmp]
            futures = [future for job in jobs for future in job.futures]
            _remove_directory_when_settled(tmp, futures)
        self._owned_tmpdirs.clear()
        self._parse_jobs.clear()

    # scan
    def scan_submit(
        self,
        stats_path: str,
        *,
        pattern: str = "stats.txt",
        limit: int = 10,
    ) -> _scan.ScanJob:
        """Submit variable discovery and return a handle-based scan job.

        Args:
            stats_path: Root directory containing simulator statistics.
            pattern: Statistics filename pattern.
            limit: Maximum files to scan; zero scans all matching files up to
                the global discovery ceiling.

        Returns:
            A submitted scan job that can be finalized or cancelled.

        Raises:
            ScanError: Discovery could not be submitted.
        """
        # [impl->req~ring5.ingestion.async-scan~1]
        try:
            futures = self.api.submit_scan_async(stats_path, pattern, limit=limit)
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            raise ScanError(str(exc)) from exc
        return _scan.ScanJob(self.api, list(futures), stats_path, pattern)

    def scan(
        self,
        stats_path: str,
        *,
        pattern: str = "stats.txt",
        limit: int = 10,
        strict: bool = True,
    ) -> ScanResult:
        """Discover variables in a statistics tree and wait for completion.

        Args:
            stats_path: Root directory containing simulator statistics.
            pattern: Statistics filename pattern.
            limit: Maximum files to scan; zero scans all matching files up to
                the global discovery ceiling.
            strict: Raise if any selected file fails to scan. When false,
                return the partial result with its ``failures`` list.

        Returns:
            Aggregated immutable scan metadata.

        Raises:
            ScanError: Discovery failed, timed out, or was incomplete in
                strict mode.
        """
        # [impl->req~ring5.ingestion.scan-limits~1]
        return self.scan_submit(stats_path, pattern=pattern, limit=limit).finalize(strict=strict)

    # parse
    def parse_submit(
        self,
        stats_path: str,
        variables: list[str | StatConfig],
        *,
        pattern: str = "stats.txt",
        strategy: str = "simple",
        output_dir: str | None = None,
        scan_limit: int = 10,
    ) -> _parse.ParseJob:
        """Scan the tree, resolve *variables*, and submit an async parse.

        Plain string names are resolved against a scan of ``scan_limit``
        files (``0`` = all files up to the global 10,000-file discovery
        ceiling — use it when stats differ across runs),
        which supplies each variable's type and metadata; pass
        :class:`StatConfig` objects for regex patterns. The returned
        :class:`ParseJob` owns its futures — ``job.finalize()`` needs no
        re-supplied arguments and ``job.cancel()`` touches nothing but
        this job.

        Args:
            stats_path: Root directory containing simulator statistics.
            variables: Statistic names or explicit statistic configurations.
            pattern: Statistics filename pattern.
            strategy: Registered parser strategy.
            output_dir: Directory for parser output. A temporary directory is used
                when omitted and is removed when the session closes.
            scan_limit: Maximum files to scan; zero scans every matching file
                up to the global discovery ceiling.

        Returns:
            A submitted parse job that can be finalized or cancelled.

        Raises:
            ScanError: No matching statistics files were found or variable
                discovery failed.
            ParseError: The parser rejected the submission.
        """
        # [impl->req~ring5.ingestion.async-parse~1]
        # [impl->req~ring5.ingestion.parse-output-provenance~1]
        configs, scanned = _parse.build_stat_configs(
            self.api, stats_path, variables, pattern=pattern, scan_limit=scan_limit
        )
        if output_dir is None:
            out_dir = tempfile.mkdtemp(prefix="ring5_parse_")
            self._owned_tmpdirs.append(out_dir)
        else:
            out_dir = output_dir
        try:
            batch = self.api.submit_parse_async(
                stats_path,
                pattern,
                cast(list[ParseVariableConfig | StatConfig], list(configs)),
                out_dir,
                strategy_type=strategy,
                scanned_vars=scanned,
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            if output_dir is None:
                shutil.rmtree(out_dir, ignore_errors=True)
                self._owned_tmpdirs.remove(out_dir)
            raise ParseError(f"Parse submission failed: {exc}") from exc

        # Store parse provenance for portfolio restoration and replay.
        sm = self.api.state_manager
        sm.set_stats_path(stats_path)
        sm.set_stats_pattern(pattern)
        sm.set_parse_variables(
            cast(
                list[ParseVariableConfig],
                [
                    dict(c) if isinstance(c, dict) else {"name": c.name, "type": c.type}
                    for c in configs
                ],
            )
        )
        sm.set_scanned_variables([v.to_dict() if hasattr(v, "to_dict") else v for v in scanned])
        job = _parse.ParseJob(
            api=self.api,
            futures=list(batch.futures),
            var_names=list(batch.var_names),
            output_dir=out_dir,
            strategy=strategy,
            stats_path=stats_path,
            stats_pattern=pattern,
        )
        self._parse_jobs.append(job)
        return job

    def parse(
        self,
        stats_path: str,
        variables: list[str | StatConfig],
        *,
        pattern: str = "stats.txt",
        strategy: str = "simple",
        output_dir: str | None = None,
        scan_limit: int = 10,
        strict: bool = True,
    ) -> _parse.ParseResult:
        """Parse simulator statistics and wait for completion.

        Args:
            stats_path: Root directory containing simulator statistics.
            variables: Statistic names or explicit statistic configurations.
            pattern: Statistics filename pattern.
            strategy: Registered parser strategy.
            output_dir: Directory for parser output. A temporary directory is used
                when omitted.
            scan_limit: Maximum files to scan; zero scans every matching file
                up to the global discovery ceiling.
            strict: Raise when a requested statistic produces no values.

        Returns:
            The assembled CSV path and any missing statistic names.

        Raises:
            ScanError: Discovery failed or a requested name was not found.
            ParseError: Parsing or CSV assembly failed.
            MissingStatError: ``strict`` is true and a requested statistic
                produced no values.
        """
        job = self.parse_submit(
            stats_path,
            variables,
            pattern=pattern,
            strategy=strategy,
            output_dir=output_dir,
            scan_limit=scan_limit,
        )
        return job.finalize(strict=strict)

    # data
    def load(self, csv_path: str) -> pd.DataFrame:
        """Load a CSV into the session.

        Args:
            csv_path: CSV file to load.

        Returns:
            The loaded DataFrame.

        Raises:
            DataLoadError: The file is missing, unreadable, malformed, or
                produces no table.
        """
        # [impl->req~ring5.ingestion.csv-load~1]
        try:
            self.api.load_data(csv_path)
        except (OSError, ValueError, UnicodeError) as exc:
            raise DataLoadError(f"Could not load CSV {csv_path!r}: {exc}") from exc
        data = self.api.state_manager.get_data()
        if data is None:
            raise DataLoadError(f"Loading {csv_path!r} produced no data.")
        return data

    def add_dataset(
        self,
        name: str,
        data: "pd.DataFrame | Table",
        *,
        select: bool = True,
        replace: bool = False,
    ) -> DatasetInfo:
        """Retain a named dataset in this session without replacing others.

        Args:
            name: Human-readable session-unique name.
            data: DataFrame or :class:`ring5.Table` retained by defensive copy.
            select: Make this dataset the active source-data view.
            replace: Permit replacement of the same name.

        Returns:
            Immutable dataset metadata.

        Raises:
            DataValidationError: The name is invalid or already exists.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        frame, _ = _unwrap_table(data)
        try:
            return self.api.add_dataset(
                name,
                frame,
                select=select,
                replace=replace,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def list_datasets(self) -> tuple[DatasetInfo, ...]:
        """Return retained dataset metadata in insertion order."""
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        return self.api.list_datasets()

    def get_dataset(self, name: str | None = None) -> pd.DataFrame:
        """Return a defensive copy of a named or selected dataset.

        Args:
            name: Dataset name, or ``None`` for the selected dataset.

        Returns:
            A newly allocated DataFrame.

        Raises:
            DataValidationError: No dataset is selected or the name is unknown.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        try:
            return self.api.get_dataset(name)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def select_dataset(self, name: str) -> pd.DataFrame:
        """Select a named dataset as the active source-data view.

        Args:
            name: Retained dataset name.

        Returns:
            A defensive copy of the selected dataset.

        Raises:
            DataValidationError: The name is invalid or unknown.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        try:
            return self.api.select_dataset(name)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def remove_dataset(self, name: str) -> None:
        """Remove one named dataset while preserving every other dataset.

        Args:
            name: Retained dataset name.

        Raises:
            DataValidationError: The name is invalid or unknown.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        try:
            self.api.remove_dataset(name)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def dataset_lineage(self, name: str | None = None) -> DatasetLineage:
        """Inspect the reproducible revision lineage of a named dataset.

        Args:
            name: Dataset name, or ``None`` for the selected dataset.

        Returns:
            Immutable revision metadata, fingerprints, ancestry, and recovery state.

        Raises:
            DataValidationError: No dataset is selected or the name is unknown.
        """
        # [impl->req~ring5.data.lineage-undo-redo~1]
        try:
            return self.api.get_dataset_lineage(name)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def get_dataset_revision(self, revision_id: str) -> pd.DataFrame:
        """Return a defensive copy of one immutable dataset revision.

        Args:
            revision_id: Revision identifier from :meth:`dataset_lineage`.

        Raises:
            DataValidationError: The revision identifier is invalid or unknown.
        """
        # [impl->req~ring5.data.lineage-undo-redo~1]
        try:
            return self.api.get_dataset_revision(revision_id)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def undo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Restore the preceding state of a named dataset.

        Args:
            name: Dataset name, or ``None`` for the selected dataset.

        Returns:
            Metadata for the newly current revision.

        Raises:
            DataValidationError: The dataset is unknown or has nothing to undo.
        """
        # [impl->req~ring5.data.lineage-undo-redo~1]
        try:
            return self.api.undo_dataset(name)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def redo_dataset(self, name: str | None = None) -> DatasetRevision:
        """Reapply the most recently undone state of a named dataset.

        Args:
            name: Dataset name, or ``None`` for the selected dataset.

        Returns:
            Metadata for the newly current revision.

        Raises:
            DataValidationError: The dataset is unknown or has nothing to redo.
        """
        # [impl->req~ring5.data.lineage-undo-redo~1]
        try:
            return self.api.redo_dataset(name)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def restore_dataset_revision(self, revision_id: str) -> DatasetRevision:
        """Restore an inspected intermediate revision by ID.

        Args:
            revision_id: Revision identifier from :meth:`dataset_lineage`.

        Returns:
            Metadata for the restored revision.

        Raises:
            DataValidationError: The revision is invalid, unknown, or no longer retained.
        """
        # [impl->req~ring5.data.lineage-undo-redo~1]
        try:
            return self.api.restore_dataset_revision(revision_id)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def list_dataset_snapshots(self) -> tuple[DatasetSnapshotInfo, ...]:
        """List reusable local dataset snapshots without decoding their tables."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        return self.api.list_dataset_snapshots()

    def save_dataset_snapshot(
        self,
        name: str,
        dataset_name: str | None = None,
        *,
        overwrite: bool = False,
    ) -> DatasetSnapshotInfo:
        """Persist a fingerprinted dataset for reuse in a later session.

        Args:
            name: Local snapshot name.
            dataset_name: Named dataset to save, or the selected/active data when omitted.
            overwrite: Permit replacing an existing snapshot of the same name.

        Returns:
            Immutable metadata including dimensions and the verified content fingerprint.

        Raises:
            DataValidationError: The dataset, name, or snapshot contents are invalid.
        """
        # [impl->req~ring5.data.dataset-snapshots~1]
        try:
            return self.api.save_dataset_snapshot(
                name,
                dataset_name,
                overwrite=overwrite,
            )
        except (FileExistsError, KeyError, OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def load_dataset_snapshot(
        self,
        name: str,
        dataset_name: str | None = None,
        *,
        select: bool = True,
        replace: bool = False,
    ) -> DatasetInfo:
        """Verify and load a reusable snapshot into the named workspace.

        Args:
            name: Saved snapshot name.
            dataset_name: Output workspace name; defaults to the recorded source name.
            select: Make the restored dataset active.
            replace: Permit replacement of an existing workspace dataset.

        Raises:
            DataValidationError: The snapshot is absent, corrupt, or conflicts with the workspace.
        """
        # [impl->req~ring5.data.dataset-snapshots~1]
        try:
            return self.api.load_dataset_snapshot(
                name,
                dataset_name,
                select=select,
                replace=replace,
            )
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def delete_dataset_snapshot(self, name: str) -> None:
        """Delete one reusable local dataset snapshot.

        Args:
            name: Saved snapshot name.

        Raises:
            DataValidationError: The snapshot name is invalid or deletion fails.
        """
        try:
            self.api.delete_dataset_snapshot(name)
        except (OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def append_datasets(
        self,
        dataset_names: Sequence[str],
        output_name: str,
        *,
        join: Literal["outer", "inner"] = "outer",
        select: bool = True,
        replace: bool = False,
    ) -> pd.DataFrame:
        """Append retained datasets and retain the result under a new name.

        Args:
            dataset_names: Ordered names of at least two retained datasets.
            output_name: Name for the appended result.
            join: Keep the union or intersection of columns.
            select: Make the result the active source-data view.
            replace: Permit replacement of ``output_name``.

        Returns:
            A defensive copy of the appended result.

        Raises:
            DataValidationError: A name, dataset, or option is invalid.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        try:
            return self.api.append_datasets(
                list(dataset_names),
                output_name,
                join=join,
                select=select,
                replace=replace,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

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
        """Join retained datasets and retain the result under a new name.

        Args:
            left_name: Left-side retained dataset.
            right_name: Right-side retained dataset.
            output_name: Name for the joined result.
            on: Shared key columns.
            how: Row-retention strategy.
            suffixes: Distinct suffixes for overlapping non-key columns.
            select: Make the result the active source-data view.
            replace: Permit replacement of ``output_name``.

        Returns:
            A defensive copy of the joined result.

        Raises:
            DataValidationError: A name, dataset, key, or option is invalid.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        try:
            return self.api.join_datasets(
                left_name,
                right_name,
                output_name,
                list(on),
                how=how,
                suffixes=suffixes,
                select=select,
                replace=replace,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def diagnose_join(
        self,
        left_name: str,
        right_name: str,
        on: Sequence[str],
        *,
        cardinality: JoinCardinality,
    ) -> JoinDiagnostics:
        """Inspect duplicate keys, unmatched rows, and join cardinality.

        Args:
            left_name: Left-side retained dataset.
            right_name: Right-side retained dataset.
            on: Shared key columns.
            cardinality: Expected one-to-one, one-to-many, many-to-one, or many-to-many shape.

        Returns:
            Immutable diagnostics without modifying either dataset.

        Raises:
            DataValidationError: A dataset, key, or cardinality is invalid.
        """
        # [impl->req~ring5.data.validated-joins~1]
        try:
            return self.api.diagnose_join(
                left_name,
                right_name,
                list(on),
                cardinality=cardinality,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

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
        """Join retained datasets only when the expected cardinality holds.

        Args:
            left_name: Left-side retained dataset.
            right_name: Right-side retained dataset.
            output_name: Name for the retained result.
            on: Shared key columns.
            cardinality: Required one-to-one, one-to-many, many-to-one, or many-to-many shape.
            how: Row-retention strategy.
            suffixes: Distinct suffixes for overlapping non-key columns.
            select: Make the result the active source-data view.
            replace: Permit replacement of ``output_name``.

        Returns:
            The new table and the diagnostics used to authorize it. Source datasets remain
            unchanged and the output receives lineage ancestry.

        Raises:
            DataValidationError: Inputs are invalid or key duplication violates cardinality.
        """
        # [impl->req~ring5.data.validated-joins~1]
        try:
            return self.api.join_datasets_validated(
                left_name,
                right_name,
                output_name,
                list(on),
                cardinality=cardinality,
                how=how,
                suffixes=suffixes,
                select=select,
                replace=replace,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

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
        """Compare retained datasets without changing either source.

        Args:
            baseline_name: Reference retained dataset.
            candidate_name: Candidate retained dataset.
            key_columns: Columns that uniquely align rows.
            metric_columns: Numeric columns to compare.
            directions: Global or per-metric preferred direction.
            thresholds: Global or per-metric non-negative tolerance.
            threshold_mode: Interpret tolerances as percentages or absolute values.

        Returns:
            Long-form comparison rows.

        Raises:
            DataValidationError: A dataset, column, or option is invalid.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        try:
            return self.api.compare_datasets(
                baseline_name,
                candidate_name,
                list(key_columns),
                list(metric_columns),
                directions=directions,
                thresholds=thresholds,
                threshold_mode=threshold_mode,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def profile_data(
        self,
        data: "pd.DataFrame | Table",
        *,
        expected_types: (
            Mapping[str, Literal["numeric", "integer", "boolean", "datetime", "string"]] | None
        ) = None,
    ) -> DataQualityReport:
        """Inspect dataset completeness, consistency, outliers, and expected types.

        Args:
            data: DataFrame or :class:`ring5.Table` to inspect without mutation.
            expected_types: Optional expected type for selected columns. Supported
                values are ``numeric``, ``integer``, ``boolean``, ``datetime``,
                and ``string``.

        Returns:
            An immutable :class:`ring5.DataQualityReport`. Call ``to_frame()``
            for the ordered per-column measurements.

        Raises:
            DataValidationError: Column names or expected types are invalid.
        """
        # [impl->req~ring5.data.quality-profiler~1]
        frame, _ = _unwrap_table(data)
        try:
            return self.api.managers.profile_data(frame, expected_types=expected_types)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def infer_schema_contract(
        self,
        data: "pd.DataFrame | Table",
        *,
        name: str = "dataset",
    ) -> DatasetSchemaContract:
        """Infer an editable schema contract from current column types and nullability.

        Args:
            data: DataFrame or :class:`ring5.Table` to inspect without mutation.
            name: Human-readable contract name.

        Returns:
            An immutable contract with one :class:`ring5.ColumnContract` per column.

        Raises:
            DataValidationError: The dataset or contract name is invalid.
        """
        # [impl->req~ring5.data.schema-contracts~1]
        frame, _ = _unwrap_table(data)
        try:
            return self.api.managers.infer_schema_contract(frame, name=name)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def validate_schema(
        self,
        data: "pd.DataFrame | Table",
        contract: DatasetSchemaContract,
    ) -> SchemaValidationReport:
        """Validate a dataset against required columns and per-column rules.

        Args:
            data: DataFrame or :class:`ring5.Table` to validate without mutation.
            contract: Explicit dataset schema contract.

        Returns:
            Immutable rule failures with bounded row-position evidence.

        Raises:
            DataValidationError: The dataset or contract is invalid.
        """
        # [impl->req~ring5.data.schema-contracts~1]
        frame, _ = _unwrap_table(data)
        try:
            return self.api.managers.validate_schema(frame, contract)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def shape(
        self, data: "pd.DataFrame | Table", pipeline: list[ShaperStepConfig]
    ) -> "pd.DataFrame | Table":
        """Run a shaper pipeline; failures carry the step index and type.

        Accepts a :class:`ring5.Table` or a raw ``DataFrame`` and returns the same kind, so
        figure scripts can express ``build_data`` as a pipeline without touching pandas.

        Args:
            data: Input table or DataFrame.
            pipeline: Ordered shaper configurations.

        Returns:
            Shaped data of the same public type as ``data``.
        """
        from src.core.services.shapers.pipeline_service import PipelineStepError

        frame, was_table = _unwrap_table(data)
        try:
            shaped = self.api.apply_shapers(frame, pipeline)
        except PipelineStepError as exc:
            raise PipelineError(
                str(exc), step_index=exc.step_index, shaper_type=exc.shaper_type
            ) from exc
        except (TypeError, ValueError) as exc:
            raise PipelineError(str(exc)) from exc
        return _rewrap_table(shaped) if was_table else shaped

    def reduce_seeds(
        self,
        data: "pd.DataFrame | Table",
        categorical_cols: list[str],
        statistic_cols: list[str],
    ) -> "pd.DataFrame | Table":
        """Aggregate across random seeds (mean + ``.sd`` stdev columns).

        Accepts a :class:`ring5.Table` or a raw ``DataFrame`` and returns the same kind, so
        figure scripts can stay pandas-free.

        Args:
            data: Input table or DataFrame.
            categorical_cols: Columns defining each experiment group.
            statistic_cols: Numeric columns to aggregate.

        Returns:
            Aggregated data of the same public type as ``data``.

        Raises:
            ColumnNotFoundError: A named column is absent.
            DataValidationError: Inputs rejected (e.g. non-numeric
                statistic column, empty selections).
        """
        frame, was_table = _unwrap_table(data)
        _require_columns(frame, categorical_cols + statistic_cols)
        errors = self.api.managers.validate_seeds_reducer_inputs(
            frame, categorical_cols, statistic_cols
        )
        if errors:
            raise DataValidationError("; ".join(errors))
        try:
            reduced = self.api.managers.reduce_seeds(frame, categorical_cols, statistic_cols)
        except (ValueError, TypeError) as exc:
            raise DataValidationError(str(exc)) from exc
        return _rewrap_table(reduced) if was_table else reduced

    def compare(
        self,
        baseline: "pd.DataFrame | Table",
        candidate: "pd.DataFrame | Table",
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
    ) -> "pd.DataFrame | Table":
        """Compare aligned baseline and candidate measurements.

        The result contains one row per key and metric with baseline and
        candidate values, absolute and percentage changes, the configured
        threshold, and an outcome. Candidate-only and baseline-only keys remain
        visible. A :class:`ring5.Table` is returned when both inputs are tables.

        Args:
            baseline: Reference measurements with one row per alignment key.
            candidate: Measurements evaluated against the reference.
            key_columns: Columns that uniquely identify corresponding rows.
            metric_columns: Numeric columns to compare.
            directions: ``"higher"`` or ``"lower"`` globally, or by metric.
            thresholds: Non-negative global or per-metric tolerance.
            threshold_mode: Interpret thresholds as ``"percentage"`` or
                ``"absolute"`` values.
            baseline_name: Label stored with reference values.
            candidate_name: Label stored with candidate values.

        Returns:
            Long-form comparison data. The output type matches table inputs only
            when both inputs are :class:`ring5.Table` instances.

        Raises:
            ColumnNotFoundError: An alignment key or metric is absent.
            DataValidationError: Keys, metrics, directions, or thresholds are invalid.
        """
        # [impl->req~ring5.analysis.regression-comparison~1]
        baseline_frame, baseline_was_table = _unwrap_table(baseline)
        candidate_frame, candidate_was_table = _unwrap_table(candidate)
        keys = list(key_columns)
        metrics = list(metric_columns)
        _require_columns(baseline_frame, keys + metrics)
        _require_columns(candidate_frame, keys + metrics)
        try:
            result = self.api.managers.compare(
                baseline_frame,
                candidate_frame,
                keys,
                metrics,
                directions=directions,
                thresholds=thresholds,
                threshold_mode=threshold_mode,
                baseline_name=baseline_name,
                candidate_name=candidate_name,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        if baseline_was_table and candidate_was_table:
            return _rewrap_table(result)
        return result

    def compare_statistics(
        self,
        baseline: "pd.DataFrame | Table",
        candidate: "pd.DataFrame | Table",
        group_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        confidence_level: float = 0.95,
        alpha: float = 0.05,
        bootstrap_samples: int = 2_000,
        random_seed: int = 0,
        minimum_sample_size: int = 5,
    ) -> "pd.DataFrame | Table":
        """Calculate statistics for repeated baseline and candidate samples.

        Results include per-side sample counts and means, a Welch confidence
        interval and p-value, Hedges' g, a deterministic bootstrap estimate and
        interval, and explicit sample-quality warnings. A :class:`ring5.Table`
        is returned when both inputs are tables.

        Args:
            baseline: Reference observations.
            candidate: Candidate observations.
            group_columns: Columns defining independent comparison groups. An
                empty sequence compares all observations together.
            metric_columns: Numeric measurements to compare.
            confidence_level: Two-sided confidence level between zero and one.
            alpha: P-value threshold used for the significance result.
            bootstrap_samples: Deterministic resample count from 100 to 50,000.
            random_seed: Non-negative resampling seed.
            minimum_sample_size: Per-side count below which a warning is emitted.

        Returns:
            Long-form statistical results. The output is a :class:`ring5.Table`
            only when both inputs are tables.

        Raises:
            ColumnNotFoundError: A grouping or metric column is absent.
            DataValidationError: Inputs or statistical options are invalid.
        """
        # [impl->req~ring5.analysis.statistical-comparison~1]
        baseline_frame, baseline_was_table = _unwrap_table(baseline)
        candidate_frame, candidate_was_table = _unwrap_table(candidate)
        groups = list(group_columns)
        metrics = list(metric_columns)
        _require_columns(baseline_frame, groups + metrics)
        _require_columns(candidate_frame, groups + metrics)
        try:
            result = self.api.managers.compare_statistics(
                baseline_frame,
                candidate_frame,
                groups,
                metrics,
                confidence_level=confidence_level,
                alpha=alpha,
                bootstrap_samples=bootstrap_samples,
                random_seed=random_seed,
                minimum_sample_size=minimum_sample_size,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        if baseline_was_table and candidate_was_table:
            return _rewrap_table(result)
        return result

    def annotate_comparison(
        self,
        comparison: "pd.DataFrame | Table",
        *,
        label_columns: Sequence[str] | None = None,
        change_mode: Literal["threshold", "percentage", "absolute"] = "threshold",
    ) -> "pd.DataFrame | Table":
        """Add accessible, plot-ready outcome annotations to comparison rows.

        Args:
            comparison: Long-form result from :meth:`compare`.
            label_columns: Columns combined with the metric for point labels.
                By default, all alignment-key columns are used.
            change_mode: Use each row's threshold mode, force percentage
                change, or force absolute change.

        Returns:
            A copy with annotation label, change, symbol, marker, color, and
            text columns. A :class:`ring5.Table` input produces a table.

        Raises:
            DataValidationError: The comparison schema, labels, or mode are invalid.
        """
        # [impl->req~ring5.analysis.regression-annotations~1]
        frame, was_table = _unwrap_table(comparison)
        try:
            result = self.api.managers.annotate_comparison(
                frame,
                label_columns=label_columns,
                change_mode=change_mode,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return _rewrap_table(result) if was_table else result

    def remove_outliers(
        self,
        data: "pd.DataFrame | Table",
        outlier_col: str,
        group_by_cols: list[str] | None = None,
    ) -> "pd.DataFrame | Table":
        """IQR outlier removal.

        Accepts a :class:`ring5.Table` or a raw ``DataFrame`` and returns the same kind,
        consistent with ``shape``/``reduce_seeds``/``create_plot``.

        Args:
            data: Input table or DataFrame.
            outlier_col: Numeric column tested for outliers.
            group_by_cols: Optional columns defining independent IQR groups.

        Returns:
            Filtered data of the same public type as ``data``.

        Raises:
            ColumnNotFoundError: A named column is absent.
            DataValidationError: Inputs rejected (e.g. non-numeric column).
        """
        frame, was_table = _unwrap_table(data)
        _require_columns(frame, [outlier_col] + (group_by_cols or []))
        try:
            cleaned = self.api.managers.remove_outliers(frame, outlier_col, group_by_cols or [])
        except (ValueError, TypeError) as exc:
            raise DataValidationError(str(exc)) from exc
        return _rewrap_table(cleaned) if was_table else cleaned

    def apply_operation(
        self,
        data: "pd.DataFrame | Table",
        operation: str,
        src1: str,
        src2: str,
        dest: str,
    ) -> "pd.DataFrame | Table":
        """Create a column using a registered binary arithmetic operation.

        Args:
            data: Input table or DataFrame.
            operation: Arithmetic operation name or supported symbol.
            src1: Left operand column.
            src2: Right operand column.
            dest: Destination column name.

        Returns:
            Transformed data of the same public type as ``data``.

        Raises:
            ColumnNotFoundError: An operand column is absent.
            DataValidationError: The operation or destination is invalid.
        """
        frame, was_table = _unwrap_table(data)
        _require_columns(frame, [src1, src2])
        if not dest:
            raise DataValidationError("Destination column name cannot be empty.")
        try:
            result = self.api.managers.apply_operation(frame, operation, src1, src2, dest)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return _rewrap_table(result) if was_table else result

    def mix_columns(
        self,
        data: "pd.DataFrame | Table",
        dest_col: str,
        source_cols: list[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> "pd.DataFrame | Table":
        """Merge columns, including standard-deviation propagation.

        Args:
            data: Input table or DataFrame.
            dest_col: Destination column name.
            source_cols: Two or more columns to merge.
            operation: ``Sum``, ``Mean``, ``Mean (Average)``, or
                ``Concatenate``.
            separator: Separator used by concatenation.

        Returns:
            Transformed data of the same public type as ``data``.

        Raises:
            ColumnNotFoundError: A source column is absent.
            DataValidationError: The merge configuration is invalid.
        """
        frame, was_table = _unwrap_table(data)
        _require_columns(frame, source_cols)
        errors = self.api.managers.validate_merge_inputs(frame, source_cols, operation, dest_col)
        if errors:
            raise DataValidationError("; ".join(errors))
        try:
            result = self.api.managers.apply_mixer(
                frame, dest_col, source_cols, operation, separator
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return _rewrap_table(result) if was_table else result

    # figures
    def create_plot(
        self,
        plot_type: str,
        *,
        data: "pd.DataFrame | Table",
        config: FigureSpec | Mapping[str, Any],
        name: str | None = None,
    ) -> BasePlot:
        # [impl->req~ring5.api.plot-validation~1]
        """Create and register a configured plot.

        Args:
            plot_type: A snake-case identifier such as ``"bar"`` or a display
                name such as ``"Grouped Bar"``. Hyphens and spaces are normalized.
            data: A :class:`ring5.Table` or pandas DataFrame.
            config: A typed :class:`FigureSpec` or a mapping containing the
                renderer's flat configuration.
            name: Portfolio/display name. A stable generated name is used when omitted.

        Returns:
            The registered plot. Pass it to :meth:`render`, or use :meth:`plot`
            to create and render in one call.

        Raises:
            DataValidationError: ``plot_type`` is not registered.
        """
        from src.web.pages.ui.plotting.plot_service import PlotService

        resolved_type = _resolve_plot_type(plot_type)
        frame, _ = _unwrap_table(data)
        if not isinstance(frame, pd.DataFrame):
            raise DataValidationError("Plot data must be a pandas DataFrame or ring5.Table.")
        try:
            raw_config = config.to_config() if isinstance(config, FigureSpec) else dict(config)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(f"Plot config must be a mapping: {exc}") from exc
        validate_plot_config(resolved_type, frame, raw_config)

        # Validation happens before registration so a rejected configuration
        # cannot leave a broken plot behind in the session portfolio.
        plot = PlotService.create_plot(name or resolved_type, resolved_type, self.api.state_manager)
        if name is None:
            plot.name = f"{resolved_type}_{plot.plot_id}"
        plot.replace_processed_data(frame.copy())
        plot.replace_source_data(frame)
        # Plot configuration contains nested lists and dictionaries. Copy it so a
        # later caller mutation cannot silently change an already registered plot.
        plot.config = copy.deepcopy(raw_config)
        return plot

    def plot(
        self,
        plot_type: str,
        *,
        data: "pd.DataFrame | Table",
        config: FigureSpec | Mapping[str, Any],
        engine: EngineMode = "plotly",
        name: str | None = None,
    ) -> _render.Figure:
        """Create, register, and render a plot in one call.

        Args:
            plot_type: Registered plot identifier or display name.
            data: A :class:`ring5.Table` or pandas DataFrame.
            config: A :class:`FigureSpec` or flat configuration mapping.
            engine: Rendering engine, ``"plotly"`` or ``"matplotlib"``.
            name: Optional portfolio/display name.

        Returns:
            The rendered Plotly or Matplotlib figure. The underlying plot remains
            registered in :attr:`plots` and is included in saved portfolios.

        Raises:
            DataValidationError: ``plot_type`` is not registered.
            RenderError: ``engine`` is invalid or rendering fails validation.
        """
        configured = self.create_plot(plot_type, data=data, config=config, name=name)
        return self.render(configured, engine=engine)

    def render(self, plot: BasePlot, *, engine: EngineMode = "plotly") -> _render.Figure:
        # [impl->req~ring5.api.plot-validation~1]
        """Render a configured plot headlessly.

        Args:
            plot: Plot returned by :meth:`create_plot` or a portfolio restore.
            engine: Rendering engine, ``"plotly"`` or ``"matplotlib"``.

        Returns:
            The rendered Plotly or Matplotlib figure.

        Raises:
            RenderError: The engine is invalid or the plot has no processed
                data.
        """
        return _render.render_figure(plot, engine=engine)

    def create_dashboard(
        self,
        plots: Sequence[BasePlot | int],
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
        """Compose two or more registered plots into an immutable grid spec.

        Plot objects and integer plot IDs may be mixed.  Panel order follows
        the input order; rows are inferred from ``columns`` when omitted.

        Args:
            plots: Registered plot objects or integer plot IDs in panel order.
            title: Title spanning the complete dashboard.
            rows: Explicit row count, or inferred from ``columns`` when omitted.
            columns: Number of grid columns.
            width: Complete dashboard width in pixels.
            height: Complete dashboard height in pixels.
            shared_xaxes: Link compatible X-axis ranges across panels.
            shared_yaxes: Link compatible Y-axis ranges across panels.
            shared_legend: Deduplicate series labels into one figure legend.
            x_title: Optional complete-dashboard X-axis title.
            y_title: Optional complete-dashboard Y-axis title.
            panel_titles: Optional titles aligned with ``plots``; plot names are the default.

        Returns:
            An immutable validated dashboard specification.

        Raises:
            DataValidationError: Plot selection, grid, titles, or dimensions are invalid.
        """
        plot_ids = [value.plot_id if isinstance(value, BasePlot) else value for value in plots]
        try:
            return self.api.create_dashboard(
                plot_ids,
                title=title,
                rows=rows,
                columns=columns,
                width=width,
                height=height,
                shared_xaxes=shared_xaxes,
                shared_yaxes=shared_yaxes,
                shared_legend=shared_legend,
                x_title=x_title,
                y_title=y_title,
                panel_titles=panel_titles,
            )
        except ValueError as exc:
            raise DataValidationError(str(exc)) from exc

    def render_dashboard(
        self,
        dashboard: DashboardSpec,
        *,
        engine: EngineMode = "plotly",
    ) -> _render.Figure:
        # [impl->req~ring5.plots.multi-panel-dashboard~1]
        """Render every live plot referenced by ``dashboard`` as one figure.

        Args:
            dashboard: Specification returned by :meth:`create_dashboard`.
            engine: Rendering engine, ``"plotly"`` or ``"matplotlib"``.

        Returns:
            A complete figure accepted by :meth:`export` and :meth:`export_bytes`.

        Raises:
            RenderError: A plot was deleted, has no processed data, or cannot be rendered.
        """
        return _dashboard.render_dashboard(self.plots, dashboard, engine=engine)

    def create_linked_selection(
        self,
        plots: Sequence[BasePlot | int] | DashboardSpec,
        *,
        axis: Literal["x", "y"] = "x",
        mode: Literal["highlight", "filter"] = "highlight",
    ) -> LinkedSelectionSpec:
        # [impl->req~ring5.plots.linked-selections~1]
        """Link visible axis values across two or more registered plots.

        Args:
            plots: Dashboard specification, registered plots, or plot IDs.
            axis: Visible values to relate, ``"x"`` or ``"y"``.
            mode: Fade unrelated points with ``"highlight"`` or remove them
                from the returned view with ``"filter"``.

        Returns:
            An immutable linked-selection specification.

        Raises:
            DataValidationError: The plots, axis, or mode are invalid.
        """
        if isinstance(plots, DashboardSpec):
            plot_ids = list(plots.plot_ids)
        else:
            plot_ids = [value.plot_id if isinstance(value, BasePlot) else value for value in plots]
        try:
            return self.api.create_linked_selection(plot_ids, axis=axis, mode=mode)
        except ValueError as exc:
            raise DataValidationError(str(exc)) from exc

    def create_small_multiples(
        self,
        plot: BasePlot | int,
        *,
        by: str | Sequence[str],
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
        """Resolve ordered categorical panels for one registered plot.

        Args:
            plot: A plot registered in this session, or its integer ID.
            by: One categorical column or an ordered sequence of columns.
            columns: Number of panels in each grid row.
            order: Optional leading panel order. Remaining groups retain data order.
            labels: Optional panel-title overrides keyed by a value or value tuple.
            title: Complete-figure title; the plot title is used when omitted.
            width: Complete figure width in pixels.
            panel_height: Height allocated to each grid row in pixels.
            shared_xaxes: Keep compatible X-axis ranges aligned across panels.
            shared_yaxes: Keep compatible Y-axis ranges aligned across panels.
            shared_legend: Deduplicate identical series labels across panels.
            x_title: Optional complete-figure X-axis title.
            y_title: Optional complete-figure Y-axis title.

        Returns:
            An immutable specification accepted by :meth:`render_small_multiples`.

        Raises:
            DataValidationError: The plot, facet columns, order, labels, or layout are invalid.
        """
        plot_id = plot.plot_id if isinstance(plot, BasePlot) else plot
        facet_columns = [by] if isinstance(by, str) else list(by)
        try:
            return self.api.create_small_multiples(
                plot_id,
                facet_columns,
                columns=columns,
                order=order,
                labels=labels,
                title=title,
                width=width,
                panel_height=panel_height,
                shared_xaxes=shared_xaxes,
                shared_yaxes=shared_yaxes,
                shared_legend=shared_legend,
                x_title=x_title,
                y_title=y_title,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def render_small_multiples(
        self,
        spec: SmallMultiplesSpec,
        *,
        engine: EngineMode = "plotly",
    ) -> _render.Figure:
        # [impl->req~ring5.plots.small-multiples~1]
        """Render a small-multiples specification with either figure engine.

        Args:
            spec: Specification returned by :meth:`create_small_multiples`.
            engine: Rendering engine, ``"plotly"`` or ``"matplotlib"``.

        Returns:
            A complete Plotly or Matplotlib figure.

        Raises:
            RenderError: The source plot or a resolved panel is no longer renderable.
        """
        return _small_multiples.render_small_multiples(self.plots, spec, engine=engine)

    def small_multiples(
        self,
        plot: BasePlot | int,
        *,
        by: str | Sequence[str],
        engine: EngineMode = "plotly",
        **layout: Any,
    ) -> _render.Figure:
        """Create and immediately render categorical facets for one plot.

        Args:
            plot: A plot registered in this session, or its integer ID.
            by: One categorical column or an ordered sequence of columns.
            engine: Rendering engine, ``"plotly"`` or ``"matplotlib"``.
            **layout: Options accepted by :meth:`create_small_multiples`.

        Returns:
            A complete Plotly or Matplotlib figure.
        """
        spec = self.create_small_multiples(plot, by=by, **layout)
        return self.render_small_multiples(spec, engine=engine)

    def drill_down(
        self,
        plot: BasePlot | int,
        filters: Mapping[str, Any],
    ) -> DrillDownResult:
        # [impl->req~ring5.plots.drill-down~1]
        """Return source rows represented by a plotted aggregate or point.

        Args:
            plot: A plot registered in this session, or its integer ID.
            filters: Exact source dimensions attached to the plotted point.

        Returns:
            A defensive source-row snapshot. Reading :attr:`rows` returns a copy.

        Raises:
            DataValidationError: The plot, source data, or filters are invalid.
        """
        plot_id = plot.plot_id if isinstance(plot, BasePlot) else plot
        try:
            return self.api.drill_down_plot(plot_id, filters)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def copy_plot_content(
        self,
        source: BasePlot | int,
        target: BasePlot | int,
        mode: PlotTransferMode,
        *,
        sections: Sequence[str] = (),
    ) -> PlotTransferResult:
        # [impl->req~ring5.plots.copy-settings-pipeline~1]
        """Copy selected settings, a complete configuration, or a pipeline.

        Args:
            source: Registered source plot or integer plot ID.
            target: Registered destination plot or integer plot ID.
            mode: ``"settings"``, ``"configuration"``, or ``"pipeline"``.
            sections: Figure sections used only by ``"settings"`` mode.

        Returns:
            A summary of copied keys or pipeline steps and whether finalization is required.

        Raises:
            DataValidationError: The plots or requested transfer are incompatible.
        """
        source_id = source.plot_id if isinstance(source, BasePlot) else source
        target_id = target.plot_id if isinstance(target, BasePlot) else target
        try:
            return self.api.copy_plot_content(
                source_id,
                target_id,
                mode,
                sections=sections,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def compare_plot_configurations(
        self,
        source: BasePlot | int,
        destination: BasePlot | int,
    ) -> PlotConfigurationComparison:
        # [impl->req~ring5.plots.configuration-comparison~1]
        """Inspect field-level differences before replacing plot configuration.

        Args:
            source: Registered source plot or integer plot ID.
            destination: Registered destination plot or integer plot ID.

        Returns:
            An immutable difference summary including replacement compatibility.

        Raises:
            DataValidationError: Either plot is unknown or both references are the same.
        """
        source_id = source.plot_id if isinstance(source, BasePlot) else source
        destination_id = destination.plot_id if isinstance(destination, BasePlot) else destination
        try:
            return self.api.compare_plot_configurations(source_id, destination_id)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def export(
        self,
        fig: _render.Figure,
        path: str,
        *,
        fmt: str | None = None,
        deterministic: bool = False,
        **kwargs: Any,
    ) -> str:
        """Export a rendered figure to a file.

        Args:
            fig: Figure returned by :meth:`render`.
            path: Destination file path.
            fmt: Explicit format; inferred from ``path`` when omitted.
            deterministic: Enable byte-stable export settings.
            **kwargs: Engine-specific dimensions and resolution options.

        Returns:
            The written file path.

        Raises:
            ExportError: The format is unsupported or the destination cannot
                be written.
            DependencyMissingError: The selected format requires an external
                executable that is unavailable.
        """
        return _export.export_file(fig, path, fmt=fmt, deterministic=deterministic, **kwargs)

    def export_bytes(
        self,
        fig: _render.Figure,
        fmt: str,
        *,
        deterministic: bool = False,
        **kwargs: Any,
    ) -> bytes:
        """Export a rendered figure to bytes.

        Args:
            fig: Figure returned by :meth:`render`.
            fmt: Output format supported by the figure's engine.
            deterministic: Enable byte-stable export settings.
            **kwargs: Engine-specific dimensions and resolution options.

        Returns:
            Encoded figure bytes.

        Raises:
            ExportError: The format is unsupported or generation fails.
            DependencyMissingError: The selected format requires an external
                executable that is unavailable.
        """
        return _export.export_bytes(fig, fmt, deterministic=deterministic, **kwargs)

    # portfolios
    @property
    def plots(self) -> list[BasePlot]:
        """The session's plots (created here or restored from a portfolio)."""
        return list(self.api.state_manager.get_plots())  # type: ignore[arg-type]

    def save_portfolio(self, name: str, *, overwrite: bool = False) -> None:
        # [impl->req~ring5.portfolio.safe-overwrite~1]
        """Snapshot the session (data + plots + config) to a portfolio.

        Unlike the web UI, ``overwrite`` defaults to **False** here:
        portfolios are keyed by name alone, and a script silently replacing
        one is data loss. Pass ``overwrite=True`` to replace.

        Args:
            name: Portfolio name.
            overwrite: Replace an existing portfolio with the same name.

        Raises:
            PortfolioError: The name exists and ``overwrite`` is False.
        """
        from src.web.rendering.config_builder import build_figure_spec_dict

        sm = self.api.state_manager
        try:
            self.api.data_services.save_portfolio(
                name=name,
                data=sm.get_data(),
                plots=sm.get_plots(),
                config=sm.get_config(),
                plot_counter=sm.get_plot_counter(),
                csv_path=sm.get_csv_path(),
                parse_variables=sm.get_parse_variables(),
                figure_spec_enricher=build_figure_spec_dict,
                overwrite=overwrite,
            )
        except FileExistsError as exc:
            raise PortfolioError(str(exc)) from exc
        except (OSError, ValueError) as exc:
            raise PortfolioError(f"Portfolio '{name}' could not be saved: {exc}") from exc

    def load_portfolio(self, name: str) -> RestoreReport:
        """Load + restore a portfolio; the report says what was skipped.

        Args:
            name: Portfolio name.

        Returns:
            A report describing restored and skipped content.

        Raises:
            PortfolioError: The portfolio does not exist.
            PortfolioVersionError: It was written by a newer RING-5.
        """
        from src.core.services.portfolio_migrator import (
            PortfolioVersionError as CoreVersionError,
        )

        from ring5.errors import PortfolioVersionError

        try:
            data = self.api.data_services.load_portfolio(name)
        except FileNotFoundError as exc:
            raise PortfolioError(str(exc)) from exc
        except CoreVersionError as exc:
            # Keep errors from the public API within the ``Ring5Error`` hierarchy.
            raise PortfolioVersionError(str(exc)) from exc
        except ValueError as exc:
            # JSON and schema validation errors both surface as ``ValueError`` here.
            raise PortfolioError(f"Portfolio '{name}' could not be read: {exc}") from exc
        try:
            return self.api.state_manager.restore_session(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio '{name}' could not be restored: {exc}") from exc


def _require_columns(data: pd.DataFrame, columns: list[str]) -> None:
    """Raise the typed missing-column error before delegating to core."""
    for col in columns:
        if col not in data.columns:
            raise ColumnNotFoundError(col, list(data.columns))
