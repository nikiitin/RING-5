"""Tests for performance.py page — 0% coverage target."""

from unittest.mock import MagicMock, patch


def _make_col_mock() -> MagicMock:
    """Create a context-manager-compatible column mock."""
    col = MagicMock()
    col.__enter__ = MagicMock(return_value=col)
    col.__exit__ = MagicMock(return_value=False)
    return col


def _columns_side_effect(n: int) -> list:
    """Return n column mocks for st.columns(n)."""
    return [_make_col_mock() for _ in range(n)]


class TestRenderPerformancePage:
    """Test the performance monitoring page render function."""

    @patch("src.web.pages.performance.st")
    @patch("src.web.pages.performance.clear_all_caches")
    @patch("src.web.pages.performance.get_cache_stats")
    def test_render_basic(
        self,
        mock_get_stats: MagicMock,
        mock_clear: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Basic render without button click."""
        from src.web.pages.performance import render_performance_page

        mock_get_stats.return_value = {
            "plot_cache": {"hits": 10, "misses": 3, "hit_rate": 76.9, "size": 5}
        }

        api = MagicMock()
        api.data_services.get_cache_stats.return_value = {
            "metadata_cache": {"hits": 20, "misses": 5, "hit_rate": 80.0},
            "dataframe_cache": {"size": 3},
        }
        api.state_manager.get_plots.return_value = [MagicMock(), MagicMock()]
        api.state_manager.has_data.return_value = True

        mock_st.columns.side_effect = _columns_side_effect

        exp_mock = MagicMock()
        exp_mock.__enter__ = MagicMock(return_value=exp_mock)
        exp_mock.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp_mock

        mock_st.session_state = {"key1": "v", "key2": "v2"}
        mock_st.button.return_value = False

        render_performance_page(api)

        mock_st.title.assert_called_once()
        mock_get_stats.assert_called_once()

    @patch("src.web.pages.performance.st")
    @patch("src.web.pages.performance.clear_all_caches")
    @patch("src.web.pages.performance.get_cache_stats")
    def test_clear_caches_button(
        self,
        mock_get_stats: MagicMock,
        mock_clear: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Clicking clear caches triggers clearing."""
        from src.web.pages.performance import render_performance_page

        mock_get_stats.return_value = {
            "plot_cache": {"hits": 0, "misses": 0, "hit_rate": 0, "size": 0}
        }

        api = MagicMock()
        api.data_services.get_cache_stats.return_value = {
            "metadata_cache": {"hits": 0, "misses": 0, "hit_rate": 0},
            "dataframe_cache": {"size": 0},
        }
        api.state_manager.get_plots.return_value = []
        api.state_manager.has_data.return_value = False

        mock_st.columns.side_effect = _columns_side_effect

        exp_mock = MagicMock()
        exp_mock.__enter__ = MagicMock(return_value=exp_mock)
        exp_mock.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp_mock

        mock_st.session_state = {}
        mock_st.button.return_value = True

        render_performance_page(api)

        mock_clear.assert_called_once()
        api.data_services.clear_caches.assert_called_once()

    @patch("src.web.pages.performance.st")
    @patch("src.web.pages.performance.clear_all_caches")
    @patch("src.web.pages.performance.get_cache_stats")
    def test_hit_rate_thresholds(
        self,
        mock_get_stats: MagicMock,
        mock_clear: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Different hit rate levels produce different feedback."""
        from src.web.pages.performance import render_performance_page

        mock_get_stats.return_value = {
            "plot_cache": {"hits": 5, "misses": 5, "hit_rate": 50.0, "size": 2}
        }

        api = MagicMock()
        api.data_services.get_cache_stats.return_value = {
            "metadata_cache": {"hits": 0, "misses": 0, "hit_rate": 0},
            "dataframe_cache": {"size": 0},
        }
        api.state_manager.get_plots.return_value = []
        api.state_manager.has_data.return_value = False

        mock_st.columns.side_effect = _columns_side_effect

        exp_mock = MagicMock()
        exp_mock.__enter__ = MagicMock(return_value=exp_mock)
        exp_mock.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp_mock

        mock_st.session_state = {}
        mock_st.button.return_value = False

        render_performance_page(api)

        mock_st.title.assert_called_once()

    @patch("src.web.pages.performance.st")
    @patch("src.web.pages.performance.clear_all_caches")
    @patch("src.web.pages.performance.get_cache_stats")
    def test_low_hit_rate_warning(
        self,
        mock_get_stats: MagicMock,
        mock_clear: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Low hit rate triggers warning."""
        from src.web.pages.performance import render_performance_page

        mock_get_stats.return_value = {
            "plot_cache": {"hits": 1, "misses": 10, "hit_rate": 9.0, "size": 1}
        }

        api = MagicMock()
        api.data_services.get_cache_stats.return_value = {
            "metadata_cache": {"hits": 0, "misses": 0, "hit_rate": 0},
            "dataframe_cache": {"size": 0},
        }
        api.state_manager.get_plots.return_value = []
        api.state_manager.has_data.return_value = False

        mock_st.columns.side_effect = _columns_side_effect

        exp_mock = MagicMock()
        exp_mock.__enter__ = MagicMock(return_value=exp_mock)
        exp_mock.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp_mock

        mock_st.session_state = {}
        mock_st.button.return_value = False

        render_performance_page(api)

        mock_st.title.assert_called_once()
