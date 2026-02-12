"""
Tests for PlotRenderer pure logic methods that don't require Streamlit.

Covers:
- _compute_figure_cache_key: deterministic, transient key filtering
- _compute_data_hash: fast DataFrame fingerprinting
- _get_mime_type: file extension to MIME type mapping
"""

import pandas as pd

from src.web.pages.ui.plotting.plot_renderer import PlotRenderer, _get_mime_type


class TestComputeFigureCacheKey:
    """Tests for _compute_figure_cache_key."""

    def test_deterministic_same_inputs(self) -> None:
        """Same inputs should always produce the same cache key."""
        config = {"x": "col_a", "y": "col_b", "title": "Test"}
        key1 = PlotRenderer._compute_figure_cache_key(1, config, "abc123")
        key2 = PlotRenderer._compute_figure_cache_key(1, config, "abc123")
        assert key1 == key2

    def test_different_plot_ids_different_keys(self) -> None:
        config = {"x": "col_a"}
        key1 = PlotRenderer._compute_figure_cache_key(1, config, "hash")
        key2 = PlotRenderer._compute_figure_cache_key(2, config, "hash")
        assert key1 != key2

    def test_different_configs_different_keys(self) -> None:
        key1 = PlotRenderer._compute_figure_cache_key(1, {"x": "a"}, "hash")
        key2 = PlotRenderer._compute_figure_cache_key(1, {"x": "b"}, "hash")
        assert key1 != key2

    def test_different_data_hashes_different_keys(self) -> None:
        config = {"x": "col"}
        key1 = PlotRenderer._compute_figure_cache_key(1, config, "hash1")
        key2 = PlotRenderer._compute_figure_cache_key(1, config, "hash2")
        assert key1 != key2

    def test_transient_keys_ignored(self) -> None:
        """legend_x, legend_y, etc. should not affect the cache key."""
        base_config = {"x": "col", "y": "val"}
        with_transient = {
            **base_config,
            "legend_x": 0.5,
            "legend_y": 0.95,
            "legend_xanchor": "left",
            "legend_yanchor": "top",
            "xaxis_range": [0, 10],
            "yaxis_range": [0, 100],
        }
        key1 = PlotRenderer._compute_figure_cache_key(1, base_config, "hash")
        key2 = PlotRenderer._compute_figure_cache_key(1, with_transient, "hash")
        assert key1 == key2

    def test_key_format_starts_with_plot_id(self) -> None:
        key = PlotRenderer._compute_figure_cache_key(42, {"x": "a"}, "abc")
        assert key.startswith("plot_42_")

    def test_handles_non_serializable_values(self) -> None:
        """Config with non-JSON-serializable values should still work (default=str)."""
        config = {"x": pd.Timestamp("2024-01-01")}
        key = PlotRenderer._compute_figure_cache_key(1, config, "hash")
        assert isinstance(key, str)


class TestComputeDataHash:
    """Tests for _compute_data_hash."""

    def test_deterministic(self) -> None:
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        hash1 = PlotRenderer._compute_data_hash(df)
        hash2 = PlotRenderer._compute_data_hash(df)
        assert hash1 == hash2

    def test_different_data_different_hash(self) -> None:
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        df2 = pd.DataFrame({"a": [4, 5, 6]})
        assert PlotRenderer._compute_data_hash(df1) != PlotRenderer._compute_data_hash(df2)

    def test_different_shape_different_hash(self) -> None:
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"a": [1, 2, 3]})
        assert PlotRenderer._compute_data_hash(df1) != PlotRenderer._compute_data_hash(df2)

    def test_different_columns_different_hash(self) -> None:
        df1 = pd.DataFrame({"a": [1, 2]})
        df2 = pd.DataFrame({"b": [1, 2]})
        assert PlotRenderer._compute_data_hash(df1) != PlotRenderer._compute_data_hash(df2)

    def test_empty_dataframe(self) -> None:
        """Empty DataFrame should still produce a valid hash."""
        df = pd.DataFrame()
        result = PlotRenderer._compute_data_hash(df)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_single_row(self) -> None:
        df = pd.DataFrame({"x": [42]})
        result = PlotRenderer._compute_data_hash(df)
        assert isinstance(result, str)

    def test_hash_length(self) -> None:
        """Hash should be truncated to 12 chars."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = PlotRenderer._compute_data_hash(df)
        assert len(result) == 12


class TestGetMimeType:
    """Tests for _get_mime_type module-level function."""

    def test_pdf(self) -> None:
        assert _get_mime_type("pdf") == "application/pdf"

    def test_pgf(self) -> None:
        assert _get_mime_type("pgf") == "application/x-tex"

    def test_eps(self) -> None:
        assert _get_mime_type("eps") == "application/postscript"

    def test_unknown_extension(self) -> None:
        assert _get_mime_type("xyz") == "application/octet-stream"

    def test_empty_string(self) -> None:
        assert _get_mime_type("") == "application/octet-stream"
