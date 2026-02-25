"""
Simple test to verify RING-5 configuration system.
Run: pytest tests/test_basic.py -v
"""

import json
from pathlib import Path
from typing import Any, cast

from src.core.services.config_validation_service import (
    ConfigTemplateGenerator,
    ConfigValidator,
)


def test_minimal_config_validation() -> None:
    """Test that minimal config passes validation."""
    config = {
        "name": "test_pipeline",
        "pipeline": [],
    }

    validator = ConfigValidator()
    assert validator.validate(config) is True


def test_invalid_config_detection() -> None:
    """Test that invalid config is detected."""
    config = {
        "name": "test"
        # Missing required 'pipeline' field
    }

    validator = ConfigValidator()
    errors = validator.get_errors(config)

    assert len(errors) > 0
    assert any("pipeline" in error for error in errors)


def test_template_generation() -> None:
    """Test template generation."""
    config = ConfigTemplateGenerator.create_minimal_config("./output", "/path/to/stats")

    assert config["outputPath"] == "./output"
    assert config["parseConfig"]["statsPath"] == "/path/to/stats"
    assert config["parseConfig"]["parser"] == "gem5_stats"
    assert isinstance(config["plots"], list)


def test_plot_config_creation() -> None:
    """Test plot configuration creation."""
    plot = ConfigTemplateGenerator.create_plot_config(
        "bar", "benchmark", "simTicks", "test_plot", title="Test Plot", grid=True
    )

    assert plot["type"] == "bar"
    data = cast(dict[str, Any], plot["data"])
    assert data["x"] == "benchmark"
    assert data["y"] == "simTicks"
    assert plot["output"]["filename"] == "test_plot"
    style = cast(dict[str, Any], plot["style"])
    assert style["title"] == "Test Plot"
    assert style["grid"] is True


def test_variable_addition() -> None:
    """Test adding variables to configuration."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")
    config_dict = cast(dict[str, Any], config)

    ConfigTemplateGenerator.add_variable(config_dict, "simTicks", "scalar")
    ConfigTemplateGenerator.add_variable(config_dict, "benchmark", "configuration")

    variables = cast(list[dict[str, Any]], config["parseConfig"]["variables"])
    assert len(variables) == 2
    assert variables[0]["name"] == "simTicks"
    assert variables[0]["type"] == "scalar"


def test_seeds_reducer_enable() -> None:
    """Test enabling seeds reducer."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")
    config_dict = cast(dict[str, Any], config)

    ConfigTemplateGenerator.enable_seeds_reducer(config_dict)

    dm = cast(dict[str, Any], config["dataManagers"])
    assert dm["seedsReducer"] is True


def test_outlier_removal_config() -> None:
    """Test outlier removal configuration."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")
    config_dict = cast(dict[str, Any], config)

    ConfigTemplateGenerator.enable_outlier_removal(
        config_dict, "simTicks", method="iqr", threshold=1.5
    )

    dm = cast(dict[str, Any], config["dataManagers"])
    assert dm["outlierRemover"]["enabled"] is True
    assert dm["outlierRemover"]["column"] == "simTicks"
    assert dm["outlierRemover"]["method"] == "iqr"


def test_normalizer_config() -> None:
    """Test normalizer configuration."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")
    config_dict = cast(dict[str, Any], config)

    ConfigTemplateGenerator.enable_normalizer(
        config_dict, baseline={"config": "baseline"}, columns=["simTicks"], group_by=["benchmark"]
    )

    dm = cast(dict[str, Any], config["dataManagers"])
    assert dm["normalizer"]["enabled"] is True
    assert dm["normalizer"]["baseline"]["config"] == "baseline"
    assert "simTicks" in dm["normalizer"]["columns"]


def test_example_config_validity() -> None:
    """Test that the example configuration is valid."""
    example_path = Path(__file__).parent.parent / "examples" / "complete_example.json"

    if example_path.exists():
        with open(example_path) as f:
            config = json.load(f)

        # Remove comments (not valid in strict JSON)
        def remove_comments(obj: Any) -> Any:

            if isinstance(obj, dict):
                return {k: remove_comments(v) for k, v in obj.items() if not k.startswith("$")}
            elif isinstance(obj, list):
                return [remove_comments(item) for item in obj]
            return obj

        config = remove_comments(config)

        validator = ConfigValidator()
        errors = validator.get_errors(config)

        assert len(errors) == 0, "Example configuration should be valid"
