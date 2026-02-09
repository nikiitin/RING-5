"""
Session Repository
Single Responsibility: Manage session lifecycle and restoration.
"""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING, List

import pandas as pd

if TYPE_CHECKING:
    from src.web.pages.ui.plotting.base_plot import BasePlot
else:
    BasePlot = None  # type: ignore

from src.core.models import PortfolioData
from src.core.state.repositories.config_repository import ConfigRepository
from src.core.state.repositories.data_repository import DataRepository
from src.core.state.repositories.parser_state_repository import ParserStateRepository
from src.core.state.repositories.plot_repository import PlotRepository
from src.core.state.repositories.preview_repository import PreviewRepository

logger = logging.getLogger(__name__)


class SessionRepository:
    """
    Repository for managing session lifecycle operations.

    Responsibilities:
    - Session initialization
    - Session restoration from portfolios
    - Widget state cleanup (conceptually, though adapter removal changes this)
    - Complete session clearing

    Adheres to SRP: Only manages session lifecycle, nothing else.
    """

    def __init__(self) -> None:
        """Initialize domain repositories."""
        self.data_repo = DataRepository()
        self.plot_repo = PlotRepository()
        self.parser_repo = ParserStateRepository()
        self.config_repo = ConfigRepository()
        self.preview_repo = PreviewRepository()

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
        st.session_state is no longer managed here directly.
        However, if we re-introduce a persistence layer, this logic belongs there.
        For now, this is a no-op/placeholder or needs to interact with the UI layer differently.

        Ideally, ApplicationAPI exposes a way to clear UI specific cache if needed,
        but domain repositories should be UI agnostic.
        """
        pass

    def restore_from_portfolio(self, portfolio_data: PortfolioData) -> None:
        """
        Restore complete session state from portfolio data.

        Args:
            portfolio_data: Portfolio restoration data
        """
        # Clear widget state first
        self.clear_widget_state()

        # Restore parser state
        self.parser_repo.set_parse_variables(portfolio_data.get("parse_variables", []))
        self.parser_repo.set_stats_path(portfolio_data.get("stats_path", ""))
        self.parser_repo.set_stats_pattern(portfolio_data.get("stats_pattern", "stats.txt"))
        self.parser_repo.set_scanned_variables(portfolio_data.get("scanned_variables", []))
        # Handle 'use_parser' which might store boolean directly
        self.parser_repo.set_using_parser(bool(portfolio_data.get("use_parser", False)))

        # Restore config state
        self.config_repo.set_csv_path(portfolio_data.get("csv_path", ""))
        self.config_repo.set_config(portfolio_data.get("config", {}))

        # Restore data
        if "data_csv" in portfolio_data:
            try:
                df = pd.read_csv(io.StringIO(portfolio_data["data_csv"]))
                self.data_repo.set_data(df)
                logger.info(f"SESSION_REPO: Restored data - {len(df)} rows")
            except Exception as e:
                logger.error(f"SESSION_REPO: Failed to restore data: {e}")

        # Restore plots
        loaded_plots: List[BasePlot] = []
        for plot_data in portfolio_data.get("plots", []):
            try:
                from src.web.pages.ui.plotting.base_plot import BasePlot

                plot = BasePlot.from_dict(plot_data)
                if plot:
                    loaded_plots.append(plot)
            except Exception as e:
                logger.error(f"SESSION_REPO: Failed to restore plot: {e}")

        self.plot_repo.set_plots(loaded_plots)  # type: ignore[arg-type]
        self.plot_repo.set_plot_counter(portfolio_data.get("plot_counter", len(loaded_plots)))

        logger.info(
            f"SESSION_REPO: Session restored - "
            f"{len(loaded_plots)} plots, "
            f"parser={'ON' if portfolio_data.get('use_parser') else 'OFF'}"
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

        # Clear widget state
        self.clear_widget_state()

        logger.info("SESSION_REPO: Complete session cleared")
