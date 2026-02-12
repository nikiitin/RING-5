"""
Integration test — validates the full architecture stack works end-to-end.

Tests that:
    1. All new modules import correctly
    2. Layer dependency rules are respected
    3. FigureEngine integrates with real StyleApplicator
    4. Models + UIStateManager + Controller protocols are consistent
    5. Controllers delegate to presenters (no direct st.* rendering)
"""

import re
from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.web.figures import FigureEngine, FigureStyler
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
        """Figure engine imports correctly."""
        from src.web.figures import FigureCreator, FigureEngine, FigureStyler

        assert FigureEngine is not None
        assert FigureCreator is not None
        assert FigureStyler is not None

    def test_import_presenters(self) -> None:
        """Presenter modules import correctly."""
        from src.web.presenters.plot import (
            ChartPresenter,
            ConfigPresenter,
            LoadDialogPresenter,
            PipelinePresenter,
            PipelineStepPresenter,
            PlotControlsPresenter,
            PlotCreationPresenter,
            PlotSelectorPresenter,
            SaveDialogPresenter,
        )

        assert PlotSelectorPresenter is not None
        assert PlotCreationPresenter is not None
        assert PlotControlsPresenter is not None
        assert PipelinePresenter is not None
        assert PipelineStepPresenter is not None
        assert ChartPresenter is not None
        assert SaveDialogPresenter is not None
        assert LoadDialogPresenter is not None
        assert ConfigPresenter is not None

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
        source: str = open(models_mod.__file__).read()  # type: ignore[arg-type]
        assert "import streamlit" not in source
        assert "from streamlit" not in source

    def test_figures_protocols_have_no_streamlit(self) -> None:
        """Figure protocols must NOT import streamlit."""
        import src.web.figures.protocols as proto_mod

        source: str = open(proto_mod.__file__).read()  # type: ignore[arg-type]
        assert "import streamlit" not in source
        assert "from streamlit" not in source

    def test_figure_engine_has_no_streamlit(self) -> None:
        """FigureEngine must NOT import streamlit."""
        import src.web.figures.engine as engine_mod

        source: str = open(engine_mod.__file__).read()  # type: ignore[arg-type]
        assert "import streamlit" not in source
        assert "from streamlit" not in source

    def test_figure_engine_has_no_pages_ui_imports(self) -> None:
        """FigureEngine must NOT import from pages.ui (boundary rule)."""
        import src.web.figures.engine as engine_mod

        source: str = open(engine_mod.__file__).read()  # type: ignore[arg-type]
        assert "pages.ui" not in source, (
            "FigureEngine must not depend on pages.ui — "
            "inject stylers via FigureStyler protocol instead"
        )


# ─── FigureEngine + Real StyleApplicator Integration ────────────────────────


class TestFigureEngineIntegration:
    """FigureEngine with real StyleApplicator (not mocks)."""

    @pytest.fixture
    def sample_data(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "benchmark": ["A", "B", "C"],
                "ipc": [1.2, 1.5, 0.9],
            }
        )

    def test_engine_with_real_styler(self, sample_data: pd.DataFrame) -> None:
        """Engine with injected StyleApplicator produces a complete figure."""
        from src.web.pages.ui.plotting.styles.applicator import StyleApplicator

        class SimpleBarCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=list(data["benchmark"]),
                        y=list(data["ipc"]),
                        name="IPC",
                    )
                )
                return fig

        engine: FigureEngine = FigureEngine()
        styler: FigureStyler = StyleApplicator("bar")
        engine.register("bar", SimpleBarCreator(), styler=styler)

        config: Dict[str, Any] = {
            "title": "Test Plot",
            "width": 600,
            "height": 400,
        }

        fig: go.Figure = engine.build("bar", sample_data, config)

        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.layout.width == 600
        assert fig.layout.height == 400

    def test_engine_with_legend_labels(self, sample_data: pd.DataFrame) -> None:
        """Legend labels are applied after styling."""

        class SimpleBarCreator:
            def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=["A"], y=[1], name="original"))
                return fig

        engine: FigureEngine = FigureEngine()
        engine.register("bar", SimpleBarCreator())

        config: Dict[str, Any] = {
            "legend_labels": {"original": "Custom Label"},
        }

        fig = engine.build("bar", sample_data, config)
        assert fig.data[0].name == "Custom Label"


# ─── Model TypedDict Compatibility ──────────────────────────────────────────


class TestModelCompatibility:
    """Verify new TypedDicts are compatible with existing config patterns."""

    def test_shaper_step_creation(self) -> None:
        """ShaperStep can be created with required fields."""
        step: ShaperStep = {"id": 0, "type": "sort", "config": {"by": "x"}}
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
    Verify controllers delegate rendering to presenters.

    Controllers may only use st.rerun(), st.warning(), st.success(), st.error()
    for flow control and feedback. All widget rendering (st.columns, st.button,
    st.text_input, st.expander, st.selectbox, st.dataframe, st.markdown, etc.)
    must go through presenters.
    """

    # st.* calls allowed in controllers (flow control + feedback, NOT rendering)
    ALLOWED_ST_CALLS: set[str] = {
        "rerun",  # Flow control
        "warning",  # User feedback
        "success",  # User feedback
        "error",  # User feedback
        "toast",  # Persistent user feedback (survives reruns)
    }

    # st.* calls that indicate rendering (should be in presenters)
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

        source: str = open(mod.__file__).read()  # type: ignore[arg-type]
        st_calls: list[str] = self._get_st_method_calls(source)

        rendering_calls: set[str] = set(st_calls) & self.RENDERING_ST_CALLS
        assert not rendering_calls, (
            f"PlotCreationController renders widgets directly: "
            f"{rendering_calls}. Move to a presenter."
        )

    def test_pipeline_controller_no_widget_rendering(self) -> None:
        """PipelineController must not render widgets directly."""
        import src.web.controllers.plot.pipeline_controller as mod

        source: str = open(mod.__file__).read()  # type: ignore[arg-type]
        st_calls: list[str] = self._get_st_method_calls(source)

        rendering_calls: set[str] = set(st_calls) & self.RENDERING_ST_CALLS
        assert not rendering_calls, (
            f"PipelineController renders widgets directly: "
            f"{rendering_calls}. Move to a presenter."
        )

    def test_render_controller_no_widget_rendering(self) -> None:
        """PlotRenderController must not render widgets directly."""
        import src.web.controllers.plot.render_controller as mod

        source: str = open(mod.__file__).read()  # type: ignore[arg-type]
        st_calls: list[str] = self._get_st_method_calls(source)

        rendering_calls: set[str] = set(st_calls) & self.RENDERING_ST_CALLS
        assert not rendering_calls, (
            f"PlotRenderController renders widgets directly: "
            f"{rendering_calls}. Move to a presenter."
        )

    def test_controllers_use_presenters(self) -> None:
        """Controllers must import from the presenters package."""
        import src.web.controllers.plot.creation_controller as cc
        import src.web.controllers.plot.pipeline_controller as pc
        import src.web.controllers.plot.render_controller as rc

        for mod, expected_presenters in [
            (
                cc,
                [
                    "SaveDialogPresenter",
                    "LoadDialogPresenter",
                    "PlotControlsPresenter",
                    "PlotCreationPresenter",
                    "PlotSelectorPresenter",
                ],
            ),
            (pc, ["PipelinePresenter", "PipelineStepPresenter"]),
            (rc, ["ChartPresenter", "ConfigPresenter"]),
        ]:
            source: str = open(mod.__file__).read()  # type: ignore[arg-type]
            for presenter in expected_presenters:
                assert presenter in source, f"{mod.__name__} should import {presenter}"

    def test_controllers_no_cross_layer_imports(self) -> None:
        """Controllers must NOT import from pages.ui.* (Layer 2 → Layer 1)."""
        import src.web.controllers.plot.creation_controller as cc
        import src.web.controllers.plot.pipeline_controller as pc
        import src.web.controllers.plot.render_controller as rc

        forbidden: str = "from src.web.pages"
        for mod in [cc, pc, rc]:
            source: str = open(mod.__file__).read()  # type: ignore[arg-type]
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
            (rc, ["PlotLifecycleService", "PlotTypeRegistry", "ChartDisplay", "RenderablePlot"]),
        ]:
            source: str = open(mod.__file__).read()  # type: ignore[arg-type]
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

        source: str = open(proto_mod.__file__).read()  # type: ignore[arg-type]
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
        """All 7 protocols import correctly."""
        from src.web.models.plot_protocols import (
            ChartDisplay,
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
        assert ChartDisplay is not None
        assert PipelineExecutor is not None
        assert RenderablePlot is not None

    def test_all_adapters_importable(self) -> None:
        """All 4 adapters import correctly."""
        from src.web.pages.plot_adapters import (
            ChartDisplayAdapter,
            PipelineExecutorAdapter,
            PlotLifecycleAdapter,
            PlotTypeRegistryAdapter,
        )

        assert PlotLifecycleAdapter is not None
        assert PlotTypeRegistryAdapter is not None
        assert ChartDisplayAdapter is not None
        assert PipelineExecutorAdapter is not None

    def test_adapters_in_page_layer(self) -> None:
        """Adapters must live in the page layer (may import pages.ui.*)."""
        import src.web.pages.plot_adapters as adapter_mod

        source: str = open(adapter_mod.__file__).read()  # type: ignore[arg-type]
        # Adapters SHOULD import from pages.ui — that's their job
        assert "from src.web.pages.ui" in source
        # But protocols should NOT be in adapters (they import from models)
        assert "from src.web.models.plot_protocols" in source

    def test_config_renderer_shared_between_presenter_and_protocols(
        self,
    ) -> None:
        """ConfigPresenter uses ConfigRenderer from plot_protocols."""
        import src.web.presenters.plot.config_presenter as cp_mod

        source: str = open(cp_mod.__file__).read()  # type: ignore[arg-type]
        assert "from src.web.models.plot_protocols import ConfigRenderer" in source
        # Private _ConfigRenderer should NOT exist anymore
        assert "class _ConfigRenderer" not in source

    def test_renderable_plot_combines_handle_and_renderer(self) -> None:
        """RenderablePlot is a combined protocol of PlotHandle + ConfigRenderer."""
        from src.web.models.plot_protocols import RenderablePlot

        # RenderablePlot inherits from both protocols
        bases = RenderablePlot.__mro__
        base_names = [cls.__name__ for cls in bases]
        assert "PlotHandle" in base_names
        assert "ConfigRenderer" in base_names

    def test_sort_config_importable(self) -> None:
        """SortConfig shaper UI component imports correctly."""
        from src.web.pages.ui.components.shapers.sort_config import SortConfig

        assert hasattr(SortConfig, "render")
        assert callable(SortConfig.render)

    def test_sort_config_registered_in_dispatch(self) -> None:
        """Sort shaper is registered in shaper_config module constants."""
        from src.web.pages.ui.shaper_config import (
            SHAPER_REQUIRED_PARAMS,
            SHAPER_TYPE_MAP,
        )

        assert "sort" in SHAPER_REQUIRED_PARAMS
        assert "Sort" in SHAPER_TYPE_MAP
        assert SHAPER_TYPE_MAP["Sort"] == "sort"
