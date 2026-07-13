"""Headless workspace for parsing, shaping, plotting, and portfolio replay."""

from __future__ import annotations

import copy
import shutil
import tempfile
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Literal, cast

import pandas as pd

from src.core.application_api import ApplicationAPI
from src.core.models import RestoreReport, StatConfig
from src.core.models.shaper_models import ShaperStepConfig
from src.core.models.visualization.engine import EngineMode
from src.web.pages.ui.plotting.base_plot import BasePlot

from ring5 import _export, _parse, _render
from ring5.errors import (
    ColumnNotFoundError,
    DataLoadError,
    DataValidationError,
    ParseError,
    PipelineError,
    PortfolioError,
)
from ring5.figure_spec import FigureSpec

PlotType = Literal[
    "bar",
    "dual_axis_bar_dot",
    "grouped_bar",
    "grouped_stacked_bar",
    "heatmap",
    "histogram",
    "line",
    "scatter",
    "stacked_bar",
]

if TYPE_CHECKING:
    from src.core.models.data_models import ParseVariableConfig
    from src.parsing.parser_protocol import SimulationParser

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


def available_plot_types() -> tuple[str, ...]:
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

    def __init__(self, *, parser: "SimulationParser | None" = None) -> None:
        # Headless portfolio restores need the web composition root's plot deserializer.
        self.api = ApplicationAPI(plot_deserializer=BasePlot.from_dict, parser=parser)
        # Temporary parse output is removed when the session closes.
        self._owned_tmpdirs: list[str] = []

    # lifecycle
    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        """Release this session's pending work (process pools stay up)."""
        self.api.cancel_pending_scans()
        for tmp in self._owned_tmpdirs:
            shutil.rmtree(tmp, ignore_errors=True)
        self._owned_tmpdirs.clear()

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
        files (``0`` = all files — use it when stats differ across runs),
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
            scan_limit: Maximum files to scan; zero scans every matching file.

        Returns:
            A submitted parse job that can be finalized or cancelled.

        Raises:
            ScanError: No matching statistics files were found or variable
                discovery failed.
            ParseError: The parser rejected the submission.
        """
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
                cast("list[ParseVariableConfig | StatConfig]", list(configs)),
                out_dir,
                strategy_type=strategy,
                scanned_vars=scanned,
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            raise ParseError(f"Parse submission failed: {exc}") from exc

        # Store parse provenance for portfolio restoration and replay.
        sm = self.api.state_manager
        sm.set_stats_path(stats_path)
        sm.set_stats_pattern(pattern)
        sm.set_parse_variables(
            cast(
                "list[ParseVariableConfig]",
                [
                    dict(c) if isinstance(c, dict) else {"name": c.name, "type": c.type}
                    for c in configs
                ],
            )
        )
        sm.set_scanned_variables([v.to_dict() if hasattr(v, "to_dict") else v for v in scanned])
        return _parse.ParseJob(
            api=self.api,
            futures=list(batch.futures),
            var_names=list(batch.var_names),
            output_dir=out_dir,
            strategy=strategy,
            stats_path=stats_path,
            stats_pattern=pattern,
        )

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
            scan_limit: Maximum files to scan; zero scans every matching file.
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
        try:
            self.api.load_data(csv_path)
        except (OSError, ValueError, UnicodeError) as exc:
            raise DataLoadError(f"Could not load CSV {csv_path!r}: {exc}") from exc
        data = self.api.state_manager.get_data()
        if data is None:
            raise DataLoadError(f"Loading {csv_path!r} produced no data.")
        return data

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

    # figures
    def create_plot(
        self,
        plot_type: str,
        *,
        data: "pd.DataFrame | Table",
        config: "FigureSpec | Mapping[str, Any]",
        name: str | None = None,
    ) -> BasePlot:
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
        plot = PlotService.create_plot(name or resolved_type, resolved_type, self.api.state_manager)
        if name is None:
            plot.name = f"{resolved_type}_{plot.plot_id}"
        plot.replace_processed_data(frame.copy())
        raw_config = config.to_config() if isinstance(config, FigureSpec) else dict(config)
        # Plot configuration contains nested lists and dictionaries. Copy it so a
        # later caller mutation cannot silently change an already registered plot.
        plot.config = copy.deepcopy(raw_config)
        return plot

    def plot(
        self,
        plot_type: str,
        *,
        data: "pd.DataFrame | Table",
        config: "FigureSpec | Mapping[str, Any]",
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
