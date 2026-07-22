"""Tests for ``PortfolioMigrator``."""

from __future__ import annotations

from typing import Any, Dict

from src.core.services.portfolio_migrator import PortfolioMigrator


class TestV1Migration:
    """V1 migration adds engine, removes export keys, and marks missing provenance."""

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

    def test_sets_current_schema_and_honest_missing_environment(self) -> None:
        """Old portfolios cannot retroactively claim current-machine provenance."""
        v1: Dict[str, Any] = {"plots": [{"config": {}}]}
        result = PortfolioMigrator.migrate(v1)
        assert result["schema_version"] == 4
        assert result["version"] == "4.0"
        assert result["environment_metadata"] is None
        assert result["integrity_manifest"] is None


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
    """Migrating an already-current portfolio is a no-op."""

    def test_already_v4_no_change(self) -> None:
        v3: Dict[str, Any] = {
            "schema_version": 4,
            "environment_metadata": {"custom": "preserved"},
            "integrity_manifest": {"custom": "preserved"},
            "plots": [{"config": {"engine": "matplotlib", "width": 800}}],
        }
        result = PortfolioMigrator.migrate(v3)
        assert result["schema_version"] == 4
        assert result["environment_metadata"] == {"custom": "preserved"}
        assert result["integrity_manifest"] == {"custom": "preserved"}
        assert result["plots"][0]["config"]["engine"] == "matplotlib"
        assert result["plots"][0]["config"]["width"] == 800

    def test_v2_records_environment_as_unavailable(self) -> None:
        v2: Dict[str, Any] = {"schema_version": 2, "plots": []}
        result = PortfolioMigrator.migrate(v2)
        assert result["schema_version"] == 4
        assert result["environment_metadata"] is None
        assert result["integrity_manifest"] is None

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
        assert result["schema_version"] == 4
        assert result["plots"] == []

    def test_missing_plots_key(self) -> None:
        data: Dict[str, Any] = {}
        result = PortfolioMigrator.migrate(data)
        assert result["schema_version"] == 4

    def test_plot_without_config(self) -> None:
        data: Dict[str, Any] = {"plots": [{"name": "test"}]}
        result = PortfolioMigrator.migrate(data)
        assert result["schema_version"] == 4

    def test_preserves_engine_if_already_set(self) -> None:
        """V1 portfolio with explicit engine keeps it."""
        v1: Dict[str, Any] = {
            "plots": [{"config": {"engine": "matplotlib"}}],
        }
        result = PortfolioMigrator.migrate(v1)
        assert result["plots"][0]["config"]["engine"] == "matplotlib"


class TestForwardVersionGuard:
    """A newer-schema portfolio must be refused, never silently downgraded."""

    def test_newer_schema_version_raises(self) -> None:
        import pytest

        from src.core.services.portfolio_migrator import PortfolioVersionError

        v4: Dict[str, Any] = {
            "schema_version": 5,
            "plots": [{"plot_type": "sankey_3d", "config": {}}],
            "v4_only_key": {"future": "data"},
        }
        with pytest.raises(PortfolioVersionError, match="newer than this RING-5"):
            PortfolioMigrator.migrate(v4)

    def test_current_version_still_loads(self) -> None:
        data: Dict[str, Any] = {"schema_version": 4, "plots": []}
        result = PortfolioMigrator.migrate(data)
        assert result["schema_version"] == 4
