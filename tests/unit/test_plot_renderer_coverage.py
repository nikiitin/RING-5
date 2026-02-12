"""Tests for PlotRenderer — branch coverage for render_plot, cache, and relayout."""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pandas as pd
import plotly.graph_objects as go

from src.web.pages.ui.plotting.plot_renderer import PlotRenderer


class TestPlotRendererCacheHelpers:
    """Cover cache helper and data hash methods."""

    def test_compute_data_hash_nonempty(self) -> None:
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        h = PlotRenderer._compute_data_hash(df)
        assert isinstance(h, str)
        assert len(h) == 12

    def test_compute_data_hash_empty(self) -> None:
        df = pd.DataFrame()
        h = PlotRenderer._compute_data_hash(df)
        assert isinstance(h, str)

    def test_compute_data_hash_deterministic(self) -> None:
        df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
        h1 = PlotRenderer._compute_data_hash(df)
        h2 = PlotRenderer._compute_data_hash(df)
        assert h1 == h2

    def test_compute_figure_cache_key(self) -> None:
        config: Dict[str, Any] = {"x": "col1", "y": "col2", "title": "test"}
        key = PlotRenderer._compute_figure_cache_key(1, config, "abc123")
        assert key.startswith("plot_1_")
        assert "abc123" in key

    def test_cache_key_ignores_transient_config(self) -> None:
        config1: Dict[str, Any] = {"x": "col1", "legend_x": 0.5, "legend_y": 0.9}
        config2: Dict[str, Any] = {"x": "col1", "legend_x": 0.1, "legend_y": 0.2}
        key1 = PlotRenderer._compute_figure_cache_key(1, config1, "abc")
        key2 = PlotRenderer._compute_figure_cache_key(1, config2, "abc")
        assert key1 == key2  # transient keys should be filtered out


class TestPlotRendererRenderPlot:
    """Cover PlotRenderer.render_plot branches."""

    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_no_processed_data_returns(
        self, mock_cache: MagicMock, mock_st: MagicMock, mock_chart: MagicMock
    ) -> None:
        plot = MagicMock()
        plot.processed_data = None

        PlotRenderer.render_plot(plot)
        mock_cache.assert_not_called()

    @patch("src.web.pages.ui.plotting.plot_renderer.PlotRenderer._render_download_button")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_cache_hit(
        self,
        mock_cache_fn: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        cache = MagicMock()
        cached_fig = go.Figure()
        cache.get.return_value = cached_fig
        mock_cache_fn.return_value = cache

        plot = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {"x": "col"}
        plot.plot_id = 1
        plot.last_generated_fig = None
        plot.name = "test"
        mock_chart.return_value = None  # no relayout

        PlotRenderer.render_plot(plot)
        # Should have used cached figure
        assert plot.last_generated_fig == cached_fig

    @patch("src.web.pages.ui.plotting.plot_renderer.PlotRenderer._render_download_button")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_force_generate(
        self,
        mock_cache_fn: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        plot = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {"x": "col"}
        plot.plot_id = 1
        plot.last_generated_fig = None
        plot.name = "test"
        plot.create_figure.return_value = go.Figure()
        plot.apply_common_layout.return_value = go.Figure()
        mock_chart.return_value = None

        PlotRenderer.render_plot(plot, should_generate=True)
        plot.create_figure.assert_called_once()
        cache.set.assert_called_once()

    @patch("src.web.pages.ui.plotting.plot_renderer.PlotRenderer._render_download_button")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_generate_with_legend_labels(
        self,
        mock_cache_fn: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        plot = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {"x": "col", "legend_labels": {"trace1": "Label1"}}
        plot.plot_id = 1
        plot.last_generated_fig = None
        plot.name = "test"
        fig = go.Figure()
        plot.create_figure.return_value = fig
        plot.apply_common_layout.return_value = fig
        plot.apply_legend_labels.return_value = fig
        mock_chart.return_value = None

        PlotRenderer.render_plot(plot, should_generate=True)
        plot.apply_legend_labels.assert_called_once()

    @patch("src.web.pages.ui.plotting.plot_renderer.PlotRenderer._render_download_button")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_generate_error_shows_st_error(
        self,
        mock_cache_fn: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        plot = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {"x": "col"}
        plot.plot_id = 1
        plot.last_generated_fig = None
        plot.create_figure.side_effect = ValueError("bad config")

        PlotRenderer.render_plot(plot, should_generate=True)
        mock_st.error.assert_called()

    @patch("src.web.pages.ui.plotting.plot_renderer.PlotRenderer._render_download_button")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_relayout_updates_config(
        self,
        mock_cache_fn: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache_fn.return_value = cache

        plot = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {
            "x": "col",
            "legend_x": 0.5,
            "legend_y": 0.9,
            "legend_xanchor": "left",
            "legend_yanchor": "top",
        }
        plot.plot_id = 1
        plot.last_generated_fig = go.Figure()
        plot.name = "test"
        plot.update_from_relayout.return_value = True

        relayout_data = {"legend.x": 0.3, "legend.y": 0.8}
        mock_chart.return_value = relayout_data
        mock_st.session_state = {}

        PlotRenderer.render_plot(plot)
        plot.update_from_relayout.assert_called_with(relayout_data)
        assert "plot.pending_updates" in mock_st.session_state
        mock_st.rerun.assert_called()

    @patch("src.web.pages.ui.plotting.plot_renderer.PlotRenderer._render_download_button")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_relayout_same_event_skipped(
        self,
        mock_cache_fn: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        cache = MagicMock()
        mock_cache_fn.return_value = cache

        plot = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {"x": "col"}
        plot.plot_id = 1
        plot.last_generated_fig = go.Figure()
        plot.name = "test"

        relayout_data = {"legend.x": 0.3}
        mock_chart.return_value = relayout_data
        # Same event already processed
        mock_st.session_state = {"last_relayout_1": relayout_data}

        PlotRenderer.render_plot(plot)
        plot.update_from_relayout.assert_not_called()

    @patch("src.web.pages.ui.plotting.plot_renderer.PlotRenderer._render_download_button")
    @patch("src.web.pages.ui.plotting.plot_renderer.interactive_plotly_chart")
    @patch("src.web.pages.ui.plotting.plot_renderer.st")
    @patch("src.web.pages.ui.plotting.plot_renderer.get_plot_cache")
    def test_render_exception(
        self,
        mock_cache_fn: MagicMock,
        mock_st: MagicMock,
        mock_chart: MagicMock,
        mock_download: MagicMock,
    ) -> None:
        cache = MagicMock()
        mock_cache_fn.return_value = cache

        plot = MagicMock()
        plot.processed_data = pd.DataFrame({"x": [1]})
        plot.config = {"x": "col"}
        plot.plot_id = 1
        plot.last_generated_fig = go.Figure()
        plot.name = "test"
        mock_chart.side_effect = RuntimeError("render fail")

        PlotRenderer.render_plot(plot)
        mock_st.error.assert_called()
