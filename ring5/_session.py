"""Headless workspace for parsing, shaping, plotting, and portfolio replay."""

from __future__ import annotations

import copy
import shutil
import tempfile
import threading
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

import pandas as pd

from src.core.application_api import ApplicationAPI
from src.core.models import (
    AccessibilityReport,
    AnalysisReport,
    AnalysisRecipe,
    AnalysisRecipeInfo,
    AnalysisRecipeMatrixResult,
    AnalysisRecipeRunResult,
    BackgroundJobInfo,
    ColumnSemantics,
    DataQualityReport,
    DashboardSpec,
    DrillDownResult,
    DatasetInfo,
    DatasetLineage,
    DatasetRevision,
    DatasetSnapshotInfo,
    DatasetSchemaContract,
    DatasetSemantics,
    EnvironmentComparison,
    EnvironmentMetadata,
    FigureTheme,
    ImportColumnCorrection,
    ImportOptions,
    ImportPreview,
    IncrementalParseBatchResult,
    JoinCardinality,
    JoinDiagnostics,
    LinkedSelectionSpec,
    ParseBatchResult,
    PipelineConfigConflictPolicy,
    PipelineConfigImportResult,
    PlotConfigurationComparison,
    PlotTransferMode,
    PlotTransferResult,
    PortfolioData,
    PortfolioBundleContents,
    PortfolioBundleInfo,
    PortfolioDiff,
    PortfolioIntegrityReport,
    PortfolioRevisionInfo,
    ReportFigure,
    RecipeExport,
    RecipeParameter,
    RecipePlot,
    RecipeScalar,
    RecipeSource,
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
    ExportError,
    JobError,
    ParseError,
    PipelineError,
    PortfolioError,
    RecipeError,
    ScanError,
)
from ring5.figure_spec import FigureSpec
from ring5._plot_validation import validate_plot_config

PlotType = Literal[
    "area",
    "bar",
    "box",
    "dual_axis_bar_dot",
    "ecdf",
    "grouped_bar",
    "grouped_stacked_bar",
    "heatmap",
    "histogram",
    "line",
    "parallel_coordinates",
    "radar",
    "sankey",
    "scatter",
    "stacked_bar",
    "violin",
    "waterfall",
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
        self._parser_override = parser
        # Temporary parse output is removed when the session closes.
        self._owned_tmpdirs: list[str] = []
        self._parse_jobs: list[_parse.ParseJob | _parse.ParserPlaygroundJob] = []
        self._incremental_output_dirs: dict[tuple[str, str, str, str], str] = {}

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
        self._incremental_output_dirs.clear()
        self.api.close_background_jobs()

    # background jobs
    def background_jobs(self) -> tuple[BackgroundJobInfo, ...]:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Return newest-first scan, parse, transformation, and export jobs.

        Returns:
            Immutable progress, attempt, cancellation, completion, and bounded
            error information for this session.
        """
        return self.api.list_background_jobs()

    def cancel_background_job(self, job: str | BackgroundJobInfo) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Request cancellation of one job without claiming running work stopped.

        Args:
            job: Job ID or snapshot returned by :meth:`background_jobs`.

        Returns:
            Updated job state, which can be ``cancelling`` until running work settles.

        Raises:
            JobError: The job identifier is invalid or unknown.
        """
        try:
            return self.api.cancel_background_job(self._background_job_id(job))
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            raise JobError(str(exc)) from exc

    def retry_background_job(self, job: str | BackgroundJobInfo) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Retry one finished job using its captured submission inputs.

        Args:
            job: Job ID or immutable job snapshot.

        Returns:
            The same job identity at its next attempt.

        Raises:
            JobError: The job is active, unknown, not retryable, or cannot be resubmitted.
        """
        try:
            return self.api.retry_background_job(self._background_job_id(job))
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            raise JobError(str(exc)) from exc

    def background_job_result(self, job: str | BackgroundJobInfo) -> Any:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Return a completed transformation or export result without waiting.

        Scan and parse results remain on their original :class:`ScanJob` and
        :class:`ParseJob` handles to avoid retaining duplicate parser payloads.

        Args:
            job: Job ID or immutable job snapshot.

        Returns:
            The completed result retained by the job center.

        Raises:
            JobError: The job is active, failed, cancelled, unknown, or keeps
                its result on another handle.
        """
        try:
            return self.api.get_background_job_result(self._background_job_id(job))
        except (KeyError, RuntimeError, TypeError, ValueError) as exc:
            raise JobError(str(exc)) from exc

    def dismiss_finished_background_jobs(self) -> int:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Remove finished job records and release retained results.

        Returns:
            Number of records removed. Active jobs are never dismissed.
        """
        return self.api.dismiss_finished_background_jobs()

    @staticmethod
    def _background_job_id(job: str | BackgroundJobInfo) -> str:
        if isinstance(job, BackgroundJobInfo):
            return job.job_id
        if not isinstance(job, str) or not job:
            raise JobError("Background job must be a non-empty ID or BackgroundJobInfo.")
        return job

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
    def parser_playground_submit(
        self,
        stats_path: str,
        variables: list[str | StatConfig],
        *,
        pattern: str = "stats.txt",
        strategy: str = "simple",
        output_dir: str | None = None,
        scan_limit: int = 10,
    ) -> _parse.ParserPlaygroundJob:
        # [impl->req~ring5.ingestion.parser-playground~1]
        """Test parser settings against a deterministic three-file sample.

        This submits the same asynchronous parser used by a full run. It only
        retains scratch output until :meth:`ParserPlaygroundJob.finalize`
        returns the immutable preview, and it does not change workspace data
        or parse provenance.

        Args:
            stats_path: Root directory containing simulator statistics.
            variables: Statistic names or explicit statistic configurations.
            pattern: Statistics filename pattern.
            strategy: Registered parser strategy.
            output_dir: Directory for temporary preview assembly. A session-owned
                temporary directory is used when omitted.
            scan_limit: Maximum files used to resolve plain statistic names.

        Returns:
            A submitted configuration-test job that can be finalized or cancelled.

        Raises:
            ScanError: Variable discovery failed.
            ParseError: The parser rejected the bounded submission.
        """
        configs, scanned = _parse.build_stat_configs(
            self.api, stats_path, variables, pattern=pattern, scan_limit=scan_limit
        )
        created_output = output_dir is None
        if created_output:
            out_dir = tempfile.mkdtemp(prefix="ring5_parser_playground_")
            self._owned_tmpdirs.append(out_dir)
        else:
            out_dir = cast(str, output_dir)

        try:
            batch = self.api.submit_parser_playground_async(
                stats_path,
                pattern,
                cast(list[ParseVariableConfig | StatConfig], list(configs)),
                out_dir,
                strategy_type=strategy,
                scanned_vars=scanned,
            )
        except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
            if created_output:
                shutil.rmtree(out_dir, ignore_errors=True)
                self._owned_tmpdirs.remove(out_dir)
            raise ParseError(f"Parser configuration test submission failed: {exc}") from exc

        job = _parse.ParserPlaygroundJob(
            api=self.api,
            batch=batch,
            futures=list(batch.futures),
            output_dir=out_dir,
            stats_path=stats_path,
            stats_pattern=pattern,
        )
        self._parse_jobs.append(job)
        return job

    def parse_submit(
        self,
        stats_path: str,
        variables: list[str | StatConfig],
        *,
        pattern: str = "stats.txt",
        strategy: str = "simple",
        output_dir: str | None = None,
        scan_limit: int = 10,
        incremental: bool = False,
        cache_path: str | None = None,
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
            incremental: Parse only new or changed inputs and reuse unchanged finalized rows.
            cache_path: Optional JSON cache location for incremental mode. By default the cache
                lives beside ``results.csv`` in ``output_dir``.

        Returns:
            A submitted parse job that can be finalized or cancelled.

        Raises:
            ScanError: No matching statistics files were found or variable
                discovery failed.
            ParseError: The parser rejected the submission.
        """
        # [impl->req~ring5.ingestion.incremental-parsing~1]
        # [impl->req~ring5.ingestion.async-parse~1]
        # [impl->req~ring5.ingestion.parse-output-provenance~1]
        configs, scanned = _parse.build_stat_configs(
            self.api, stats_path, variables, pattern=pattern, scan_limit=scan_limit
        )
        created_output = False
        if output_dir is None and incremental:
            cache_key = (
                str(Path(stats_path).expanduser().resolve()),
                pattern,
                strategy,
                str(Path(cache_path).expanduser().resolve()) if cache_path else "",
            )
            existing_output = self._incremental_output_dirs.get(cache_key)
            if existing_output is None:
                out_dir = tempfile.mkdtemp(prefix="ring5_incremental_parse_")
                self._owned_tmpdirs.append(out_dir)
                self._incremental_output_dirs[cache_key] = out_dir
                created_output = True
            else:
                out_dir = existing_output
        elif output_dir is None:
            out_dir = tempfile.mkdtemp(prefix="ring5_parse_")
            self._owned_tmpdirs.append(out_dir)
            created_output = True
        else:
            out_dir = output_dir
        batch: ParseBatchResult | IncrementalParseBatchResult
        try:
            if incremental:
                batch = self.api.submit_incremental_parse_async(
                    stats_path,
                    pattern,
                    cast(list[ParseVariableConfig | StatConfig], list(configs)),
                    out_dir,
                    strategy_type=strategy,
                    scanned_vars=scanned,
                    cache_path=cache_path,
                )
            else:
                batch = self.api.submit_parse_async(
                    stats_path,
                    pattern,
                    cast(list[ParseVariableConfig | StatConfig], list(configs)),
                    out_dir,
                    strategy_type=strategy,
                    scanned_vars=scanned,
                )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            if created_output:
                shutil.rmtree(out_dir, ignore_errors=True)
                self._owned_tmpdirs.remove(out_dir)
                for key, value in tuple(self._incremental_output_dirs.items()):
                    if value == out_dir:
                        self._incremental_output_dirs.pop(key)
            raise ParseError(f"Parse submission failed: {exc}") from exc

        # Store parse provenance for portfolio restoration and replay.
        sm = self.api.state_manager
        sm.set_stats_path(stats_path)
        sm.set_stats_pattern(pattern)
        sm.set_parser_strategy(strategy)
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
            incremental_batch=(batch if isinstance(batch, IncrementalParseBatchResult) else None),
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
        incremental: bool = False,
        cache_path: str | None = None,
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
            incremental: Parse only new or changed files and reuse unchanged finalized rows.
            cache_path: Optional JSON cache location for incremental mode.

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
            incremental=incremental,
            cache_path=cache_path,
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

    def preview_import(
        self,
        file_path: str,
        *,
        encoding: str | None = None,
        delimiter: str | None = None,
        header_row: int = 1,
        trim_whitespace: bool = True,
        null_values: Sequence[str] = ("", "NA", "N/A", "null", "None"),
        column_types: (
            Mapping[str, Literal["auto", "text", "integer", "number", "boolean", "datetime"]] | None
        ) = None,
        preview_rows: int = 50,
    ) -> ImportPreview:
        # [impl->req~ring5.ingestion.import-preview~1]
        """Inspect and correct a delimited table without loading it.

        Args:
            file_path: CSV or other delimited-text source.
            encoding: Explicit supported encoding, or ``None`` to detect it.
            delimiter: Explicit comma, semicolon, tab, or pipe, or ``None`` to detect it.
            header_row: One-based record containing column names.
            trim_whitespace: Strip surrounding whitespace from headers and cells.
            null_values: Source tokens interpreted as missing values.
            column_types: Optional per-column type overrides.
            preview_rows: Maximum accepted rows retained for display, from 1 through 500.

        Returns:
            An immutable result with detected format, types, accepted rows, and rejections.

        Raises:
            DataLoadError: The source or corrections cannot be inspected safely.
        """
        try:
            options = ImportOptions(
                encoding=encoding,
                delimiter=delimiter,
                header_row=header_row,
                trim_whitespace=trim_whitespace,
                null_values=tuple(null_values),
                column_types=tuple(
                    ImportColumnCorrection(column, import_as)
                    for column, import_as in (column_types or {}).items()
                ),
                preview_rows=preview_rows,
            )
            return self.api.preview_import(file_path, options)
        except (OSError, TypeError, UnicodeError, ValueError) as exc:
            raise DataLoadError(f"Could not preview import {file_path!r}: {exc}") from exc

    def load_import(self, preview: ImportPreview) -> pd.DataFrame:
        # [impl->req~ring5.ingestion.import-preview~1]
        """Load accepted rows from an unchanged import preview.

        Args:
            preview: Result returned by :meth:`preview_import`.

        Returns:
            Loaded accepted rows with reviewed column types.

        Raises:
            DataLoadError: The source changed, has no accepted rows, or cannot be loaded.
        """
        try:
            return self.api.load_import_preview(preview)
        except (OSError, TypeError, UnicodeError, ValueError) as exc:
            raise DataLoadError(f"Could not load reviewed import: {exc}") from exc

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

    def apply_semantics(
        self,
        data: "pd.DataFrame | Table",
        semantics: DatasetSemantics | DatasetSchemaContract,
    ) -> "pd.DataFrame | Table":
        """Return a table that retains human labels and physical units.

        A schema contract may be supplied directly; its ``semantic_label`` and
        ``unit`` fields become the retained metadata. This operation does not
        run contract validation or mutate the input.

        Args:
            data: DataFrame or :class:`ring5.Table` to annotate.
            semantics: Explicit metadata or the schema contract that declares it.

        Raises:
            DataValidationError: Metadata names or units are invalid.
        """
        # [impl->req~ring5.data.semantic-units~1]
        frame, was_table = _unwrap_table(data)
        if isinstance(semantics, DatasetSchemaContract):
            semantics = DatasetSemantics(
                tuple(
                    ColumnSemantics(column.name, column.semantic_label, column.unit)
                    for column in semantics.columns
                    if column.semantic_label or column.unit
                )
            )
        try:
            result = self.api.managers.attach_semantics(frame, semantics)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return _rewrap_table(result) if was_table else result

    def inspect_semantics(
        self,
        data: "pd.DataFrame | Table",
    ) -> DatasetSemantics:
        """Return the ordered semantic labels and units retained by a table.

        Args:
            data: DataFrame or :class:`ring5.Table` to inspect without mutation.

        Returns:
            Immutable ordered semantic metadata.

        Raises:
            DataValidationError: Retained external metadata is malformed.
        """
        # [impl->req~ring5.data.semantic-units~1]
        frame, _ = _unwrap_table(data)
        try:
            return self.api.managers.inspect_semantics(frame)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def convert_unit(
        self,
        data: "pd.DataFrame | Table",
        column: str,
        target_unit: str,
    ) -> "pd.DataFrame | Table":
        """Convert one numeric column and retain its new canonical unit.

        Conversion is allowed only when the source unit is declared and both
        units describe the same dimension. The input remains unchanged.

        Args:
            data: DataFrame or :class:`ring5.Table` carrying source-unit metadata.
            column: Numeric column to convert.
            target_unit: Compatible canonical unit or documented alias.

        Returns:
            Converted data of the same public type as ``data``.

        Raises:
            DataValidationError: The column, source unit, target unit, or values are invalid.
        """
        # [impl->req~ring5.data.semantic-units~1]
        frame, was_table = _unwrap_table(data)
        try:
            result = self.api.managers.convert_unit(frame, column, target_unit)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return _rewrap_table(result) if was_table else result

    def supported_units(self) -> tuple[str, ...]:
        """Return canonical unit symbols accepted by :meth:`convert_unit`."""
        # [impl->req~ring5.data.semantic-units~1]
        return self.api.managers.supported_units()

    def apply_accessible_theme(
        self,
        config: Mapping[str, Any],
        plot_type: str,
    ) -> dict[str, Any]:
        """Enable cross-engine accessible defaults for a figure configuration.

        Args:
            config: Flat figure configuration to copy and enrich.
            plot_type: Registered plot type whose marks determine redundant encodings.

        Returns:
            A newly allocated configuration with accessibility mode enabled.

        Raises:
            DataValidationError: The configuration or plot type is invalid.
        """
        # [impl->req~ring5.figure.accessible-themes~1]
        from src.core.services.visualization.accessibility_service import AccessibilityService

        if not isinstance(config, Mapping):
            raise DataValidationError("Figure accessibility configuration must be a mapping.")
        if not isinstance(plot_type, str) or not plot_type.strip():
            raise DataValidationError("Figure accessibility requires a plot type.")
        enabled = copy.deepcopy(dict(config))
        enabled["accessibility_mode"] = True
        return AccessibilityService.apply_defaults(enabled, plot_type.strip())

    def audit_figure_accessibility(
        self,
        config: Mapping[str, Any],
        plot_type: str,
        *,
        series_count: int = 1,
    ) -> AccessibilityReport:
        """Audit palette safety, contrast, text sizes, and redundant encodings.

        Args:
            config: Flat figure configuration to audit without mutation.
            plot_type: Plot type whose marks determine redundant encodings.
            series_count: Number of independently identified visual series.

        Returns:
            Immutable findings with ratios and a pass/fail summary.

        Raises:
            DataValidationError: Inputs or colors cannot be validated.
        """
        # [impl->req~ring5.figure.accessible-themes~1]
        from src.core.services.visualization.accessibility_service import AccessibilityService

        if not isinstance(config, Mapping):
            raise DataValidationError("Figure accessibility configuration must be a mapping.")
        try:
            return AccessibilityService.audit(
                dict(config),
                plot_type,
                series_count=series_count,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def available_figure_themes(self) -> tuple[FigureTheme, ...]:
        """Return isolated built-in themes for paper, slides, dashboards, and dark use."""
        # [impl->req~ring5.figure.theme-presets~1]
        from src.core.services.visualization.figure_theme_service import FigureThemeService

        return FigureThemeService.available_themes()

    def apply_figure_theme(
        self,
        config: Mapping[str, Any],
        theme: str | FigureTheme,
        plot_type: str,
    ) -> dict[str, Any]:
        """Apply a theme's appearance while retaining data and plot-type configuration.

        Args:
            config: Existing figure configuration to copy.
            theme: Built-in identifier or an imported/customized theme.
            plot_type: Plot type used to resolve accessible mark defaults.

        Returns:
            A newly allocated themed configuration.

        Raises:
            DataValidationError: The theme or inputs are invalid.
        """
        # [impl->req~ring5.figure.theme-presets~1]
        from src.core.services.visualization.figure_theme_service import FigureThemeService

        try:
            return FigureThemeService.apply(config, theme, plot_type)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def customize_figure_theme(
        self,
        theme: str | FigureTheme,
        overrides: Mapping[str, Any],
        *,
        name: str,
    ) -> FigureTheme:
        """Create a portable theme from a base plus appearance-only overrides.

        Args:
            theme: Built-in identifier or existing theme to customize.
            overrides: Appearance-only configuration values to replace.
            name: Human-readable name for the new theme.

        Returns:
            A validated customized theme that can be applied or exported.

        Raises:
            DataValidationError: The base, name, or overrides are invalid.
        """
        # [impl->req~ring5.figure.theme-presets~1]
        from src.core.services.visualization.figure_theme_service import FigureThemeService

        try:
            return FigureThemeService.customize(theme, overrides, name=name)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def export_figure_theme(self, theme: FigureTheme) -> bytes:
        """Serialize one validated figure theme as deterministic versioned JSON.

        Args:
            theme: Theme to validate and serialize.

        Returns:
            Stable UTF-8 JSON bytes.

        Raises:
            DataValidationError: The theme is invalid.
        """
        # [impl->req~ring5.figure.theme-presets~1]
        from src.core.services.visualization.figure_theme_service import FigureThemeService

        try:
            return FigureThemeService.dumps(theme)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def import_figure_theme(self, payload: str | bytes | bytearray) -> FigureTheme:
        """Load one bounded, versioned figure theme JSON document.

        Args:
            payload: UTF-8 JSON text or bytes, limited to 256 KiB.

        Returns:
            A validated portable figure theme.

        Raises:
            DataValidationError: The payload is malformed, unsafe, or unsupported.
        """
        # [impl->req~ring5.figure.theme-presets~1]
        from src.core.services.visualization.figure_theme_service import FigureThemeService

        try:
            return FigureThemeService.loads(payload)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def export_pipeline_configuration(
        self,
        name: str,
        pipeline: list[ShaperStepConfig],
        *,
        description: str = "",
        csv_path: str | None = None,
    ) -> bytes:
        """Serialize a validated shaper pipeline as portable versioned JSON.

        Args:
            name: Human-readable configuration name.
            pipeline: Ordered flat shaper configurations.
            description: Optional human-readable explanation.
            csv_path: Optional source CSV association.

        Returns:
            Deterministic UTF-8 JSON bytes.

        Raises:
            PipelineError: The metadata or a pipeline step is invalid.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        try:
            return self.api.export_configuration(name, description, pipeline, csv_path)
        except (TypeError, ValueError) as exc:
            raise PipelineError(str(exc)) from exc

    def import_pipeline_configuration(
        self,
        payload: str | bytes | bytearray,
        *,
        conflict: PipelineConfigConflictPolicy = "error",
    ) -> PipelineConfigImportResult:
        """Validate, migrate, and save one portable pipeline configuration.

        Args:
            payload: UTF-8 JSON text or bytes, limited to 256 KiB. Legacy
                unversioned saved-configuration records are accepted.
            conflict: Logical-name policy: ``"error"``, ``"rename"``, or
                ``"replace"``.

        Returns:
            Saved configuration and migration/conflict details.

        Raises:
            PipelineError: The document is invalid, unsupported, or conflicts
                with an existing record under the selected policy.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        try:
            return self.api.import_configuration(payload, conflict=conflict)
        except (OSError, TypeError, ValueError) as exc:
            raise PipelineError(str(exc)) from exc

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

    def shape_submit(
        self,
        data: "pd.DataFrame | Table",
        pipeline: list[ShaperStepConfig],
        *,
        label: str = "Shape data",
    ) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Submit a shaper pipeline without blocking the calling thread.

        The input data and pipeline are defensively copied at submission.
        Poll :meth:`background_jobs`, then pass the finished record to
        :meth:`background_job_result`.

        Args:
            data: Input DataFrame or :class:`ring5.Table`.
            pipeline: Ordered shaper configurations.
            label: Human-readable job-center label.

        Returns:
            Initial immutable job snapshot.

        Raises:
            JobError: Submission metadata or the session job center is invalid.
        """
        frame, was_table = _unwrap_table(data)
        captured_data: pd.DataFrame | Table = frame.copy(deep=True)
        if was_table:
            captured_data = _rewrap_table(cast(pd.DataFrame, captured_data))
        captured_pipeline = copy.deepcopy(pipeline)
        try:
            return self.api.submit_background_operation(
                "transformation",
                label,
                lambda: self.shape(captured_data, captured_pipeline),
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            raise JobError(str(exc)) from exc

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
        panel_labels: Sequence[str] | Literal["auto"] | None = None,
        panel_captions: Sequence[str] | None = None,
        horizontal_spacing: float | None = None,
        vertical_spacing: float | None = None,
    ) -> DashboardSpec:
        # [impl->req~ring5.plots.multi-panel-dashboard~1]
        # [impl->req~ring5.figure.panel-composition~1]
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
            panel_labels: Optional custom labels aligned with ``plots``, or ``"auto"`` for
                publication labels ``(a)``, ``(b)``, and so on.
            panel_captions: Optional captions aligned with ``plots`` and rendered below each panel.
            horizontal_spacing: Optional normalized horizontal gap from 0 through 0.2.
            vertical_spacing: Optional normalized vertical gap from 0 through 0.2.

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
                panel_labels=panel_labels,
                panel_captions=panel_captions,
                horizontal_spacing=horizontal_spacing,
                vertical_spacing=vertical_spacing,
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

    def export_submit(
        self,
        fig: _render.Figure,
        path: str,
        *,
        fmt: str | None = None,
        deterministic: bool = False,
        label: str | None = None,
        **kwargs: Any,
    ) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Submit a figure export without blocking the calling thread.

        Args:
            fig: Figure returned by :meth:`render`.
            path: Destination file path.
            fmt: Explicit format, or infer it from ``path``.
            deterministic: Enable byte-stable export settings.
            label: Optional job-center label.
            **kwargs: Engine-specific dimensions and resolution options.

        Returns:
            Initial immutable job snapshot. The completed result is the path.

        Raises:
            JobError: Submission metadata or the session job center is invalid.
        """
        captured_figure = copy.deepcopy(fig)
        captured_kwargs = copy.deepcopy(kwargs)
        selected_label = label or f"Download {Path(path).name or 'figure'}"
        try:
            return self.api.submit_background_operation(
                "export",
                selected_label,
                lambda: _export.export_file(
                    captured_figure,
                    path,
                    fmt=fmt,
                    deterministic=deterministic,
                    **captured_kwargs,
                ),
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            raise JobError(str(exc)) from exc

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

    def create_report(
        self,
        title: str,
        figures: Sequence[BasePlot | int | DashboardSpec],
        *,
        tables: Mapping[str, pd.DataFrame] | None = None,
        narrative: Mapping[str, str] | None = None,
        figure_captions: Sequence[str] | None = None,
        table_row_limit: int = 100,
    ) -> AnalysisReport:
        # [impl->req~ring5.export.batch-reports~1]
        """Create a report from selected plots, dashboards, tables, and text.

        Data provenance and the current execution environment are captured
        automatically. Tables are copied into a bounded immutable display
        representation; input DataFrames are never mutated.

        Args:
            title: Human-readable report title.
            figures: Registered plots, plot IDs, or dashboard specifications.
            tables: Optional ordered mapping of table titles to DataFrames.
            narrative: Optional ordered mapping of section headings to plain text.
            figure_captions: Optional captions aligned with ``figures``.
            table_row_limit: Displayed rows per table, from 1 through 500.

        Returns:
            An immutable report accepted by :meth:`report_bytes` and
            :meth:`export_report`.

        Raises:
            DataValidationError: Content is missing, unregistered, misaligned,
                or outside report bounds.
        """
        from src.core.services.environment_metadata_service import EnvironmentMetadataService
        from src.core.services.report_service import ReportService

        captions = tuple(("",) * len(figures) if figure_captions is None else figure_captions)
        if len(captions) != len(figures):
            raise DataValidationError("figure_captions must contain one value per figure.")
        live = {plot.plot_id: plot for plot in self.plots}
        resolved: list[ReportFigure] = []
        try:
            for value, caption in zip(figures, captions, strict=True):
                if isinstance(value, DashboardSpec):
                    missing = [plot_id for plot_id in value.plot_ids if plot_id not in live]
                    if missing:
                        raise ValueError(
                            "Report dashboard plots are no longer available: "
                            + ", ".join(map(str, missing))
                            + "."
                        )
                    resolved.append(
                        ReportFigure(
                            plot_ids=value.plot_ids,
                            title=value.title or "Multi-panel figure",
                            caption=caption,
                            dashboard=value,
                        )
                    )
                    continue
                plot_id = value.plot_id if isinstance(value, BasePlot) else value
                if isinstance(plot_id, bool) or not isinstance(plot_id, int) or plot_id not in live:
                    raise ValueError(f"Report plot {plot_id!r} is not registered in this session.")
                resolved.append(
                    ReportFigure(
                        plot_ids=(plot_id,),
                        title=live[plot_id].name,
                        caption=caption,
                    )
                )

            state = self.api.state_manager
            provenance = ReportService.capture_provenance(
                state.get_data(),
                use_parser=state.is_using_parser(),
                csv_path=state.get_csv_path(),
                stats_path=state.get_stats_path(),
                stats_pattern=state.get_stats_pattern(),
                parse_variables=state.get_parse_variables(),
                history=state.get_portfolio_history(),
            )
            return ReportService.create(
                title,
                resolved,
                tables=tables,
                narrative=narrative,
                provenance=provenance,
                environment=EnvironmentMetadataService.capture(),
                table_row_limit=table_row_limit,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def report_bytes(self, report: AnalysisReport, fmt: Literal["html", "pdf"] = "html") -> bytes:
        # [impl->req~ring5.export.batch-reports~1]
        """Render a deterministic self-contained HTML or PDF report.

        Args:
            report: Specification returned by :meth:`create_report`.
            fmt: Output format, ``"html"`` or ``"pdf"``.

        Returns:
            Deterministic report bytes.

        Raises:
            ExportError: Rendering fails or a selected plot is no longer live.
        """
        from src.web.rendering.report_builder import render_report

        try:
            return render_report(self.plots, report, fmt=fmt)
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
            raise ExportError(f"Could not render {fmt!r} analysis report: {exc}") from exc

    def export_report(
        self,
        report: AnalysisReport,
        path: str,
        *,
        fmt: Literal["html", "pdf"] | None = None,
    ) -> str:
        # [impl->req~ring5.export.batch-reports~1]
        """Write a deterministic analysis report to a file.

        Args:
            report: Specification returned by :meth:`create_report`.
            path: Destination file path.
            fmt: Explicit format; inferred from the ``.html`` or ``.pdf`` suffix.

        Returns:
            The written file path.

        Raises:
            ExportError: The format is unsupported or the destination cannot be written.
        """
        target = Path(path)
        selected_format = fmt or target.suffix.lower().removeprefix(".")
        if selected_format not in {"html", "pdf"}:
            raise ExportError("Report path or fmt must select HTML or PDF.")
        try:
            payload = self.report_bytes(report, cast(Literal["html", "pdf"], selected_format))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        except ExportError:
            raise
        except OSError as exc:
            raise ExportError(f"Could not write report to '{target}': {exc}") from exc
        return str(target)

    # portfolios
    def environment_metadata(self, *, refresh: bool = False) -> EnvironmentMetadata:
        # [impl->req~ring5.portfolio.environment-metadata~1]
        """Return privacy-conscious metadata for the current runtime.

        Args:
            refresh: Re-probe dependency and external-tool versions instead
                of using the process-level cache.

        Returns:
            RING-5, Python, platform, dependency, renderer, and tool versions.
        """
        from src.core.services.environment_metadata_service import EnvironmentMetadataService

        return EnvironmentMetadataService.capture(refresh=refresh)

    def _read_portfolio_data(
        self,
        name: str,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioData:
        """Read a portfolio while translating storage errors to public errors."""
        from src.core.services.portfolio_migrator import (
            PortfolioVersionError as CoreVersionError,
        )

        from ring5.errors import PortfolioVersionError

        try:
            if signing_key is None and not require_signature:
                return self.api.data_services.load_portfolio(name)
            return self.api.data_services.load_portfolio(
                name,
                signing_key=signing_key,
                require_signature=require_signature,
            )
        except FileNotFoundError as exc:
            raise PortfolioError(str(exc)) from exc
        except CoreVersionError as exc:
            raise PortfolioVersionError(str(exc)) from exc
        except (OSError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio '{name}' could not be read: {exc}") from exc

    def _read_portfolio_revision_data(
        self,
        name: str,
        revision_id: str,
    ) -> PortfolioData:
        """Read one portfolio revision while preserving public error types."""
        from src.core.services.portfolio_migrator import (
            PortfolioVersionError as CoreVersionError,
        )

        from ring5.errors import PortfolioVersionError

        try:
            return self.api.data_services.load_portfolio_revision(name, revision_id)
        except FileNotFoundError as exc:
            raise PortfolioError(str(exc)) from exc
        except CoreVersionError as exc:
            raise PortfolioVersionError(str(exc)) from exc
        except (OSError, TypeError, ValueError) as exc:
            raise PortfolioError(
                f"Portfolio revision for '{name}' could not be read: {exc}"
            ) from exc

    def compare_portfolio_environment(
        self, name: str, *, refresh: bool = False
    ) -> EnvironmentComparison:
        # [impl->req~ring5.portfolio.environment-metadata~1]
        """Compare a portfolio's save-time environment with this runtime.

        Exact version differences are reported without claiming that a
        changed environment is necessarily incompatible.

        Args:
            name: Saved portfolio name.
            refresh: Re-probe current versions instead of using the cache.

        Returns:
            A component-level saved-versus-current comparison.

        Raises:
            PortfolioError: The portfolio or its environment metadata is invalid.
            PortfolioVersionError: The portfolio uses a newer schema.
        """
        from src.core.services.environment_metadata_service import EnvironmentMetadataService

        data = self._read_portfolio_data(name)
        try:
            recorded = EnvironmentMetadataService.from_payload(data.get("environment_metadata"))
        except ValueError as exc:
            raise PortfolioError(
                f"Portfolio '{name}' has invalid environment metadata: {exc}"
            ) from exc
        return EnvironmentMetadataService.compare(
            recorded,
            current=EnvironmentMetadataService.capture(refresh=refresh),
        )

    @property
    def plots(self) -> list[BasePlot]:
        """The session's plots (created here or restored from a portfolio)."""
        return list(self.api.state_manager.get_plots())  # type: ignore[arg-type]

    def save_portfolio(
        self,
        name: str,
        *,
        overwrite: bool = False,
        signing_key: str | bytes | None = None,
        signing_key_id: str = "default",
    ) -> None:
        # [impl->req~ring5.portfolio.safe-overwrite~1]
        """Snapshot the session (data + plots + config) to a portfolio.

        Unlike the web UI, ``overwrite`` defaults to **False** here:
        portfolios are keyed by name alone, and a script silently replacing
        one is data loss. Pass ``overwrite=True`` to replace.

        Args:
            name: Portfolio name.
            overwrite: Replace an existing portfolio with the same name.
            signing_key: Optional shared secret used to add an HMAC-SHA-256 signature.
            signing_key_id: Non-secret label stored with the signature.

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
                signing_key=signing_key,
                signing_key_id=signing_key_id,
            )
        except FileExistsError as exc:
            raise PortfolioError(str(exc)) from exc
        except (OSError, ValueError) as exc:
            raise PortfolioError(f"Portfolio '{name}' could not be saved: {exc}") from exc

    def verify_portfolio(
        self,
        name: str,
        *,
        signing_key: str | bytes | None = None,
    ) -> PortfolioIntegrityReport:
        # [impl->req~ring5.portfolio.signed-manifests~1]
        """Verify a saved portfolio without changing this session.

        Args:
            name: Saved portfolio name.
            signing_key: Optional shared secret for HMAC-SHA-256 verification.

        Returns:
            Structured checksum and signature evidence. A checksum-valid but
            unsigned portfolio is not presented as authenticated.

        Raises:
            PortfolioError: The portfolio cannot be read or inspected.
        """
        try:
            return self.api.data_services.verify_portfolio(name, signing_key=signing_key)
        except FileNotFoundError as exc:
            raise PortfolioError(str(exc)) from exc
        except (OSError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio '{name}' could not be verified: {exc}") from exc

    def load_portfolio(
        self,
        name: str,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> RestoreReport:
        # [impl->req~ring5.portfolio.signed-manifests~1]
        """Load + restore a portfolio; the report says what was skipped.

        Args:
            name: Portfolio name.
            signing_key: Optional shared secret for signature verification.
            require_signature: Refuse restore unless that secret verifies a signature.

        Returns:
            A report describing restored and skipped content.

        Raises:
            PortfolioError: The portfolio does not exist.
            PortfolioVersionError: It was written by a newer RING-5.
        """
        data = self._read_portfolio_data(
            name,
            signing_key=signing_key,
            require_signature=require_signature,
        )
        try:
            return self.api.state_manager.restore_session(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio '{name}' could not be restored: {exc}") from exc

    def export_portfolio_bundle(
        self,
        name: str,
        *,
        snapshot_name: str | None = None,
        results: Mapping[str, bytes] | None = None,
        signing_key: str | bytes | None = None,
        signing_key_id: str = "default",
    ) -> bytes:
        # [impl->req~ring5.portfolio.portable-bundles~1]
        """Package a saved portfolio and reproducibility artifacts for transfer.

        The bundle always contains source provenance, environment metadata, and
        pinned Python requirements. A named exact dataset snapshot and generated
        result bytes are optional. Supplying ``signing_key`` signs the bundled
        portfolio copy without changing the saved portfolio.

        Args:
            name: Saved portfolio and bundle name.
            snapshot_name: Optional reusable dataset snapshot to include.
            results: Optional safe relative result names mapped to exact bytes.
            signing_key: Optional shared secret for the bundled portfolio signature.
            signing_key_id: Non-secret label stored with a new signature.

        Returns:
            Complete deterministic ``.ring5-bundle`` bytes.

        Raises:
            PortfolioError: Inputs are absent, invalid, modified, or exceed bundle limits.
        """
        try:
            return self.api.data_services.export_portfolio_bundle(
                name,
                snapshot_name=snapshot_name,
                results=results,
                signing_key=signing_key,
                signing_key_id=signing_key_id,
            )
        except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio bundle '{name}' could not be created: {exc}") from exc

    def inspect_portfolio_bundle(
        self,
        payload: bytes,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioBundleInfo:
        # [impl->req~ring5.portfolio.portable-bundles~1]
        """Validate and summarize a portable bundle without changing this session.

        Args:
            payload: Complete ``.ring5-bundle`` bytes.
            signing_key: Optional shared secret for its portfolio signature.
            require_signature: Require that secret to authenticate the portfolio.

        Returns:
            Artifact inventory, source/result counts, and integrity evidence.

        Raises:
            PortfolioError: The archive or any nested artifact fails validation.
        """
        try:
            return self.api.data_services.inspect_portfolio_bundle(
                payload,
                signing_key=signing_key,
                require_signature=require_signature,
            )
        except (OSError, TypeError, UnicodeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio bundle could not be inspected: {exc}") from exc

    def read_portfolio_bundle(
        self,
        payload: bytes,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioBundleContents:
        # [impl->req~ring5.portfolio.portable-bundles~1]
        """Read verified portfolio, snapshot, provenance, and result artifacts.

        Args:
            payload: Complete ``.ring5-bundle`` bytes.
            signing_key: Optional shared secret for its portfolio signature.
            require_signature: Require that secret to authenticate the portfolio.

        Returns:
            Verified content without restoring or writing any artifact.

        Raises:
            PortfolioError: The archive or any nested artifact fails validation.
        """
        try:
            return self.api.data_services.read_portfolio_bundle(
                payload,
                signing_key=signing_key,
                require_signature=require_signature,
            )
        except (OSError, TypeError, UnicodeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio bundle could not be read: {exc}") from exc

    def restore_portfolio_bundle(
        self,
        payload: bytes,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> RestoreReport:
        # [impl->req~ring5.portfolio.portable-bundles~1]
        """Verify a portable bundle and explicitly restore its portfolio.

        Args:
            payload: Complete ``.ring5-bundle`` bytes.
            signing_key: Optional shared secret for its portfolio signature.
            require_signature: Require that secret to authenticate the portfolio.

        Returns:
            Normal portfolio restore report. Bundled files are not written to disk.

        Raises:
            PortfolioError: Validation or restoration fails.
        """
        contents = self.read_portfolio_bundle(
            payload,
            signing_key=signing_key,
            require_signature=require_signature,
        )
        try:
            return self.api.state_manager.restore_session(contents.portfolio)
        except (KeyError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Portfolio bundle could not be restored: {exc}") from exc

    def list_portfolio_revisions(self, name: str) -> tuple[PortfolioRevisionInfo, ...]:
        # [impl->req~ring5.portfolio.history-diff~1]
        """List retained versions of a saved portfolio.

        Existing portfolios created before revision retention are captured as
        a baseline the first time they are listed.

        Args:
            name: Saved portfolio name.

        Returns:
            Immutable version summaries in save order.

        Raises:
            PortfolioError: Revision history could not be read.
        """
        try:
            return self.api.data_services.list_portfolio_revisions(name)
        except (OSError, TypeError, ValueError) as exc:
            raise PortfolioError(
                f"Portfolio history for '{name}' could not be read: {exc}"
            ) from exc

    def compare_portfolio_revisions(
        self,
        name: str,
        before_revision: str,
        after_revision: str,
    ) -> PortfolioDiff:
        # [impl->req~ring5.portfolio.history-diff~1]
        """Compare reviewable fields in two saved portfolio versions.

        Embedded data rows are deliberately excluded. The result groups leaf
        changes into data sources, pipelines, plots, and figure settings.

        Args:
            name: Saved portfolio name.
            before_revision: SHA-256 identity of the earlier version.
            after_revision: SHA-256 identity of the later version.

        Returns:
            Bounded field-level difference entries and section totals.

        Raises:
            PortfolioError: Either revision is missing, invalid, or unreadable.
            PortfolioVersionError: A revision uses a newer portfolio schema.
        """
        from src.core.services.portfolio_migrator import (
            PortfolioVersionError as CoreVersionError,
        )

        from ring5.errors import PortfolioVersionError

        try:
            return self.api.data_services.compare_portfolio_revisions(
                name,
                before_revision,
                after_revision,
            )
        except FileNotFoundError as exc:
            raise PortfolioError(str(exc)) from exc
        except CoreVersionError as exc:
            raise PortfolioVersionError(str(exc)) from exc
        except (OSError, TypeError, ValueError) as exc:
            raise PortfolioError(
                f"Portfolio revisions for '{name}' could not be compared: {exc}"
            ) from exc

    def restore_portfolio_revision(self, name: str, revision_id: str) -> RestoreReport:
        # [impl->req~ring5.portfolio.history-diff~1]
        """Restore one retained portfolio version into this session.

        Restoring does not replace the named portfolio on disk. Call
        :meth:`save_portfolio` explicitly if the restored state should become
        a new current version.

        Args:
            name: Saved portfolio name.
            revision_id: SHA-256 identity returned by
                :meth:`list_portfolio_revisions`.

        Returns:
            A report describing restored and skipped content.

        Raises:
            PortfolioError: The revision is unavailable or cannot be restored.
            PortfolioVersionError: The revision uses a newer portfolio schema.
        """
        data = self._read_portfolio_revision_data(name, revision_id)
        try:
            return self.api.state_manager.restore_session(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise PortfolioError(
                f"Portfolio revision for '{name}' could not be restored: {exc}"
            ) from exc

    # analysis recipes
    def capture_analysis_recipe(
        self,
        name: str,
        *,
        description: str = "",
        parameters: Sequence[RecipeParameter] = (),
        source: RecipeSource | None = None,
        transformations: Sequence[ShaperStepConfig] = (),
        exports: Sequence[RecipeExport] = (),
    ) -> AnalysisRecipe:
        """Capture this session's source, plots, and pipelines as a recipe.

        The active CSV path or parser provenance is used when ``source`` is
        omitted. Runtime placeholders use ``{{parameter_name}}`` in source
        paths, shaper values, plot configuration values, and export paths.

        Args:
            name: Stable recipe name.
            description: Human-readable purpose.
            parameters: Typed runtime placeholder declarations.
            source: Explicit source, or ``None`` to capture current provenance.
            transformations: Dataset-wide shapers applied before every plot.
            exports: Named-plot output instructions.

        Returns:
            A validated immutable recipe. Call :meth:`save_analysis_recipe`
            to retain it locally.

        Raises:
            RecipeError: Current provenance or recipe content is invalid.
        """
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        try:
            return self.api.data_services.capture_analysis_recipe(
                name,
                description=description,
                parameters=parameters,
                source=source,
                transformations=transformations,
                exports=exports,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def save_analysis_recipe(
        self,
        recipe: AnalysisRecipe,
        *,
        overwrite: bool = False,
    ) -> str:
        """Save a validated recipe without silent replacement.

        Args:
            recipe: Recipe returned by :meth:`capture_analysis_recipe` or
                constructed from the public recipe dataclasses.
            overwrite: Replace an existing recipe with the same name.

        Returns:
            Local saved JSON path.

        Raises:
            RecipeError: Validation or storage fails, or the name exists while
                ``overwrite`` is false.
        """
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        try:
            return self.api.data_services.save_analysis_recipe(recipe, overwrite=overwrite)
        except (OSError, TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def list_analysis_recipes(self) -> tuple[AnalysisRecipeInfo, ...]:
        """List readable saved recipes in case-insensitive name order.

        Returns:
            Immutable catalog entries with content counts and saved paths.
        """
        return self.api.data_services.list_analysis_recipes()

    def load_analysis_recipe(self, name: str) -> AnalysisRecipe:
        """Load and validate a saved recipe by logical name.

        Args:
            name: Exact saved recipe name.

        Returns:
            The immutable recipe.

        Raises:
            RecipeError: The recipe is missing, unreadable, or invalid.
        """
        try:
            return self.api.data_services.load_analysis_recipe(name)
        except (OSError, TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def delete_analysis_recipe(self, name: str) -> None:
        """Delete one saved recipe.

        Args:
            name: Exact saved recipe name.

        Raises:
            RecipeError: The recipe does not exist or cannot be deleted.
        """
        try:
            self.api.data_services.delete_analysis_recipe(name)
        except (OSError, TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def export_analysis_recipe(self, recipe: AnalysisRecipe) -> bytes:
        """Serialize a recipe as deterministic versioned UTF-8 JSON.

        Args:
            recipe: Valid recipe to serialize.

        Returns:
            Portable JSON bytes without timestamps or host-specific metadata.

        Raises:
            RecipeError: The recipe is invalid or exceeds safety limits.
        """
        try:
            return self.api.data_services.export_analysis_recipe(recipe)
        except (TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def decode_analysis_recipe(self, payload: str | bytes | bytearray) -> AnalysisRecipe:
        """Decode portable recipe JSON without saving or executing it.

        This read-only operation is intended for generated automation and
        callers that want to inspect a recipe before deciding whether to run
        or persist it.

        Args:
            payload: Versioned UTF-8 recipe JSON, limited to 512 KiB.

        Returns:
            The validated immutable recipe.

        Raises:
            RecipeError: The document is invalid or unsupported.
        """
        # [impl->req~ring5.automation.script-notebook-export~1]
        try:
            return self.api.data_services.decode_analysis_recipe(payload)
        except (TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def export_analysis_recipe_script(self, recipe: AnalysisRecipe) -> bytes:
        """Generate a documented command-line Python script for a recipe.

        The deterministic UTF-8 script embeds the canonical recipe, exposes
        each runtime parameter as a typed option, and imports only the public
        :mod:`ring5` package plus Python's standard library.

        Args:
            recipe: Valid recipe to reproduce.

        Returns:
            Executable Python source bytes.

        Raises:
            RecipeError: The recipe is invalid or exceeds safety limits.
        """
        # [impl->req~ring5.automation.script-notebook-export~1]
        try:
            return self.api.data_services.export_analysis_recipe_script(recipe)
        except (TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def export_analysis_recipe_notebook(self, recipe: AnalysisRecipe) -> bytes:
        """Generate a documented Jupyter notebook for a recipe.

        The deterministic notebook needs no notebook-writing dependency. It
        embeds the canonical recipe, provides an editable parameter cell, and
        uses only the supported :mod:`ring5` API for application work.

        Args:
            recipe: Valid recipe to reproduce.

        Returns:
            UTF-8 Jupyter notebook JSON bytes.

        Raises:
            RecipeError: The recipe is invalid or exceeds safety limits.
        """
        # [impl->req~ring5.automation.script-notebook-export~1]
        try:
            return self.api.data_services.export_analysis_recipe_notebook(recipe)
        except (TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def import_analysis_recipe(
        self,
        payload: str | bytes | bytearray,
        *,
        overwrite: bool = False,
    ) -> AnalysisRecipe:
        """Validate and save one portable recipe JSON document.

        Args:
            payload: Versioned UTF-8 recipe JSON, limited to 512 KiB.
            overwrite: Replace an existing recipe with the same name.

        Returns:
            The imported immutable recipe.

        Raises:
            RecipeError: The document is invalid, unsupported, or conflicts
                with an existing saved recipe.
        """
        try:
            return self.api.data_services.import_analysis_recipe(payload, overwrite=overwrite)
        except (OSError, TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def materialize_analysis_recipe(
        self,
        recipe: AnalysisRecipe,
        values: Mapping[str, RecipeScalar] | None = None,
    ) -> AnalysisRecipe:
        """Resolve typed runtime values without executing a recipe.

        Args:
            recipe: Recipe containing declared placeholders.
            values: Runtime values keyed by parameter name. Missing values use
                declared defaults.

        Returns:
            A fully concrete recipe suitable for review or execution.

        Raises:
            RecipeError: Values are missing, unknown, mistyped, or invalid.
        """
        try:
            return self.api.data_services.materialize_analysis_recipe(recipe, values)
        except (KeyError, TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def run_analysis_recipe(
        self,
        recipe: AnalysisRecipe | str,
        values: Mapping[str, RecipeScalar] | None = None,
    ) -> AnalysisRecipeRunResult:
        """Execute a recipe in this session and write its configured exports.

        CSV recipes load their source directly. Parser recipes use the normal
        owned scan/parse job lifecycle before applying dataset-wide and
        per-plot shapers. Plot mappings are validated before existing session
        plots are replaced.

        Args:
            recipe: Recipe object or exact locally saved recipe name.
            values: Typed runtime values keyed by parameter name.

        Returns:
            Dataset dimensions, created plot names, resolved parameters, and
            written export paths.

        Raises:
            RecipeError: Loading, materialization, or source access fails.
            ScanError: Parser-source discovery fails.
            ParseError: Parser-source execution fails.
            PipelineError: A transformation fails.
            DataValidationError: A plot mapping is invalid for transformed data.
            ExportError: Rendering or writing an export fails.
        """
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        definition = self.load_analysis_recipe(recipe) if isinstance(recipe, str) else recipe
        materialized = self.materialize_analysis_recipe(definition, values)
        resolved_values = tuple(
            (
                parameter.name,
                cast(
                    RecipeScalar,
                    (values or {}).get(parameter.name, parameter.default),
                ),
            )
            for parameter in definition.parameters
        )

        source = materialized.source
        try:
            if source.kind == "csv":
                data = self.api.data_services.load_csv_file(source.path)
                source_path = source.path
            else:
                parser_variables = _recipe_stat_configs(source.variables)
                parsed = self.parse(
                    source.path,
                    cast(list[str | StatConfig], parser_variables),
                    pattern=source.pattern,
                    strategy=source.strategy,
                    scan_limit=source.scan_limit,
                    strict=source.strict,
                )
                source_path = parsed.csv_path
                data = self.api.data_services.load_csv_file(parsed.csv_path)
        except (OSError, TypeError, UnicodeError, ValueError) as exc:
            raise RecipeError(f"Could not load recipe source {source.path!r}: {exc}") from exc

        transformed = cast(
            pd.DataFrame,
            self.shape(data, list(materialized.transformations)),
        )
        prepared: list[tuple[RecipePlot, pd.DataFrame]] = []
        for plot_spec in materialized.plots:
            plot_data = cast(
                pd.DataFrame,
                self.shape(transformed, list(plot_spec.pipeline)),
            )
            resolved_type = _resolve_plot_type(plot_spec.plot_type)
            validate_plot_config(resolved_type, plot_data, dict(plot_spec.config))
            prepared.append((plot_spec, plot_data))

        state = self.api.state_manager
        for existing in state.get_plots():
            state.remove_visualization_config(existing.plot_id)
        state.set_plots([])
        state.set_plot_counter(0)
        state.set_current_plot_id(None)
        state.set_data(transformed, operation=f"Run analysis recipe: {materialized.name}")
        state.set_processed_data(None)
        state.set_csv_path(source_path)
        state.set_use_parser(source.kind == "parser")

        created: dict[str, BasePlot] = {}
        for plot_spec, plot_data in prepared:
            plot = self.create_plot(
                plot_spec.plot_type,
                data=plot_data,
                config=plot_spec.config,
                name=plot_spec.name,
            )
            plot.pipeline = [
                {"id": index, "type": config["type"], "config": copy.deepcopy(config)}
                for index, config in enumerate(plot_spec.pipeline)
            ]
            plot.pipeline_counter = len(plot.pipeline)
            plot.replace_source_data(transformed)
            created[plot_spec.name] = plot

        exported: list[str] = []
        figures: dict[tuple[str, str], _render.Figure] = {}
        for export in materialized.exports:
            key = (export.plot, export.engine)
            figure = figures.get(key)
            if figure is None:
                figure = self.render(created[export.plot], engine=export.engine)
                figures[key] = figure
            exported.append(
                self.export(
                    figure,
                    export.path,
                    fmt=export.format,
                    deterministic=export.deterministic,
                )
            )

        return AnalysisRecipeRunResult(
            recipe_name=materialized.name,
            parameter_values=resolved_values,
            rows=len(transformed),
            columns=tuple(str(column) for column in transformed.columns),
            plot_names=tuple(created),
            exported_paths=tuple(exported),
        )

    def run_analysis_recipe_matrix(
        self,
        recipe: AnalysisRecipe | str,
        matrix: Mapping[str, Sequence[RecipeScalar]],
        *,
        output_directory: str = "ring5-batch-output",
        max_workers: int = 2,
    ) -> AnalysisRecipeMatrixResult:
        """Execute the Cartesian product of typed recipe parameter values.

        Each case runs in an isolated session. Results retain recipe parameter
        order regardless of completion order, and exports are redirected to a
        stable ``case-NNN-<digest>`` directory beneath ``output_directory``.

        Args:
            recipe: Recipe object or exact locally saved recipe name.
            matrix: Parameter names mapped to ordered value sequences. Omitted
                parameters use recipe defaults.
            output_directory: Root for collision-free per-case exports.
            max_workers: Concurrency bound from one through eight.

        Returns:
            Ordered case outcomes, including bounded per-case failures.

        Raises:
            RecipeError: The recipe, matrix, output path, or worker bound is invalid.
        """
        # [impl->req~ring5.automation.batch-matrices~1]
        from src.core.services.analysis_recipe_matrix_service import (
            AnalysisRecipeMatrixService,
        )

        definition = self.load_analysis_recipe(recipe) if isinstance(recipe, str) else recipe

        def run_case(
            case_recipe: AnalysisRecipe,
            values: Mapping[str, RecipeScalar],
        ) -> AnalysisRecipeRunResult:
            with Session(parser=self._parser_override) as child:
                return child.run_analysis_recipe(case_recipe, values)

        try:
            return AnalysisRecipeMatrixService.execute(
                definition,
                matrix,
                output_directory,
                run_case,
                max_workers=max_workers,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RecipeError(str(exc)) from exc

    def run_analysis_recipe_matrix_submit(
        self,
        recipe: AnalysisRecipe | str,
        matrix: Mapping[str, Sequence[RecipeScalar]],
        *,
        output_directory: str = "ring5-batch-output",
        max_workers: int = 2,
        label: str | None = None,
    ) -> BackgroundJobInfo:
        """Submit a bounded recipe matrix to this session's background jobs.

        Poll :meth:`background_jobs`, then pass its completed record to
        :meth:`background_job_result` to obtain an
        :class:`AnalysisRecipeMatrixResult`.

        Args:
            recipe: Recipe object or exact locally saved recipe name.
            matrix: Parameter names mapped to ordered value sequences.
            output_directory: Root for collision-free per-case exports.
            max_workers: Concurrency bound from one through eight.
            label: Optional human-readable job-center label.

        Returns:
            Initial immutable background-job snapshot.

        Raises:
            RecipeError: A saved recipe cannot be loaded.
            JobError: Submission metadata or the job center is invalid.
        """
        # [impl->req~ring5.automation.batch-matrices~1]
        definition = self.load_analysis_recipe(recipe) if isinstance(recipe, str) else recipe
        captured_recipe = copy.deepcopy(definition)
        captured_matrix = copy.deepcopy(matrix)
        selected_label = label or f"Recipe matrix: {definition.name}"
        try:
            return self.api.submit_background_operation(
                "transformation",
                selected_label,
                lambda: self.run_analysis_recipe_matrix(
                    captured_recipe,
                    captured_matrix,
                    output_directory=output_directory,
                    max_workers=max_workers,
                ),
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            raise JobError(str(exc)) from exc


def _require_columns(data: pd.DataFrame, columns: list[str]) -> None:
    """Raise the typed missing-column error before delegating to core."""
    for col in columns:
        if col not in data.columns:
            raise ColumnNotFoundError(col, list(data.columns))


def _recipe_stat_configs(
    variables: Sequence[ParseVariableConfig],
) -> list[StatConfig]:
    """Convert captured parser-variable dictionaries without losing metadata."""
    from src.core.models.pattern_index_service import PatternIndexService

    configs: list[StatConfig] = []
    for variable in variables:
        source_name = variable["name"]
        alias = variable.get("alias")
        output_name = alias or source_name
        try:
            repeat = int(variable.get("repeat", 1))
        except (TypeError, ValueError) as exc:
            raise RecipeError(
                f"Parser variable {source_name!r} has invalid repeat metadata."
            ) from exc
        configs.append(
            StatConfig(
                name=output_name,
                source_name=source_name if alias else None,
                type=str(variable["type"]).lower(),
                repeat=repeat,
                params=cast(dict[str, Any], copy.deepcopy(dict(variable))),
                statistics_only=bool(variable.get("statisticsOnly", False)),
                is_regex=PatternIndexService.is_pattern_variable(source_name),
                keep_indices=bool(variable.get("keepIndices", False)),
            )
        )
    return configs
