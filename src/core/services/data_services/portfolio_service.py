"""Save, migrate, and restore application portfolios."""

import json
import logging
from collections.abc import Callable
from typing import Any, cast

import pandas as pd

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.models import ParseVariableConfig, PlotProtocol, PortfolioData
from src.core.services.data_services.path_service import PathService
from src.core.services.portfolio_migrator import PortfolioMigrator
from src.core.state.state_manager import StateManager
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService


class PortfolioService:
    """
    Service responsible for managing portfolios (save/load state).
    It interacts with the StateManager to persist/retrieve the full application state.
    """

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize the PortfolioService with a StateManager instance."""
        self.state_manager = state_manager

    def list_portfolios(self) -> list[str]:
        # [impl->req~ring5.portfolio.manage~1]
        """Return saved portfolio names."""
        portfolios_dir = PathService.get_portfolios_dir()
        if not portfolios_dir.exists():
            return []
        return [p.stem for p in portfolios_dir.glob("*.json")]

    def save_portfolio(
        self,
        name: str,
        data: pd.DataFrame | None,
        plots: list[PlotProtocol],
        config: dict[str, Any],
        plot_counter: int,
        csv_path: str | None = None,
        parse_variables: list[ParseVariableConfig] | None = None,
        figure_spec_enricher: None | (
            Callable[[dict[str, Any], str], dict[str, Any] | None]
        ) = None,
        overwrite: bool = True,
    ) -> None:
        # [impl->req~ring5.portfolio.save~1]
        # [impl->req~ring5.data.semantic-units~1]
        """Serialize and save the current workspace state.

        Args:
            name: Portfolio name.
            data: Current DataFrame (may be None).
            plots: Active plot objects implementing PlotProtocol.
            config: Global configuration dict.
            plot_counter: Current plot counter for ID generation.
            csv_path: Path to the original CSV file.
            parse_variables: Parse-variable config dicts (the shape
                ``StateManager.get_parse_variables()`` returns); a plain list
                of strings would crash ``restore_session`` on load.
            figure_spec_enricher: Optional callback from the presentation layer
                that converts a plot config dict and plot_type into a
                FigureConfig dict. Injected to avoid core→web imports.
            overwrite: When False, raise FileExistsError instead of replacing
                an existing portfolio of the same name (portfolios are keyed
                by name alone — the default silently overwrites).
        """
        if not name:
            raise ValueError("Portfolio name cannot be empty")

        logger = logging.getLogger(__name__)
        serialized_plots: list[dict[str, Any]] = []
        for plot in plots:
            plot_dict: dict[str, Any] = plot.to_dict()
            plot_config: dict[str, Any] = plot_dict.get("config", {})
            if figure_spec_enricher is not None:
                try:
                    spec_dict = figure_spec_enricher(plot_config, plot_dict.get("plot_type", ""))
                    if spec_dict is not None:
                        plot_dict["figure_spec"] = spec_dict
                except Exception:
                    logger.debug(
                        "Could not build FigureConfig for plot %s; saving without it",
                        plot_dict.get("name", "?"),
                    )
            serialized_plots.append(plot_dict)

        data_csv = data.to_csv(index=False) if data is not None and not data.empty else ""
        data_semantics = (
            SemanticMetadataService.to_payload(SemanticMetadataService.inspect(data))
            if data is not None
            else {}
        )

        portfolio_data: dict[str, Any] = {
            "schema_version": PortfolioMigrator.CURRENT_VERSION,
            "version": "2.0",
            "timestamp": pd.Timestamp.now().isoformat(),
            "data_csv": data_csv,
            "data_semantics": data_semantics,
            "csv_path": str(csv_path) if csv_path else None,
            "plots": serialized_plots,
            "plot_counter": plot_counter,
            "config": config,
            "parse_variables": parse_variables or [],
            # Persist parser-vs-CSV mode so restore reinstates it (PortfolioData documents
            # the key; restore reads it — without this it always defaults back to CSV).
            "use_parser": self.state_manager.is_using_parser(),
            # Persist stats location & scanning results using injected state manager
            "stats_path": self.state_manager.get_stats_path(),
            "stats_pattern": self.state_manager.get_stats_pattern(),
            "scanned_variables": self.state_manager.get_scanned_variables(),
            # Persist operation history
            "manager_history": self.state_manager.get_manager_history(),
            "portfolio_history": self.state_manager.get_portfolio_history(),
        }

        save_path = validate_path_within(
            PathService.get_portfolios_dir() / f"{sanitize_filename(name)}.json",
            PathService.get_portfolios_dir(),
        )
        # 'x' = atomic exclusive create: a check-then-write would let two
        # concurrent savers both pass the check and silently clobber.
        mode = "w" if overwrite else "x"
        try:
            with open(save_path, mode) as f:
                json.dump(portfolio_data, f, indent=2)
        except FileExistsError as exc:
            raise FileExistsError(f"Portfolio '{name}' already exists at {save_path}") from exc

    def load_portfolio(self, name: str) -> PortfolioData:
        """Load a portfolio JSON by name.

        Runs schema migration via :class:`PortfolioMigrator` to ensure
        backward compatibility with older portfolio formats.
        """
        load_path = validate_path_within(
            PathService.get_portfolios_dir() / f"{sanitize_filename(name)}.json",
            PathService.get_portfolios_dir(),
        )
        if not load_path.exists():
            raise FileNotFoundError(f"Portfolio '{name}' not found")

        with open(load_path) as f:
            raw: dict[str, Any] = cast(dict[str, Any], json.load(f))

        return cast(PortfolioData, PortfolioMigrator.migrate(raw))

    def delete_portfolio(self, name: str) -> None:
        # [impl->req~ring5.portfolio.manage~1]
        """Delete a portfolio if it exists.

        Args:
            name: Portfolio name, without a filename extension.
        """
        path = validate_path_within(
            PathService.get_portfolios_dir() / f"{sanitize_filename(name)}.json",
            PathService.get_portfolios_dir(),
        )
        if path.exists():
            path.unlink()
