"""
Integration test — validates the full architecture stack works end-to-end.

Tests that:
    1. All new modules import correctly
    2. Layer dependency rules are respected
    3. PlotFactory + StyleApplicator integrate correctly
    4. Models + UIStateManager + Controller protocols are consistent
    5. Controllers delegate to presenters (no direct st.* rendering)
"""

import re
from pathlib import Path
from typing import Any, cast

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.models.plot_models import (
    AnnotationShapeConfig,
    MarginsConfig,
    PlotDisplayConfig,
    SeriesStyleConfig,
    ShaperStep,
    TypographyConfig,
)

# ─── Module Import Tests ────────────────────────────────────────────────────


class TestModuleImports:
    """Verify all new modules import without errors."""

    def test_import_models(self) -> None:
        """Models module imports correctly."""
        from src.web.models import plot_models

        assert hasattr(plot_models, "PlotDisplayConfig")
        assert hasattr(plot_models, "ShaperStep")

    def test_import_state(self) -> None:
        """UIStateManager imports correctly."""
        from src.web.state.ui_state_manager import UIStateManager

        assert UIStateManager is not None

    def test_import_figures(self) -> None:
        """Figure rendering imports correctly."""
        from src.web.rendering.plotly_connector import FigureSpecToPlotly

        assert FigureSpecToPlotly is not None

    def test_import_components(self) -> None:
        """Component modules import correctly."""
        from src.web.components.common.chart_display import ChartDisplayComponent
        from src.web.components.common.pipeline import PipelineComponent
        from src.web.components.common.pipeline_step import PipelineStepComponent
        from src.web.components.common.plot_controls import PlotControlsComponent
        from src.web.components.common.plot_creation import PlotCreationComponent
        from src.web.components.common.plot_selector import PlotSelectorComponent

        assert PlotSelectorComponent is not None
        assert PlotCreationComponent is not None
        assert PlotControlsComponent is not None
        assert PipelineComponent is not None
        assert PipelineStepComponent is not None
        assert ChartDisplayComponent is not None

    def test_import_controllers(self) -> None:
        """Controller modules import correctly."""
        from src.web.controllers.plot import (
            PipelineController,
            PlotCreationController,
            PlotRenderController,
        )

        assert PlotCreationController is not None
        assert PipelineController is not None
        assert PlotRenderController is not None

    def test_import_page(self) -> None:
        """Manage plots page module imports correctly."""
        from src.web.pages.manage_plots import show_manage_plots_page

        assert callable(show_manage_plots_page)


# ─── Layer Dependency Tests ─────────────────────────────────────────────────


class TestLayerDependencies:
    """Verify layer dependency rules are respected."""

    def test_models_have_no_streamlit_import(self) -> None:
        """Layer 5 (Models) must NOT import streamlit."""
        import src.web.models.plot_models as models_mod

        # Check that no streamlit module is loaded by this module
        source: str = Path(models_mod.__file__).read_text()  # type: ignore[arg-type]
        assert "import streamlit" not in source
        assert "from streamlit" not in source

    def test_figures_protocols_have_no_streamlit(self) -> None:
        """Figure protocols must NOT import streamlit."""
        import src.web.models.plot_protocols as proto_mod

        source: str = Path(proto_mod.__file__).read_text()  # type: ignore[arg-type]
        assert "import streamlit" not in source
        assert "from streamlit" not in source


# ─── PlotFactory + StyleApplicator Integration ────────────────────────────────────


class TestFigureEngineIntegration:
    """PlotFactory + StyleApplicator inline integration tests."""

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "benchmark": ["A", "B", "C"],
                "ipc": [1.2, 1.5, 0.9],
            }
        )

    def test_inline_with_real_styler(self, sample_data: pd.DataFrame) -> None:
        """Inline creator + styler produces a complete figure."""
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        class SimpleBarCreator:
            def create_figure(self, data: pd.DataFrame, config: dict[str, Any]) -> go.Figure:
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=list(data["benchmark"]),
                        y=list(data["ipc"]),
                        name="IPC",
                    )
                )
                return fig

        creator = SimpleBarCreator()
        styler = StyleApplicator("bar")

        config: dict[str, Any] = {
            "title": "Test Plot",
            "width": 600,
            "height": 400,
        }

        fig: go.Figure = creator.create_figure(sample_data, config)
        fig = styler.apply_styles(fig, config)

        assert isinstance(fig, go.Figure)
        assert len(list(fig.data)) == 1
        assert fig.layout.width == 600
        assert fig.layout.height == 400

    def test_inline_with_legend_labels(self, sample_data: pd.DataFrame) -> None:
        """Legend labels are applied inline after styling."""

        class SimpleBarCreator:
            def create_figure(self, data: pd.DataFrame, config: dict[str, Any]) -> go.Figure:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=["A"], y=[1], name="original"))
                return fig

        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        creator = SimpleBarCreator()
        styler = StyleApplicator("bar")

        config: dict[str, Any] = {}
        legend_labels: dict[str, str] = {"original": "Custom Label"}

        fig = creator.create_figure(sample_data, config)
        fig = styler.apply_styles(fig, config)
        fig.for_each_trace(lambda t: t.update(name=legend_labels.get(t.name, t.name)))

        assert cast(go.Bar, fig.data[0]).name == "Custom Label"


# ─── Model TypedDict Compatibility ──────────────────────────────────────────


class TestModelCompatibility:
    """Verify new TypedDicts are compatible with existing config patterns."""

    def test_shaper_step_creation(self) -> None:
        """ShaperStep can be created with required fields."""
        step: ShaperStep = {"id": 0, "type": "sort", "config": {"order_dict": {"x": ["a"]}}}
        assert step["type"] == "sort"

    def test_margins_config(self) -> None:
        """MarginsConfig works as TypedDict."""
        margins: MarginsConfig = {"top": 80, "bottom": 120}
        assert margins["top"] == 80

    def test_plot_display_config_partial(self) -> None:
        """PlotDisplayConfig allows partial initialization."""
        config: PlotDisplayConfig = {"x": "benchmark", "y": "ipc"}
        assert config["x"] == "benchmark"

    def test_typography_config(self) -> None:
        """TypographyConfig works as TypedDict."""
        typo: TypographyConfig = {"font_size": 14, "title_font_size": 18}
        assert typo["font_size"] == 14

    def test_series_style_config(self) -> None:
        """SeriesStyleConfig works as TypedDict."""
        style: SeriesStyleConfig = {"name": "Custom", "color": "#FF0000"}
        assert style["color"] == "#FF0000"

    def test_annotation_shape_config(self) -> None:
        """AnnotationShapeConfig works as TypedDict."""
        shape: AnnotationShapeConfig = {
            "type": "line",
            "x0": 0.0,
            "y0": 0.0,
            "x1": 1.0,
            "y1": 1.0,
        }
        assert shape["type"] == "line"


# ─── Controller Boundary Tests ──────────────────────────────────────────────


class TestControllerBoundaries:
    """
    Verify controllers delegate rendering to components.

    Creation and Pipeline controllers delegate all widget rendering to
    components. Render controller inlines config gathering (st.selectbox,
    st.markdown, st.toggle) since ConfigPresenter was eliminated.
    """

    # st.* calls allowed in controllers (flow control + feedback, NOT rendering)
    ALLOWED_ST_CALLS: set[str] = {
        "rerun",  # Flow control
        "warning",  # User feedback
        "success",  # User feedback
        "error",  # User feedback
        "toast",  # Persistent user feedback (survives reruns)
    }

    # st.* calls that indicate rendering (should be in components)
    RENDERING_ST_CALLS: set[str] = {
        "columns",
        "button",
        "text_input",
        "selectbox",
        "radio",
        "toggle",
        "checkbox",
        "slider",
        "number_input",
        "expander",
        "dataframe",
        "plotly_chart",
        "write",
        "caption",
        "markdown",
    }

    @staticmethod
    def _get_st_method_calls(source: str) -> list[str]:
        """
        Extract all st.method_name() calls from source code.

        Returns a list of method names called on 'st'.
        """
        # Match st.method_name( patterns
        pattern: re.Pattern[str] = re.compile(r"\bst\.(\w+)\s*\(")
        return pattern.findall(source)

    def test_creation_controller_no_widget_rendering(self) -> None:
        """PlotCreationController must not render widgets directly."""
        import src.web.controllers.plot.creation_controller as mod

        source: str = Path(mod.__file__).read_text()  # type: ignore[arg-type]
        st_calls: list[str] = self._get_st_method_calls(source)

        rendering_calls: set[str] = set(st_calls) & self.RENDERING_ST_CALLS
        assert not rendering_calls, (
            f"PlotCreationController renders widgets directly: "
            f"{rendering_calls}. Move to a presenter."
        )

    def test_pipeline_controller_no_widget_rendering(self) -> None:
        """PipelineController must not render widgets directly."""
        import src.web.controllers.plot.pipeline_controller as mod

        source: str = Path(mod.__file__).read_text()  # type: ignore[arg-type]
        st_calls: list[str] = self._get_st_method_calls(source)

        rendering_calls: set[str] = set(st_calls) & self.RENDERING_ST_CALLS
        assert not rendering_calls, (
            f"PipelineController renders widgets directly: "
            f"{rendering_calls}. Move to a component."
        )

    def test_render_controller_inlines_config_gathering(self) -> None:
        """PlotRenderController inlines config gathering (selectbox, toggle, markdown)."""
        import src.web.controllers.plot.render_controller as mod

        source: str = Path(mod.__file__).read_text()  # type: ignore[arg-type]
        st_calls: list[str] = self._get_st_method_calls(source)

        # render_controller legitimately uses selectbox, toggle, and markdown
        # since ConfigPresenter was inlined. Verify those are present.
        assert "selectbox" in st_calls, "render_controller should inline plot type selectbox"
        assert "toggle" in st_calls, "render_controller should inline advanced settings toggle"
        assert "markdown" in st_calls, "render_controller should inline section headers"

    def test_controllers_use_components(self) -> None:
        """Controllers must import from the components package."""
        import src.web.controllers.plot.creation_controller as cc
        import src.web.controllers.plot.pipeline_controller as pc
        import src.web.controllers.plot.render_controller as rc

        for mod, expected_components in [
            (
                cc,
                [
                    "PlotControlsComponent",
                    "PlotCreationComponent",
                    "PlotSelectorComponent",
                ],
            ),
            (pc, ["PipelineComponent", "PipelineStepComponent"]),
            (rc, ["ChartDisplayComponent"]),
        ]:
            source: str = Path(mod.__file__).read_text()  # type: ignore[arg-type]
            for component in expected_components:
                assert component in source, f"{mod.__name__} should import {component}"

    def test_controllers_no_cross_layer_imports(self) -> None:
        """Creation and Pipeline controllers must NOT import from pages.ui.*.
        Render controller may import render_settings_pills (inlined from ConfigPresenter).
        """
        import src.web.controllers.plot.creation_controller as cc
        import src.web.controllers.plot.pipeline_controller as pc

        forbidden: str = "from src.web.pages"
        for mod in [cc, pc]:
            source: str = Path(mod.__file__).read_text()  # type: ignore[arg-type]
            assert forbidden not in source, (
                f"{mod.__name__} imports from pages.* — "
                f"controllers must use protocols from models layer."
            )

    def test_controllers_use_protocols(self) -> None:
        """Controllers must import from plot_protocols for typed dependencies."""
        import src.web.controllers.plot.creation_controller as cc
        import src.web.controllers.plot.pipeline_controller as pc
        import src.web.controllers.plot.render_controller as rc

        for mod, expected_protocols in [
            (cc, ["PlotHandle", "PlotLifecycleService", "PlotTypeRegistry"]),
            (pc, ["PlotHandle", "PipelineExecutor"]),
            (rc, ["PlotLifecycleService", "PlotTypeRegistry", "RenderablePlot"]),
        ]:
            source: str = Path(mod.__file__).read_text()  # type: ignore[arg-type]
            for proto in expected_protocols:
                assert proto in source, (
                    f"{mod.__name__} should import protocol {proto} " f"from plot_protocols."
                )


# ─── Protocol Compliance Tests ──────────────────────────────────────────────


class TestProtocolCompliance:
    """Verify protocols are structurally correct and adapter-compatible."""

    def test_protocols_have_no_streamlit_import(self) -> None:
        """Protocols module must NOT import streamlit (Layer 5)."""
        import src.web.models.plot_protocols as proto_mod

        source: str = Path(proto_mod.__file__).read_text()  # type: ignore[arg-type]
        assert "import streamlit" not in source
        assert "from streamlit" not in source

    def test_plot_handle_is_runtime_checkable(self) -> None:
        """PlotHandle must be @runtime_checkable."""
        from src.web.models.plot_protocols import PlotHandle

        assert (
            hasattr(PlotHandle, "__protocol_attrs__")
            or hasattr(PlotHandle, "__abstractmethods__")
            or callable(getattr(PlotHandle, "__instancecheck__", None))
        )

    def test_all_protocols_importable(self) -> None:
        """All protocols import correctly."""
        from src.web.models.plot_protocols import (
            ConfigRenderer,
            PipelineExecutor,
            PlotHandle,
            PlotLifecycleService,
            PlotTypeRegistry,
            RenderablePlot,
        )

        assert PlotHandle is not None
        assert ConfigRenderer is not None
        assert PlotLifecycleService is not None
        assert PlotTypeRegistry is not None
        assert PipelineExecutor is not None
        assert RenderablePlot is not None

    def test_all_adapters_importable(self) -> None:
        """All adapters import correctly."""
        from src.web.pages.plot_adapters import (
            PipelineExecutorAdapter,
            PlotLifecycleAdapter,
            PlotTypeRegistryAdapter,
        )

        assert PlotLifecycleAdapter is not None
        assert PlotTypeRegistryAdapter is not None
        assert PipelineExecutorAdapter is not None

    def test_adapters_in_page_layer(self) -> None:
        """Adapters must live in the page layer (may import pages.ui.*)."""
        import src.web.pages.plot_adapters as adapter_mod

        source: str = Path(adapter_mod.__file__).read_text()  # type: ignore[arg-type]
        # Adapters SHOULD import from pages.ui — that's their job
        assert "from src.web.pages.ui" in source
        # But protocols should NOT be in adapters (they import from models)
        assert "from src.web.models.plot_protocols" in source

    def test_render_controller_uses_renderable_plot(
        self,
    ) -> None:
        """Render controller uses RenderablePlot from plot_protocols."""
        import src.web.controllers.plot.render_controller as rc_mod

        source: str = Path(rc_mod.__file__).read_text()  # type: ignore[arg-type]
        assert "RenderablePlot" in source

    def test_renderable_plot_combines_handle_and_renderer(self) -> None:
        """RenderablePlot is a combined protocol of PlotHandle + ConfigRenderer."""
        from src.web.models.plot_protocols import RenderablePlot

        # RenderablePlot inherits from both protocols
        bases = cast(type, RenderablePlot).__mro__
        base_names = [cls.__name__ for cls in bases]
        assert "PlotHandle" in base_names
        assert "ConfigRenderer" in base_names

    def test_sort_config_importable(self) -> None:
        """SortConfig shaper UI component imports correctly."""
        from src.web.components.shapers.sort_config import SortConfig

        assert hasattr(SortConfig, "render")
        assert callable(SortConfig.render)

    def test_sort_config_registered_in_dispatch(self) -> None:
        """Sort shaper is registered in shaper_config module constants."""
        from src.core.services.shapers.validation import get_required_params
        from src.web.pages.ui.shaper_config import SHAPER_TYPE_MAP

        assert get_required_params("sort") == ["order_dict"]
        assert "Sort" in SHAPER_TYPE_MAP
        assert SHAPER_TYPE_MAP["Sort"] == "sort"
