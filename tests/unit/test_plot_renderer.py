"""Tests for PlotRenderer cache utility methods.

After B6, PlotRenderer only retains cache-key computation utilities.
Rendering, engine selection, and display are handled by ChartDisplayComponent
and PlotRenderController.
"""

import pandas as pd

from src.web.pages.ui.plotting.plot_renderer import PlotRenderer


class TestPlotRendererCacheKey:
    """PlotRenderer._compute_figure_cache_key determinism."""

    def test_same_input_produces_same_key(self) -> None:
        config = {"x_col": "a", "y_col": "b"}
        key1 = PlotRenderer._compute_figure_cache_key(1, config, "abc123")
        key2 = PlotRenderer._compute_figure_cache_key(1, config, "abc123")
        assert key1 == key2

    def test_different_config_produces_different_key(self) -> None:
        config_a = {"x_col": "a"}
        config_b = {"x_col": "b"}
        key_a = PlotRenderer._compute_figure_cache_key(1, config_a, "abc")
        key_b = PlotRenderer._compute_figure_cache_key(1, config_b, "abc")
        assert key_a != key_b

    def test_zoom_range_ignored(self) -> None:
        """xaxis_range and yaxis_range should NOT affect cache key."""
        config_base = {"x_col": "a"}
        config_zoom = {"x_col": "a", "xaxis_range": [0, 10], "yaxis_range": [0, 5]}
        key_base = PlotRenderer._compute_figure_cache_key(1, config_base, "abc")
        key_zoom = PlotRenderer._compute_figure_cache_key(1, config_zoom, "abc")
        assert key_base == key_zoom


class TestPlotRendererDataHash:
    """PlotRenderer._compute_data_hash correctness."""

    def test_same_data_same_hash(self) -> None:
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        h1 = PlotRenderer._compute_data_hash(df)
        h2 = PlotRenderer._compute_data_hash(df)
        assert h1 == h2

    def test_different_data_different_hash(self) -> None:
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"a": [1, 3]})
        assert PlotRenderer._compute_data_hash(df1) != PlotRenderer._compute_data_hash(df2)

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        h = PlotRenderer._compute_data_hash(df)
        assert isinstance(h, str)
        assert len(h) == 12
