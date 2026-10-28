"""Tests for plot protocols -- runtime_checkable conformance and structural typing."""

from typing import Any, cast

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
            pipeline=cast(Any, [{"id": 1, "type": "sort", "config": {}}]),
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
        config: dict[str, Any] = {"x": "a"}

        result = plot.render_config_ui(data, config)
        assert isinstance(result, dict)

        result = plot.render_settings_section("layout", config, data)
        assert isinstance(result, dict)
