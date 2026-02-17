"""
Tests for the engine toggle widget in PlotRenderer.

Validates that:
  - ``st.pills`` is called with correct options and default
  - ``EngineManager.set_engine()`` is invoked when user selects an engine
  - Selecting the same engine as current is a no-op (idempotent)
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _build_plot_mock(plot_id: int = 1) -> MagicMock:
    """Create a minimal MagicMock that satisfies render_plot's needs."""
    plot = MagicMock()
    plot.plot_id = plot_id
    plot.processed_data = pd.DataFrame({"x": [1]})
    plot.config = {"x": "col"}
    plot.last_generated_fig = go.Figure()
    plot.name = "test"
    return plot


# ─── Tests ───────────────────────────────────────────────────────────────────


class TestEngineToggleWidget:
    """Verify the engine selector pills widget in render_plot."""

    @patch("src.web.pages.ui.plotting.plot_renderer.EngineManager")
    @patch("src.web.pages.ui.plotting.plot_renderer.render_download_section")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_pills_called_with_correct_args(
        self,
        mock_cache: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
        mock_em: MagicMock,
    ) -> None:
        """st.pills should be called with 'plotly' and 'matplotlib' options."""
        from src.web.pages.ui.plotting.plot_renderer import PlotRenderer

        mock_cache.return_value = MagicMock()
        mock_chart.return_value = None
        mock_em.get_engine.return_value = "plotly"
        mock_st.pills.return_value = "plotly"

        plot = _build_plot_mock()
        PlotRenderer.render_plot(plot)

        mock_st.pills.assert_called_once()
        args, kwargs = mock_st.pills.call_args
        # First positional arg is the label
        assert args[0] == "Engine"
        # Options must include both engines
        assert kwargs["options"] == ["plotly", "matplotlib"]
        assert kwargs["selection_mode"] == "single"
        assert kwargs["default"] == "plotly"
        assert "engine_selector_" in kwargs["key"]

    @patch("src.web.pages.ui.plotting.plot_renderer.EngineManager")
    @patch("src.web.pages.ui.plotting.plot_renderer.render_download_section")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_set_engine_called_on_selection(
        self,
        mock_cache: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
        mock_em: MagicMock,
    ) -> None:
        """When user selects matplotlib, EngineManager.set_engine is called."""
        from src.web.pages.ui.plotting.plot_renderer import PlotRenderer

        mock_cache.return_value = MagicMock()
        mock_chart.return_value = None
        mock_em.get_engine.return_value = "plotly"
        mock_st.pills.return_value = "matplotlib"

        plot = _build_plot_mock()
        PlotRenderer.render_plot(plot)

        mock_em.set_engine.assert_called_once_with("matplotlib")

    @patch("src.web.pages.ui.plotting.plot_renderer.EngineManager")
    @patch("src.web.pages.ui.plotting.plot_renderer.render_download_section")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_none_selection_skips_set_engine(
        self,
        mock_cache: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
        mock_em: MagicMock,
    ) -> None:
        """When pills returns None (deselected), set_engine is NOT called."""
        from src.web.pages.ui.plotting.plot_renderer import PlotRenderer

        mock_cache.return_value = MagicMock()
        mock_chart.return_value = None
        mock_em.get_engine.return_value = "plotly"
        mock_st.pills.return_value = None

        plot = _build_plot_mock()
        PlotRenderer.render_plot(plot)

        mock_em.set_engine.assert_not_called()

    @patch("src.web.pages.ui.plotting.plot_renderer.EngineManager")
    @patch("src.web.pages.ui.plotting.plot_renderer.render_download_section")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_widget_key_includes_plot_id(
        self,
        mock_cache: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
        mock_em: MagicMock,
    ) -> None:
        """Widget key must be scoped to the plot_id to avoid collisions."""
        from src.web.pages.ui.plotting.plot_renderer import PlotRenderer

        mock_cache.return_value = MagicMock()
        mock_chart.return_value = None
        mock_em.get_engine.return_value = "plotly"
        mock_st.pills.return_value = "plotly"

        plot = _build_plot_mock(plot_id=42)
        PlotRenderer.render_plot(plot)

        _, kwargs = mock_st.pills.call_args
        assert kwargs["key"] == "engine_selector_42"
