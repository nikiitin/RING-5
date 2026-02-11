"""Tests for PlotRenderer pure-compute methods — 78% → 90%+."""

import pandas as pd

from src.web.pages.ui.plotting.plot_renderer import PlotRenderer


class TestComputeDataHash:
    """Tests for PlotRenderer._compute_data_hash."""

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        h = PlotRenderer._compute_data_hash(df)
        assert isinstance(h, str)
        assert len(h) == 12

    def test_non_empty_dataframe(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        h = PlotRenderer._compute_data_hash(df)
        assert isinstance(h, str)
        assert len(h) == 12

    def test_different_data_different_hash(self) -> None:
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"a": [3, 4]})
        h1 = PlotRenderer._compute_data_hash(df1)
        h2 = PlotRenderer._compute_data_hash(df2)
        assert h1 != h2

    def test_same_data_same_hash(self) -> None:
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        h1 = PlotRenderer._compute_data_hash(df)
        h2 = PlotRenderer._compute_data_hash(df)
        assert h1 == h2


class TestComputeFigureCacheKey:
    """Tests for PlotRenderer._compute_figure_cache_key."""

    def test_basic_key(self) -> None:
        config = {"x": "col_a", "y": "col_b", "title": "Test"}
        key = PlotRenderer._compute_figure_cache_key(1, config, "abc123")
        assert key.startswith("plot_1_")
        assert "abc123" in key

    def test_ignores_legend_position(self) -> None:
        config_a = {"x": "a", "y": "b", "legend_x": 0.1, "legend_y": 0.9}
        config_b = {"x": "a", "y": "b", "legend_x": 0.5, "legend_y": 0.5}
        key_a = PlotRenderer._compute_figure_cache_key(1, config_a, "hash1")
        key_b = PlotRenderer._compute_figure_cache_key(1, config_b, "hash1")
        assert key_a == key_b

    def test_different_config_different_key(self) -> None:
        config_a = {"x": "a", "y": "b"}
        config_b = {"x": "a", "y": "c"}
        key_a = PlotRenderer._compute_figure_cache_key(1, config_a, "hash1")
        key_b = PlotRenderer._compute_figure_cache_key(1, config_b, "hash1")
        assert key_a != key_b

    def test_different_plot_id_different_key(self) -> None:
        config = {"x": "a", "y": "b"}
        key_a = PlotRenderer._compute_figure_cache_key(1, config, "hash1")
        key_b = PlotRenderer._compute_figure_cache_key(2, config, "hash1")
        assert key_a != key_b

    def test_ignores_axis_range(self) -> None:
        config_a = {"x": "a", "xaxis_range": [0, 10], "yaxis_range": [0, 5]}
        config_b = {"x": "a"}
        key_a = PlotRenderer._compute_figure_cache_key(1, config_a, "h")
        key_b = PlotRenderer._compute_figure_cache_key(1, config_b, "h")
        assert key_a == key_b
