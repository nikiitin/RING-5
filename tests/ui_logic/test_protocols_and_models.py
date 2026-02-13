"""Tests for plot protocols -- runtime_checkable conformance and structural typing."""

from typing import Any, Dict

import pandas as pd

from tests.ui_logic.conftest import StubPlotHandle


class TestPlotHandleProtocol:
    """Verify PlotHandle runtime_checkable protocol."""

    def test_stub_satisfies_plot_handle(self) -> None:
        """StubPlotHandle is recognized by isinstance check."""
        from src.web.models.plot_protocols import PlotHandle

        plot = StubPlotHandle()
        assert isinstance(plot, PlotHandle)

    def test_plot_handle_requires_all_attributes(self) -> None:
        """Objects missing required attributes do NOT satisfy PlotHandle."""
        from src.web.models.plot_protocols import PlotHandle

        class Incomplete:
            plot_id: int = 1
            name: str = "x"
            # Missing: plot_type, config, processed_data, pipeline, pipeline_counter

        obj = Incomplete()
        assert not isinstance(obj, PlotHandle)

    def test_plot_handle_attribute_types(self) -> None:
        """Verify attribute types on a conforming object."""
        plot = StubPlotHandle(
            plot_id=5,
            name="Test",
            plot_type="bar",
            config={"x": 1},
            processed_data=pd.DataFrame({"a": [1]}),
            pipeline=[{"id": 1, "type": "sort", "config": {}}],
            pipeline_counter=1,
        )
        assert isinstance(plot.plot_id, int)
        assert isinstance(plot.name, str)
        assert isinstance(plot.plot_type, str)
        assert isinstance(plot.config, dict)
        assert isinstance(plot.processed_data, pd.DataFrame)
        assert isinstance(plot.pipeline, list)
        assert isinstance(plot.pipeline_counter, int)


class TestRenderablePlotProtocol:
    """Verify RenderablePlot combined protocol."""

    def test_stub_satisfies_renderable_plot(self) -> None:
        """StubPlotHandle satisfies RenderablePlot (PlotHandle + ConfigRenderer)."""
        from src.web.models.plot_protocols import RenderablePlot

        plot = StubPlotHandle()
        assert isinstance(plot, RenderablePlot)

    def test_config_renderer_methods_callable(self) -> None:
        """ConfigRenderer methods are callable on StubPlotHandle."""
        plot = StubPlotHandle()
        data = pd.DataFrame({"a": [1]})
        config: Dict[str, Any] = {"x": "a"}

        result = plot.render_config_ui(data, config)
        assert isinstance(result, dict)

        result = plot.render_advanced_options(config, data)
        assert isinstance(result, dict)

        result = plot.render_display_options(config)
        assert isinstance(result, dict)

        result = plot.render_theme_options(config)
        assert isinstance(result, dict)


class TestPlotModels:
    """Test plot model TypedDicts construction and required fields."""

    def test_shaper_step_construction(self) -> None:
        """ShaperStep can be constructed with required fields."""
        from src.web.models.plot_models import ShaperStep

        step: ShaperStep = {"id": 1, "type": "sort", "config": {"column": "a"}}
        assert step["id"] == 1
        assert step["type"] == "sort"
        assert step["config"]["column"] == "a"

    def test_plot_display_config_partial(self) -> None:
        """PlotDisplayConfig can be constructed with partial fields (total=False)."""
        from src.web.models.plot_models import PlotDisplayConfig

        cfg: PlotDisplayConfig = {  # type: ignore[typeddict-item]
            "x_column": "benchmark",
            "y_column": "ipc",
        }
        assert cfg["x_column"] == "benchmark"

    def test_margins_config(self) -> None:
        """MarginsConfig holds top/bottom/left/right."""
        from src.web.models.plot_models import MarginsConfig

        m: MarginsConfig = {"top": 10, "bottom": 20, "left": 30, "right": 40}
        assert m["top"] == 10
        assert m["right"] == 40

    def test_series_style_config(self) -> None:
        """SeriesStyleConfig holds name and color."""
        from src.web.models.plot_models import SeriesStyleConfig

        s: SeriesStyleConfig = {"name": "trace1", "color": "#ff0000"}
        assert s["name"] == "trace1"

    def test_relayout_event_data(self) -> None:
        """RelayoutEventData can hold axis range and legend position."""
        from src.web.models.plot_models import RelayoutEventData

        r: RelayoutEventData = {
            "legend_x": 0.5,
            "legend_y": 0.5,
            "legend_xanchor": "center",
        }
        assert r["legend_x"] == 0.5

    def test_annotation_shape_config(self) -> None:
        """AnnotationShapeConfig holds shape type and coordinates."""
        from src.web.models.plot_models import AnnotationShapeConfig

        a: AnnotationShapeConfig = {
            "type": "rect",
            "x0": 0,
            "y0": 0,
            "x1": 1,
            "y1": 1,
        }
        assert a["type"] == "rect"
