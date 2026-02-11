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
