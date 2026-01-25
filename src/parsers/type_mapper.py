"""
Type Mapper Module

Centralizes logic for mapping external (Perl/Scanner) type strings to internal Python types.
Ensures consistency between Scanner and Parser.
"""

from typing import Any, Dict


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
    def create_stat(cls, var_config: Dict[str, Any]) -> Any:
        """
        Create a strongly-typed Stat object from a configuration dictionary.
        
        This encapsulates the logic of mapping config keys (e.g. 'vectorEntries')
        to internal arguments (e.g. 'entries').
        
        Args:
            var_config: Dictionary containing variable configuration.
            
        Returns:
            An instance of a class registered in StatTypeRegistry.
        """
        from src.parsers.types import StatTypeRegistry
        
        var_type = var_config.get("type")
        if not var_type:
            raise ValueError("Configuration missing 'type' field")
            
        # Common args
        kwargs = {"repeat": var_config.get("repeat", 1)}
        
        # Type-specific mapping
        norm_type = cls.normalize_type(var_type)
        
        if norm_type == "vector":
            kwargs["entries"] = var_config.get("vectorEntries") or var_config.get("entries")
            
        elif norm_type == "distribution":
            kwargs["minimum"] = var_config.get("minimum", 0)
            kwargs["maximum"] = var_config.get("maximum", 100)
            kwargs["statistics"] = var_config.get("vectorEntries") or var_config.get("statistics")
            
        elif norm_type == "histogram":
            kwargs["bins"] = var_config.get("bins", 0)
            kwargs["max_range"] = var_config.get("max_range", 0.0)
            kwargs["entries"] = var_config.get("entries")
            kwargs["statistics"] = var_config.get("statistics") or var_config.get("vectorEntries")
            
        elif norm_type == "configuration":
            kwargs["onEmpty"] = var_config.get("onEmpty", "None")
            
        return StatTypeRegistry.create(var_type, **kwargs)
