"""
Tests for Plot Components — verify pure UI rendering returns correct dicts.

Since components call Streamlit widgets, we mock st.* to verify:
    1. Correct widget types are rendered
    2. Return dicts have the expected keys and types
    3. No state mutations or API calls happen
"""

from typing import Any
from unittest.mock import MagicMock, patch

# ─── PlotCreationComponent Tests ─────────────────────────────────────────────


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


# ─── PlotControlsComponent Tests ────────────────────────────────────────────


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


# ─── PlotSelectorComponent Tests ────────────────────────────────────────────


class TestPlotSelectorComponent:
    """Tests for PlotSelectorComponent."""

    @patch("src.web.components.common.plot_selector.st")
    def test_render_returns_selected_name(self, mock_st: MagicMock) -> None:
        """Returns the name selected by radio."""
        from src.web.components.common.plot_selector import PlotSelectorComponent

        mock_st.pills.return_value = "Plot 2"

        result: str = PlotSelectorComponent.render(["Plot 1", "Plot 2", "Plot 3"], default_index=1)

        assert result == "Plot 2"

    @patch("src.web.components.common.plot_selector.st")
    def test_pills_called_correctly(self, mock_st: MagicMock) -> None:
        """Pills widget is rendered for plot selection."""
        from src.web.components.common.plot_selector import PlotSelectorComponent

        mock_st.pills.return_value = "Plot 1"

        PlotSelectorComponent.render(["Plot 1"], default_index=0)

        mock_st.pills.assert_called_once()
        call_kwargs = mock_st.pills.call_args
        assert (
            call_kwargs.kwargs.get("key") == "plot_selector"
            or call_kwargs[1].get("key") == "plot_selector"
        )


# ─── PipelineComponent Tests ────────────────────────────────────────────────


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

        result: dict[str, Any] = PipelineComponent.render_add_shaper(plot_id=1)

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
        """SHAPER_DISPLAY_MAP and REVERSE_MAP are consistent."""
        from src.web.components.common.pipeline import PipelineComponent

        for display_name, internal_type in PipelineComponent.SHAPER_DISPLAY_MAP.items():
            assert PipelineComponent.REVERSE_MAP[internal_type] == display_name

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
            shaper_type="sort",
            is_first=True,
            is_last=False,
        )

        assert "move_up" in result
        assert "move_down" in result
        assert "delete" in result


# ─── ChartDisplayComponent Tests ───────────────────────────────────────────────────


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


# ─── PipelineStepComponent Tests ────────────────────────────────────────────


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

        mock_pp.REVERSE_MAP = {"sort": "Sort"}
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
            current_config={"type": "sort"},
            is_first=True,
            is_last=False,
            configure_fn=configure_fn,
            apply_fn=apply_fn,
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

        mock_pp.REVERSE_MAP = {"sort": "Sort"}
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
            current_config={},
            is_first=False,
            is_last=True,
            configure_fn=configure_fn,
            apply_fn=apply_fn,
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

        mock_pp.REVERSE_MAP = {"sort": "Sort"}
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
            current_config={},
            is_first=True,
            is_last=True,
            configure_fn=configure_fn,
            apply_fn=apply_fn,
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
