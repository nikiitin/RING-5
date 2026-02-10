"""
Repository State Manager - Concrete Implementation.

Implements the AbstractStateManager protocol using in-memory repositories
coordinated through a SessionRepository aggregate root.

Architecture:
    RepositoryStateManager delegates all state operations to domain-specific
    repositories (DataRepository, PlotRepository, etc.) managed by a single
    SessionRepository instance.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from src.core.models import PlotProtocol, PortfolioData
from src.core.state.repositories.session_repository import SessionRepository

logger: logging.Logger = logging.getLogger(__name__)


class RepositoryStateManager:
    """
    Concrete implementation of StateManager using pure Python repositories.
    Holds the SessionRepository acting as the Aggregate Root.
    """

    def __init__(self) -> None:
        """Initialize the repository layer.

        SessionRepository.__init__ already creates all domain repositories
        with sensible defaults, so no additional initialization is needed.
        """
        self._session_repo = SessionRepository()

    def initialize(self) -> None:
        """Re-initialize the session to clean defaults.

        Useful for resetting state without constructing a new instance.
        """
        self._session_repo.initialize_session()

    # ==================== Data Management ====================

    def get_data(self) -> Optional[pd.DataFrame]:
        return self._session_repo.data_repo.get_data()

    def set_data(
        self, data: Optional[pd.DataFrame], on_change: Optional[Callable[[], None]] = None
    ) -> None:
        # Enforce type constraints logic moved here from old static StateManager
        if data is not None:
            try:
                variables = self._session_repo.parser_repo.get_parse_variables()
                config_vars: List[str] = [
                    v["name"] for v in variables if v.get("type") == "configuration"
                ]
                for col in config_vars:
                    if col in data.columns:
                        data[col] = data[col].astype(str)
            except Exception as e:
                logger.error(f"STATE: Type enforcement failed: {e}")

        self._session_repo.data_repo.set_data(data, on_change)

    def get_processed_data(self) -> Optional[pd.DataFrame]:
        return self._session_repo.data_repo.get_processed_data()

    def set_processed_data(self, data: Optional[pd.DataFrame]) -> None:
        self._session_repo.data_repo.set_processed_data(data)

    def has_data(self) -> bool:
        return self._session_repo.data_repo.has_data()

    def clear_data(self) -> None:
        # Cleanup temp dir logic
        temp_dir = self._session_repo.config_repo.get_temp_dir()
        if temp_dir and Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.warning(f"STATE: Cleanup failed for {temp_dir}: {e}")

        self._session_repo.data_repo.clear_data()
        self._session_repo.config_repo.set_csv_path("")
        self._session_repo.config_repo.set_temp_dir("")
        self._session_repo.plot_repo.clear_plots()
        self._session_repo.plot_repo.set_plot_counter(0)
        self._session_repo.plot_repo.set_current_plot_id(None)

    # ==================== Config & Parser ====================

    def get_config(self) -> Dict[str, Any]:
        return self._session_repo.config_repo.get_config()

    def set_config(self, config: Dict[str, Any]) -> None:
        self._session_repo.config_repo.set_config(config)

    def update_config(self, key: str, value: Any) -> None:
        self._session_repo.config_repo.update_config(key, value)

    def get_temp_dir(self) -> Optional[str]:
        return self._session_repo.config_repo.get_temp_dir()

    def set_temp_dir(self, path: str) -> None:
        self._session_repo.config_repo.set_temp_dir(path)

    def get_csv_path(self) -> Optional[str]:
        return self._session_repo.config_repo.get_csv_path()

    def set_csv_path(self, path: str) -> None:
        self._session_repo.config_repo.set_csv_path(path)

    def get_csv_pool(self) -> List[Dict[str, Any]]:
        return self._session_repo.config_repo.get_csv_pool()

    def set_csv_pool(self, pool: List[Dict[str, Any]]) -> None:
        self._session_repo.config_repo.set_csv_pool(pool)

    def get_saved_configs(self) -> List[Dict[str, Any]]:
        return self._session_repo.config_repo.get_saved_configs()

    def set_saved_configs(self, configs: List[Dict[str, Any]]) -> None:
        self._session_repo.config_repo.set_saved_configs(configs)

    def is_using_parser(self) -> bool:
        return self._session_repo.parser_repo.is_using_parser()

    def set_use_parser(self, use: bool) -> None:
        self._session_repo.parser_repo.set_using_parser(use)

    def get_parse_variables(self) -> List[Dict[str, Any]]:
        return self._session_repo.parser_repo.get_parse_variables()

    def set_parse_variables(self, variables: List[Dict[str, Any]]) -> None:
        self._session_repo.parser_repo.set_parse_variables(variables)

    def get_stats_path(self) -> str:
        return self._session_repo.parser_repo.get_stats_path()

    def set_stats_path(self, path: str) -> None:
        self._session_repo.parser_repo.set_stats_path(path)

    def get_stats_pattern(self) -> str:
        return self._session_repo.parser_repo.get_stats_pattern()

    def set_stats_pattern(self, pattern: str) -> None:
        self._session_repo.parser_repo.set_stats_pattern(pattern)

    def get_scanned_variables(self) -> List[Dict[str, Any]]:
        return self._session_repo.parser_repo.get_scanned_variables()

    def set_scanned_variables(self, variables: List[Dict[str, Any]]) -> None:
        self._session_repo.parser_repo.set_scanned_variables(variables)

    def get_parser_strategy(self) -> str:
        return self._session_repo.parser_repo.get_parser_strategy()

    def set_parser_strategy(self, strategy: str) -> None:
        self._session_repo.parser_repo.set_parser_strategy(strategy)

    # ==================== Plots ====================

    def get_plots(self) -> List[PlotProtocol]:
        return self._session_repo.plot_repo.get_plots()

    def set_plots(self, plots: List[PlotProtocol]) -> None:
        self._session_repo.plot_repo.set_plots(plots)

    def add_plot(self, plot_obj: PlotProtocol) -> None:
        self._session_repo.plot_repo.add_plot(plot_obj)

    def get_plot_counter(self) -> int:
        return self._session_repo.plot_repo.get_plot_counter()

    def set_plot_counter(self, counter: int) -> None:
        self._session_repo.plot_repo.set_plot_counter(counter)

    def start_next_plot_id(self) -> int:
        return self._session_repo.plot_repo.increment_plot_counter()

    def get_current_plot_id(self) -> Optional[int]:
        return self._session_repo.plot_repo.get_current_plot_id()

    def set_current_plot_id(self, plot_id: Optional[int]) -> None:
        self._session_repo.plot_repo.set_current_plot_id(plot_id)

    # ==================== Previews ====================

    def set_preview(self, operation_name: str, data: pd.DataFrame) -> None:
        self._session_repo.preview_repo.set_preview(operation_name, data)

    def get_preview(self, operation_name: str) -> Optional[pd.DataFrame]:
        return self._session_repo.preview_repo.get_preview(operation_name)

    def has_preview(self, operation_name: str) -> bool:
        return self._session_repo.preview_repo.has_preview(operation_name)

    def clear_preview(self, operation_name: str) -> None:
        self._session_repo.preview_repo.clear_preview(operation_name)

    # ==================== Session ====================

    def clear_all(self) -> None:
        self._session_repo.clear_all()

    def restore_session(self, portfolio_data: PortfolioData) -> None:
        self._session_repo.restore_from_portfolio(portfolio_data)
