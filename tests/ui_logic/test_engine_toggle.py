"""Tests for engine selector rendering in ChartPresenter.

Verifies that ``ChartPresenter.render_engine_selector()`` correctly
renders the ``st.pills`` widget for engine selection and returns
the user's choice.
"""

from typing import Optional
from unittest.mock import MagicMock, patch

_PRESENTER = "src.web.presenters.plot.chart_presenter"


class TestEngineSelector:
    """ChartPresenter.render_engine_selector rendering and return value."""

    @patch(f"{_PRESENTER}.st")
    def test_pills_called_with_correct_args(self, mock_st: MagicMock) -> None:
        """st.pills receives engine options and current default."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_st.pills.return_value = "plotly"
        ChartPresenter.render_engine_selector(plot_id=5, current_engine="plotly")

        mock_st.pills.assert_called_once()
        call_kwargs = mock_st.pills.call_args
        assert call_kwargs[0][0] == "Engine"
        assert call_kwargs[1]["options"] == ["plotly", "matplotlib"]
        assert call_kwargs[1]["default"] == "plotly"
        assert "engine_selector_5" in call_kwargs[1]["key"]

    @patch(f"{_PRESENTER}.st")
    def test_returns_selected_engine(self, mock_st: MagicMock) -> None:
        """Returns the engine string selected by the user."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_st.pills.return_value = "matplotlib"
        result: Optional[str] = ChartPresenter.render_engine_selector(
            plot_id=1, current_engine="plotly"
        )
        assert result == "matplotlib"

    @patch(f"{_PRESENTER}.st")
    def test_returns_none_when_deselected(self, mock_st: MagicMock) -> None:
        """Returns None when user deselects all options."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_st.pills.return_value = None
        result: Optional[str] = ChartPresenter.render_engine_selector(
            plot_id=1, current_engine="plotly"
        )
        assert result is None

    @patch(f"{_PRESENTER}.st")
    def test_widget_key_includes_plot_id(self, mock_st: MagicMock) -> None:
        """Widget key is unique per plot_id."""
        from src.web.presenters.plot.chart_presenter import ChartPresenter

        mock_st.pills.return_value = "plotly"
        ChartPresenter.render_engine_selector(plot_id=42, current_engine="plotly")

        key = mock_st.pills.call_args[1]["key"]
        assert "42" in key
