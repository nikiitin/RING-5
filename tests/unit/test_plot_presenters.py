"""
Tests for Plot Presenters — verify pure UI rendering returns correct dicts.

Since presenters call Streamlit widgets, we mock st.* to verify:
    1. Correct widget types are rendered
    2. Return dicts have the expected keys and types
    3. No state mutations or API calls happen
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# ─── PlotCreationPresenter Tests ─────────────────────────────────────────────


class TestPlotCreationPresenter:
    """Tests for PlotCreationPresenter."""

    @patch("src.web.presenters.plot.creation_presenter.st")
    def test_render_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """Return dict has name, plot_type, create_clicked."""
        from src.web.presenters.plot.creation_presenter import PlotCreationPresenter

        # Setup mocks
        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "My Plot"
        mock_st.selectbox.return_value = "bar"
        mock_st.form_submit_button.return_value = False

        result: Dict[str, Any] = PlotCreationPresenter.render(
            default_name="Plot 1", available_types=["bar", "line"]
        )

        assert "name" in result
        assert "plot_type" in result
        assert "create_clicked" in result

    @patch("src.web.presenters.plot.creation_presenter.st")
    def test_render_returns_user_input(self, mock_st: MagicMock) -> None:
        """Returns the values from widgets."""
        from src.web.presenters.plot.creation_presenter import PlotCreationPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "Custom Name"
        mock_st.selectbox.return_value = "scatter"
        mock_st.form_submit_button.return_value = True

        result = PlotCreationPresenter.render("Default", ["bar", "scatter"])

        assert result["name"] == "Custom Name"
        assert result["plot_type"] == "scatter"
        assert result["create_clicked"] is True

    @patch("src.web.presenters.plot.creation_presenter.st")
    def test_render_does_not_access_session_state(self, mock_st: MagicMock) -> None:
        """Presenter does not read/write session_state."""
        from src.web.presenters.plot.creation_presenter import PlotCreationPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.text_input.return_value = "X"
        mock_st.selectbox.return_value = "bar"
        mock_st.form_submit_button.return_value = False

        PlotCreationPresenter.render("X", ["bar"])

        # session_state should never be accessed
        mock_st.session_state.__getitem__.assert_not_called()
        mock_st.session_state.__setitem__.assert_not_called()


# ─── PlotControlsPresenter Tests ────────────────────────────────────────────


class TestPlotControlsPresenter:
    """Tests for PlotControlsPresenter."""

    @patch("src.web.presenters.plot.controls_presenter.st")
    def test_render_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """Return dict has all action keys."""
        from src.web.presenters.plot.controls_presenter import PlotControlsPresenter

        mock_col = MagicMock()
        # Handle nested st.columns calls (outer 4-col + inner 2-col)
        mock_st.columns.side_effect = [
            [mock_col, mock_col, mock_col, mock_col],  # outer
            [mock_col, mock_col],  # inner c2_1, c2_2
        ]
        mock_st.text_input.return_value = "My Plot"
        mock_st.button.return_value = False

        result: Dict[str, Any] = PlotControlsPresenter.render(plot_id=1, current_name="My Plot")

        expected_keys: List[str] = [
            "new_name",
            "save_clicked",
            "load_clicked",
            "delete_clicked",
            "duplicate_clicked",
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    @patch("src.web.presenters.plot.controls_presenter.st")
    def test_render_detects_rename(self, mock_st: MagicMock) -> None:
        """Detects name change via text_input."""
        from src.web.presenters.plot.controls_presenter import PlotControlsPresenter

        mock_col = MagicMock()
        mock_st.columns.side_effect = [
            [mock_col, mock_col, mock_col, mock_col],
            [mock_col, mock_col],
        ]
        mock_st.text_input.return_value = "New Name"
        mock_st.button.return_value = False

        result = PlotControlsPresenter.render(plot_id=1, current_name="Old Name")

        assert result["new_name"] == "New Name"


# ─── PlotSelectorPresenter Tests ────────────────────────────────────────────


class TestPlotSelectorPresenter:
    """Tests for PlotSelectorPresenter."""

    @patch("src.web.presenters.plot.selector_presenter.st")
    def test_render_returns_selected_name(self, mock_st: MagicMock) -> None:
        """Returns the name selected by radio."""
        from src.web.presenters.plot.selector_presenter import PlotSelectorPresenter

        mock_st.radio.return_value = "Plot 2"

        result: str = PlotSelectorPresenter.render(["Plot 1", "Plot 2", "Plot 3"], default_index=1)

        assert result == "Plot 2"

    @patch("src.web.presenters.plot.selector_presenter.st")
    def test_radio_called_with_horizontal(self, mock_st: MagicMock) -> None:
        """Radio is rendered horizontally."""
        from src.web.presenters.plot.selector_presenter import PlotSelectorPresenter

        mock_st.radio.return_value = "Plot 1"

        PlotSelectorPresenter.render(["Plot 1"], default_index=0)

        mock_st.radio.assert_called_once()
        call_kwargs = mock_st.radio.call_args
        assert (
            call_kwargs.kwargs.get("horizontal") is True or call_kwargs[1].get("horizontal") is True
        )


# ─── PipelinePresenter Tests ────────────────────────────────────────────────


class TestPipelinePresenter:
    """Tests for PipelinePresenter."""

    @patch("src.web.presenters.plot.pipeline_presenter.st")
    def test_render_add_shaper_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """render_add_shaper returns add_clicked and shaper_type."""
        from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.selectbox.return_value = "Sort"
        mock_st.button.return_value = True

        result: Dict[str, Any] = PipelinePresenter.render_add_shaper(plot_id=1)

        assert result["add_clicked"] is True
        assert result["shaper_type"] == "sort"

    @patch("src.web.presenters.plot.pipeline_presenter.st")
    def test_render_finalize_button(self, mock_st: MagicMock) -> None:
        """render_finalize_button returns button state."""
        from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

        mock_st.button.return_value = True

        result: bool = PipelinePresenter.render_finalize_button(plot_id=1)
        assert result is True

    def test_shaper_display_map_consistency(self) -> None:
        """SHAPER_DISPLAY_MAP and REVERSE_MAP are consistent."""
        from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

        for display_name, internal_type in PipelinePresenter.SHAPER_DISPLAY_MAP.items():
            assert PipelinePresenter.REVERSE_MAP[internal_type] == display_name

    @patch("src.web.presenters.plot.pipeline_presenter.st")
    def test_render_shaper_controls_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """render_shaper_controls returns move/delete action flags."""
        from src.web.presenters.plot.pipeline_presenter import PipelinePresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col, mock_col]
        mock_st.button.return_value = False

        result: Dict[str, bool] = PipelinePresenter.render_shaper_controls(
            plot_id=1,
            idx=0,
            shaper_type="sort",
            is_first=True,
            is_last=False,
        )

        assert "move_up" in result
        assert "move_down" in result
        assert "delete" in result


# ─── ChartPresenter Tests ───────────────────────────────────────────────────


class TestChartPresenter:
    """Tests for ChartPresenter."""

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_render_refresh_controls_returns_expected_keys(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Returns auto_refresh, manual_refresh, should_generate."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = True
        mock_st.button.return_value = False

        result: Dict[str, Any] = ChartPresenter.render_refresh_controls(
            plot_id=1,
            auto_refresh=True,
            config_changed=True,
        )

        assert "auto_refresh" in result
        assert "manual_refresh" in result
        assert "should_generate" in result

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_should_generate_when_auto_and_changed(
        self,
        mock_st: MagicMock,
    ) -> None:
        """should_generate is True when auto=True and config changed."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = True
        mock_st.button.return_value = False

        result = ChartPresenter.render_refresh_controls(
            plot_id=1,
            auto_refresh=True,
            config_changed=True,
        )

        assert result["should_generate"] is True

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_should_not_generate_when_no_auto_and_no_manual(
        self,
        mock_st: MagicMock,
    ) -> None:
        """should_generate is False when auto=False and no manual click."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = False
        mock_st.button.return_value = False

        result = ChartPresenter.render_refresh_controls(
            plot_id=1,
            auto_refresh=False,
            config_changed=True,
        )

        assert result["should_generate"] is False

    @patch("src.web.presenters.plot.chart_presenter.st")
    def test_should_generate_on_manual_click(
        self,
        mock_st: MagicMock,
    ) -> None:
        """should_generate is True on manual Refresh click even if no auto."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.toggle.return_value = False
        mock_st.button.return_value = True  # Manual click

        result = ChartPresenter.render_refresh_controls(
            plot_id=1,
            auto_refresh=False,
            config_changed=False,
        )

        assert result["should_generate"] is True


# ─── ConfigPresenter Tests ──────────────────────────────────────────────────


class TestConfigPresenter:
    """Tests for ConfigPresenter — delegates to renderer methods."""

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_type_config_delegates(self, mock_st: MagicMock) -> None:
        """render_type_config calls renderer.render_config_ui."""
        import pandas as pd

        from src.web.presenters.plot.config_presenter import ConfigPresenter

        renderer = MagicMock()
        renderer.render_config_ui.return_value = {"x_col": "a"}
        df = pd.DataFrame({"a": [1]})

        result: Dict[str, Any] = ConfigPresenter.render_type_config(renderer, df, {"saved": True})

        renderer.render_config_ui.assert_called_once_with(df, {"saved": True})
        assert result == {"x_col": "a"}

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_section_headers(self, mock_st: MagicMock) -> None:
        """render_section_headers calls st.markdown."""
        from src.web.presenters.plot.config_presenter import ConfigPresenter

        ConfigPresenter.render_section_headers()

        assert mock_st.markdown.call_count == 3

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_no_data_warning(self, mock_st: MagicMock) -> None:
        """render_no_data_warning calls st.warning."""
        from src.web.presenters.plot.config_presenter import ConfigPresenter

        ConfigPresenter.render_no_data_warning()

        mock_st.warning.assert_called_once()

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_advanced(self, mock_st: MagicMock) -> None:
        """render_advanced delegates to renderer.render_advanced_options."""
        import pandas as pd

        from src.web.presenters.plot.config_presenter import ConfigPresenter

        renderer = MagicMock()
        renderer.render_advanced_options.return_value = {"show_grid": True}
        df = pd.DataFrame({"a": [1]})

        result: Dict[str, Any] = ConfigPresenter.render_advanced(renderer, {"x_col": "a"}, df)

        renderer.render_advanced_options.assert_called_once_with({"x_col": "a"}, df)
        assert result == {"show_grid": True}

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_theme(self, mock_st: MagicMock) -> None:
        """render_theme combines display + theme options."""
        from src.web.presenters.plot.config_presenter import ConfigPresenter

        renderer = MagicMock()
        renderer.render_display_options.return_value = {"width": 800}
        renderer.render_theme_options.return_value = {"color": "blue"}

        result: Dict[str, Any] = ConfigPresenter.render_theme(renderer, {"x": "a"})

        assert result["width"] == 800
        assert result["color"] == "blue"

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_advanced_and_theme(self, mock_st: MagicMock) -> None:
        """render_advanced_and_theme produces combined config."""
        import pandas as pd

        from src.web.presenters.plot.config_presenter import ConfigPresenter

        renderer = MagicMock()
        renderer.render_advanced_options.return_value = {"grid": True}
        renderer.render_display_options.return_value = {"w": 800}
        renderer.render_theme_options.return_value = {"c": "red"}

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]

        result: Dict[str, Any] = ConfigPresenter.render_advanced_and_theme(
            renderer, {"x": "a"}, pd.DataFrame({"a": [1]})
        )

        assert "grid" in result
        assert "w" in result
        assert "c" in result

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_plot_type_selector_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """render_plot_type_selector returns new_type and type_changed."""
        from src.web.presenters.plot.config_presenter import ConfigPresenter

        mock_st.selectbox.return_value = "scatter"

        result: Dict[str, Any] = ConfigPresenter.render_plot_type_selector(
            "bar", ["bar", "scatter", "line"], 1
        )

        assert result["new_type"] == "scatter"
        assert result["type_changed"] is True

    @patch("src.web.presenters.plot.config_presenter.st")
    def test_render_plot_type_selector_no_change(self, mock_st: MagicMock) -> None:
        """type_changed is False when same type selected."""
        from src.web.presenters.plot.config_presenter import ConfigPresenter

        mock_st.selectbox.return_value = "bar"

        result = ConfigPresenter.render_plot_type_selector("bar", ["bar"], 1)

        assert result["type_changed"] is False


# ─── PipelineStepPresenter Tests ────────────────────────────────────────────


class TestPipelineStepPresenter:
    """Tests for PipelineStepPresenter — single pipeline step rendering."""

    @patch("src.web.presenters.plot.pipeline_step_presenter.PipelinePresenter")
    @patch("src.web.presenters.plot.pipeline_step_presenter.st")
    def test_render_step_returns_expected_keys(
        self, mock_st: MagicMock, mock_pp: MagicMock
    ) -> None:
        """render_step returns all required keys."""
        import pandas as pd

        from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter

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

        result: Dict[str, Any] = PipelineStepPresenter.render_step(
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

        expected: List[str] = [
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

    @patch("src.web.presenters.plot.pipeline_step_presenter.PipelinePresenter")
    @patch("src.web.presenters.plot.pipeline_step_presenter.st")
    def test_render_step_calls_configure_fn(self, mock_st: MagicMock, mock_pp: MagicMock) -> None:
        """render_step invokes configure_fn with correct args."""
        import pandas as pd

        from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter

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

        PipelineStepPresenter.render_step(
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

    @patch("src.web.presenters.plot.pipeline_step_presenter.PipelinePresenter")
    @patch("src.web.presenters.plot.pipeline_step_presenter.st")
    def test_render_step_handles_configure_error(
        self, mock_st: MagicMock, mock_pp: MagicMock
    ) -> None:
        """render_step gracefully handles configure_fn exception."""
        import pandas as pd

        from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter

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

        result = PipelineStepPresenter.render_step(
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

        mock_st.error.assert_called_once()
        assert result["new_config"] == {}

    @patch("src.web.presenters.plot.pipeline_step_presenter.st")
    def test_render_finalize_result(self, mock_st: MagicMock) -> None:
        """render_finalize_result calls st.success + st.dataframe."""
        import pandas as pd

        from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter

        df = pd.DataFrame({"a": range(20)})
        PipelineStepPresenter.render_finalize_result(df)

        mock_st.success.assert_called_once()
        mock_st.dataframe.assert_called_once()

    @patch("src.web.presenters.plot.pipeline_step_presenter.st")
    def test_render_finalize_error(self, mock_st: MagicMock) -> None:
        """render_finalize_error calls st.error."""
        from src.web.presenters.plot.pipeline_step_presenter import PipelineStepPresenter

        PipelineStepPresenter.render_finalize_error("something broke")

        mock_st.error.assert_called_once()
        assert "something broke" in mock_st.error.call_args[0][0]


# ─── SaveDialogPresenter Tests ──────────────────────────────────────────────


class TestSaveDialogPresenter:
    """Tests for SaveDialogPresenter — save pipeline dialog."""

    @patch("src.web.presenters.plot.save_dialog_presenter.st")
    def test_render_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """render returns pipeline_name, save_clicked, cancel_clicked."""
        from src.web.presenters.plot.save_dialog_presenter import SaveDialogPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.text_input.return_value = "my_pipeline"
        mock_st.form_submit_button.return_value = False
        mock_st.button.return_value = False

        result: Dict[str, Any] = SaveDialogPresenter.render(plot_id=1, plot_name="Plot 1")

        assert "pipeline_name" in result
        assert "save_clicked" in result
        assert "cancel_clicked" in result

    @patch("src.web.presenters.plot.save_dialog_presenter.st")
    def test_render_default_name_uses_plot_name(self, mock_st: MagicMock) -> None:
        """Default pipeline name is derived from plot_name."""
        from src.web.presenters.plot.save_dialog_presenter import SaveDialogPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.text_input.return_value = "MyPlot_pipeline"
        mock_st.form_submit_button.return_value = True
        mock_st.button.return_value = False

        result = SaveDialogPresenter.render(plot_id=1, plot_name="MyPlot")

        assert result["pipeline_name"] == "MyPlot_pipeline"
        assert result["save_clicked"] is True

    @patch("src.web.presenters.plot.save_dialog_presenter.st")
    def test_render_cancel(self, mock_st: MagicMock) -> None:
        """Cancel button sets cancel_clicked."""
        from src.web.presenters.plot.save_dialog_presenter import SaveDialogPresenter

        mock_col = MagicMock()
        mock_st.columns.return_value = [mock_col, mock_col]
        mock_st.text_input.return_value = "x"
        mock_st.form_submit_button.return_value = False
        mock_st.button.return_value = True

        result = SaveDialogPresenter.render(plot_id=2, plot_name="P")

        assert result["cancel_clicked"] is True


# ─── LoadDialogPresenter Tests ──────────────────────────────────────────────


class TestLoadDialogPresenter:
    """Tests for LoadDialogPresenter — load pipeline dialog."""

    @patch("src.web.presenters.plot.load_dialog_presenter.st")
    def test_render_empty_returns_close_clicked(self, mock_st: MagicMock) -> None:
        """render_empty returns close_clicked key."""
        from src.web.presenters.plot.load_dialog_presenter import LoadDialogPresenter

        mock_st.button.return_value = False

        result: Dict[str, Any] = LoadDialogPresenter.render_empty(plot_id=1)

        assert "close_clicked" in result
        mock_st.warning.assert_called_once()

    @patch("src.web.presenters.plot.load_dialog_presenter.st")
    def test_render_empty_close_clicked(self, mock_st: MagicMock) -> None:
        """Close button sets close_clicked True."""
        from src.web.presenters.plot.load_dialog_presenter import LoadDialogPresenter

        mock_st.button.return_value = True

        result = LoadDialogPresenter.render_empty(plot_id=1)

        assert result["close_clicked"] is True

    @patch("src.web.presenters.plot.load_dialog_presenter.st")
    def test_render_returns_expected_keys(self, mock_st: MagicMock) -> None:
        """render returns selected_pipeline, load_clicked, cancel_clicked."""
        from src.web.presenters.plot.load_dialog_presenter import LoadDialogPresenter

        mock_st.selectbox.return_value = "pipe_1"
        mock_st.button.side_effect = [False, False]

        result: Dict[str, Any] = LoadDialogPresenter.render(
            plot_id=1, available_pipelines=["pipe_1", "pipe_2"]
        )

        assert "selected_pipeline" in result
        assert "load_clicked" in result
        assert "cancel_clicked" in result

    @patch("src.web.presenters.plot.load_dialog_presenter.st")
    def test_render_selects_pipeline(self, mock_st: MagicMock) -> None:
        """Selected pipeline is returned."""
        from src.web.presenters.plot.load_dialog_presenter import LoadDialogPresenter

        mock_st.selectbox.return_value = "pipe_2"
        mock_st.button.side_effect = [True, False]

        result = LoadDialogPresenter.render(plot_id=1, available_pipelines=["pipe_1", "pipe_2"])

        assert result["selected_pipeline"] == "pipe_2"
        assert result["load_clicked"] is True
