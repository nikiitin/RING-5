"""Integration tests for portfolio migration (Step 34).

Tests end-to-end migration scenarios: V1 load, V2 passthrough,
roundtrip save → load → verify.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from src.core.visualization.connectors.builders import ConfigSpecBuilder
from src.core.visualization.figure_spec import FigureSpec
from src.web.services.portfolio_migrator import PortfolioMigrator


class TestV1LoadAndMigrate:
    """Load a V1-shaped portfolio, migrate, verify valid structure."""

    def test_v1_portfolio_produces_valid_v2(self) -> None:
        """V1 portfolio migrates to V2 with engine and no export keys."""
        v1: Dict[str, Any] = {
            "version": "1.0",
            "plots": [
                {
                    "name": "IPC analysis",
                    "plot_type": "grouped_bar",
                    "config": {
                        "width": 800,
                        "height": 500,
                        "export_format": "pdf",
                        "export_dpi": 300,
                        "title_font_size": 14,
                    },
                }
            ],
        }
        result = PortfolioMigrator.migrate(v1)
        assert result["schema_version"] == 2
        cfg = result["plots"][0]["config"]
        assert cfg["engine"] == "plotly"
        assert "export_format" not in cfg
        assert "export_dpi" not in cfg
        assert cfg["width"] == 800
        assert cfg["title_font_size"] == 14

    def test_v1_config_builds_valid_figure_spec(self) -> None:
        """Migrated V1 config can build a FigureSpec without errors."""
        v1: Dict[str, Any] = {
            "plots": [
                {
                    "plot_type": "grouped_bar",
                    "config": {
                        "width": 800,
                        "height": 500,
                        "export_format": "pdf",
                        "margin_l": 100,
                    },
                }
            ],
        }
        migrated = PortfolioMigrator.migrate(v1)
        cfg = migrated["plots"][0]["config"]
        spec = ConfigSpecBuilder.from_config(cfg, "grouped_bar")
        assert isinstance(spec, FigureSpec)
        assert spec.dimensions.width == 800.0


class TestV2Passthrough:
    """V2 portfolio needs no migration, passes through unchanged."""

    def test_v2_no_modification(self) -> None:
        original: Dict[str, Any] = {
            "schema_version": 2,
            "plots": [
                {
                    "config": {"engine": "matplotlib", "width": 600},
                    "figure_spec": {"dimensions": {"width": 600}},
                }
            ],
        }
        result = PortfolioMigrator.migrate(original)
        assert result["plots"][0]["config"]["engine"] == "matplotlib"
        assert result["plots"][0]["figure_spec"]["dimensions"]["width"] == 600


class TestRoundtrip:
    """Save → load → verify identical FigureSpec."""

    def test_spec_roundtrip_via_dict(self) -> None:
        """FigureSpec.to_dict → from_dict produces equivalent spec."""
        config: Dict[str, Any] = {
            "width": 800,
            "height": 500,
            "margin_l": 100,
            "margin_r": 80,
            "margin_t": 60,
            "margin_b": 120,
            "title_font_size": 14,
        }
        spec = ConfigSpecBuilder.from_config(config, "grouped_bar")
        spec_dict = spec.to_dict()
        restored = FigureSpec.from_dict(spec_dict)
        assert restored.dimensions.width == spec.dimensions.width
        assert restored.dimensions.height == spec.dimensions.height

    def test_portfolio_save_load_roundtrip(self) -> None:
        """Serialize portfolio → JSON → deserialize → migrate → verify."""
        portfolio: Dict[str, Any] = {
            "schema_version": 2,
            "plots": [
                {
                    "name": "test",
                    "plot_type": "grouped_bar",
                    "config": {"width": 800, "engine": "plotly"},
                }
            ],
        }
        # Simulate save/load via JSON serialization
        json_str = json.dumps(portfolio)
        loaded: Dict[str, Any] = json.loads(json_str)
        migrated = PortfolioMigrator.migrate(loaded)

        assert migrated["schema_version"] == 2
        assert migrated["plots"][0]["config"]["width"] == 800
        assert migrated["plots"][0]["config"]["engine"] == "plotly"


class TestMultiplePlotMigration:
    """Test migration with multiple plots of different types."""

    def test_mixed_plot_types(self) -> None:
        v1: Dict[str, Any] = {
            "plots": [
                {
                    "plot_type": "grouped_bar",
                    "config": {"width": 800, "export_format": "pdf"},
                },
                {
                    "plot_type": "line",
                    "config": {"width": 600, "export_dpi": 300},
                },
                {
                    "plot_type": "scatter",
                    "config": {"width": 1000},
                },
            ],
        }
        result = PortfolioMigrator.migrate(v1)
        assert len(result["plots"]) == 3
        for plot in result["plots"]:
            assert plot["config"]["engine"] == "plotly"
            assert not any(k.startswith("export_") for k in plot["config"])
