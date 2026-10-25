"""Independent-review controls for CSS opacity, legend ownership and value admission."""

import json
from typing import Any, Literal, cast, override
from unittest.mock import patch

import matplotlib.pyplot as plt
from matplotlib.legend import Legend
import pandas as pd
import pytest

import ring5
from src.core.models.recipe_models import AnalysisRecipe, RecipeParameter, RecipePlot, RecipeSource
from src.core.models.visualization.trace_build_result import TraceBuildResult
from src.core.models.visualization.trace_config import BarTraceConfig
from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.types.bar_plot import BarPlot
from src.web.rendering.config_builder import ConfigSpecBuilder
from src.web.rendering.figure_preparation import prepare_figure
from src.web.rendering.matplotlib_connector import FigureSpecToMatplotlib
from src.web.rendering.matplotlib_figure_builder import draw_matplotlib_axes
from src.web.rendering.report_builder import _single_plot_figure, _single_plot_plotly

_CSS = (
    "hsl(120,100%,50%)",
    "hsl(120deg 100% 50%)",
    "hsla(120deg 100% 50% / 0.25)",
    "rgb(100%,0%,0%)",
    "rgb(255 0 0)",
    "rgba(255 0 0 / 0.25)",
    "rgb(100% 0% 0% / 25%)",
    "hwb(120 0% 0%)",
    "lab(50% 20 30)",
    "lch(50% 30 120)",
    "oklab(0.7 0.1 0.1)",
    "oklch(0.7 0.15 180)",
    "#1234",
    "#12345678",
    "rgba(12,34,56,0.25)",
    "#123456",
    "rebeccapurple",
    "rgb(25.5%,0%,0%)",
    "rgba(0.5 1.25 2.75 / 0.25)",
)
_TINY = float.fromhex("0x0.0000000000001p-1022")


def _table() -> ring5.Table:
    return ring5.Table(pd.DataFrame({"x": ["a"], "v": [3.0], "w": [5.0], "group": ["G"]}))


@pytest.mark.public_api
@pytest.mark.parametrize("color", _CSS)
def test_plotly_opacity_preserves_current_static_css_function_admission(color: str) -> None:
    # [test->req~ring5.figure.legends~1]
    with ring5.Session() as session:
        figure = cast(
            Any,
            session.plot(
                "bar",
                data=_table(),
                config={"x": "x", "y": "v", "legend_bgcolor": color, "legend_bgalpha": 0.4},
                engine="plotly",
            ),
        )
        assert list(figure.data[0].y) == [3.0]
        native = figure.layout.legend.bgcolor
        assert native.endswith("0.4)")
        if color.startswith("rgba(0.5"):
            assert native == "rgba(0.5,1.25,2.75,0.4)"
        if color.startswith("rgb(25.5%"):
            assert native == "rgba(25.5%,0%,0%,0.4)"


@pytest.mark.public_api
@pytest.mark.parametrize(
    "color",
    ["color(display-p3 1 0 0)", "var(--brand-color)", "var(--brand-color, var(--fallback))"],
)
def test_profile_and_unresolved_colors_remain_admitted_without_unsupported_opacity(
    color: str,
) -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar", data=_table(), config={"x": "x", "y": "v", "legend_bgcolor": color}
        )
        previous = session.render(plot, engine="plotly")
        assert cast(Any, previous).layout.legend.bgcolor == color
        plot.config["legend_bgalpha"] = 0.4
        with pytest.raises(
            ring5.RenderError, match="concrete RGB, HSL or hexadecimal color, or omit bgalpha"
        ):
            session.render(plot, engine="plotly")
        assert plot.last_generated_fig is previous


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("role", ["primary", "secondary", "numbered"])
@pytest.mark.parametrize("color", ["hsl(120deg 100% 50% / 25%)", "rgb(100% 0% 0% / 25%)"])
@pytest.mark.parametrize("alpha", [0.0, _TINY, 1e-12, 1.0])
def test_shared_color_projection_preserves_tiny_alpha_and_all_legend_roles(
    engine: Literal["plotly", "matplotlib"],
    role: str,
    color: str,
    alpha: float,
) -> None:
    prefix = "legend_" if role == "primary" else "legend2_"
    config = {
        "x": "x",
        "group": "group",
        "y_columns": ["v"],
        "dual_axis": role == "secondary",
        "y_columns_right": ["w"],
        "unified_legend": role != "secondary",
        f"{prefix}bgcolor": color,
        f"{prefix}bgalpha": alpha,
    }
    if role == "numbered":
        config["numbered_xaxis_modes"] = ["Number legend"]
    with ring5.Session() as session:
        plot = session.create_plot("grouped_stacked_bar", data=_table(), config=config)
        native = cast(Any, session.render(plot, engine=engine))
        try:
            if engine == "plotly":
                value = (
                    next(
                        ann.bgcolor
                        for ann in native.layout.annotations
                        if ann.text.startswith("1.")
                    )
                    if role == "numbered"
                    else getattr(
                        native.layout, "legend2" if role == "secondary" else "legend"
                    ).bgcolor
                )
                token = (
                    value[:-1].rsplit("/", 1)[-1].strip()
                    if "/" in value
                    else value[:-1].rsplit(",", 1)[-1]
                )
                assert "e" not in token.lower()
                assert len(token) <= 326
                assert float(token) == alpha
            else:
                primary = native.axes[0]
                if role == "numbered":
                    actor = next(text for text in primary.texts if text.get_text().startswith("1."))
                    background = actor.get_bbox_patch().get_facecolor()
                else:
                    target = primary._ring5_twin if role == "secondary" else primary
                    background = target.get_legend().get_frame().get_facecolor()
                expected = (0.0, 1.0, 0.0) if color.startswith("hsl") else (1.0, 0.0, 0.0)
                assert background[:3] == expected
                assert background[3] == alpha
        finally:
            if engine == "matplotlib":
                plt.close(native)


class _RolePlot(BarPlot):
    """A registered strategy authors legend roles independently from Y-axis choice."""

    def __init__(self, plot_id: int, name: str) -> None:
        super().__init__(plot_id, name)
        self.plot_type = "review_role_plot"

    @override
    def create_traces(self, data: pd.DataFrame, config: dict[str, Any]) -> TraceBuildResult:
        mixed = bool(config.get("mixed_y"))
        variant = config.get("visibility", "both")
        return TraceBuildResult(
            traces=[
                BarTraceConfig(
                    name=role,
                    x=data["x"].tolist(),
                    y=data[column].tolist(),
                    yaxis="y2" if mixed and role == "primary" else "y",
                    legend_role=cast(Literal["primary", "secondary"], role),
                    visible=variant != f"hide_{role}",
                    show_in_legend=variant != f"exclude_{role}",
                )
                for role, column in (("primary", "v"), ("secondary", "w"))
            ],
            secondary_y=mixed,
        )


@pytest.fixture
def role_plugin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(PlotFactory._plot_classes, "review_role_plot", _RolePlot)


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("route", ["session", "report", "dashboard", "shared_dashboard"])
@pytest.mark.parametrize("mixed", [False, True])
@pytest.mark.parametrize(
    "visibility", ["both", "hide_primary", "hide_secondary", "exclude_primary", "exclude_secondary"]
)
def test_registered_legend_roles_keep_owned_styles_on_one_panel_or_twin(
    engine: Literal["plotly", "matplotlib"],
    route: str,
    mixed: bool,
    visibility: str,
    role_plugin: None,
) -> None:
    # [test->req~ring5.figure.legends~1]
    with ring5.Session() as session:
        config = {
            "mixed_y": mixed,
            "dual_axis": mixed,
            "visibility": visibility,
            "legend_font_size": 11.5,
            "legend2_font_size": 18.5,
            "legend_anchor_x": "left",
            "legend2_anchor_x": "right",
            "legend_x": 0.1,
            "legend2_x": 0.9,
        }
        plots = [session.create_plot("review_role_plot", data=_table(), config=config)]
        if "dashboard" in route:
            plots.append(session.create_plot("review_role_plot", data=_table(), config=config))
            dashboard = session.create_dashboard(
                plots, shared_legend=route == "shared_dashboard", columns=2
            )
            native = cast(Any, session.render_dashboard(dashboard, engine=engine))
        elif route == "report":
            native = (
                _single_plot_plotly(plots[0])
                if engine == "plotly"
                else _single_plot_figure(plots[0])
            )
        else:
            native = cast(Any, session.render(plots[0], engine=engine))
        expected = [
            role
            for role in ("primary", "secondary")
            if visibility not in (f"hide_{role}", f"exclude_{role}")
        ]
        try:
            if engine == "matplotlib":
                for panel in native.axes[: len(plots)]:
                    targets = [panel, panel._ring5_twin] if mixed else [panel]
                    measured = sorted(
                        patch.get_height() for target in targets for patch in target.patches
                    )
                    assert measured == sorted(
                        value
                        for role, value in (("primary", 3.0), ("secondary", 5.0))
                        if visibility != f"hide_{role}"
                    )
            if engine == "plotly":
                for index, trace in enumerate(native.data):
                    role = "primary" if index % 2 == 0 else "secondary"
                    assert list(trace.y) == ([3.0] if role == "primary" else [5.0])
                    assert trace.visible is (visibility != f"hide_{role}")
                    if visibility == f"exclude_{role}":
                        assert trace.showlegend is False
                    if route != "shared_dashboard":
                        legend = getattr(native.layout, trace.legend or "legend")
                        assert legend.font.size == (11.5 if role == "primary" else 18.5)
            elif route == "shared_dashboard":
                assert len(native.legends) == bool(expected)
                if expected:
                    assert [text.get_text() for text in native.legends[0].get_texts()] == expected
            else:
                for panel in native.axes[: len(plots)]:
                    targets = [panel, panel._ring5_twin] if mixed else [panel]
                    legends = [
                        artist
                        for target in targets
                        for artist in target.get_children()
                        if isinstance(artist, Legend)
                    ]
                    found = {legend.get_texts()[0].get_text(): legend for legend in legends}
                    assert set(found) == set(expected)
                    for role, legend in found.items():
                        assert legend.get_texts()[0].get_fontsize() == (
                            11.5 if role == "primary" else 18.5
                        )
        finally:
            if engine == "matplotlib":
                plt.close(native)


def test_reapplying_role_legends_removes_only_recorded_owned_artists(role_plugin: None) -> None:
    plot = _RolePlot(0, "Roles")
    data = pd.DataFrame({"x": ["a"], "v": [3.0], "w": [5.0]})
    prepared = prepare_figure(
        data,
        {"legend_font_size": 11.5, "legend2_font_size": 18.5},
        plot.plot_type,
        plot.create_traces,
    )
    figure, axis = plt.subplots()
    external = axis.legend(axis.plot([0], [1], label="external"), ["external"], fontsize=7)
    try:
        context = draw_matplotlib_axes(prepared, axis)
        for _ in range(2):
            FigureSpecToMatplotlib.apply(prepared.spec, axis, context)
            legends = [artist for artist in axis.get_children() if isinstance(artist, Legend)]
            assert len(legends) == 3
            assert external in legends
            assert external.get_texts()[0].get_fontsize() == 7
            assert sorted(legend.get_texts()[0].get_text() for legend in legends) == [
                "external",
                "primary",
                "secondary",
            ]
    finally:
        plt.close(figure)


@pytest.mark.public_api
@pytest.mark.parametrize("tier", ["legend_", "legend2_", "legend3_"])
@pytest.mark.parametrize("value", ["h", "v", "sideways", "HORIZONTAL", None, False])
def test_noncanonical_orientation_rejects_before_public_or_restore_publication(
    tier: str, value: Any
) -> None:
    # [test->req~ring5.api.plot-validation~1]
    key = f"{tier}orientation"
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="must be exactly"):
            session.create_plot("bar", data=_table(), config={"x": "x", "y": "v", key: value})
        assert not session.plots
    with pytest.raises(ValueError, match="must be exactly"):
        ring5.FigureSpec(extra={key: value})
    with patch.object(PlotFactory, "create_plot", side_effect=AssertionError("model published")):
        with pytest.raises(ValueError, match="must be exactly"):
            PlotFactory.from_dict(
                {"id": 0, "name": "Bad", "plot_type": "bar", "config": {key: value}}
            )
    with pytest.raises(ValueError, match="must be exactly"):
        ConfigSpecBuilder.from_config({key: value})


@pytest.mark.public_api
@pytest.mark.parametrize("tier", ["legend_", "legend2_", "legend3_"])
@pytest.mark.parametrize("value", ["horizontal", "vertical", "h", "v", "sideways"])
def test_recipe_orientation_is_checked_only_after_parameter_materialization(
    tier: str, value: str
) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    recipe = AnalysisRecipe(
        name="Orientation",
        source=RecipeSource(kind="csv", path="data.csv"),
        parameters=(RecipeParameter("orientation", "string", default=value),),
        plots=(
            RecipePlot(
                "Bars", "bar", {"x": "x", "y": "v", f"{tier}orientation": "{{orientation}}"}
            ),
        ),
    )
    payload = AnalysisRecipeService.dumps(recipe)
    assert json.loads(payload)["plots"][0]["config"][f"{tier}orientation"] == "{{orientation}}"
    restored = AnalysisRecipeService.loads(payload)
    if value in ("horizontal", "vertical"):
        with ring5.Session() as session:
            materialized = session.materialize_analysis_recipe(restored)
            assert materialized.plots[0].config[f"{tier}orientation"] == value
    else:
        with ring5.Session() as session:
            with pytest.raises(ring5.RecipeError, match="must be exactly"):
                session.materialize_analysis_recipe(restored)


@pytest.mark.public_api
@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
@pytest.mark.parametrize("tier", ["legend_", "legend2_", "legend3_"])
@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
def test_canonical_orientation_values_reach_both_native_models(
    engine: Literal["plotly", "matplotlib"],
    tier: str,
    orientation: str,
    role_plugin: None,
) -> None:
    # [test->req~ring5.api.plot-validation~1]
    with ring5.Session() as session:
        plot = session.create_plot(
            "review_role_plot", data=_table(), config={f"{tier}orientation": orientation}
        )
        native = cast(Any, session.render(plot, engine=engine))
        try:
            if engine == "plotly":
                legend = getattr(native.layout, tier[:-1])
                assert legend.orientation == ("h" if orientation == "horizontal" else "v")
            else:
                role = {"legend_": "primary", "legend2_": "secondary", "legend3_": "tertiary"}[tier]
                legend = next(item for item in native._ring5_spec.legends if item.role == role)
                assert legend.orientation == orientation
        finally:
            if engine == "matplotlib":
                plt.close(native)


@pytest.mark.public_api
@pytest.mark.parametrize(
    ("color", "alpha"), [("rgb(12 34 56)", None), ("rgba(12 34 56 / .25)", 0.25), ("#1234", 4 / 15)]
)
def test_matplotlib_color_projection_retains_opaque_defaults_and_embedded_opacity(
    color: str,
    alpha: float | None,
) -> None:
    default = plt.rcParams["legend.framealpha"]
    with ring5.Session() as session:
        figure = cast(
            Any,
            session.plot(
                "bar",
                data=_table(),
                config={"x": "x", "y": "v", "legend_bgcolor": color},
                engine="matplotlib",
            ),
        )
        try:
            assert figure.axes[0].get_legend().get_frame().get_alpha() == (
                default if alpha is None else alpha
            )
        finally:
            plt.close(figure)
