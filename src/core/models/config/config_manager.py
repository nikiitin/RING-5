"""
JSON Schema validator and template generator for RING-5 configuration files.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict, cast

from jsonschema import Draft7Validator, validate

from src.core.common.utils import sanitize_filename, validate_path_within

logger: logging.Logger = logging.getLogger(__name__)


class OutputConfig(TypedDict):
    """Type definition for plot output configuration."""

    filename: str
    format: str  # "png", "pdf", "svg"
    dpi: int


class PlotDataConfig(TypedDict, total=False):
    """Type definition for plot data configuration."""

    x: str
    y: str
    hue: str
    filters: Dict[str, Any]
    aggregate: str


class PlotStyleConfig(TypedDict, total=False):
    """Type definition for plot style configuration."""

    width: int
    height: int
    theme: str
    title: str
    xlabel: str
    ylabel: str
    ylim: List[float]
    grid: bool
    legend: Dict[str, Any]


class PlotConfig(TypedDict):
    """Type definition for complete plot configuration."""

    type: str
    output: OutputConfig
    data: PlotDataConfig
    style: PlotStyleConfig


class VariableConfig(TypedDict, total=False):
    """Type definition for variable parsing configuration."""

    name: str
    type: str  # "scalar", "vector", "distribution", "configuration"
    rename: str


class ParseConfig(TypedDict):
    """Type definition for parsing configuration."""

    parser: str
    statsPath: str
    statsPattern: str
    variables: List[VariableConfig]


class DataManagersConfig(TypedDict, total=False):
    """Type definition for data managers configuration."""

    seedsReducer: bool
    outlierRemover: Dict[str, Any]
    normalizer: Dict[str, Any]


class RingConfig(TypedDict):
    """Type definition for complete RING-5 configuration."""

    outputPath: str
    parseConfig: ParseConfig
    dataManagers: DataManagersConfig
    plots: List[PlotConfig]


class ConfigValidator:
    """Validates RING-5 configuration files against JSON schema."""

    def __init__(self, schema_path: Optional[str] = None) -> None:
        """
        Initialize the validator with a schema file.

        Args:
            schema_path: Path to JSON schema file. If None, uses default schema
        """
        schemas_dir = os.path.join(os.path.dirname(__file__), "schemas")
        if schema_path is None:
            schema_path = os.path.join(schemas_dir, "pipeline_schema.json")

        # Validate schema_path is within the schemas directory
        validated_schema = validate_path_within(Path(schema_path), Path(schemas_dir))
        with open(validated_schema, "r") as f:
            self.schema: Dict[str, Any] = json.load(f)

        self.validator: Draft7Validator = Draft7Validator(self.schema)

    def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate a configuration dictionary.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        validate(instance=config, schema=self.schema)
        return True

    def validate_file(self, config_path: str) -> bool:
        """
        Validate a configuration file.

        Args:
            config_path: Path to configuration JSON file

        Returns:
            True if valid

        Raises:
            ValidationError: If validation fails
        """
        resolved_path = Path(config_path).resolve()
        with open(resolved_path, "r") as f:
            config = json.load(f)

        return self.validate(config)

    def get_errors(self, config: Dict[str, Any]) -> List[str]:
        """
        Get all validation errors for a configuration.

        Args:
            config: Configuration dictionary

        Returns:
            List of error messages
        """
        errors: List[str] = []
        for error in self.validator.iter_errors(config):
            error_path: str = ".".join(str(p) for p in error.path)
            errors.append(f"{error_path}: {error.message}")

        return errors


class ConfigTemplateGenerator:
    """Generates configuration templates with guided prompts."""

    PLOT_TYPES: Dict[str, str] = {
        "bar": "Bar plot - vertical bars for comparing categories",
        "line": "Line plot - trends over continuous variables",
        "heatmap": "Heatmap - 2D matrix of values with color encoding",
        "grouped_bar": "Grouped bar plot - multiple bars per category",
        "stacked_bar": "Stacked bar plot - bars stacked on top of each other",
        "box": "Box plot - distribution with quartiles",
        "violin": "Violin plot - distribution with kernel density",
        "scatter": "Scatter plot - relationship between two variables",
    }

    AGGREGATE_METHODS: Dict[str, str] = {
        "mean": "Arithmetic mean",
        "median": "Median value",
        "sum": "Sum of values",
        "geomean": "Geometric mean (useful for normalized values)",
    }

    THEMES: Dict[str, str] = {
        "default": "Default matplotlib theme",
        "whitegrid": "White background with grid",
        "darkgrid": "Dark background with grid",
        "white": "White background, no grid",
        "dark": "Dark background, no grid",
        "ticks": "White background with ticks",
    }

    @staticmethod
    def create_minimal_config(output_path: str, stats_path: str) -> RingConfig:
        """
        Create a minimal configuration with required fields only.

        Args:
            output_path: Where to save output files
            stats_path: Path to gem5 stats files

        Returns:
            Minimal configuration dictionary
        """
        return {
            "outputPath": output_path,
            "parseConfig": {
                "parser": "gem5_stats",
                "statsPath": stats_path,
                "statsPattern": "**/stats.txt",
                "variables": [],
            },
            "dataManagers": {"seedsReducer": False},
            "plots": [],
        }

    @staticmethod
    def create_plot_config(
        plot_type: str, x: str, y: str, filename: str, **kwargs: Any
    ) -> PlotConfig:
        """
        Create a plot configuration.

        Args:
            plot_type: Type of plot (bar, line, heatmap, etc.)
            x: X-axis variable
            y: Y-axis variable
            filename: Output filename
            **kwargs: Additional plot options (hue, title, etc.)

        Returns:
            Plot configuration dictionary
        """
        plot_config: PlotConfig = {
            "type": plot_type,
            "output": {
                "filename": filename,
                "format": kwargs.get("format", "png"),
                "dpi": kwargs.get("dpi", 300),
            },
            "data": {"x": x, "y": y},
            "style": {
                "width": kwargs.get("width", 10),
                "height": kwargs.get("height", 6),
                "theme": kwargs.get("theme", "whitegrid"),
            },
        }

        # Optional data fields
        if "hue" in kwargs:
            plot_config["data"]["hue"] = kwargs["hue"]

        if "filters" in kwargs:
            plot_config["data"]["filters"] = kwargs["filters"]

        if "aggregate" in kwargs:
            plot_config["data"]["aggregate"] = kwargs["aggregate"]

        # Optional style fields
        if "title" in kwargs:
            plot_config["style"]["title"] = kwargs["title"]

        if "xlabel" in kwargs:
            plot_config["style"]["xlabel"] = kwargs["xlabel"]

        if "ylabel" in kwargs:
            plot_config["style"]["ylabel"] = kwargs["ylabel"]

        if "ylim" in kwargs:
            plot_config["style"]["ylim"] = kwargs["ylim"]

        if "grid" in kwargs:
            plot_config["style"]["grid"] = kwargs["grid"]

        if "legend" in kwargs:
            plot_config["style"]["legend"] = kwargs["legend"]

        return plot_config

    @staticmethod
    def add_variable(
        config: Dict[str, Any], name: str, var_type: str, rename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a variable to parse configuration.

        Args:
            config: Configuration dictionary
            name: Variable name in stats file
            var_type: Type (scalar, vector, distribution, configuration)
            rename: Optional new name

        Returns:
            Updated configuration
        """
        var_config = {"name": name, "type": var_type}

        if rename:
            var_config["rename"] = rename

        config["parseConfig"]["variables"].append(var_config)
        return config

    @staticmethod
    def enable_seeds_reducer(config: Dict[str, Any]) -> Dict[str, Any]:
        """Enable automatic reduction of random seeds."""
        config["dataManagers"]["seedsReducer"] = True
        return config

    @staticmethod
    def enable_outlier_removal(
        config: Dict[str, Any], column: str, method: str = "iqr", threshold: float = 1.5
    ) -> Dict[str, Any]:
        """
        Enable outlier removal.

        Args:
            config: Configuration dictionary
            column: Column to check for outliers
            method: Detection method (iqr or zscore)
            threshold: Threshold value

        Returns:
            Updated configuration
        """
        config["dataManagers"]["outlierRemover"] = {
            "enabled": True,
            "column": column,
            "method": method,
            "threshold": threshold,
        }
        return config

    @staticmethod
    def enable_normalizer(
        config: Dict[str, Any], baseline: Dict[str, str], columns: List[str], group_by: List[str]
    ) -> Dict[str, Any]:
        """
        Enable data normalization.

        Args:
            config: Configuration dictionary
            baseline: Baseline configuration
            columns: Columns to normalize
            group_by: Grouping columns

        Returns:
            Updated configuration
        """
        config["dataManagers"]["normalizer"] = {
            "enabled": True,
            "baseline": baseline,
            "columns": columns,
            "groupBy": group_by,
        }
        return config

    @staticmethod
    def save_config(config: Dict[str, Any], output_path: str) -> None:
        """
        Save configuration to JSON file.

        Args:
            config: Configuration dictionary
            output_path: Output file path
        """
        resolved_path = Path(output_path).resolve()
        with open(resolved_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info("Configuration saved to: %s", resolved_path)

    @staticmethod
    def load_template(template_name: str = "config_template.json") -> Dict[str, Any]:
        """
        Load a configuration template.

        Args:
            template_name: Name of template file

        Returns:
            Template configuration dictionary
        """
        templates_dir = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
        safe_name = sanitize_filename(template_name)
        template_path = validate_path_within(
            Path(os.path.join(templates_dir, safe_name)),
            Path(templates_dir),
        )

        with open(template_path, "r") as f:
            return cast(Dict[str, Any], json.load(f))


# Example usage functions
def create_simple_bar_plot_config(
    output_path: str, stats_path: str, x_var: str, y_var: str, hue_var: Optional[str] = None
) -> RingConfig:
    """
    Create a simple configuration for a bar plot.

    Args:
        output_path: Output directory
        stats_path: Path to gem5 stats
        x_var: X-axis variable
        y_var: Y-axis variable
        hue_var: Optional grouping variable

    Returns:
        Complete configuration
    """
    config: RingConfig = ConfigTemplateGenerator.create_minimal_config(output_path, stats_path)
    config_dict: Dict[str, Any] = cast(Dict[str, Any], config)

    # Add variables
    ConfigTemplateGenerator.add_variable(config_dict, x_var, "configuration")
    ConfigTemplateGenerator.add_variable(config_dict, y_var, "scalar")

    if hue_var:
        ConfigTemplateGenerator.add_variable(config_dict, hue_var, "configuration")

    # Enable seeds reducer
    ConfigTemplateGenerator.enable_seeds_reducer(config_dict)

    # Add plot
    plot_kwargs: Dict[str, Any] = {
        "title": f"{y_var} by {x_var}",
        "xlabel": x_var,
        "ylabel": y_var,
        "grid": True,
    }

    if hue_var:
        plot_kwargs["hue"] = hue_var

    plot: PlotConfig = ConfigTemplateGenerator.create_plot_config(
        "bar", x_var, y_var, f"{y_var}_plot", **plot_kwargs
    )

    config_dict["plots"].append(plot)

    return config
