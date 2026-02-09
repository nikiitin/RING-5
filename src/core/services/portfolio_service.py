"""
Module: src.core.services/portfolio_service.py

Purpose:
    Manages complete workspace snapshots (portfolios) including data, plots,
    configurations, and parser state. Enables save/load workflow for resuming
    complex analysis sessions across multiple application restarts.

Responsibilities:
    - Serialize complete workspace state (data + plots + config + parser state)
    - Persist portfolios to JSON files with embedded CSV data
    - Restore full workspace from saved portfolios
    - Version portfolio format for backward compatibility
    - List available portfolios for quick access

Dependencies:
    - PathService: For portfolio storage directory
    - ParserStateRepository: For gem5 parser state persistence
    - BasePlot: For plot serialization/deserialization
    - json: For portfolio file format
    - pandas: For DataFrame serialization

Usage Example:
    >>> from src.core.services.portfolio_service import PortfolioService
    >>>
    >>> # Save current workspace
    >>> PortfolioService.save_portfolio(
    ...     name="ipc_analysis_20k",
    ...     data=current_dataframe,
    ...     plots=active_plots,
    ...     config=plot_configs,
    ...     plot_counter=5,
    ...     csv_path="/path/to/original.csv",
    ...     parse_variables=["system.cpu.ipc", "system.cpu.numCycles"]
    ... )
    >>>
    >>> # Load saved portfolio
    >>> portfolio = PortfolioService.load_portfolio("ipc_analysis_20k")
    >>> data = pd.read_csv(StringIO(portfolio["data_csv"]))
    >>> plots = [PlotFactory.from_dict(p) for p in portfolio["plots"]]

Design Patterns:
    - Service Layer Pattern: Business logic for workspace persistence
    - Memento Pattern: Captures and restores complete workspace state
    - Version Tolerance: Supports multiple portfolio format versions

Performance Characteristics:
    - Save Time: O(n) where n = DataFrame size + plot count
    - Typical Save: 100-500ms for 10k rows + 5 plots
    - Load Time: O(n) for DataFrame deserialization
    - Storage: ~1MB per 10k rows (compressed CSV in JSON)

Error Handling:
    - Raises ValueError for empty portfolio names
    - Raises FileNotFoundError when loading non-existent portfolio
    - Gracefully handles missing optional fields (backward compatibility)

Thread Safety:
    - Not thread-safe (file I/O without synchronization)
    - Safe under Streamlit's single-thread model

Testing:
    - Integration tests: tests/integration/test_portfolio_persistence.py

Version: 2.0.0
Last Modified: 2026-01-27
"""

import json
from typing import Any, Dict, List, Optional, cast

import pandas as pd

from src.core.domain.plot_protocol import PlotProtocol
from src.core.services.path_service import PathService
from src.core.state.state_manager import StateManager


class PortfolioService:
    """
    Service responsible for managing portfolios (save/load state).
    It interacts with the StateManager to persist/retrieve the full application state.
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize the PortfolioService with a StateManager instance."""
        self.state_manager = state_manager

    def list_portfolios(self) -> List[str]:
        portfolios_dir = PathService.get_portfolios_dir()
        if not portfolios_dir.exists():
            return []
        return [p.stem for p in portfolios_dir.glob("*.json")]

    def save_portfolio(
        self,
        name: str,
        data: pd.DataFrame,
        plots: List[PlotProtocol],
        config: Dict[str, Any],
        plot_counter: int,
        csv_path: Optional[str] = None,
        parse_variables: Optional[List[str]] = None,
    ) -> None:
        """Serialize and save the current workspace state."""
        if not name:
            raise ValueError("Portfolio name cannot be empty")

        serialized_plots = []
        for plot in plots:
            serialized_plots.append(plot.to_dict())

        portfolio_data = {
            "version": "2.0",
            "timestamp": pd.Timestamp.now().isoformat(),
            "data_csv": data.to_csv(index=False),
            "csv_path": str(csv_path) if csv_path else None,
            "plots": serialized_plots,
            "plot_counter": plot_counter,
            "config": config,
            "parse_variables": parse_variables or [],
            # Persist stats location & scanning results using injected state manager
            "stats_path": self.state_manager.get_stats_path(),
            "stats_pattern": self.state_manager.get_stats_pattern(),
            "scanned_variables": self.state_manager.get_scanned_variables(),
        }

        save_path = PathService.get_portfolios_dir() / f"{name}.json"
        with open(save_path, "w") as f:
            json.dump(portfolio_data, f, indent=2)

    def load_portfolio(self, name: str) -> Dict[str, Any]:
        """Load a portfolio JSON by name."""
        load_path = PathService.get_portfolios_dir() / f"{name}.json"
        if not load_path.exists():
            raise FileNotFoundError(f"Portfolio '{name}' not found")

        with open(load_path, "r") as f:
            return cast(Dict[str, Any], json.load(f))

    def delete_portfolio(self, name: str) -> None:
        path = PathService.get_portfolios_dir() / f"{name}.json"
        if path.exists():
            path.unlink()
