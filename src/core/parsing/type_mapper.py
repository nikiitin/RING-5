"""
Type Mapper Module

Centralizes logic for mapping external (Perl/Scanner) type strings to internal Python types.
Ensures consistency between Scanner and Parser.
"""

from typing import Any, Dict, Union

from src.core.parsing.models import StatConfig
from src.core.parsing.types import StatTypeRegistry


class TypeMapper:
    """
    Static utility for mapping and normalizing stat types.
    """

    # Mapping from Perl/Legacy names to internal normalized names (lowercase usually)
    # The registry uses lowercase names.
    @classmethod
    def normalize_type(cls, type_name: str) -> str:
        """Normalize a type string (case-insensitive)."""
        return type_name.lower()

    @classmethod
    def map_scan_result(cls, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a dictionary result from the scanner.
        Ensures 'type' field is consistent.
        """
        if "type" in scan_result:
            scan_result["type"] = cls.normalize_type(scan_result["type"])
        return scan_result

    @staticmethod
    def is_entry_type(type_name: str) -> bool:
        """Check if type requires entries (Vector, Distribution, Histogram)."""
        norm = type_name.lower()
        return norm in ("vector", "distribution", "histogram")

    @classmethod
    def create_stat(cls, var_config: Union[StatConfig, Dict[str, Any]]) -> Any:
        """
        Create a strongly-typed Stat object from a configuration.

        Args:
            var_config: StatConfig model or dictionary containing variable configuration.

        Returns:
            An instance of a class registered in StatTypeRegistry.
        """
        var_type: str = ""
        repeat: int = 1
        statistics_only: bool = False
        params: Dict[str, Any] = {}

        if isinstance(var_config, StatConfig):
            var_type = var_config.type
            repeat = var_config.repeat
            statistics_only = var_config.statistics_only
            params = var_config.params
        else:
            var_type_raw: Any = var_config.get("type")
            var_type = str(var_type_raw) if var_type_raw else ""
            repeat = int(var_config.get("repeat", 1))
            statistics_only = bool(
                var_config.get("statistics_only", var_config.get("statisticsOnly", False))
            )
            params = var_config

        if not var_type:
            raise ValueError("Configuration missing 'type' field")

        # Common args
        kwargs: Dict[str, Any] = {"repeat": repeat}

        # Type-specific mapping
        norm_type = cls.normalize_type(var_type)

        if norm_type == "vector":
            if statistics_only:
                kwargs["entries"] = params.get("statistics") or []
            else:
                kwargs["entries"] = params.get("vectorEntries") or params.get("entries")

        elif norm_type == "distribution":
            kwargs["statistics_only"] = statistics_only
            if statistics_only:
                kwargs["minimum"] = 0
                kwargs["maximum"] = 0
            else:
                kwargs["minimum"] = params.get("minimum", 0)
                kwargs["maximum"] = params.get("maximum", 100)
            kwargs["statistics"] = params.get("vectorEntries") or params.get("statistics")

        elif norm_type == "histogram":
            if statistics_only:
                kwargs["bins"] = 0
                kwargs["max_range"] = 0.0
                kwargs["entries"] = None
            else:
                kwargs["bins"] = params.get("bins", 0)
                kwargs["max_range"] = params.get("max_range", 0.0)
                kwargs["entries"] = params.get("entries")
            kwargs["statistics"] = params.get("statistics") or params.get("vectorEntries")

        elif norm_type == "configuration":
            kwargs["onEmpty"] = params.get("onEmpty", "None")

        return StatTypeRegistry.create(norm_type, **kwargs)
