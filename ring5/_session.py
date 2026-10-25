"""Headless workspace for parsing, shaping, plotting, and portfolio replay."""

from __future__ import annotations

import copy
import shutil
import tempfile
import threading
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
from matplotlib.figure import Figure as MplFigure

from src.core.application_api import ApplicationAPI
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.accessibility_models import AccessibilityReport
from src.core.models.report_models import AnalysisReport, ReportFigure
from src.core.models.recipe_models import (
    AnalysisRecipe,
    AnalysisRecipeInfo,
    AnalysisRecipeRunResult,
    RecipeExport,
    RecipeParameter,
    RecipePlot,
    RecipeScalar,
    RecipeSource,
)
from src.core.models.recipe_matrix_models import AnalysisRecipeMatrixResult
from src.core.models.background_job_models import BackgroundJobInfo
from src.core.models.semantic_metadata_models import ColumnSemantics, DatasetSemantics
from src.core.models.quality_models import DataQualityReport
from src.core.models.visualization.dashboard_spec import DashboardSpec
from src.core.models.dataset_workspace_models import (
    DatasetInfo,
    DatasetLineage,
    DatasetRevision,
    DatasetSnapshotInfo,
    JoinCardinality,
    JoinDiagnostics,
)
from src.core.models.schema_contract_models import DatasetSchemaContract, SchemaValidationReport
from src.core.models.environment_models import EnvironmentComparison, EnvironmentMetadata
from src.core.models.figure_theme_models import FigureTheme
from src.core.models.import_models import ImportColumnCorrection, ImportOptions, ImportPreview
from src.core.models.parsing_models import (
    IncrementalParseBatchResult,
    ParseBatchResult,
    ScanResult,
    StatConfig,
)
from src.core.models.visualization.linked_selection_spec import LinkedSelectionSpec
from src.core.models.data_models import PipelineConfigConflictPolicy, PipelineConfigImportResult
from src.core.models.visualization.plot_configuration_comparison import PlotConfigurationComparison
from src.core.models.visualization.plot_transfer_result import PlotTransferMode, PlotTransferResult
from src.core.models.portfolio_models import PortfolioData, RestoreReport
from src.core.models.portfolio_bundle_models import PortfolioBundleContents, PortfolioBundleInfo
from src.core.models.portfolio_revision_models import PortfolioDiff, PortfolioRevisionInfo
from src.core.models.portfolio_integrity_models import PortfolioIntegrityReport
from src.core.models.visualization.small_multiples_spec import SmallMultiplesSpec
from src.core.models.scheduled_report_models import ScheduledReportResult
from src.core.models.workspace_search_models import WorkspaceSearchResponse
from src.core.models.workspace_command_models import WorkspaceCommandSearchResponse
from src.core.models.workspace_metadata_models import (
    WorkspaceArtifact,
    WorkspaceArtifactKind,
    WorkspaceArtifactResponse,
)
from src.core.models.analysis_review_models import (
    AnalysisReviewResponse,
    AnalysisReviewStatus,
    AnalysisReviewTargetKind,
    AnalysisReviewTargetResponse,
    AnalysisReviewThread,
)

from src.core.models.recovery_models import RecoveryDraftCapture, RecoveryDraftInfo
from src.core.models.guided_analysis_models import GuidedAnalysisProgress
from src.core.models.visualization.engine import EngineMode
from src.core.models.visualization.export_options import TexSystem, validate_tex_system
from src.parsing.parser_protocol import SimulationParser
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.rendering._matplotlib_copy import copy_matplotlib_figure
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
    Ring5Error,
)
from ring5.figure_spec import FigureSpec
from ring5.data import DrillDownResult, Table
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


def _require_table(data: Table, error_type: type[Ring5Error] = DataValidationError) -> Table:
    """Require the declared handle before invoking any pandas interoperability."""
    if not isinstance(data, Table):
        raise error_type(
            "Data must be a ring5.Table. Use Table(frame) for explicit pandas interoperability."
        )
    return data


def _table_frame(data: Table, error_type: type[Ring5Error] = DataValidationError) -> pd.DataFrame:
    """Return an owned frame from the declared public data handle."""
    return _require_table(data, error_type).frame


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
    """Validate an exact registered plot identifier."""
    from src.web.pages.ui.plotting.plot_factory import PlotFactory

    available = PlotFactory.get_available_plot_types()
    if plot_type in available:
        return plot_type

    choices = ", ".join(available)
    raise DataValidationError(f"Unknown plot type {plot_type!r}. Available types: {choices}.")


class Session:
    # [impl->req~ring5.api.session~1]
    """A headless RING-5 workspace.

    Mirrors what one browser session of the web app can do — parse, shape,
    plot, render, export, snapshot — as plain method calls::

        with ring5.Session() as s:
            csv = s.parse("/sims", variables=["simTicks"]).csv_path
            data = s.load(csv)
            data = s.reduce_seeds(data, ["config_description_abbrev"], ["simTicks"])
            fig = s.plot("bar", data=data,
                         config={"x": "config_description_abbrev",
                                 "y": "simTicks"},
                         engine="matplotlib")
            s.export(fig, "out/simticks.pdf")

    Declared data methods accept and return :class:`ring5.Table`. The full
    :class:`ApplicationAPI` remains available as ``session.api`` for explicit advanced
    Core interoperability, including its pandas-based state and service contracts.
    """

    def __init__(self, *, parser: SimulationParser | None = None) -> None:
        # Headless portfolio restores need the web composition root's plot deserializer.
        self.api = ApplicationAPI(plot_deserializer=PlotFactory.from_dict, parser=parser)
        self._parser_override = parser
        # Temporary parse output is removed when the session closes.
        self._owned_tmpdirs: list[str] = []
        self._parse_jobs: list[_parse.ParseJob | _parse.ParserPlaygroundJob] = []
        self._incremental_output_dirs: dict[tuple[str, str, str, str], str] = {}
        self._guided_comparison_ready = False
        self._guided_rendered_plot_ids: set[int] = set()
        self._guided_exported = False

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
        self.api.close()

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
        try:
            configs, scanned = _parse.build_stat_configs(
                self.api, stats_path, variables, pattern=pattern, scan_limit=scan_limit
            )
        except (TypeError, ValueError) as exc:
            raise ParseError(f"Invalid statistic configuration: {exc}") from exc
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
                configs,
                out_dir,
                strategy_type=strategy,
                scanned_vars=scanned,
            )
        except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError) as exc:
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
        try:
            configs, scanned = _parse.build_stat_configs(
                self.api, stats_path, variables, pattern=pattern, scan_limit=scan_limit
            )
        except (TypeError, ValueError) as exc:
            raise ParseError(f"Invalid statistic configuration: {exc}") from exc
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
                    configs,
                    out_dir,
                    strategy_type=strategy,
                    scanned_vars=scanned,
                    cache_path=cache_path,
                )
            else:
                batch = self.api.submit_parse_async(
                    stats_path,
                    pattern,
                    configs,
                    out_dir,
                    strategy_type=strategy,
                    scanned_vars=scanned,
                )
        except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
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
        sm.set_parse_variables([StatConfigCodec.to_draft(config) for config in configs])
        sm.set_scanned_variables([variable.to_dict() for variable in scanned])
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
    def load(self, csv_path: str) -> Table:
        """Load a CSV into the session.

        Args:
            csv_path: CSV file to load.

        Returns:
            The loaded table.

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
        return Table(data)

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

    def load_import(self, preview: ImportPreview) -> Table:
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
            return Table(self.api.load_import_preview(preview))
        except (OSError, TypeError, UnicodeError, ValueError) as exc:
            raise DataLoadError(f"Could not load reviewed import: {exc}") from exc

    def add_dataset(
        self,
        name: str,
        data: "Table",
        *,
        select: bool = True,
        replace: bool = False,
    ) -> DatasetInfo:
        """Retain a named dataset in this session without replacing others.

        Args:
            name: Human-readable session-unique name.
            data: A :class:`ring5.Table` retained by defensive copy.
            select: Make this dataset the active source-data view.
            replace: Permit replacement of the same name.

        Returns:
            Immutable dataset metadata.

        Raises:
            DataValidationError: The name is invalid or already exists.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        frame = _table_frame(data)
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

    def search_workspace(self, query: str, *, limit: int = 20) -> WorkspaceSearchResponse:
        """Search every discoverable item in the current workspace.

        The case-insensitive index includes configured and scanned variables,
        named datasets, plots, pipeline steps, saved portfolios, navigation
        commands, and published documentation. Results contain typed locations
        and identifiers but do not mutate the active workspace.

        Args:
            query: Up to 200 characters; multiple terms use AND matching.
            limit: Maximum returned matches, from 1 through 100.

        Returns:
            Ranked matches plus explicit result and index truncation metadata.

        Raises:
            DataValidationError: The query or result limit is invalid.
        """
        # [impl->req~ring5.workspace.global-search~1]
        try:
            return self.api.search_workspace(query, limit=limit)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def search_workspace_commands(
        self,
        query: str = "",
        *,
        limit: int = 20,
    ) -> WorkspaceCommandSearchResponse:
        """List or search the safe commands exposed by the web workspace.

        Args:
            query: Optional case-insensitive task or destination terms.
            limit: Maximum returned commands, from 1 through 100.

        Returns:
            Matching commands and explicit result truncation metadata.

        Raises:
            DataValidationError: The query or result limit is invalid.
        """
        # [impl->req~ring5.workspace.command-palette~1]
        try:
            return self.api.search_workspace_commands(query, limit=limit)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def list_workspace_artifacts(
        self,
        *,
        kind: WorkspaceArtifactKind | None = None,
        tags: Sequence[str] = (),
        favorites_only: bool = False,
        limit: int = 100,
    ) -> WorkspaceArtifactResponse:
        """Filter variables, datasets, plots, pipelines, and portfolios.

        Args:
            kind: Optional artifact kind to retain.
            tags: Canonical case-insensitive tags that must all match.
            favorites_only: Return only artifacts marked as favorites.
            limit: Maximum returned artifacts, from 1 through 100.

        Returns:
            Bounded matching artifacts and all tags currently available.

        Raises:
            DataValidationError: A filter or retained metadata document is invalid.
        """
        # [impl->req~ring5.workspace.favorites-tags~1]
        try:
            return self.api.list_workspace_artifacts(
                kind=kind,
                tags=tags,
                favorites_only=favorites_only,
                limit=limit,
            )
        except (OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def set_workspace_artifact_metadata(
        self,
        kind: WorkspaceArtifactKind,
        identifier: str,
        *,
        tags: Sequence[str] = (),
        favorite: bool = False,
    ) -> WorkspaceArtifact:
        """Replace tags and favorite state for one discoverable artifact.

        Tags are normalized to lower case and may contain letters, numbers,
        spaces, underscores, and hyphens. Clearing the tags and favorite state
        removes the stored marker.

        Args:
            kind: Kind of workspace artifact to update.
            identifier: Stable identifier of a discoverable artifact.
            tags: Replacement tags, normalized case-insensitively.
            favorite: Whether the artifact should be marked as a favorite.

        Returns:
            The artifact with its updated metadata.

        Raises:
            DataValidationError: The target or metadata is invalid.
        """
        # [impl->req~ring5.workspace.favorites-tags~1]
        try:
            return self.api.set_workspace_artifact_metadata(
                kind,
                identifier,
                tags=tags,
                favorite=favorite,
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def list_analysis_review_targets(
        self,
        *,
        kind: AnalysisReviewTargetKind | None = None,
        limit: int = 100,
    ) -> AnalysisReviewTargetResponse:
        """Discover plots and exact saved portfolio versions that can be reviewed.

        Args:
            kind: Optional plot or portfolio-revision target filter.
            limit: Maximum returned targets, from 1 through 100.

        Returns:
            Bounded targets with transparent indexing and truncation totals.

        Raises:
            DataValidationError: The filter or retained revision data is invalid.
        """
        # [impl->req~ring5.workspace.collaborative-review~1]
        try:
            return self.api.list_analysis_review_targets(kind=kind, limit=limit)
        except (OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def list_analysis_reviews(
        self,
        *,
        kind: AnalysisReviewTargetKind | None = None,
        status: AnalysisReviewStatus | None = None,
        limit: int = 100,
    ) -> AnalysisReviewResponse:
        """List portable authored comments and review-status histories.

        Args:
            kind: Optional plot or portfolio-revision target filter.
            status: Optional current review status filter.
            limit: Maximum returned threads, from 1 through 100.

        Returns:
            Bounded review threads with current status totals.

        Raises:
            DataValidationError: A filter or portable review document is invalid.
        """
        # [impl->req~ring5.workspace.collaborative-review~1]
        try:
            return self.api.list_analysis_reviews(kind=kind, status=status, limit=limit)
        except (OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def record_analysis_review(
        self,
        kind: AnalysisReviewTargetKind,
        identifier: str,
        *,
        author_id: str,
        comment: str = "",
        status: AnalysisReviewStatus | None = None,
        portfolio_name: str | None = None,
    ) -> AnalysisReviewThread:
        """Append an authored, timestamped review update to an exact target.

        Review histories are included when this session is saved as a portfolio
        or portable bundle. Existing events remain append-only.

        Args:
            kind: Plot or immutable portfolio-revision target kind.
            identifier: Plot ID or exact SHA-256 portfolio revision ID.
            author_id: Human or service identifier responsible for the update.
            comment: Optional review comment, limited to 4,000 characters.
            status: Optional replacement review status.
            portfolio_name: Required only for a portfolio-revision target.

        Returns:
            The complete updated review thread.

        Raises:
            DataValidationError: The target or review update is invalid.
        """
        # [impl->req~ring5.workspace.collaborative-review~1]
        try:
            return self.api.record_analysis_review(
                kind,
                identifier,
                author_id=author_id,
                comment=comment,
                status=status,
                portfolio_name=portfolio_name,
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def create_recovery_draft(self, owner_key: str) -> RecoveryDraftCapture | None:
        """Capture meaningful workspace state in a private bounded local draft.

        Args:
            owner_key: Secret namespace key retained by the caller, never stored raw.

        Returns:
            Capture details, or ``None`` when the workspace is still empty.

        Raises:
            PortfolioError: The key, state, or local recovery storage is invalid.
        """
        # [impl->req~ring5.workspace.autosave-recovery~1]
        try:
            return self.api.create_recovery_draft(owner_key)
        except (OSError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Recovery draft could not be created: {exc}") from exc

    def list_recovery_drafts(self, owner_key: str) -> tuple[RecoveryDraftInfo, ...]:
        """List private local recovery points newest first.

        Args:
            owner_key: Same secret namespace key used while capturing.

        Returns:
            Bounded draft metadata without loading embedded workspace data.

        Raises:
            PortfolioError: The key or local recovery storage is invalid.
        """
        # [impl->req~ring5.workspace.autosave-recovery~1]
        try:
            return self.api.list_recovery_drafts(owner_key)
        except (OSError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Recovery drafts could not be listed: {exc}") from exc

    def restore_recovery_draft(self, owner_key: str, draft_id: str) -> RestoreReport:
        """Explicitly verify and restore one private local recovery point.

        Args:
            owner_key: Same secret namespace key used while capturing.
            draft_id: Exact identifier returned by :meth:`list_recovery_drafts`.

        Returns:
            Structured report of restored and skipped state.

        Raises:
            PortfolioError: The draft is absent, modified, invalid, or cannot be restored.
        """
        # [impl->req~ring5.workspace.autosave-recovery~1]
        try:
            return self.api.restore_recovery_draft(owner_key, draft_id)
        except (FileNotFoundError, KeyError, OSError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Recovery draft could not be restored: {exc}") from exc

    def delete_recovery_draft(self, owner_key: str, draft_id: str) -> None:
        """Delete one exact private local recovery point.

        Args:
            owner_key: Same secret namespace key used while capturing.
            draft_id: Exact identifier returned by :meth:`list_recovery_drafts`.

        Raises:
            PortfolioError: The draft is absent or cannot be safely removed.
        """
        try:
            self.api.delete_recovery_draft(owner_key, draft_id)
        except (FileNotFoundError, OSError, TypeError, ValueError) as exc:
            raise PortfolioError(f"Recovery draft could not be deleted: {exc}") from exc

    def guided_analysis_progress(self) -> GuidedAnalysisProgress:
        """Return progress through source, validation, comparison, plot, and export work.

        Progress is inferred from successful operations in this session. Calling
        :meth:`compare` or :meth:`compare_statistics`, :meth:`render`, and an
        export method advances their corresponding milestones. The result does
        not change the workspace or limit access to lower-level methods.

        Returns:
            Immutable ordered stages, completion count, percentage, and next stage.
        """
        # [impl->req~ring5.workspace.guided-analysis~1]
        from src.core.services.guided_analysis_service import GuidedAnalysisService

        plots = self.api.state_manager.get_plots()
        comparison_ready = self._guided_comparison_ready or self.api.state_manager.has_preview(
            "regression_comparison"
        )
        rendered_ids = self._guided_rendered_plot_ids | {
            plot.plot_id for plot in plots if plot.render_state.snapshot() is not None
        }
        return GuidedAnalysisService.assess(
            self.api.state_manager.get_data(),
            comparison_ready=comparison_ready,
            plot_count=len(plots),
            rendered_plot_count=sum(plot.plot_id in rendered_ids for plot in plots),
            exported=self._guided_exported,
        )

    def get_dataset(self, name: str | None = None) -> Table:
        """Return a defensive copy of a named or selected dataset.

        Args:
            name: Dataset name, or ``None`` for the selected dataset.

        Returns:
            A newly allocated table.

        Raises:
            DataValidationError: No dataset is selected or the name is unknown.
        """
        # [impl->req~ring5.data.multi-dataset-workspace~1]
        try:
            return Table(self.api.get_dataset(name))
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def select_dataset(self, name: str) -> Table:
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
            return Table(self.api.select_dataset(name))
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

    def get_dataset_revision(self, revision_id: str) -> Table:
        """Return a defensive copy of one immutable dataset revision.

        Args:
            revision_id: Revision identifier from :meth:`dataset_lineage`.

        Raises:
            DataValidationError: The revision identifier is invalid or unknown.
        """
        # [impl->req~ring5.data.lineage-undo-redo~1]
        try:
            return Table(self.api.get_dataset_revision(revision_id))
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
    ) -> Table:
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
            return Table(
                self.api.append_datasets(
                    list(dataset_names),
                    output_name,
                    join=join,
                    select=select,
                    replace=replace,
                )
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
    ) -> Table:
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
            return Table(
                self.api.join_datasets(
                    left_name,
                    right_name,
                    output_name,
                    list(on),
                    how=how,
                    suffixes=suffixes,
                    select=select,
                    replace=replace,
                )
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
    ) -> tuple[Table, JoinDiagnostics]:
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
            frame, diagnostics = self.api.join_datasets_validated(
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
            return Table(frame), diagnostics
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
    ) -> Table:
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
            return Table(
                self.api.compare_datasets(
                    baseline_name,
                    candidate_name,
                    list(key_columns),
                    list(metric_columns),
                    directions=directions,
                    thresholds=thresholds,
                    threshold_mode=threshold_mode,
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def profile_data(
        self,
        data: "Table",
        *,
        expected_types: (
            Mapping[str, Literal["numeric", "integer", "boolean", "datetime", "string"]] | None
        ) = None,
    ) -> DataQualityReport:
        """Inspect dataset completeness, consistency, outliers, and expected types.

        Args:
            data: A :class:`ring5.Table` to inspect without mutation.
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
        frame = _table_frame(data)
        try:
            return self.api.managers.profile_data(frame, expected_types=expected_types)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def infer_schema_contract(
        self,
        data: "Table",
        *,
        name: str = "dataset",
    ) -> DatasetSchemaContract:
        """Infer an editable schema contract from current column types and nullability.

        Args:
            data: A :class:`ring5.Table` to inspect without mutation.
            name: Human-readable contract name.

        Returns:
            An immutable contract with one :class:`ring5.ColumnContract` per column.

        Raises:
            DataValidationError: The dataset or contract name is invalid.
        """
        # [impl->req~ring5.data.schema-contracts~1]
        frame = _table_frame(data)
        try:
            return self.api.managers.infer_schema_contract(frame, name=name)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def validate_schema(
        self,
        data: "Table",
        contract: DatasetSchemaContract,
    ) -> SchemaValidationReport:
        """Validate a dataset against required columns and per-column rules.

        Args:
            data: A :class:`ring5.Table` to validate without mutation.
            contract: Explicit dataset schema contract.

        Returns:
            Immutable rule failures with bounded row-position evidence.

        Raises:
            DataValidationError: The dataset or contract is invalid.
        """
        # [impl->req~ring5.data.schema-contracts~1]
        frame = _table_frame(data)
        try:
            return self.api.managers.validate_schema(frame, contract)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def apply_semantics(
        self,
        data: "Table",
        semantics: DatasetSemantics | DatasetSchemaContract,
    ) -> "Table":
        """Return a table that retains human labels and physical units.

        A schema contract may be supplied directly; its ``semantic_label`` and
        ``unit`` fields become the retained metadata. This operation does not
        run contract validation or mutate the input.

        Args:
            data: A :class:`ring5.Table` to annotate.
            semantics: Explicit metadata or the schema contract that declares it.

        Raises:
            DataValidationError: Metadata names or units are invalid.
        """
        # [impl->req~ring5.data.semantic-units~1]
        frame = _table_frame(data)
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
        return Table(result)

    def inspect_semantics(
        self,
        data: "Table",
    ) -> DatasetSemantics:
        """Return the ordered semantic labels and units retained by a table.

        Args:
            data: A :class:`ring5.Table` to inspect without mutation.

        Returns:
            Immutable ordered semantic metadata.

        Raises:
            DataValidationError: Retained external metadata is malformed.
        """
        # [impl->req~ring5.data.semantic-units~1]
        frame = _table_frame(data)
        try:
            return self.api.managers.inspect_semantics(frame)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def convert_unit(
        self,
        data: "Table",
        column: str,
        target_unit: str,
    ) -> "Table":
        """Convert one numeric column and retain its new canonical unit.

        Conversion is allowed only when the source unit is declared and both
        units describe the same dimension. The input remains unchanged.

        Args:
            data: A :class:`ring5.Table` carrying source-unit metadata.
            column: Numeric column to convert.
            target_unit: Compatible canonical unit.

        Returns:
            A new table containing the converted data.

        Raises:
            DataValidationError: The column, source unit, target unit, or values are invalid.
        """
        # [impl->req~ring5.data.semantic-units~1]
        frame = _table_frame(data)
        try:
            result = self.api.managers.convert_unit(frame, column, target_unit)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return Table(result)

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
        try:
            return AccessibilityService.apply_defaults(enabled, plot_type.strip())
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

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
        pipeline: Sequence[Mapping[str, object]],
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
            return self.api.data_services.export_configuration(
                name, description, pipeline, csv_path
            )
        except (TypeError, ValueError) as exc:
            raise PipelineError(str(exc)) from exc

    def import_pipeline_configuration(
        self,
        payload: str | bytes | bytearray,
        *,
        conflict: PipelineConfigConflictPolicy = "error",
    ) -> PipelineConfigImportResult:
        """Validate and save one current portable pipeline configuration.

        Args:
            payload: Current versioned UTF-8 JSON text or bytes, limited to 256 KiB.
            conflict: Logical-name policy: ``"error"``, ``"rename"``, or
                ``"replace"``.

        Returns:
            Saved configuration and conflict details.

        Raises:
            PipelineError: The document is invalid, unsupported, or conflicts
                with an existing record under the selected policy.
        """
        # [impl->req~ring5.shaping.config-import-export~1]
        try:
            return self.api.data_services.import_configuration(payload, conflict=conflict)
        except (OSError, TypeError, ValueError) as exc:
            raise PipelineError(str(exc)) from exc

    def shape(self, data: "Table", pipeline: Sequence[Mapping[str, object]]) -> "Table":
        """Run a shaper pipeline; failures carry the step index and type.

        Figure scripts express transformations with registered configurations and owned tables.

        Args:
            data: Input :class:`ring5.Table`.
            pipeline: Ordered configuration mappings for built-in or registered plugin shapers.

        Returns:
            A new table containing the shaped data.
        """
        from src.core.services.shapers.pipeline_service import PipelineStepError

        frame = _table_frame(data, PipelineError)
        try:
            shaped = self.api.shapers.process_pipeline(frame, pipeline)
            return Table(shaped)
        except PipelineStepError as exc:
            raise PipelineError(
                str(exc), step_index=exc.step_index, shaper_type=exc.shaper_type
            ) from exc
        except (TypeError, ValueError) as exc:
            raise PipelineError(str(exc)) from exc

    def shape_submit(
        self,
        data: "Table",
        pipeline: Sequence[Mapping[str, object]],
        *,
        label: str = "Shape data",
    ) -> BackgroundJobInfo:
        # [impl->req~ring5.workspace.background-jobs~1]
        """Submit a shaper pipeline without blocking the calling thread.

        The full pipeline is validated before submission. Input data and admitted configurations
        are defensively copied before background work starts.
        Poll :meth:`background_jobs`, then pass the finished record to
        :meth:`background_job_result`.

        Args:
            data: Input :class:`ring5.Table`.
            pipeline: Ordered configuration mappings for built-in or registered plugin shapers.
            label: Human-readable job-center label.

        Returns:
            Initial immutable job snapshot.

        Raises:
            JobError: Submission metadata or the session job center is invalid.
        """
        source = _require_table(data, JobError)
        try:
            captured_pipeline = self.api.shapers.validate_pipeline(pipeline)
            captured_data = Table(source.frame)
            return self.api.submit_background_operation(
                "transformation",
                label,
                lambda: self.shape(captured_data, captured_pipeline),
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            raise JobError(str(exc)) from exc

    def reduce_seeds(
        self,
        data: "Table",
        categorical_cols: list[str],
        statistic_cols: list[str],
    ) -> "Table":
        """Aggregate across random seeds (mean + ``.sd`` stdev columns).

        Source measurements and semantic metadata remain owned by their input table.

        Args:
            data: Input :class:`ring5.Table`.
            categorical_cols: Columns defining each experiment group.
            statistic_cols: Numeric columns to aggregate.

        Returns:
            A new table containing the aggregate.

        Raises:
            ColumnNotFoundError: A named column is absent.
            DataValidationError: Inputs rejected (e.g. non-numeric
                statistic column, empty selections).
        """
        frame = _table_frame(data)
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
        return Table(reduced)

    def compare(
        self,
        baseline: "Table",
        candidate: "Table",
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
    ) -> "Table":
        """Compare aligned baseline and candidate measurements.

        The result contains one row per key and metric with baseline and
        candidate values, absolute and percentage changes, the configured
        threshold, and an outcome. Candidate-only and baseline-only keys remain
        visible in the returned :class:`ring5.Table`.

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
            A table containing long-form comparison data.

        Raises:
            ColumnNotFoundError: An alignment key or metric is absent.
            DataValidationError: Keys, metrics, directions, or thresholds are invalid.
        """
        # [impl->req~ring5.analysis.regression-comparison~1]
        baseline_frame = _table_frame(baseline)
        candidate_frame = _table_frame(candidate)
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
        self._guided_comparison_ready = True
        return Table(result)

    def compare_statistics(
        self,
        baseline: "Table",
        candidate: "Table",
        group_columns: Sequence[str],
        metric_columns: Sequence[str],
        *,
        confidence_level: float = 0.95,
        alpha: float = 0.05,
        bootstrap_samples: int = 2_000,
        random_seed: int = 0,
        minimum_sample_size: int = 5,
    ) -> "Table":
        """Calculate statistics for repeated baseline and candidate samples.

        Results include per-side sample counts and means, a Welch confidence
        interval and p-value, Hedges' g, a deterministic bootstrap estimate and
        interval, and explicit sample-quality warnings in a new table.

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
            A table containing long-form statistical results.

        Raises:
            ColumnNotFoundError: A grouping or metric column is absent.
            DataValidationError: Inputs or statistical options are invalid.
        """
        # [impl->req~ring5.analysis.statistical-comparison~1]
        baseline_frame = _table_frame(baseline)
        candidate_frame = _table_frame(candidate)
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
        self._guided_comparison_ready = True
        return Table(result)

    def annotate_comparison(
        self,
        comparison: "Table",
        *,
        label_columns: Sequence[str] | None = None,
        change_mode: Literal["threshold", "percentage", "absolute"] = "threshold",
    ) -> "Table":
        """Add accessible, plot-ready outcome annotations to comparison rows.

        Args:
            comparison: Long-form result from :meth:`compare`.
            label_columns: Columns combined with the metric for point labels.
                By default, all alignment-key columns are used.
            change_mode: Use each row's threshold mode, force percentage
                change, or force absolute change.

        Returns:
            A copy with annotation label, change, symbol, marker, color, and
            text columns in a new table.

        Raises:
            DataValidationError: The comparison schema, labels, or mode are invalid.
        """
        # [impl->req~ring5.analysis.regression-annotations~1]
        frame = _table_frame(comparison)
        try:
            result = self.api.managers.annotate_comparison(
                frame,
                label_columns=label_columns,
                change_mode=change_mode,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return Table(result)

    def export_regression_results(
        self,
        comparison: "Table",
        format: Literal["json", "junit"] = "json",
    ) -> bytes:
        """Export a threshold comparison as deterministic JSON or JUnit XML.

        The versioned JSON document includes source identifiers, outcome counts,
        alignment keys, values, thresholds, and outcomes. In JUnit, regressions
        are failures, incomplete comparisons are skipped, and improvements or
        unchanged rows pass.

        Args:
            comparison: Long-form result from :meth:`compare`.
            format: ``"json"`` or ``"junit"``.

        Returns:
            Deterministic UTF-8 document bytes.

        Raises:
            DataValidationError: The comparison schema or format is invalid.
        """
        # [impl->req~ring5.automation.machine-readable-regression~1]
        frame = _table_frame(comparison)
        try:
            return self.api.managers.export_regression_results(frame, format)
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def remove_outliers(
        self,
        data: "Table",
        outlier_col: str,
        group_by_cols: list[str] | None = None,
    ) -> "Table":
        """IQR outlier removal.

        The input table remains unchanged.

        Args:
            data: Input :class:`ring5.Table`.
            outlier_col: Numeric column tested for outliers.
            group_by_cols: Optional columns defining independent IQR groups.

        Returns:
            A new table containing the retained rows.

        Raises:
            ColumnNotFoundError: A named column is absent.
            DataValidationError: Inputs rejected (e.g. non-numeric column).
        """
        frame = _table_frame(data)
        _require_columns(frame, [outlier_col] + (group_by_cols or []))
        try:
            cleaned = self.api.managers.remove_outliers(frame, outlier_col, group_by_cols or [])
        except (ValueError, TypeError) as exc:
            raise DataValidationError(str(exc)) from exc
        return Table(cleaned)

    def apply_operation(
        self,
        data: "Table",
        operation: str,
        src1: str,
        src2: str,
        dest: str,
    ) -> "Table":
        """Create a column using a registered binary arithmetic operation.

        Args:
            data: Input :class:`ring5.Table`.
            operation: Exact ``Division``, ``Sum``, ``Subtraction``, or ``Multiplication`` token.
            src1: Left operand column.
            src2: Right operand column.
            dest: Destination column name.

        Returns:
            A new table containing the transformed data.

        Raises:
            ColumnNotFoundError: An operand column is absent.
            DataValidationError: The operation or destination is invalid.
        """
        frame = _table_frame(data)
        _require_columns(frame, [src1, src2])
        if not dest:
            raise DataValidationError("Destination column name cannot be empty.")
        try:
            result = self.api.managers.apply_operation(frame, operation, src1, src2, dest)
        except (KeyError, TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc
        return Table(result)

    def mix_columns(
        self,
        data: "Table",
        dest_col: str,
        source_cols: list[str],
        operation: str = "Sum",
        separator: str = "_",
    ) -> "Table":
        """Merge columns, including standard-deviation propagation.

        Args:
            data: Input :class:`ring5.Table`.
            dest_col: Destination column name.
            source_cols: Two or more columns to merge.
            operation: ``Sum``, ``Mean``, or ``Concatenate``.
            separator: Separator used by concatenation.

        Returns:
            A new table containing the transformed data.

        Raises:
            ColumnNotFoundError: A source column is absent.
            DataValidationError: The merge configuration is invalid.
        """
        frame = _table_frame(data)
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
        return Table(result)

    # figures
    def create_plot(
        self,
        plot_type: str,
        *,
        data: "Table",
        config: FigureSpec | Mapping[str, Any],
        name: str | None = None,
    ) -> BasePlot:
        # [impl->req~ring5.api.plot-validation~1]
        """Create and register a configured plot.

        Args:
            plot_type: Exact registered identifier, such as ``"bar"`` or ``"grouped_bar"``.
            data: A :class:`ring5.Table`.
            config: A typed :class:`FigureSpec` or a mapping containing the
                renderer's flat configuration.
            name: Portfolio/display name. A stable generated name is used when omitted.

        Returns:
            The registered plot. Pass it to :meth:`render`, or use :meth:`plot`
            to create and render in one call.

        Raises:
            DataValidationError: The plot identifier or configuration is unsupported.
            ColumnNotFoundError: A mapped column is absent from the data.
        """
        from src.web.pages.ui.plotting.plot_service import PlotService

        resolved_type = _resolve_plot_type(plot_type)
        frame = _table_frame(data)
        try:
            raw_config = (
                config.to_config(plot_type=resolved_type)
                if isinstance(config, FigureSpec)
                else dict(config)
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(f"Invalid plot configuration: {exc}") from exc
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
        data: "Table",
        config: FigureSpec | Mapping[str, Any],
        engine: EngineMode = "plotly",
        name: str | None = None,
    ) -> _render.Figure:
        """Create, register, and render a plot in one call.

        Args:
            plot_type: Exact registered plot identifier.
            data: A :class:`ring5.Table`.
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
        figure = _render.render_figure(plot, engine=engine)
        self._guided_rendered_plot_ids.add(plot.plot_id)
        return figure

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
            A source-row snapshot with an independently owned :class:`ring5.Table`.

        Raises:
            DataValidationError: The plot, source data, or filters are invalid.
        """
        plot_id = plot.plot_id if isinstance(plot, BasePlot) else plot
        try:
            result = self.api.drill_down_plot(plot_id, filters)
            return DrillDownResult(result.plot_id, result.filters, Table(result.rows))
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
        tex_system: TexSystem = "xelatex",
        **kwargs: Any,
    ) -> str:
        """Export a rendered figure to a file.

        Args:
            fig: Figure returned by :meth:`render`.
            path: Destination file path.
            fmt: Explicit format; inferred from ``path`` when omitted.
            deterministic: Enable byte-stable export settings.
            tex_system: PGF compiler: ``xelatex``, ``pdflatex`` or ``lualatex``.
            **kwargs: Engine-specific dimensions and resolution options.

        Returns:
            The written file path.

        Raises:
            ExportError: The format is unsupported or the destination cannot
                be written.
            DependencyMissingError: The selected format requires an external
                executable that is unavailable.
        """
        exported_path = _export.export_file(
            fig,
            path,
            fmt=fmt,
            deterministic=deterministic,
            tex_system=tex_system,
            **kwargs,
        )
        self._guided_exported = True
        return exported_path

    def export_submit(
        self,
        fig: _render.Figure,
        path: str,
        *,
        fmt: str | None = None,
        deterministic: bool = False,
        tex_system: TexSystem = "xelatex",
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
            tex_system: PGF compiler: ``xelatex``, ``pdflatex`` or ``lualatex``.
            label: Optional job-center label.
            **kwargs: Engine-specific dimensions and resolution options.

        Returns:
            Initial immutable job snapshot. The completed result is the path.

        Raises:
            JobError: The figure snapshot, submission metadata or session job center is invalid.
        """
        try:
            captured_figure = (
                copy_matplotlib_figure(fig) if isinstance(fig, MplFigure) else copy.deepcopy(fig)
            )
            captured_kwargs = copy.deepcopy(kwargs)
            selected_label = label or f"Download {Path(path).name or 'figure'}"
            return self.api.submit_background_operation(
                "export",
                selected_label,
                lambda: self.export(
                    captured_figure,
                    path,
                    fmt=fmt,
                    deterministic=deterministic,
                    tex_system=tex_system,
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
        tex_system: TexSystem = "xelatex",
        **kwargs: Any,
    ) -> bytes:
        """Export a rendered figure to bytes.

        Args:
            fig: Figure returned by :meth:`render`.
            fmt: Output format supported by the figure's engine.
            deterministic: Enable byte-stable export settings.
            tex_system: PGF compiler: ``xelatex``, ``pdflatex`` or ``lualatex``.
            **kwargs: Engine-specific dimensions and resolution options.

        Returns:
            Encoded figure bytes.

        Raises:
            ExportError: The format is unsupported or generation fails.
            DependencyMissingError: The selected format requires an external
                executable that is unavailable.
        """
        payload = _export.export_bytes(
            fig, fmt, deterministic=deterministic, tex_system=tex_system, **kwargs
        )
        self._guided_exported = True
        return payload

    def create_report(
        self,
        title: str,
        figures: Sequence[BasePlot | int | DashboardSpec],
        *,
        tables: Mapping[str, Table] | None = None,
        narrative: Mapping[str, str] | None = None,
        figure_captions: Sequence[str] | None = None,
        table_row_limit: int = 100,
    ) -> AnalysisReport:
        # [impl->req~ring5.export.batch-reports~1]
        """Create a report from selected plots, dashboards, tables, and text.

        Data provenance and the current execution environment are captured
        automatically. Tables are copied into a bounded immutable display
        representation; input tables are never mutated.

        Args:
            title: Human-readable report title.
            figures: Registered plots, plot IDs, or dashboard specifications.
            tables: Optional ordered mapping of titles to :class:`ring5.Table` values.
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
        table_frames = (
            {name: _table_frame(table) for name, table in tables.items()}
            if tables is not None
            else None
        )
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
                tables=table_frames,
                narrative=narrative,
                provenance=provenance,
                environment=EnvironmentMetadataService.capture(),
                table_row_limit=table_row_limit,
            )
        except (TypeError, ValueError) as exc:
            raise DataValidationError(str(exc)) from exc

    def report_bytes(
        self,
        report: AnalysisReport,
        fmt: Literal["html", "pdf"] = "html",
        *,
        html_mode: Literal["document", "gallery"] = "document",
    ) -> bytes:
        # [impl->req~ring5.export.batch-reports~1]
        # [impl->req~ring5.export.interactive-gallery~1]
        """Render a deterministic self-contained HTML or PDF report.

        Args:
            report: Specification returned by :meth:`create_report`.
            fmt: Output format, ``"html"`` or ``"pdf"``.
            html_mode: For HTML, render a static publication ``"document"``
                or an interactive plot-and-data ``"gallery"``.

        Returns:
            Deterministic report bytes.

        Raises:
            ExportError: Rendering fails or a selected plot is no longer live.
        """
        from src.web.rendering.report_builder import render_report

        try:
            return render_report(self.plots, report, fmt=fmt, html_mode=html_mode)
        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as exc:
            raise ExportError(f"Could not render {fmt!r} analysis report: {exc}") from exc

    def export_report(
        self,
        report: AnalysisReport,
        path: str,
        *,
        fmt: Literal["html", "pdf"] | None = None,
        html_mode: Literal["document", "gallery"] = "document",
    ) -> str:
        # [impl->req~ring5.export.batch-reports~1]
        # [impl->req~ring5.export.interactive-gallery~1]
        """Write a deterministic analysis report to a file.

        Args:
            report: Specification returned by :meth:`create_report`.
            path: Destination file path.
            fmt: Explicit format; inferred from the ``.html`` or ``.pdf`` suffix.
            html_mode: For HTML, render a static publication ``"document"``
                or an interactive plot-and-data ``"gallery"``.

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
            payload = self.report_bytes(
                report,
                cast(Literal["html", "pdf"], selected_format),
                html_mode=html_mode,
            )
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
        from src.core.models.portfolio_contract import (
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
        from src.core.models.portfolio_contract import (
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
            PortfolioVersionError: The portfolio uses an unsupported schema.
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
            PortfolioVersionError: The portfolio uses an unsupported schema.
        """
        from src.core.models.portfolio_contract import PortfolioVersionError as CoreVersionError

        from ring5.errors import PortfolioVersionError

        try:
            return self.api.data_services.verify_portfolio(name, signing_key=signing_key)
        except FileNotFoundError as exc:
            raise PortfolioError(str(exc)) from exc
        except CoreVersionError as exc:
            raise PortfolioVersionError(str(exc)) from exc
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
            PortfolioVersionError: The portfolio uses an unsupported schema.
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
            PortfolioVersionError: A revision uses an unsupported portfolio schema.
        """
        from src.core.models.portfolio_contract import (
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
            PortfolioVersionError: The revision uses an unsupported portfolio schema.
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
        transformations: Sequence[Mapping[str, object]] = (),
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
                parser_variables = [
                    StatConfigCodec.from_payload(value) for value in source.variables
                ]
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

        transformed = self.shape(Table(data), materialized.transformations)
        prepared: list[tuple[RecipePlot, Table]] = []
        for plot_spec in materialized.plots:
            plot_data = self.shape(transformed, plot_spec.pipeline)
            resolved_type = _resolve_plot_type(plot_spec.plot_type)
            validate_plot_config(resolved_type, plot_data.frame, dict(plot_spec.config))
            prepared.append((plot_spec, plot_data))

        state = self.api.state_manager
        for existing in state.get_plots():
            state.remove_visualization_config(existing.plot_id)
        state.set_plots([])
        state.set_plot_counter(0)
        state.set_current_plot_id(None)
        state.set_data(transformed.frame, operation=f"Run analysis recipe: {materialized.name}")
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
                {"id": index, "type": cast(str, config["type"]), "config": copy.deepcopy(config)}
                for index, config in enumerate(plot_spec.pipeline)
            ]
            plot.pipeline_counter = len(plot.pipeline)
            plot.replace_source_data(transformed.frame)
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
                    tex_system=validate_tex_system(
                        created[export.plot].config.get("tex_system", "xelatex")
                    ),
                )
            )

        return AnalysisRecipeRunResult(
            recipe_name=materialized.name,
            parameter_values=resolved_values,
            rows=len(transformed),
            columns=tuple(transformed.columns()),
            plot_names=tuple(created),
            exported_paths=tuple(exported),
        )

    def run_scheduled_report(
        self,
        recipe: AnalysisRecipe,
        report_path: str,
        *,
        values: Mapping[str, RecipeScalar] | None = None,
        state_path: str | None = None,
        stable_for_seconds: float = 30.0,
        title: str | None = None,
        format: Literal["html", "pdf"] = "html",
    ) -> ScheduledReportResult:
        """Run one durable scheduled-report source check.

        A changed recipe source must remain unchanged for
        ``stable_for_seconds`` before the recipe runs. The report is built in
        memory, the source is fingerprinted again, and only then is the report
        atomically published and its generated fingerprint retained. Calling
        this method from cron is a single scheduled tick; repeated calls skip
        an already reported source.

        Recipe plot exports are suppressed for this workflow so an unstable
        source cannot leave partial side artifacts. The generated report still
        contains every recipe plot plus data and environment provenance.

        Args:
            recipe: Valid analysis recipe with at least one plot.
            report_path: HTML or PDF destination replaced only after success.
            values: Typed runtime recipe parameters.
            state_path: Durable state JSON path. Defaults beside the report.
            stable_for_seconds: Required unchanged interval, from zero through
                seven days.
            title: Report title; defaults to the recipe name.
            format: Deterministic ``"html"`` or ``"pdf"`` report format.

        Returns:
            A :class:`ring5.ScheduledReportResult` whose outcome is
            ``generated``, ``unchanged``, or ``waiting_for_stability``.

        Raises:
            RecipeError: Recipe, source, state, or stability settings are invalid.
            PipelineError: A recipe transformation fails.
            DataValidationError: A plot or report mapping is invalid.
            ExportError: Report rendering or atomic publication fails.
        """
        # [impl->req~ring5.automation.scheduled-reporting~1]
        from src.core.services.scheduled_report_service import (
            ScheduledReportError,
            ScheduledReportPublishError,
            ScheduledReportService,
        )

        materialized = self.materialize_analysis_recipe(recipe, values)
        resolved_state = state_path or f"{report_path}.ring5-state.json"

        def resolve_source_files() -> tuple[str, ...]:
            return ScheduledReportService.source_files(
                materialized.source,
                self.api.find_stats_files,
            )

        def generate() -> bytes:
            execution_recipe = replace(recipe, exports=())
            self.run_analysis_recipe(execution_recipe, values)
            if not self.plots:
                raise RecipeError("Scheduled report recipes need at least one plot.")
            report = self.create_report(
                report_title,
                self.plots,
                narrative={
                    "Scheduled execution": (
                        "Generated after the configured source remained stable and changed."
                    )
                },
            )
            return self.report_bytes(report, format)

        try:
            report_title = title or materialized.name
            configuration_fingerprint = ScheduledReportService.report_configuration_fingerprint(
                self.export_analysis_recipe(replace(materialized, exports=())),
                report_path=report_path,
                title=report_title,
                format=format,
            )
            return ScheduledReportService.run(
                recipe_name=materialized.name,
                configuration_fingerprint=configuration_fingerprint,
                resolve_source_files=resolve_source_files,
                report_path=report_path,
                state_path=resolved_state,
                stable_for_seconds=stable_for_seconds,
                generate=generate,
            )
        except ScheduledReportPublishError as exc:
            raise ExportError(str(exc)) from exc
        except ScheduledReportError as exc:
            raise RecipeError(str(exc)) from exc

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
