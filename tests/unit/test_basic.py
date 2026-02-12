"""
Simple test to verify RING-5 configuration system.
Run: pytest tests/test_basic.py -v
"""

import json
from pathlib import Path

from src.core.models.config.config_manager import ConfigTemplateGenerator, ConfigValidator


def test_minimal_config_validation():
    """Test that minimal config passes validation."""
    config = {
        "name": "test_pipeline",
        "pipeline": [],
    }

    validator = ConfigValidator()
    assert validator.validate(config) is True


def test_invalid_config_detection():
    """Test that invalid config is detected."""
    config = {
        "name": "test"
        # Missing required 'pipeline' field
    }

    validator = ConfigValidator()
    errors = validator.get_errors(config)

    assert len(errors) > 0
    assert any("pipeline" in error for error in errors)


def test_template_generation():
    """Test template generation."""
    config = ConfigTemplateGenerator.create_minimal_config("./output", "/path/to/stats")

    assert config["outputPath"] == "./output"
    assert config["parseConfig"]["statsPath"] == "/path/to/stats"
    assert config["parseConfig"]["parser"] == "gem5_stats"
    assert isinstance(config["plots"], list)


def test_plot_config_creation():
    """Test plot configuration creation."""
    plot = ConfigTemplateGenerator.create_plot_config(
        "bar", "benchmark", "simTicks", "test_plot", title="Test Plot", grid=True
    )

    assert plot["type"] == "bar"
    assert plot["data"]["x"] == "benchmark"
    assert plot["data"]["y"] == "simTicks"
    assert plot["output"]["filename"] == "test_plot"
    assert plot["style"]["title"] == "Test Plot"
    assert plot["style"]["grid"] is True


def test_variable_addition():
    """Test adding variables to configuration."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")

    ConfigTemplateGenerator.add_variable(config, "simTicks", "scalar")
    ConfigTemplateGenerator.add_variable(config, "benchmark", "configuration")

    assert len(config["parseConfig"]["variables"]) == 2
    assert config["parseConfig"]["variables"][0]["name"] == "simTicks"
    assert config["parseConfig"]["variables"][0]["type"] == "scalar"


def test_seeds_reducer_enable():
    """Test enabling seeds reducer."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")

    ConfigTemplateGenerator.enable_seeds_reducer(config)

    assert config["dataManagers"]["seedsReducer"] is True


def test_outlier_removal_config():
    """Test outlier removal configuration."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")

    ConfigTemplateGenerator.enable_outlier_removal(config, "simTicks", method="iqr", threshold=1.5)

    assert config["dataManagers"]["outlierRemover"]["enabled"] is True
    assert config["dataManagers"]["outlierRemover"]["column"] == "simTicks"
    assert config["dataManagers"]["outlierRemover"]["method"] == "iqr"


def test_normalizer_config():
    """Test normalizer configuration."""
    config = ConfigTemplateGenerator.create_minimal_config("./out", "/stats")

    ConfigTemplateGenerator.enable_normalizer(
        config, baseline={"config": "baseline"}, columns=["simTicks"], group_by=["benchmark"]
    )

    assert config["dataManagers"]["normalizer"]["enabled"] is True
    assert config["dataManagers"]["normalizer"]["baseline"]["config"] == "baseline"
    assert "simTicks" in config["dataManagers"]["normalizer"]["columns"]


def test_example_config_validity():
    """Test that the example configuration is valid."""
    example_path = Path(__file__).parent.parent / "examples" / "complete_example.json"

    if example_path.exists():
        with open(example_path) as f:
            config = json.load(f)

        # Remove comments (not valid in strict JSON)
        def remove_comments(obj):
            if isinstance(obj, dict):
                return {k: remove_comments(v) for k, v in obj.items() if not k.startswith("$")}
            elif isinstance(obj, list):
                return [remove_comments(item) for item in obj]
            return obj

        config = remove_comments(config)

        validator = ConfigValidator()
        errors = validator.get_errors(config)

        assert len(errors) == 0, "Example configuration should be valid"
