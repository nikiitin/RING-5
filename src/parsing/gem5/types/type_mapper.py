"""
Type Mapper Module

Centralizes logic for mapping external (Perl/Scanner) type strings to internal Python types.
Ensures consistency between Scanner and Parser.
"""

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from src.core.common.safe_regex import SafeRegexError, numeric_pattern_id
from src.core.models import StatConfig
from src.core.models.data_models import ScannedVariableDict
from src.core.models.parsing_models import StatParamValue
from src.parsing.gem5.types import StatTypeRegistry

if TYPE_CHECKING:
    from src.parsing.gem5.types.base import StatType


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
    def map_scan_result(cls, scan_result: dict[str, Any]) -> ScannedVariableDict:
        """
        Normalize a scanner result dict into a ScannedVariableDict.

        Pure projection: the caller's dict is never mutated, and mutable members
        (entries, pattern_indices) are copied into the new dict.
        """
        raw_type = scan_result.get("type", "")
        # The scan_result dict has the same shape as ScannedVariableDict
        result: ScannedVariableDict = ScannedVariableDict(
            name=scan_result.get("name", ""),
            type=cls.normalize_type(raw_type) if raw_type else "",
            entries=list(scan_result.get("entries", [])),
        )
        if "source_type" in scan_result:
            result["source_type"] = scan_result["source_type"]
        if "minimum" in scan_result:
            result["minimum"] = scan_result["minimum"]
        if "maximum" in scan_result:
            result["maximum"] = scan_result["maximum"]
        if "pattern_indices" in scan_result:
            result["pattern_indices"] = list(scan_result["pattern_indices"])
        return result

    @staticmethod
    def is_entry_type(type_name: str) -> bool:
        """Check if type requires entries (Vector, Distribution, Histogram)."""
        norm = type_name.lower()
        return norm in ("vector", "distribution", "histogram")

    @staticmethod
    def is_scalar_pattern_vector(config: StatConfig, concrete_names: Sequence[str]) -> bool:
        """Identify a scanner vector whose entries are concrete scalar indices.

        Raises:
            ValueError: Legacy metadata cannot distinguish scalar indices from vector entries.
        """
        source_type = config.params.get("source_type")
        if source_type is not None:
            return config.type == "vector" and source_type == "scalar"
        entries = config.params.get("entries", [])
        if config.type != "vector" or not isinstance(entries, list) or not concrete_names:
            return False
        try:
            indices = [
                numeric_pattern_id(config.source_name or config.name, name)
                for name in concrete_names
            ]
        except SafeRegexError:
            return False
        if all(index is not None for index in indices) and set(indices) == set(entries):
            raise ValueError(
                f"PARSER: Original source type for {config.name!r} is ambiguous "
                "in saved scan metadata. "
                "Scan the simulator files again before parsing this pattern."
            )
        return False

    @classmethod
    def create_stat(cls, var_config: StatConfig | Mapping[str, StatParamValue] | Any) -> "StatType":
        """
        Create a strongly-typed Stat object from a configuration.

        Args:
            var_config: StatConfig model or dictionary containing variable configuration.

        Returns:
            An instance of a class registered in StatTypeRegistry.
        """
        # [impl->req~ring5.ingestion.statistics-only~1]
        var_type: str = ""
        repeat: int = 1
        statistics_only: bool = False
        params: dict[str, StatParamValue] = {}

        if isinstance(var_config, Mapping):
            var_type_raw = var_config.get("type")
            var_type = str(var_type_raw) if var_type_raw else ""
            repeat_raw = var_config.get("repeat", 1)
            repeat = int(repeat_raw) if isinstance(repeat_raw, (int, float, str)) else 1
            statistics_only = bool(
                var_config.get("statistics_only", var_config.get("statisticsOnly", False))
            )
            params = dict(var_config)
        elif (
            hasattr(var_config, "type")
            and hasattr(var_config, "repeat")
            and hasattr(var_config, "statistics_only")
            and hasattr(var_config, "params")
        ):
            var_type_raw = getattr(var_config, "type", "")
            var_type = str(var_type_raw) if var_type_raw else ""
            repeat_raw = getattr(var_config, "repeat", 1)
            repeat = int(repeat_raw) if isinstance(repeat_raw, (int, float, str)) else 1
            statistics_only = bool(getattr(var_config, "statistics_only", False))
            params_raw = getattr(var_config, "params", {})
            params = params_raw if isinstance(params_raw, dict) else {}
        else:
            raise TypeError(
                "Unsupported var_config type. Expected mapping or StatConfig-like object."
            )

        if not var_type:
            raise ValueError("Configuration missing 'type' field")

        # Common args
        kwargs: dict[str, StatParamValue] = {"repeat": repeat}

        # Type-specific mapping
        norm_type = cls.normalize_type(var_type)

        match norm_type:
            case "vector":
                if statistics_only:
                    kwargs["entries"] = params.get("statistics") or []
                else:
                    kwargs["entries"] = params.get("vectorEntries") or params.get("entries")
            case "distribution":
                kwargs["statistics_only"] = statistics_only
                if statistics_only:
                    kwargs["minimum"] = 0
                    kwargs["maximum"] = 0
                else:
                    kwargs["minimum"] = params.get("minimum", 0)
                    kwargs["maximum"] = params.get("maximum", 100)
                kwargs["statistics"] = params.get("vectorEntries") or params.get("statistics")
            case "histogram":
                if statistics_only:
                    kwargs["bins"] = 0
                    kwargs["max_range"] = 0.0
                    kwargs["entries"] = None
                else:
                    kwargs["bins"] = params.get("bins", 0)
                    kwargs["max_range"] = params.get("max_range", 0.0)
                    kwargs["entries"] = params.get("entries")
                kwargs["statistics"] = params.get("statistics") or params.get("vectorEntries")
            case "configuration":
                kwargs["onEmpty"] = params.get("onEmpty", "None")

        return StatTypeRegistry.create(norm_type, **kwargs)  # type: ignore[arg-type]
