"""Save, migrate, and restore application portfolios."""

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pandas as pd

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.models import (
    ParseVariableConfig,
    PlotProtocol,
    PortfolioData,
    PortfolioDiff,
    PortfolioIntegrityReport,
    PortfolioRevisionInfo,
)
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.portfolio_revision_service import (
    PortfolioRevisionService,
)
from src.core.services.environment_metadata_service import EnvironmentMetadataService
from src.core.services.portfolio_migrator import PortfolioMigrator
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
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
        signing_key: str | bytes | None = None,
        signing_key_id: str = "default",
    ) -> None:
        # [impl->req~ring5.portfolio.save~1]
        # [impl->req~ring5.data.semantic-units~1]
        # [impl->req~ring5.portfolio.environment-metadata~1]
        # [impl->req~ring5.portfolio.signed-manifests~1]
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
            signing_key: Optional shared secret for an HMAC-SHA-256 signature.
            signing_key_id: Non-secret label stored with a signature.
        """
        if not name:
            raise ValueError("Portfolio name cannot be empty")
        payload = self.serialize_workspace(
            data,
            plots,
            config,
            plot_counter,
            csv_path=csv_path,
            parse_variables=parse_variables,
            figure_spec_enricher=figure_spec_enricher,
            signing_key=signing_key,
            signing_key_id=signing_key_id,
        )

        save_path = self._portfolio_path(name)
        try:
            PortfolioRevisionService.retain_and_replace(
                name,
                payload,
                save_path,
                overwrite=overwrite,
            )
        except FileExistsError as exc:
            raise FileExistsError(f"Portfolio '{name}' already exists at {save_path}") from exc

    def serialize_workspace(
        self,
        data: pd.DataFrame | None,
        plots: list[PlotProtocol],
        config: dict[str, Any],
        plot_counter: int,
        *,
        csv_path: str | None = None,
        parse_variables: list[ParseVariableConfig] | None = None,
        figure_spec_enricher: None | (
            Callable[[dict[str, Any], str], dict[str, Any] | None]
        ) = None,
        signing_key: str | bytes | None = None,
        signing_key_id: str = "default",
    ) -> bytes:
        """Serialize current state into the integrity-checked portfolio format."""
        # [impl->req~ring5.workspace.autosave-recovery~1]
        logger = logging.getLogger(__name__)
        serialized_plots: list[dict[str, Any]] = []
        for plot in plots:
            plot_dict: dict[str, Any] = plot.to_dict()
            plot_config: dict[str, Any] = plot_dict.get("config", {})
            if figure_spec_enricher is not None:
                try:
                    spec_dict = figure_spec_enricher(
                        plot_config,
                        plot_dict.get("plot_type", ""),
                    )
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
            "version": "4.0",
            "timestamp": pd.Timestamp.now().isoformat(),
            "environment_metadata": EnvironmentMetadataService.capture().to_dict(),
            "data_csv": data_csv,
            "data_semantics": data_semantics,
            "csv_path": str(csv_path) if csv_path else None,
            "plots": serialized_plots,
            "plot_counter": plot_counter,
            "config": config,
            "parse_variables": parse_variables or [],
            "use_parser": self.state_manager.is_using_parser(),
            "stats_path": self.state_manager.get_stats_path(),
            "stats_pattern": self.state_manager.get_stats_pattern(),
            "scanned_variables": self.state_manager.get_scanned_variables(),
            "manager_history": self.state_manager.get_manager_history(),
            "portfolio_history": self.state_manager.get_portfolio_history(),
        }
        portfolio_data["integrity_manifest"] = PortfolioIntegrityService.create_manifest(
            portfolio_data,
            signing_key=signing_key,
            key_id=signing_key_id,
        )
        return json.dumps(portfolio_data, indent=2).encode("utf-8")

    def load_portfolio(
        self,
        name: str,
        *,
        signing_key: str | bytes | None = None,
        require_signature: bool = False,
    ) -> PortfolioData:
        # [impl->req~ring5.portfolio.signed-manifests~1]
        """Load a portfolio JSON by name.

        Runs schema migration via :class:`PortfolioMigrator` to ensure
        backward compatibility with older portfolio formats.
        """
        load_path = self._portfolio_path(name)
        if not load_path.exists():
            raise FileNotFoundError(f"Portfolio '{name}' not found")

        with open(load_path, encoding="utf-8") as f:
            value = json.load(f)
        if not isinstance(value, dict):
            raise ValueError("Portfolio JSON must contain one top-level object.")
        raw: dict[str, Any] = value

        report = PortfolioIntegrityService.verify(raw, signing_key=signing_key)
        PortfolioIntegrityService.require_restorable(
            report,
            require_signature=require_signature,
        )
        return cast(PortfolioData, PortfolioMigrator.migrate(raw))

    def verify_portfolio(
        self,
        name: str,
        *,
        signing_key: str | bytes | None = None,
    ) -> PortfolioIntegrityReport:
        # [impl->req~ring5.portfolio.signed-manifests~1]
        """Return checksum and optional signature evidence without restoring state.

        Args:
            name: Saved portfolio name.
            signing_key: Optional shared secret for HMAC verification.

        Returns:
            Structured integrity status for the exact saved content.
        """
        load_path = self._portfolio_path(name)
        if not load_path.exists():
            raise FileNotFoundError(f"Portfolio '{name}' not found")
        with open(load_path, encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError("Portfolio JSON must contain one top-level object.")
        return PortfolioIntegrityService.verify(raw, signing_key=signing_key)

    def export_portfolio_bytes(self, name: str) -> bytes:
        """Return exact manifest-verified portfolio bytes for portable packaging.

        Args:
            name: Saved portfolio name.

        Returns:
            Exact JSON file bytes after content-integrity verification.
        """
        load_path = self._portfolio_path(name)
        if not load_path.exists():
            raise FileNotFoundError(f"Portfolio '{name}' not found")
        payload = load_path.read_bytes()
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"Portfolio '{name}' is not valid UTF-8 JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("Portfolio JSON must contain one top-level object.")
        report = PortfolioIntegrityService.verify(value)
        PortfolioIntegrityService.require_restorable(report)
        PortfolioMigrator.migrate(value)
        return payload

    def list_portfolio_revisions(self, name: str) -> tuple[PortfolioRevisionInfo, ...]:
        # [impl->req~ring5.portfolio.history-diff~1]
        """List immutable saved versions for a named portfolio."""
        return PortfolioRevisionService.list_revisions(name, self._portfolio_path(name))

    def load_portfolio_revision(self, name: str, revision_id: str) -> PortfolioData:
        # [impl->req~ring5.portfolio.history-diff~1]
        """Load one checksum-verified portfolio revision."""
        return PortfolioRevisionService.load_revision(name, revision_id)

    def compare_portfolio_revisions(
        self,
        name: str,
        before_revision: str,
        after_revision: str,
    ) -> PortfolioDiff:
        # [impl->req~ring5.portfolio.history-diff~1]
        """Return a bounded field-level comparison of two revisions."""
        return PortfolioRevisionService.compare(name, before_revision, after_revision)

    def delete_portfolio(self, name: str) -> None:
        # [impl->req~ring5.portfolio.manage~1]
        """Delete a portfolio if it exists.

        Args:
            name: Portfolio name, without a filename extension.
        """
        path = self._portfolio_path(name)
        if path.exists():
            path.unlink()
        PortfolioRevisionService.delete_history(name)

    @staticmethod
    def _portfolio_path(name: str) -> Path:
        directory = PathService.get_portfolios_dir()
        return validate_path_within(directory / f"{sanitize_filename(name)}.json", directory)
