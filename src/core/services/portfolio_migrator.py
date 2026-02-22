"""Portfolio schema migration for backward compatibility.

Migrates portfolio JSON between schema versions so that portfolios
saved under older schemas can be loaded by the current application.

Schema versions:
    - **V1** (original): flat config dicts, ``export_*`` keys for LaTeX.
    - **V2** (current): ``engine`` field per plot, no ``export_*`` keys.
"""

from __future__ import annotations

from typing import Any


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
        """Migrate portfolio to current schema version.

        Args:
            portfolio_data: Raw portfolio dictionary loaded from JSON.

        Returns:
            Portfolio dictionary at ``CURRENT_VERSION``.
        """
        version: int = int(portfolio_data.get("schema_version", 1))

        if version < 2:
            portfolio_data = PortfolioMigrator._migrate_v1_to_v2(portfolio_data)

        portfolio_data["schema_version"] = PortfolioMigrator.CURRENT_VERSION
        return portfolio_data

    @staticmethod
    def _migrate_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
        """V1 → V2: add engine field, clean export keys.

        Changes:
            - Sets ``config["engine"]`` to ``"plotly"`` (default) if absent.
            - Removes all ``export_*`` keys from each plot config (they
              are superseded by the download section in V2).
            - Preserves unknown keys for forward compatibility.
        """
        plots: list[dict[str, Any]] = data.get("plots", [])
        for plot in plots:
            config: dict[str, Any] = plot.get("config", {})
            config.setdefault("engine", "plotly")
            keys_to_remove: list[str] = [k for k in config if k.startswith("export_")]
            for k in keys_to_remove:
                del config[k]
        return data
