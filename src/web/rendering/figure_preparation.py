"""Prepare owned neutral traces and resolved styling before native rendering."""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, replace

import pandas as pd

from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.figure_config import FigureConfig
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService
from src.core.services.visualization.accessibility_service import AccessibilityService
from src.core.services.visualization.config_resolver import resolve_config
from src.web.rendering._connector_protocol import validate_annotation_types, validate_trace_types
from src.web.rendering.config_builder import ConfigSpecBuilder, enrich_from_traces


@dataclass(frozen=True)
class PreparedFigure:
    """One render's effective configuration, neutral output and resolved style."""

    config: PlotConfig
    trace_result: TraceBuildResult
    spec: FigureConfig


def _relabel_traces(
    result: TraceBuildResult, legend_labels: dict[str, str] | None
) -> TraceBuildResult:
    """Apply display names once before either native engine consumes traces."""
    # [impl->req~ring5.figure.ordering-renaming~2]
    if not legend_labels:
        return result
    return replace(
        result,
        traces=[
            replace(trace, name=legend_labels.get(trace.name, trace.name))
            for trace in result.traces
        ],
    )


def prepare_figure(
    data: pd.DataFrame,
    config: PlotConfig,
    plot_type: str,
    create_traces: Callable[[pd.DataFrame, PlotConfig], TraceBuildResult],
) -> PreparedFigure:
    """Build one owned render description without constructing a native figure.

    Args:
        data: Processed data read by the registered plot's trace callback.
        config: Editable configuration, retained unchanged.
        plot_type: Exact registered plot identifier.
        create_traces: Registered strategy's engine-neutral callback.

    Returns:
        Effective configuration, owned traces and resolved typed styling.

    Raises:
        TypeError: A callback emits an unsupported neutral trace or annotation family.
        ValueError: Configuration or trace construction is invalid.
    """
    # [impl->req~ring5.render.engine-independent-traces~1]
    # [impl->req~ring5.data.semantic-units~1]
    # [impl->req~ring5.figure.accessible-themes~1]
    effective = SemanticMetadataService.enrich_figure_config(data, deepcopy(config))
    effective = AccessibilityService.apply_defaults(effective, plot_type)
    result = create_traces(data, effective)
    validate_trace_types(result.traces)
    validate_annotation_types(result.annotations)
    result = deepcopy(result)
    result = AccessibilityService.apply_non_color_encodings(result, effective)
    result = _relabel_traces(result, effective.get("legend_labels"))
    spec = ConfigSpecBuilder.from_config(effective, plot_type)
    enrich_from_traces(spec, result)
    spec = resolve_config(spec)
    result = replace(result, annotations=list(spec.annotations))
    return PreparedFigure(effective, result, spec)
