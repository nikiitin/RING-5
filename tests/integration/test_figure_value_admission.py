"""Current figure admission preserves plugin fields and rejects unsupported values."""

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, cast, override
from unittest.mock import Mock, patch

import matplotlib.pyplot as plt
from matplotlib.figure import Figure as MplFigure
from matplotlib.patches import Rectangle
from matplotlib.colors import to_rgba
import plotly.graph_objects as go
import pandas as pd
import pytest

import ring5
from src.core.common.plot_payload import (
    BAR_HATCH_PATTERNS,
    validate_plot_config_keys,
    validate_plot_config_values,
)
from src.core.models.portfolio_models import PortfolioData
from src.core.models.recipe_models import AnalysisRecipe, RecipeParameter, RecipePlot, RecipeSource
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import HeatmapTraceConfig
from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.base_plot import BasePlot
from src.web.pages.ui.plotting.plot_factory import PlotFactory

_HEATMAP_KEYS = ("colorscale", "show_cell_values")


def _table() -> ring5.Table:
    return ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]}))


def _recipe(config: dict[str, Any], *, plot_type: str = "bar") -> AnalysisRecipe:
    return AnalysisRecipe(
        name="Figure contract",
        source=RecipeSource(kind="csv", path="data.csv"),
        plots=(RecipePlot("Measured", plot_type, config),),
    )


@pytest.mark.parametrize("key", _HEATMAP_KEYS)
@pytest.mark.parametrize("plot_type", [None, "bar", "parallel_coordinates", "custom_heatmap"])
def test_heatmap_key_policy_requires_explicit_builtin_context(
    key: str, plot_type: str | None
) -> None:
    config = {key: {"plugin": "retained"}, "parallel_colorscale": "Viridis"}
    before = copy.deepcopy(config)
    validate_plot_config_keys(config, plot_type=plot_type)
    assert config == before
    with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
        validate_plot_config_keys(config, plot_type="heatmap")
    assert config == before


@pytest.mark.public_api
@pytest.mark.parametrize("key", _HEATMAP_KEYS)
@pytest.mark.parametrize("typed", [False, True])
def test_public_heatmap_context_rejects_before_registering_plot(key: str, typed: bool) -> None:
    # [test->req~ring5.api.plot-validation~1]
    raw = {"x": "x", "metric_columns": ["y"], key: "unsupported"}
    before = copy.deepcopy(raw)
    config = ring5.FigureSpec(extra=raw) if typed else raw
    with ring5.Session() as session:
        with pytest.raises(
            ring5.DataValidationError, match="Unsupported heatmap configuration keys"
        ):
            session.create_plot("heatmap", data=_table(), config=config)
        assert not session.plots
    assert raw == before
    if typed:
        assert isinstance(config, ring5.FigureSpec)
        assert config.to_config()[key] == "unsupported"
        with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
            config.to_config(plot_type="heatmap")


@pytest.mark.parametrize("key", _HEATMAP_KEYS)
def test_restore_capture_and_recipe_reject_heatmap_keys_before_effects(
    key: str, tmp_path: Path
) -> None:
    # [test->req~ring5.portfolio.schema~1]
    state = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    original = pd.DataFrame({"x": ["retained"], "y": [9.0]})
    state.set_data(original)
    plot = PlotFactory.create_plot("heatmap", 0, "Measured")
    plot.config = {"x": "x", "metric_columns": ["y"]}
    plot.replace_processed_data(_table().frame)
    service = PortfolioService(state, portfolios_dir=tmp_path)
    document = json.loads(service.serialize_workspace(original, [plot], {}, 1))
    document["plots"][0]["config"][key] = "unsupported"
    with patch.object(PlotFactory, "create_plot", side_effect=AssertionError("model creation")):
        with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
            PlotFactory.from_dict(document["plots"][0])
        with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
            state.restore_session(cast(PortfolioData, document))
    pd.testing.assert_frame_equal(cast(pd.DataFrame, state.get_data()), original)

    before = copy.deepcopy(plot.config)
    invalid = {**before, key: "unsupported"}
    with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
        plot.config = invalid
    serialized = plot.to_dict()
    serialized["config"] = invalid
    enricher = Mock(side_effect=AssertionError("enrichment reached"))
    with patch.object(plot, "to_dict", return_value=serialized):
        with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
            service.save_portfolio(
                "Rejected", original, [plot], {}, 1, figure_spec_enricher=enricher
            )
    enricher.assert_not_called()
    assert plot.config == before
    assert not (tmp_path / "Rejected.json").exists()
    with patch(
        "src.core.services.data_services.analysis_recipe_service."
        "PathService.get_analysis_recipes_dir",
        side_effect=AssertionError("storage reached"),
    ):
        with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
            AnalysisRecipeService.save(_recipe({key: "{{value}}"}, plot_type="heatmap"))


class _HeatmapPlugin(BasePlot):
    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name, "custom_heatmap_contract")

    @override
    def render_config_ui(self, data: pd.DataFrame, saved_config: dict[str, Any]) -> dict[str, Any]:
        return dict(saved_config)

    @override
    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        assert config["colorscale"] == {"plugin": "retained"}
        assert config["show_cell_values"] == "plugin meaning"
        return TraceBuildResult(
            traces=[
                HeatmapTraceConfig(
                    col_labels=["a"],
                    row_labels=["metric"],
                    z=[[3.0]],
                    colorscale="viridis",
                    show_values=False,
                )
            ]
        )


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_plugin_fields_and_typed_heatmap_trace_keep_independent_contracts(
    engine: Literal["plotly", "matplotlib"], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(PlotFactory._plot_classes, "custom_heatmap_contract", _HeatmapPlugin)
    config = {
        "colorscale": {"plugin": "retained"},
        "show_cell_values": "plugin meaning",
        "parallel_colorscale": "Viridis",
    }
    before = copy.deepcopy(config)
    recipe = _recipe(config, plot_type="custom_heatmap_contract")
    assert AnalysisRecipeService.loads(AnalysisRecipeService.dumps(recipe)) == recipe
    assert AnalysisRecipeService.materialize(recipe).plots[0].config == config
    with ring5.Session() as session:
        plot = session.create_plot("custom_heatmap_contract", data=_table(), config=config)
        restored = PlotFactory.from_dict(plot.to_dict())
        figure = cast(Any, session.render(restored, engine=engine))
        try:
            if engine == "plotly":
                assert [list(row) for row in figure.data[0].z] == [[3.0]]
                assert figure.data[0].colorscale
            else:
                assert figure.axes[0].collections[0].get_array().tolist() == [[3.0]]
        finally:
            if engine == "matplotlib":
                plt.close(figure)
    assert config == before


@pytest.mark.public_api
@pytest.mark.parametrize("pattern", BAR_HATCH_PATTERNS)
def test_current_pattern_vocabulary_preserves_matplotlib_capability(pattern: str) -> None:
    config = {"x": "x", "y": "y", "series_styles": {"y": {"pattern": pattern}}}
    validate_plot_config_values(config)
    spec = ring5.FigureSpec(extra=config)
    assert spec.to_config()["series_styles"]["y"]["pattern"] == pattern
    with ring5.Session() as session:
        figure = cast(Any, session.plot("bar", data=_table(), config=spec, engine="matplotlib"))
        try:
            assert [bar.get_height() for bar in figure.axes[0].patches] == [3.0]
            assert figure.axes[0].patches[0].get_hatch() in (
                pattern,
                None if pattern == "" else pattern,
            )
        finally:
            plt.close(figure)


class _CoerciblePattern:
    def __str__(self) -> str:
        return "/"


@pytest.mark.parametrize(
    "pattern", [None, False, 1, ["/"], {"shape": "/"}, "//", " /", _CoerciblePattern()]
)
def test_pattern_values_are_strings_without_adapters_or_coercion(pattern: object) -> None:
    config = {"series_styles": {"Measured": {"pattern": pattern}}}
    with pytest.raises(ValueError, match="pattern must be a string"):
        validate_plot_config_values(config)


@pytest.mark.public_api
@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        *(
            ("pattern", value, "pattern must be a string")
            for value in (None, {"shape": "/"}, 5, "//")
        ),
        *(
            ("opacity", value, "opacity must be a finite real number")
            for value in (None, True, "0.5", -0.1, 1.1, float("nan"), float("inf"))
        ),
    ],
)
def test_invalid_style_value_rejects_at_public_restore_and_capture_boundaries(
    field: str, value: object, message: str, tmp_path: Path
) -> None:
    # [test->req~ring5.api.plot-validation~1]
    # [test->req~ring5.figure.series-styling~2]
    config: dict[str, Any] = {"x": "x", "y": "y", "series_styles": {"y": {field: value}}}
    before = copy.deepcopy(config)
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match=message):
            session.create_plot("bar", data=_table(), config=config)
        assert not session.plots
    with pytest.raises(ValueError, match=message):
        ring5.FigureSpec(extra=config)
    with patch.object(PlotFactory, "create_plot", side_effect=AssertionError("model creation")):
        with pytest.raises(ValueError, match=message):
            PlotFactory.from_dict(
                {"id": 0, "name": "Invalid", "plot_type": "bar", "config": config}
            )
    state = RepositoryStateManager()
    plot = PlotFactory.create_plot("bar", 0, "Invalid")
    with pytest.raises(ValueError, match=message):
        plot.config = config
    serialized = plot.to_dict()
    serialized["config"] = config
    enricher = Mock(side_effect=AssertionError("enrichment reached"))
    with patch.object(plot, "to_dict", return_value=serialized):
        with pytest.raises(ValueError, match=message):
            PortfolioService(state, portfolios_dir=tmp_path).save_portfolio(
                "Rejected", None, [plot], {}, 1, figure_spec_enricher=enricher
            )
    enricher.assert_not_called()
    assert not (tmp_path / "Rejected.json").exists()
    assert config["series_styles"]["y"][field] is value
    assert config == before


@pytest.mark.public_api
@pytest.mark.parametrize("styles", [None, [], "styles", {1: {}}, {"y": None}, {"y": []}])
def test_invalid_style_structure_rejects_before_publication(styles: object) -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="series_styles must map text"):
            session.create_plot(
                "bar", data=_table(), config={"x": "x", "y": "y", "series_styles": styles}
            )
        assert not session.plots


@pytest.mark.parametrize("pattern", ["/", "o", "O", "*", "//"])
def test_pattern_recipe_values_validate_after_parameter_materialization(pattern: str) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    recipe = _recipe({"series_styles": {"y": {"pattern": "{{pattern}}", "plugin": {"label": 1}}}})
    recipe = AnalysisRecipe(
        name=recipe.name,
        source=recipe.source,
        plots=recipe.plots,
        parameters=(RecipeParameter("pattern", "string", default=pattern),),
    )
    payload = AnalysisRecipeService.dumps(recipe)
    restored = AnalysisRecipeService.loads(payload)
    assert restored.plots[0].config["series_styles"]["y"]["pattern"] == "{{pattern}}"
    if pattern == "//":
        with pytest.raises(ValueError, match="pattern must be a string"):
            AnalysisRecipeService.materialize(restored)
    else:
        concrete = AnalysisRecipeService.materialize(restored)
        assert concrete.plots[0].config["series_styles"]["y"] == {
            "pattern": pattern,
            "plugin": {"label": 1},
        }


@pytest.mark.parametrize("plot_type", ["heatmap", "custom_heatmap_contract"])
def test_recipe_plot_type_context_is_resolved_before_contextual_admission(plot_type: str) -> None:
    recipe = AnalysisRecipe(
        name="Typed context",
        source=RecipeSource(kind="csv", path="data.csv"),
        parameters=(RecipeParameter("kind", "string", default=plot_type),),
        plots=(RecipePlot("Measured", "{{kind}}", {"colorscale": "plugin value"}),),
    )
    restored = AnalysisRecipeService.loads(AnalysisRecipeService.dumps(recipe))
    assert restored.plots[0].plot_type == "{{kind}}"
    if plot_type == "heatmap":
        with pytest.raises(ValueError, match="Unsupported heatmap configuration keys"):
            AnalysisRecipeService.materialize(restored)
    else:
        resolved = AnalysisRecipeService.materialize(restored)
        assert resolved.plots[0].plot_type == plot_type
        assert resolved.plots[0].config["colorscale"] == "plugin value"


def test_style_admission_preserves_other_plugin_fields_and_does_not_modify_inputs() -> None:
    config: Mapping[str, Any] = {"series_styles": {"custom": {"plugin": {"labels": ["a"]}}}}
    before = copy.deepcopy(config)
    validate_plot_config_values(config)
    assert config == before


@pytest.mark.public_api
@pytest.mark.parametrize("opacity", [0.0, 0.25, 1.0])
def test_source_opacity_portfolio_replay_preserves_embedded_alpha_and_values(
    opacity: float, portfolios_dir: Path
) -> None:
    # [test->req~ring5.figure.series-styling~2]
    config = {
        "x": "x",
        "y": "y",
        "series_styles": {
            "y": {"opacity": opacity, "color": "rgba(10,20,30,0.4)", "use_color": True}
        },
    }
    with ring5.Session() as session:
        table = _table()
        session.api.state_manager.set_data(table.frame)
        session.create_plot(
            "bar", data=table, config=ring5.FigureSpec(extra=config), name="Measured"
        )
        session.save_portfolio("Source opacity")
    assert (portfolios_dir / "Source opacity.json").is_file()
    with ring5.Session() as session:
        report = session.load_portfolio("Source opacity")
        assert report.complete and report.data_restored and report.plots_restored == 1
        plot = session.plots[0]
        assert plot.config["series_styles"]["y"]["opacity"] == opacity
        matplotlib = session.render(plot, engine="matplotlib")
        assert isinstance(matplotlib, MplFigure)
        try:
            bars = matplotlib.axes[0].patches
            assert len(bars) == 1 and isinstance(bars[0], Rectangle)
            assert bars[0].get_height() == 3
            assert to_rgba(bars[0].get_facecolor())[3] == pytest.approx(0.4 * opacity)
        finally:
            plt.close(matplotlib)
        plotly = session.render(plot, engine="plotly")
        assert isinstance(plotly, go.Figure) and isinstance(plotly.data[0], go.Bar)
        assert plotly.data[0].opacity == opacity
        assert plotly.data[0].marker.color == "rgba(10,20,30,0.4)"
        assert list(plotly.data[0].y) == [3]


@pytest.mark.parametrize("value", [0.0, 0.25, 1.0, -0.1, 1.1])
def test_opacity_recipe_template_retains_type_until_materialization(value: float) -> None:
    # [test->req~ring5.figure.series-styling~2]
    recipe = _recipe({"series_styles": {"y": {"opacity": "{{opacity}}", "plugin": {"label": 1}}}})
    recipe = AnalysisRecipe(
        name=recipe.name,
        source=recipe.source,
        plots=recipe.plots,
        parameters=(RecipeParameter("opacity", "number", default=value),),
    )
    restored = AnalysisRecipeService.loads(AnalysisRecipeService.dumps(recipe))
    assert restored.plots[0].config["series_styles"]["y"]["opacity"] == "{{opacity}}"
    if not 0 <= value <= 1:
        with pytest.raises(ValueError, match="opacity must be a finite real number"):
            AnalysisRecipeService.materialize(restored)
    else:
        concrete = AnalysisRecipeService.materialize(restored)
        assert concrete.plots[0].config["series_styles"]["y"] == {
            "opacity": value,
            "plugin": {"label": 1},
        }
