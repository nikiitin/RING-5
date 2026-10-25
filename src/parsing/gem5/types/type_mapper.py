"""Construct registered accumulators from explicit current statistic configurations."""

from typing import TYPE_CHECKING, cast

from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parsing_models import StatParamValue
from src.parsing.gem5.types import StatTypeRegistry
from src.parsing.gem5.impl.source_bindings import AccumulatorSpec

if TYPE_CHECKING:
    from src.parsing.gem5.types.base import StatContent, StatResult, StatType


class TypeMapper:
    """Factory adapter for a resolved typed statistic configuration."""

    @classmethod
    def create_stat(cls, spec: AccumulatorSpec) -> "StatType[StatContent, StatResult]":
        """Build one registered statistic from the current validated runnable type.

        Args:
            spec: Resolved private execution specification.

        Returns:
            Registered backend statistic instance.

        Raises:
            TypeError: Input is not AccumulatorSpec or has incorrectly typed options.
            ValueError: Configuration or backend type is unsupported.
        """
        # [impl->req~ring5.ingestion.statistics-only~1]
        if not isinstance(spec, AccumulatorSpec):
            raise TypeError("Accumulator construction requires a resolved AccumulatorSpec.")
        config = StatConfigCodec.validate(spec.config)
        params = config.params
        kwargs: dict[str, StatParamValue] = {"repeat": spec.repeat}
        match spec.output_type:
            case "vector":
                if spec.entries is None:
                    raise ValueError("Vector accumulator requires a resolved entry schema.")
                kwargs["entries"] = list(spec.entries)
            case "distribution":
                kwargs["statistics_only"] = config.statistics_only
                if not config.statistics_only:
                    # The runnable codec rejects fractional bounds; conversion is lossless.
                    kwargs["minimum"] = int(cast(float, params["minimum"]))
                    kwargs["maximum"] = int(cast(float, params["maximum"]))
                kwargs["statistics"] = params.get("statistics", [])
            case "histogram":
                kwargs["statistics_only"] = config.statistics_only
                if not config.statistics_only:
                    kwargs["bins"] = params.get("bins", 0)
                    kwargs["max_range"] = params.get("max_range", 0.0)
                    kwargs["entries"] = list(spec.entries) if spec.entries is not None else None
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
                        if key not in {"selected_sources", "source_type"}
                    }
                )
        return StatTypeRegistry.create(spec.output_type, **kwargs)  # type: ignore[arg-type]
