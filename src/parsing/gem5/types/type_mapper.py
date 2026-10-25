"""
Type Mapper Module

Centralizes logic for mapping external (Perl/Scanner) type strings to internal Python types.
Ensures consistency between Scanner and Parser.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from src.core.common.stat_config_codec import StatConfigCodec
from src.core.common.safe_regex import SafeRegexError, normalize_stat_pattern, numeric_pattern_id
from src.core.models.parsing_models import StatConfig
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
            SafeRegexError: Numeric index matching exceeds an input or execution bound.
        """
        source_type = config.params.get("source_type")
        if source_type is not None:
            return config.type == "vector" and source_type == "scalar"
        entries = config.params.get("entries", [])
        if config.type != "vector" or not isinstance(entries, list) or not concrete_names:
            return False
        try:
            source = normalize_stat_pattern(config.source_name or config.name)
        except SafeRegexError:
            return False
        indices = [numeric_pattern_id(source, name) for name in concrete_names]
        if all(index is not None for index in indices) and set(indices) == set(entries):
            raise ValueError(
                f"PARSER: Original source type for {config.name!r} is ambiguous "
                "in saved scan metadata. "
                "Scan the simulator files again before parsing this pattern."
            )
        return False

    @classmethod
    def create_stat(cls, var_config: StatConfig) -> "StatType":
        """Build one registered statistic from the current validated runnable type.

        Args:
            var_config: Runnable statistic configuration.

        Returns:
            Registered backend statistic instance.

        Raises:
            TypeError: Input is not StatConfig or has incorrectly typed options.
            ValueError: Configuration or backend type is unsupported.
        """
        # [impl->req~ring5.ingestion.statistics-only~1]
        config = StatConfigCodec.validate(var_config)
        params = config.params
        kwargs: dict[str, StatParamValue] = {"repeat": config.repeat}
        match config.type:
            case "vector":
                entries = (
                    [] if config.statistics_only else cast(list[str], params.get("entries", []))
                )
                statistics = cast(list[str], params.get("statistics", []))
                kwargs["entries"] = list(dict.fromkeys([*entries, *statistics]))
            case "distribution":
                kwargs["statistics_only"] = config.statistics_only
                if not config.statistics_only:
                    kwargs["minimum"] = params["minimum"]
                    kwargs["maximum"] = params["maximum"]
                kwargs["statistics"] = params.get("statistics", [])
            case "histogram":
                kwargs["statistics_only"] = config.statistics_only
                if not config.statistics_only:
                    kwargs["bins"] = params.get("bins", 0)
                    kwargs["max_range"] = params.get("max_range", 0.0)
                    kwargs["entries"] = params.get("entries")
                kwargs["statistics"] = params.get("statistics", [])
            case "configuration":
                kwargs["on_empty"] = params.get("on_empty", "None")
            case "scalar":
                pass
            case _:
                kwargs.update(
                    {
                        key: value
                        for key, value in params.items()
                        if key not in {"parsed_ids", "source_type"}
                    }
                )
        return StatTypeRegistry.create(config.type, **kwargs)  # type: ignore[arg-type]
