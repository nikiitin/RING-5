"""Build one selected-engine artifact from a registered neutral plot source."""

from copy import deepcopy

from src.core.common.dataframe_copy import copy_dataframe
from src.core.models.plot_config import PlotConfig
from src.core.models.visualization.engine import VALID_ENGINES, EngineMode
from src.core.models.visualization.small_multiples_spec import SmallMultiplesSpec
from src.web.models.plot_protocols import PlotRenderSource
from src.web.models.render_artifact import RenderArtifact
from src.web.rendering.figure_preparation import prepare_figure
from src.web.rendering.matplotlib_figure_builder import build_matplotlib_figure_from_prepared
from src.web.rendering.plotly_figure_builder import build_plotly_figure
from src.web.rendering.small_multiples_builder import (
    build_small_multiples_figure,
    prepare_small_multiples,
)


def build_render_artifact(
    plot: PlotRenderSource,
    config: PlotConfig,
    engine: EngineMode,
    *,
    multiples: SmallMultiplesSpec | None = None,
) -> RenderArtifact:
    """Build privately, retaining actual source rows and every real panel preparation.

    Args:
        plot: Registered neutral strategy and processed source data.
        config: Detached candidate configuration; never assigned during construction.
        engine: Explicit selected native engine.
        multiples: Actual facet layout, or None for a single figure.

    Returns:
        Complete native artifact ready for one successful publication.

    Raises:
        ValueError: Engine, source data, configuration or native construction is invalid.
        TypeError: A strategy emits an unsupported trace or annotation.
    """
    if engine not in VALID_ENGINES:
        raise ValueError(f"Unknown engine {engine!r}.")
    if plot.processed_data is None:
        raise ValueError(f"Plot '{plot.name}' has no processed data to render.")
    data = copy_dataframe(plot.processed_data)
    if multiples is not None:
        view = plot.copy_without_render_state()
        view.processed_data = data
        owned_config = deepcopy(config)
        composite = prepare_small_multiples([view], multiples, owned_config)
        figure = build_small_multiples_figure(composite, multiples, engine=engine)
        return RenderArtifact(owned_config, figure, composite, engine, source_data=data)

    prepared = prepare_figure(data, config, plot.plot_type, plot.create_traces)
    figure = (
        build_plotly_figure(prepared)
        if engine == "plotly"
        else build_matplotlib_figure_from_prepared(prepared)[0]
    )
    return RenderArtifact(None, figure, prepared, engine, source_data=data)
