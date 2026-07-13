"""Coordinate repository initialization, restoration, and cleanup."""

from __future__ import annotations

import io
import logging

import pandas as pd

from src.core.models import PortfolioData, RestoreReport
from src.core.models.plot_protocol import PlotDeserializer, PlotProtocol
from src.core.state.repositories.config_repository import ConfigRepository
from src.core.state.repositories.data_repository import DataRepository
from src.core.state.repositories.history_repository import HistoryRepository
from src.core.state.repositories.parser_state_repository import ParserStateRepository
from src.core.state.repositories.plot_repository import PlotRepository
from src.core.state.repositories.preview_repository import PreviewRepository
from src.core.state.repositories.visualization_repository import VisualizationRepository

logger = logging.getLogger(__name__)


class SessionRepository:
    """Own the repositories that compose an application session."""

    def __init__(self, plot_deserializer: PlotDeserializer | None = None) -> None:
        """Initialize domain repositories.

        Args:
            plot_deserializer: Optional callable that converts a dict into
                a ``PlotProtocol`` instance.  Injected by the application
                bootstrap so this layer never imports web-layer classes.
        """
        self.data_repo = DataRepository()
        self.plot_repo = PlotRepository()
        self.parser_repo = ParserStateRepository()
        self.config_repo = ConfigRepository()
        self.preview_repo = PreviewRepository()
        self.history_repo = HistoryRepository()
        self.visualization_repo = VisualizationRepository()
        self._plot_deserializer = plot_deserializer

    def initialize_session(self) -> None:
        """
        Initialize all session state with default values.

        With in-memory repositories, this primarily ensures clean state.
        Real initialization happens on instantiation in __init__.
        """
        # Ensure clean state on explicit initialization
        if not self.data_repo.has_data():
            self.data_repo.set_data(None)
            self.data_repo.set_processed_data(None)

        # Plot defaults are handled by PlotRepository __init__

        # Parser defaults handled by ParserStateRepository __init__

        # Config defaults handled by ConfigRepository __init__

        logger.info("SESSION_REPO: Session initialized with default values")

    def clear_widget_state(self) -> None:
        """
        Clear widget-specific state markers.

        NOTE: With the move to Pure Python repositories, strict "widget state" stored in
        st session state is no longer managed here directly.
        However, if we re-introduce a persistence layer, this logic belongs there.
        For now, this is a no-op/placeholder or needs to interact with the UI layer differently.

        Ideally, ApplicationAPI exposes a way to clear UI specific cache if needed,
        but domain repositories should be UI agnostic.
        """

    def enforce_config_dtypes(self, data: pd.DataFrame) -> pd.DataFrame:
        """Cast configuration-typed columns to str on a copy of *data*.

        Configuration columns are grouping keys, so every ingestion path
        (fresh load and portfolio restore) must agree on their dtype. Returns
        a new frame; never mutates the caller's.
        """
        result = data.copy()
        try:
            variables = self.parser_repo.get_parse_variables()
            config_vars = [v["name"] for v in variables if v.get("type") == "configuration"]
            for col in (c for c in config_vars if c in result.columns):
                result[col] = result[col].astype(str)
        except (KeyError, TypeError, ValueError) as e:
            logger.error("SESSION_REPO: config dtype enforcement failed: %s", e)
        return result

    def restore_from_portfolio(self, portfolio_data: PortfolioData) -> RestoreReport:
        """
        Restore complete session state from portfolio data.

        Restore is best-effort per item; the returned :class:`RestoreReport`
        records exactly what was skipped or lost so callers (scripts in
        particular) never have to scrape logs.

        Args:
            portfolio_data: Portfolio restoration data

        Returns:
            A report of what was restored, skipped, and why.
        """
        # Clear widget state first
        self.clear_widget_state()

        # Restore parser state. Portfolio JSON is untrusted input — a
        # malformed parse_variables list (e.g. plain strings) would crash
        # set_parse_variables, which mutates each entry dict.
        raw_vars = portfolio_data.get("parse_variables", [])
        parse_vars = [v for v in raw_vars if isinstance(v, dict)]
        vars_skipped = len(raw_vars) - len(parse_vars)
        if vars_skipped:
            logger.warning(
                "SESSION_REPO: Skipped %d malformed parse_variables entries "
                "(expected dicts, e.g. got plain strings)",
                vars_skipped,
            )
        self.parser_repo.set_parse_variables(parse_vars)
        self.parser_repo.set_stats_path(portfolio_data.get("stats_path", ""))
        self.parser_repo.set_stats_pattern(portfolio_data.get("stats_pattern", "stats.txt"))
        self.parser_repo.set_scanned_variables(portfolio_data.get("scanned_variables", []))
        # Handle 'use_parser' which might store boolean directly
        self.parser_repo.set_using_parser(bool(portfolio_data.get("use_parser", False)))

        # Restore config state
        self.config_repo.set_csv_path(portfolio_data.get("csv_path", ""))
        self.config_repo.set_config(portfolio_data.get("config", {}))

        # Restore data
        data_restored = False
        data_error: str | None = None
        data_csv = portfolio_data.get("data_csv", "")
        if data_csv:
            try:
                df = self.enforce_config_dtypes(pd.read_csv(io.StringIO(data_csv)))
                self.data_repo.set_data(df)
                data_restored = True
                logger.info("SESSION_REPO: Restored data - %d rows", len(df))
            except Exception as e:
                # Plots reference this data; surface the loss loudly rather than
                # silently continuing with a half-restored session.
                data_error = str(e)
                logger.error(
                    "SESSION_REPO: Failed to restore data CSV — plots may render " "empty: %s",
                    e,
                    exc_info=True,
                )
        else:
            logger.info("SESSION_REPO: No data in portfolio (config-only save)")

        # Restore plots via injected deserializer (no web-layer import)
        loaded_plots: list[PlotProtocol] = []
        plots_skipped: list[str] = []
        plot_specs = portfolio_data.get("plots", [])
        if self._plot_deserializer is not None:
            for plot_data in plot_specs:
                plot_name = str(plot_data.get("name", "?"))
                try:
                    plot = self._plot_deserializer(plot_data)
                    if plot is not None:
                        loaded_plots.append(plot)
                    else:
                        plots_skipped.append(f"{plot_name}: deserializer returned None")
                except Exception as e:
                    plots_skipped.append(f"{plot_name}: {e}")
                    logger.error(f"SESSION_REPO: Failed to restore plot: {e}", exc_info=True)
            if plots_skipped:
                logger.warning(
                    "SESSION_REPO: Restored %d/%d plots (%d failed to deserialize)",
                    len(loaded_plots),
                    len(plot_specs),
                    len(plots_skipped),
                )
        elif plot_specs:
            plots_skipped = [
                f"{spec.get('name', '?')}: no plot_deserializer injected" for spec in plot_specs
            ]
            logger.warning(
                "SESSION_REPO: No plot_deserializer injected — skipping %d plots",
                len(plot_specs),
            )

        self.plot_repo.set_plots(loaded_plots)
        # Counter must clear every restored id (which keep their original, possibly sparse
        # values) — len(plots) can collide with a high/sparse id and reissue a live id.
        next_id = max((p.plot_id for p in loaded_plots), default=-1) + 1
        self.plot_repo.set_plot_counter(max(portfolio_data.get("plot_counter", 0), next_id))

        logger.info(
            f"SESSION_REPO: Session restored - "
            f"{len(loaded_plots)} plots, "
            f"parser={'ON' if portfolio_data.get('use_parser') else 'OFF'}"
        )

        # Restore history
        self.history_repo.set_manager_history(portfolio_data.get("manager_history", []))
        self.history_repo.set_portfolio_history(portfolio_data.get("portfolio_history", []))

        return RestoreReport(
            data_restored=data_restored,
            data_error=data_error,
            plots_restored=len(loaded_plots),
            plots_skipped=plots_skipped,
            parse_variables_skipped=vars_skipped,
        )

    def clear_all(self) -> None:
        """
        Clear all session state completely.
        """
        # Clear each domain
        self.data_repo.clear_data()
        self.plot_repo.clear_plots()
        self.plot_repo.set_plot_counter(0)
        self.plot_repo.set_current_plot_id(None)
        self.parser_repo.clear_parser_state()
        self.config_repo.clear_config()
        self.config_repo.set_csv_path("")
        self.config_repo.set_temp_dir("")
        self.history_repo.clear_all()
        self.visualization_repo.clear()

        # Clear widget state
        self.clear_widget_state()

        logger.info("SESSION_REPO: Complete session cleared")
