import json
from typing import Any, Dict, List, Optional

import pandas as pd

from src.plotting import BasePlot
from src.web.services.paths import PathService
from src.web.state_manager import StateManager


class PortfolioService:
    """Service to handle saving and loading full portfolios."""

    @staticmethod
    def list_portfolios() -> List[str]:
        portfolios_dir = PathService.get_portfolios_dir()
        if not portfolios_dir.exists():
            return []
        return [p.stem for p in portfolios_dir.glob("*.json")]

    @staticmethod
    def save_portfolio(
        name: str,
        data: pd.DataFrame,
        plots: List[BasePlot],
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
            # Persist stats location & scanning results
            "stats_path": StateManager.get_stats_path(),
            "stats_pattern": StateManager.get_stats_pattern(),
            "scanned_variables": StateManager.get_scanned_variables(),
        }

        save_path = PathService.get_portfolios_dir() / f"{name}.json"
        with open(save_path, "w") as f:
            json.dump(portfolio_data, f, indent=2)

    @staticmethod
    def load_portfolio(name: str) -> Dict[str, Any]:
        """Load a portfolio JSON by name."""
        load_path = PathService.get_portfolios_dir() / f"{name}.json"
        if not load_path.exists():
            raise FileNotFoundError(f"Portfolio '{name}' not found")

        with open(load_path, "r") as f:
            return json.load(f)

    @staticmethod
    def delete_portfolio(name: str) -> None:
        path = PathService.get_portfolios_dir() / f"{name}.json"
        if path.exists():
            path.unlink()
