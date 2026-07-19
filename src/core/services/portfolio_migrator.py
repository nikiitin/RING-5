"""Portfolio schema migration for backward compatibility.

Migrates portfolio JSON between schema versions so that portfolios
saved under older schemas can be loaded by the current application.

Schema versions:
    - **V1** (original): flat config dicts, ``export_*`` keys for LaTeX.
    - **V2** (current): ``engine`` field per plot, no ``export_*`` keys.
"""

from __future__ import annotations

from typing import Any

from src.core.models.visualization.engine import DEFAULT_ENGINE


class PortfolioVersionError(ValueError):
    """A portfolio's schema_version is newer than this RING-5 understands.

    Loading it anyway would silently downgrade-stamp the version, drop
    unknown plot types, and — on the next save — permanently destroy the
    newer data. Refusing to load is the only safe behavior.
    """


class PortfolioMigrator:
    """Migrate portfolio JSON between schema versions.

    All migrations are **idempotent** — applying a migration to an
    already-migrated portfolio is a safe no-op.

    Usage::

        raw = json.load(f)
        migrated = PortfolioMigrator.migrate(raw)
    """

    CURRENT_VERSION: int = 2

    @staticmethod
    def migrate(portfolio_data: dict[str, Any]) -> dict[str, Any]:
        # [impl->req~ring5.portfolio.migration~1]
        """Migrate portfolio to current schema version.

        Args:
            portfolio_data: Raw portfolio dictionary loaded from JSON.

        Returns:
            Portfolio dictionary at ``CURRENT_VERSION``.

        Raises:
            PortfolioVersionError: When the portfolio was written by a NEWER
                schema than this version understands (forward compatibility
                is refused, never silently downgraded).
        """
        version: int = int(portfolio_data.get("schema_version", 1))

        if version > PortfolioMigrator.CURRENT_VERSION:
            raise PortfolioVersionError(
                f"Portfolio schema_version {version} is newer than this RING-5 "
                f"supports (current: {PortfolioMigrator.CURRENT_VERSION}). "
                "Upgrade RING-5 to load it — loading here would silently drop "
                "newer data and destroy it on the next save."
            )

        if version < 2:
            portfolio_data = PortfolioMigrator._migrate_v1_to_v2(portfolio_data)
        else:
            # Shallow-copy so the already-current path never mutates the
            # caller's dict (only the top-level schema_version key is written).
            portfolio_data = dict(portfolio_data)

        portfolio_data["schema_version"] = PortfolioMigrator.CURRENT_VERSION
        return portfolio_data

    @staticmethod
    def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
        """V1 → V2: add engine field, clean export keys.

        Changes:
            - Sets ``config["engine"]`` to ``DEFAULT_ENGINE`` if absent.
            - Removes all ``export_*`` keys from each plot config (they
              are superseded by the download section in V2).
            - Preserves unknown keys for forward compatibility.

        Note:
            Works on a shallow copy to avoid mutating the caller's dict.
        """
        import copy

        data = copy.deepcopy(data)
        # Defend the trust boundary: migrate() runs on every load of untrusted/hand-edited
        # JSON, so malformed plots/config must not raise a raw AttributeError.
        plots_raw = data.get("plots", [])
        if not isinstance(plots_raw, list):
            return data
        for plot in plots_raw:
            if not isinstance(plot, dict):
                continue
            config = plot.get("config")
            if not isinstance(config, dict):
                config = {}
                plot["config"] = config
            config.setdefault("engine", DEFAULT_ENGINE)
            keys_to_remove: list[str] = [k for k in config if k.startswith("export_")]
            for k in keys_to_remove:
                del config[k]
        return data
