"""
Preset manager for LaTeX export configurations.

Loads and validates journal-specific export presets from YAML configuration.
"""

from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.plotting.export.presets.preset_schema import LaTeXPreset


class PresetManager:
    """
    Manages LaTeX export presets.

    Loads preset configurations from YAML, validates them, and provides
    caching for performance.

    Example:
        >>> preset = PresetManager.load_preset("single_column")
        >>> print(preset["width_inches"])
        3.5
        >>> PresetManager.validate_preset(preset)  # Validates structure
    """

    _cache: Dict[str, LaTeXPreset] = {}
    _presets_data: Dict[str, Any] = {}
    _initialized: bool = False

    @classmethod
    def _initialize(cls) -> None:
        """Load presets YAML file once."""
        if cls._initialized:
            return

        # Path from preset_manager.py: ../../../.. gets to project root, then /config
        config_path = (
            Path(__file__).parent.parent.parent.parent.parent / "config" / "latex_presets.yaml"
        )

        if not config_path.exists():
            raise FileNotFoundError(f"Presets file not found: {config_path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            cls._presets_data = data.get("presets", {})

        cls._initialized = True

    @classmethod
    def load_preset(cls, preset_name: str) -> LaTeXPreset:
        """
        Load a LaTeX export preset by name.

        Args:
            preset_name: Name of the preset (e.g., "single_column", "nature")

        Returns:
            LaTeXPreset configuration dictionary

        Raises:
            ValueError: If preset name is unknown
            FileNotFoundError: If presets YAML file not found
        """
        # Check cache first
        if preset_name in cls._cache:
            return cls._cache[preset_name]

        # Initialize if needed
        cls._initialize()

        # Load from YAML
        if preset_name not in cls._presets_data:
            available = ", ".join(cls._presets_data.keys())
            raise ValueError(f"Unknown preset: {preset_name}. " f"Available presets: {available}")

        raw_preset = cls._presets_data[preset_name]

        # Extract only LaTeXPreset fields (exclude description, typical_use)
        preset: LaTeXPreset = {
            "width_inches": raw_preset["width_inches"],
            "height_inches": raw_preset["height_inches"],
            "font_family": raw_preset["font_family"],
            "font_size_base": raw_preset["font_size_base"],
            "font_size_labels": raw_preset["font_size_labels"],
            "font_size_title": raw_preset["font_size_title"],
            "font_size_ticks": raw_preset["font_size_ticks"],
            "line_width": raw_preset["line_width"],
            "marker_size": raw_preset["marker_size"],
            "dpi": raw_preset["dpi"],
        }

        # Validate before caching
        cls.validate_preset(preset)

        # Cache for next time
        cls._cache[preset_name] = preset

        return preset

    @classmethod
    def list_presets(cls) -> List[str]:
        """
        List all available preset names.

        Returns:
            List of preset names (e.g., ["single_column", "double_column", ...])
        """
        cls._initialize()
        return list(cls._presets_data.keys())

    @classmethod
    def get_preset_info(cls, preset_name: str) -> Dict[str, str]:
        """
        Get metadata about a preset without loading full configuration.

        Args:
            preset_name: Name of the preset

        Returns:
            Dictionary with "description" and "typical_use" keys

        Raises:
            ValueError: If preset name is unknown
        """
        cls._initialize()

        if preset_name not in cls._presets_data:
            raise ValueError(f"Unknown preset: {preset_name}")

        raw_preset = cls._presets_data[preset_name]
        return {
            "description": raw_preset.get("description", ""),
            "typical_use": raw_preset.get("typical_use", ""),
        }

    @classmethod
    def validate_preset(cls, preset: Any) -> None:
        """
        Validate a LaTeX preset configuration.

        Args:
            preset: Preset configuration to validate

        Raises:
            ValueError: If preset is invalid (missing fields, negative values, etc.)
        """
        # Check all required fields exist
        required_fields = [
            "width_inches",
            "height_inches",
            "font_family",
            "font_size_base",
            "font_size_labels",
            "font_size_title",
            "font_size_ticks",
            "line_width",
            "marker_size",
            "dpi",
        ]

        for field in required_fields:
            if field not in preset:
                raise ValueError(f"Missing required field: {field}")

        # Validate dimensions are positive
        if preset["width_inches"] <= 0:
            raise ValueError("width_inches must be positive")

        if preset["height_inches"] <= 0:
            raise ValueError("height_inches must be positive")

        # Validate font sizes are positive
        if preset["font_size_base"] <= 0:
            raise ValueError("font_size_base must be positive")

        if preset["font_size_labels"] <= 0:
            raise ValueError("font_size_labels must be positive")

        if preset["font_size_title"] <= 0:
            raise ValueError("font_size_title must be positive")

        if preset["font_size_ticks"] <= 0:
            raise ValueError("font_size_ticks must be positive")

        # Validate line width and marker size are positive
        if preset["line_width"] <= 0:
            raise ValueError("line_width must be positive")

        if preset["marker_size"] <= 0:
            raise ValueError("marker_size must be positive")

        # Validate DPI is positive
        if preset["dpi"] <= 0:
            raise ValueError("dpi must be positive")
