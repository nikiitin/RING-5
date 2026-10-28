"""
Tests for Plot Components — verify pure UI rendering returns correct dicts.

Since components call Streamlit widgets, we mock st.* to verify:
    1. Correct widget types are rendered
    2. Return dicts have the expected keys and types
    3. No state mutations or API calls happen
"""

from typing import Any, cast

import ring5
from unittest.mock import MagicMock, patch

import pandas as pd
from src.core.services.shapers.factory import ShaperFactory

# PlotCreationComponent Tests


class TestPlotCreationComponent:
    """Tests for PlotCreationComponent."""

    @patch("src.web.components.common.plot_creation.st")
    def test_render_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """Return dict has name, plot_type, create_clicked."""
        from src.web.components.common.plot_creation import PlotCreationComponent

        # Setup mocks
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "My Plot"
        mock_st.selectbox.return_value = "bar"
        mock_st.form_submit_button.return_value = False

        result: dict[str, Any] = PlotCreationComponent.render(
            default_name="Plot 1", available_types=["bar", "line"]
        )

        assert "name" in result
        assert "plot_type" in result
        assert "create_clicked" in result

    @patch("src.web.components.common.plot_creation.st")
    def test_render_returns_user_input(self, mock_st: MagicMock) -> None:
        """Returns the values from widgets."""
        from src.web.components.common.plot_creation import PlotCreationComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "Custom Name"
        mock_st.selectbox.return_value = "scatter"
        mock_st.form_submit_button.return_value = True

        result = PlotCreationComponent.render("Default", ["bar", "scatter"])

        assert result["name"] == "Custom Name"
        assert result["plot_type"] == "scatter"
        assert result["create_clicked"] is True

    @patch("src.web.components.common.plot_creation.st")
    def test_render_does_not_access_session_state(self, mock_st: MagicMock) -> None:
        """Component does not read/write session_state."""
        from src.web.components.common.plot_creation import PlotCreationComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "X"
        mock_st.selectbox.return_value = "bar"
        mock_st.form_submit_button.return_value = False

        PlotCreationComponent.render("X", ["bar"])

        # session_state should never be accessed
        mock_st.session_state.__getitem__.assert_not_called()
        mock_st.session_state.__setitem__.assert_not_called()


# PlotControlsComponent Tests


class TestPlotControlsComponent:
    """Tests for PlotControlsComponent."""

    @patch("src.web.components.common.plot_controls.st")
    def test_render_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """Return dict has all action keys."""
        from src.web.components.common.plot_controls import PlotControlsComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "My Plot"
        mock_st.button.return_value = False

        result: dict[str, Any] = PlotControlsComponent.render(plot_id=1, current_name="My Plot")

        expected_keys: list[str] = [
            "new_name",
            "delete_clicked",
            "duplicate_clicked",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    @patch("src.web.components.common.plot_controls.st")
    def test_render_detects_rename(self, mock_st: MagicMock) -> None:
        """Detects name change via text_input."""
        from src.web.components.common.plot_controls import PlotControlsComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "New Name"
        mock_st.button.return_value = False

        result = PlotControlsComponent.render(plot_id=1, current_name="Old Name")

        assert result["new_name"] == "New Name"


# PlotSelectorComponent Tests


class TestPlotSelectorComponent:
    """Tests for PlotSelectorComponent."""

    @patch("src.web.components.common.plot_selector.st")
    def test_render_returns_selected_id(self, mock_st: MagicMock) -> None:
        """Return the selected immutable ID independently of its label."""
        from src.web.components.common.plot_selector import PlotSelectorComponent

        mock_st.pills.return_value = 2
        result = PlotSelectorComponent.render(
            {1: "Plot 1", 2: "Plot 2", 3: "Plot 3"}, key="plot.1.selector"
        )
        assert result == 2

    @patch("src.web.components.common.plot_selector.st")
    def test_pills_called_correctly(self, mock_st: MagicMock) -> None:
        """Render a required ID selector with its caller-prepared key."""
        from src.web.components.common.plot_selector import PlotSelectorComponent

        mock_st.pills.return_value = 0
        PlotSelectorComponent.render({0: "Plot 1"}, key="plot.0.selector")
        mock_st.pills.assert_called_once()
        args, kwargs = mock_st.pills.call_args
        assert args == ("Select Plot", [0])
        assert kwargs["key"] == "plot.0.selector"
        assert kwargs["required"] is True
        assert "default" not in kwargs
        assert kwargs["format_func"](0) == "Plot 1"


# PipelineComponent Tests


class TestPipelineComponent:
    """Tests for PipelineComponent."""

    @patch("src.web.components.common.pipeline.st")
    def test_render_add_shaper_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """render_add_shaper returns add_clicked and shaper_type."""
        from src.web.components.common.pipeline import PipelineComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.selectbox.return_value = "Sort"
        mock_st.button.return_value = True

        result: dict[str, Any] = PipelineComponent.render_add_shaper(
            plot_id=1, display_names=ShaperFactory.get_display_name_map()
        )

        assert result["add_clicked"] is True
        assert result["shaper_type"] == "sort"

    @patch("src.web.components.common.pipeline.st")
    def test_render_finalize_button(self, mock_st: MagicMock) -> None:
        """render_finalize_button returns button state."""
        from src.web.components.common.pipeline import PipelineComponent

        mock_st.button.return_value = True

        result: bool = PipelineComponent.render_finalize_button(plot_id=1)
        assert result is True

    def test_shaper_display_map_consistency(self) -> None:
        """Canonical editor labels identify their registered operation."""

        for display_name, internal_type in ShaperFactory.get_display_name_map().items():
            assert ShaperFactory.get_display_name(internal_type) == display_name

    @patch("src.web.components.common.pipeline.st")
    def test_render_shaper_controls_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """render_shaper_controls returns move/delete action flags."""
        from src.web.components.common.pipeline import PipelineComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.button.return_value = False

        result: dict[str, bool] = PipelineComponent.render_shaper_controls(
            plot_id=1,
            idx=0,
            is_first=True,
            is_last=False,
        )

        assert "move_up" in result
        assert "move_down" in result
        assert "delete" in result


# ChartDisplayComponent Tests


class TestChartDisplayComponent:
    """Tests for ChartDisplayComponent."""

    @patch("src.web.components.common.chart_display.st")
    def test_render_refresh_controls_returns_expected_keys(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Returns auto_refresh, manual_refresh, should_generate."""
        from src.web.components.common.chart_display import ChartDisplayComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = True
        mock_st.button.return_value = False

        result: dict[str, Any] = ChartDisplayComponent.render_refresh_controls(
            plot_id=1,
            auto_refresh=True,
            config_changed=True,
        )

        assert "auto_refresh" in result
        assert "manual_refresh" in result
        assert "should_generate" in result

    @patch("src.web.components.common.chart_display.st")
    def test_should_generate_when_auto_and_changed(
        self,
        mock_st: MagicMock,
    ) -> None:
        """should_generate is True when auto=True and config changed."""
        from src.web.components.common.chart_display import ChartDisplayComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = True
        mock_st.button.return_value = False

        result = ChartDisplayComponent.render_refresh_controls(
            plot_id=1,
            auto_refresh=True,
            config_changed=True,
        )

        assert result["should_generate"] is True

    @patch("src.web.components.common.chart_display.render_download_section")
    @patch("src.web.components.common.chart_display.interactive_plotly_chart")
    def test_plotly_modebar_uses_configured_export_scale(
        self,
        mock_chart: MagicMock,
        mock_download: MagicMock,
        plot_session: ring5.Session,
    ) -> None:
        # [test->req~ring5.export.plotly-scale~1]
        """The configured export scale reaches Plotly's mode-bar image control."""
        from src.web.components.common.chart_display import ChartDisplayComponent

        source_data = pd.DataFrame({"ipc": [2.1]})
        plot = plot_session.create_plot(
            "bar",
            data=ring5.Table(source_data),
            config={"x": "ipc", "y": "ipc", "width": 900, "height": 540, "export_scale": 3},
        )
        plot_session.render(plot)
        artifact = plot.render_artifact
        ChartDisplayComponent.render_plotly_chart(artifact, plot_id=7, plot_name="ipc")

        plotly_config = mock_chart.call_args.kwargs["config"]
        assert plotly_config["toImageButtonOptions"] == {
            "format": "svg",
            "filename": "ipc_view",
            "height": 540,
            "width": 900,
            "scale": 3,
        }
        assert mock_chart.call_args.kwargs["capture_click"] is False
        mock_download.assert_called_once_with(7, "ipc", artifact)
        assert mock_chart.call_args.args[0] is artifact.figure

    @patch("src.web.components.common.chart_display.st")
    def test_should_not_generate_when_no_auto_and_no_manual(
        self,
        mock_st: MagicMock,
    ) -> None:
        """should_generate is False when auto=False and no manual click."""
        from src.web.components.common.chart_display import ChartDisplayComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = False
        mock_st.button.return_value = False

        result = ChartDisplayComponent.render_refresh_controls(
            plot_id=1,
            auto_refresh=False,
            config_changed=True,
        )

        assert result["should_generate"] is False

    @patch("src.web.components.common.chart_display.st")
    def test_should_generate_on_manual_click(
        self,
        mock_st: MagicMock,
    ) -> None:
        """should_generate is True on manual Refresh click even if no auto."""
        from src.web.components.common.chart_display import ChartDisplayComponent

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = False
        mock_st.button.return_value = True  # Manual click

        result = ChartDisplayComponent.render_refresh_controls(
            plot_id=1,
            auto_refresh=False,
            config_changed=False,
        )

        assert result["should_generate"] is True


# PipelineStepComponent Tests


class TestPipelineStepComponent:
    """Tests for PipelineStepComponent — single pipeline step rendering."""

    @patch("src.web.components.common.pipeline_step.PipelineComponent")
    @patch("src.web.components.common.pipeline_step.st")
    def test_render_step_returns_expected_keys(
        self, mock_st: MagicMock, mock_pp: MagicMock
    ) -> None:
        """render_step returns all required keys."""
        import pandas as pd

        from src.web.components.common.pipeline_step import (
            PipelineStepComponent,
            PipelineStepResult,
        )

        mock_pp.render_shaper_controls.return_value = {
            "move_up": False,
            "move_down": False,
            "delete": False,
        }
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]

        df = pd.DataFrame({"a": [1, 2, 3]})
        output_df = pd.DataFrame({"a": [3, 2, 1]})
        configure_fn = MagicMock(return_value={"type": "sort"})
        apply_fn = MagicMock(return_value=output_df)

        result: PipelineStepResult = PipelineStepComponent.render_step(
            plot_id=1,
            idx=0,
            shaper_type="sort",
            shaper_id=100,
            step_input=df,
            current_config=cast(Any, {"type": "sort"}),
            is_first=True,
            is_last=False,
            configure_fn=configure_fn,
            apply_fn=apply_fn,
            display_name="Mean Calculator",
        )

        expected: list[str] = [
            "new_config",
            "move_up",
            "move_down",
            "delete",
            "preview_data",
            "preview_error",
            "step_output",
        ]
        for key in expected:
            assert key in result, f"Missing key: {key}"

    @patch("src.web.components.common.pipeline_step.PipelineComponent")
    @patch("src.web.components.common.pipeline_step.st")
    def test_render_step_calls_configure_fn(self, mock_st: MagicMock, mock_pp: MagicMock) -> None:
        """render_step invokes configure_fn with correct args."""
        import pandas as pd

        from src.web.components.common.pipeline_step import (
            PipelineStepComponent,
        )

        mock_pp.render_shaper_controls.return_value = {
            "move_up": False,
            "move_down": False,
            "delete": False,
        }
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]

        df = pd.DataFrame({"a": [1]})
        configure_fn = MagicMock(return_value={"type": "sort"})
        apply_fn = MagicMock(return_value=df)

        PipelineStepComponent.render_step(
            plot_id=5,
            idx=2,
            shaper_type="sort",
            shaper_id=42,
            step_input=df,
            current_config=cast(Any, {}),
            is_first=False,
            is_last=True,
            configure_fn=configure_fn,
            apply_fn=apply_fn,
            display_name="Mean Calculator",
        )

        configure_fn.assert_called_once_with("sort", df, 42, {}, 5)

    @patch("src.web.components.common.pipeline_step.PipelineComponent")
    @patch("src.web.components.common.pipeline_step.st")
    def test_render_step_handles_configure_error(
        self, mock_st: MagicMock, mock_pp: MagicMock
    ) -> None:
        """render_step gracefully handles configure_fn exception."""
        import pandas as pd

        from src.web.components.common.pipeline_step import (
            PipelineStepComponent,
        )

        mock_pp.render_shaper_controls.return_value = {
            "move_up": False,
            "move_down": False,
            "delete": False,
        }
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]

        df = pd.DataFrame({"a": [1]})
        configure_fn = MagicMock(side_effect=ValueError("bad config"))
        apply_fn = MagicMock(return_value=df)

        result = PipelineStepComponent.render_step(
            plot_id=1,
            idx=0,
            shaper_type="sort",
            shaper_id=1,
            step_input=df,
            current_config=cast(Any, {}),
            is_first=True,
            is_last=True,
            configure_fn=configure_fn,
            apply_fn=apply_fn,
            display_name="Mean Calculator",
        )

        mock_st.exception.assert_called_once()
        assert result["new_config"] == {}

    @patch("src.web.components.common.pipeline_step.st")
    def test_render_finalize_result(self, mock_st: MagicMock) -> None:
        """render_finalize_result calls st.toast + st.dataframe."""
        import pandas as pd

        from src.web.components.common.pipeline_step import (
            PipelineStepComponent,
        )

        df = pd.DataFrame({"a": range(20)})
        PipelineStepComponent.render_finalize_result(df)

        mock_st.toast.assert_called_once()
        mock_st.dataframe.assert_called_once()

    @patch("src.web.components.common.pipeline_step.st")
    def test_render_finalize_error(self, mock_st: MagicMock) -> None:
        """render_finalize_error calls st.exception."""
        from src.web.components.common.pipeline_step import (
            PipelineStepComponent,
        )

        PipelineStepComponent.render_finalize_error("something broke")

        mock_st.exception.assert_called_once()
        assert "something broke" in str(mock_st.exception.call_args[0][0])


@patch("src.web.components.common.chart_display.render_download_section")
@patch("src.web.components.common.chart_display.interactive_plotly_chart")
def test_modebar_uses_actual_multi_panel_native_dimensions_with_the_published_export_scale(
    mock_chart: MagicMock,
    mock_download: MagicMock,
    plot_session: ring5.Session,
) -> None:
    # [test->req~ring5.export.plotly-scale~1]
    import plotly.graph_objects as go

    from src.web.components.common.chart_display import ChartDisplayComponent
    from src.web.rendering.plot_renderer import build_render_artifact

    plot = plot_session.create_plot(
        "bar",
        data=ring5.Table(
            pd.DataFrame(
                {"x": ["a", "b", "c"], "y": [3.0, 5.0, 7.0], "facet": ["one", "two", "three"]}
            )
        ),
        config={"x": "x", "y": "y", "width": 600, "height": 300, "export_scale": 3},
    )
    facets = plot_session.create_small_multiples(
        plot, by="facet", columns=2, width=900, panel_height=320
    )
    artifact = build_render_artifact(plot, plot.config, "plotly", multiples=facets)
    plot.publish_render_artifact(artifact)
    assert isinstance(artifact.figure, go.Figure)
    assert [list(cast(go.Bar, trace).y) for trace in artifact.figure.data] == [[3.0], [5.0], [7.0]]
    assert (artifact.figure.layout.width, artifact.figure.layout.height) == (900, 640)
    assert (artifact.config["width"], artifact.config["height"]) == (600, 300)
    ChartDisplayComponent.render_plotly_chart(artifact, plot.plot_id, plot.name)
    options = mock_chart.call_args.kwargs["config"]["toImageButtonOptions"]
    assert (options["width"], options["height"], options["scale"]) == (900, 640, 3)
    assert mock_chart.call_args.args[0] is artifact.figure
    mock_download.assert_called_once_with(plot.plot_id, plot.name, artifact)
