"""Tests for PortfolioMigrator (Step 32)."""

from __future__ import annotations

from typing import Any, Dict

from src.core.services.portfolio_migrator import PortfolioMigrator


class TestV1Migration:
    """V1 → V2 migration adds engine and removes export_ keys."""

    def test_adds_engine_field(self) -> None:
        """Each plot config gets engine='plotly' if absent."""
        v1: Dict[str, Any] = {
            "plots": [{"config": {"width": 800}}, {"config": {"height": 500}}],
        }
        result = PortfolioMigrator.migrate(v1)
        for plot in result["plots"]:
            assert plot["config"]["engine"] == "plotly"

    def test_removes_export_keys(self) -> None:
        """All export_* keys are removed from config."""
        v1: Dict[str, Any] = {
            "plots": [
                {
                    "config": {
                        "width": 800,
                        "export_format": "pdf",
                        "export_dpi": 300,
                        "export_path": "/tmp/out",
                    }
                }
            ],
        }
        result = PortfolioMigrator.migrate(v1)
        config = result["plots"][0]["config"]
        assert "export_format" not in config
        assert "export_dpi" not in config
        assert "export_path" not in config
        assert config["width"] == 800

    def test_sets_schema_version_2(self) -> None:
        """Migrated portfolio has schema_version=2."""
        v1: Dict[str, Any] = {"plots": [{"config": {}}]}
        result = PortfolioMigrator.migrate(v1)
        assert result["schema_version"] == 2


class TestUnknownKeysPreserved:
    """Custom keys survive migration untouched."""

    def test_custom_key_preserved(self) -> None:
        v1: Dict[str, Any] = {
            "plots": [{"config": {"custom_key": "value", "my_setting": 42}}],
        }
        result = PortfolioMigrator.migrate(v1)
        config = result["plots"][0]["config"]
        assert config["custom_key"] == "value"
        assert config["my_setting"] == 42


class TestIdempotent:
    """Migrating an already V2 portfolio is a no-op."""

    def test_already_v2_no_change(self) -> None:
        v2: Dict[str, Any] = {
            "schema_version": 2,
            "plots": [{"config": {"engine": "matplotlib", "width": 800}}],
        }
        result = PortfolioMigrator.migrate(v2)
        assert result["schema_version"] == 2
        assert result["plots"][0]["config"]["engine"] == "matplotlib"
        assert result["plots"][0]["config"]["width"] == 800

    def test_double_migration_identical(self) -> None:
        v1: Dict[str, Any] = {
            "plots": [{"config": {"export_format": "svg"}}],
        }
        first = PortfolioMigrator.migrate(v1)
        second = PortfolioMigrator.migrate(first)
        assert first == second


class TestEdgeCases:
    """Edge cases for migrator robustness."""

    def test_empty_plots_list(self) -> None:
        data: Dict[str, Any] = {"plots": []}
        result = PortfolioMigrator.migrate(data)
        assert result["schema_version"] == 2
        assert result["plots"] == []

    def test_missing_plots_key(self) -> None:
        data: Dict[str, Any] = {}
        result = PortfolioMigrator.migrate(data)
        assert result["schema_version"] == 2

    def test_plot_without_config(self) -> None:
        data: Dict[str, Any] = {"plots": [{"name": "test"}]}
        result = PortfolioMigrator.migrate(data)
        assert result["schema_version"] == 2

    def test_preserves_engine_if_already_set(self) -> None:
        """V1 portfolio with explicit engine keeps it."""
        v1: Dict[str, Any] = {
            "plots": [{"config": {"engine": "matplotlib"}}],
        }
        result = PortfolioMigrator.migrate(v1)
        assert result["plots"][0]["config"]["engine"] == "matplotlib"
