"""The ring5 Session — one workspace, the full workflow, no Streamlit.

A ``Session`` owns one :class:`ApplicationAPI` (isolated in-memory state)
and adds the seams the facade never had: plot creation, engine-explicit
rendering, file export, and portfolio replay. Sessions share the
process-wide worker pools (safe — verified under concurrent load); use
:func:`ring5.shutdown` once per process to tear those down.
"""

from __future__ import annotations

import copy
import shutil
import tempfile
from typing import TYPE_CHECKING, Any, cast

import pandas as pd

from src.core.application_api import ApplicationAPI
from src.core.models import RestoreReport, StatConfig
from src.core.models.shaper_models import ShaperStepConfig
from src.core.models.visualization.engine import EngineMode
from src.web.pages.ui.plotting.base_plot import BasePlot

from ring5 import _export, _parse, _render
from ring5.errors import (
    ColumnNotFoundError,
    DataValidationError,
    ParseError,
    PipelineError,
    PortfolioError,
)

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


class Session:
    """A headless RING-5 workspace.

    Mirrors what one browser session of the web app can do — parse, shape,
    plot, render, export, snapshot — as plain method calls::

        with ring5.Session() as s:
            csv = s.parse("/sims", variables=["simTicks"]).csv_path
            df = s.load(csv)
            df = s.reduce_seeds(df, ["config_description_abbrev"], ["simTicks"])
            plot = s.create_plot("bar", data=df,
                                 config={"x": "config_description_abbrev",
                                         "y": "simTicks"})
            fig = s.render(plot, engine="matplotlib")
            s.export(fig, "out/simticks.pdf")

    The full :class:`ApplicationAPI` remains available as ``session.api``
    (history, previews, CSV pool, saved configs, …).
    """

    def __init__(self, *, parser: "SimulationParser | None" = None) -> None:
        # The plot deserializer is ALWAYS wired — a Session can never hit
        # the silent drop-all-plots restore path a bare ApplicationAPI has.
        self.api = ApplicationAPI(plot_deserializer=BasePlot.from_dict, parser=parser)
        # Temp dirs this session created for parse output (no explicit output_dir) — cleaned
        # up in close()/__exit__ so each parse/CLI run doesn't orphan a dir in the system tmp.
        self._owned_tmpdirs: list[str] = []

    # ── lifecycle ────────────────────────────────────────────────

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

    # ── parse ────────────────────────────────────────────────────

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
        """
        configs, scanned = _parse.build_stat_configs(
            self.api, stats_path, variables, pattern=pattern, scan_limit=scan_limit
        )
        if output_dir is None:
            out_dir = tempfile.mkdtemp(prefix="ring5_parse_")
            self._owned_tmpdirs.append(out_dir)  # cleaned in close()/__exit__
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

        # Record parse provenance in session state so a portfolio saved from
        # this session carries the real source (an app load of the portfolio
        # shows it on the Data Source page and can re-run the parse).
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
        """Blocking convenience: ``parse_submit(...)`` + ``finalize()``."""
        job = self.parse_submit(
            stats_path,
            variables,
            pattern=pattern,
            strategy=strategy,
            output_dir=output_dir,
            scan_limit=scan_limit,
        )
        return job.finalize(strict=strict)

    # ── data ─────────────────────────────────────────────────────

    def load(self, csv_path: str) -> pd.DataFrame:
        """Load a CSV into the session and return the DataFrame."""
        self.api.load_data(csv_path)
        data = self.api.state_manager.get_data()
        if data is None:
            raise ParseError(f"Loading {csv_path!r} produced no data.")
        return data

    def shape(
        self, data: "pd.DataFrame | Table", pipeline: list[ShaperStepConfig]
    ) -> "pd.DataFrame | Table":
        """Run a shaper pipeline; failures carry the step index and type.

        Accepts a :class:`ring5.Table` or a raw ``DataFrame`` and returns the same kind, so
        figure scripts can express ``build_data`` as a pipeline without touching pandas.
        """
        from src.core.services.shapers.pipeline_service import PipelineStepError

        frame, was_table = _unwrap_table(data)
        try:
            shaped = self.api.apply_shapers(frame, pipeline)
        except PipelineStepError as exc:
            raise PipelineError(
                str(exc), step_index=exc.step_index, shaper_type=exc.shaper_type
            ) from exc
        except ValueError as exc:
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

    # ── figures ──────────────────────────────────────────────────

    def create_plot(
        self,
        plot_type: str,
        *,
        data: "pd.DataFrame | Table",
        config: dict[str, Any],
        name: str | None = None,
    ) -> BasePlot:
        """Create a plot (snake_case type, e.g. ``bar``, ``grouped_bar``).

        The plot is registered in the session (so portfolios include it)
        and carries *data* as its processed data and *config* as its plot
        config — the same dict the web UI builds (``x``, ``y``,
        ``y_columns``, styling keys, …). *data* may be a :class:`ring5.Table`
        or a raw ``DataFrame``.
        """
        from src.web.pages.ui.plotting.plot_service import PlotService

        frame, _ = _unwrap_table(data)
        plot = PlotService.create_plot(name or plot_type, plot_type, self.api.state_manager)
        if name is None:
            plot.name = f"{plot_type}_{plot.plot_id}"
        plot.processed_data = frame.copy()
        # Deep copy: nested mutables (y_columns, series_styles) must not stay
        # shared with the caller's dict — the web UI deep-copies for the
        # same reason (a later caller mutation would rewrite the plot).
        plot.config = copy.deepcopy(config)
        return plot

    def render(self, plot: BasePlot, *, engine: EngineMode = "plotly") -> _render.Figure:
        """Render headlessly with an explicit engine (never session state)."""
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
        """Export a rendered figure to *path* (format from the extension)."""
        return _export.export_file(fig, path, fmt=fmt, deterministic=deterministic, **kwargs)

    def export_bytes(
        self,
        fig: _render.Figure,
        fmt: str,
        *,
        deterministic: bool = False,
        **kwargs: Any,
    ) -> bytes:
        """Export a rendered figure to bytes."""
        return _export.export_bytes(fig, fmt, deterministic=deterministic, **kwargs)

    # ── portfolios ───────────────────────────────────────────────

    @property
    def plots(self) -> list[BasePlot]:
        """The session's plots (created here or restored from a portfolio)."""
        return list(self.api.state_manager.get_plots())  # type: ignore[arg-type]

    def save_portfolio(self, name: str, *, overwrite: bool = False) -> None:
        """Snapshot the session (data + plots + config) to a portfolio.

        Unlike the web UI, ``overwrite`` defaults to **False** here:
        portfolios are keyed by name alone, and a script silently replacing
        one is data loss. Pass ``overwrite=True`` to replace.

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

    def load_portfolio(self, name: str) -> RestoreReport:
        """Load + restore a portfolio; the report says what was skipped.

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
            # Re-typed at the public boundary so it joins the Ring5Error
            # hierarchy (the core class is a ValueError for the web UI).
            raise PortfolioVersionError(str(exc)) from exc
        except ValueError as exc:
            # Corrupt JSON (json.JSONDecodeError) or a malformed
            # schema_version — both ValueErrors from the load/migrate path.
            raise PortfolioError(f"Portfolio '{name}' could not be read: {exc}") from exc
        return self.api.state_manager.restore_session(data)


def _require_columns(data: pd.DataFrame, columns: list[str]) -> None:
    """Raise the typed missing-column error before delegating to core."""
    for col in columns:
        if col not in data.columns:
            raise ColumnNotFoundError(col, list(data.columns))
