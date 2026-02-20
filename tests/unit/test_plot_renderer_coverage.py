"""Tests for PlotRenderer — cache helper branch coverage."""

from typing import Any, Dict

import pandas as pd

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
        config1: Dict[str, Any] = {"x": "col1", "xaxis_range": [0, 10], "yaxis_range": [0, 50]}
        config2: Dict[str, Any] = {"x": "col1", "xaxis_range": [5, 15], "yaxis_range": [10, 60]}
        key1 = PlotRenderer._compute_figure_cache_key(1, config1, "abc")
        key2 = PlotRenderer._compute_figure_cache_key(1, config2, "abc")
        assert key1 == key2  # transient keys should be filtered out
