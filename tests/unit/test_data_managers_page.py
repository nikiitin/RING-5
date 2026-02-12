"""Tests for data_managers.py page — 36% → 100% coverage."""

from unittest.mock import MagicMock, patch

import pandas as pd


class TestShowDataManagersPage:
    """Tests for show_data_managers_page."""

    @patch("src.web.pages.data_managers.st")
    def test_no_data_shows_warning(self, mock_st: MagicMock) -> None:
        from src.web.pages.data_managers import show_data_managers_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False

        show_data_managers_page(api)

        mock_st.warning.assert_called_once()

    @patch("src.web.pages.data_managers.st")
    def test_get_data_returns_none_shows_error(self, mock_st: MagicMock) -> None:
        from src.web.pages.data_managers import show_data_managers_page

        api = MagicMock()
        api.state_manager.has_data.return_value = True
        api.state_manager.get_data.return_value = None

        show_data_managers_page(api)

        mock_st.error.assert_called_once()

    @patch("src.web.pages.data_managers.HistoryComponents")
    @patch("src.web.pages.data_managers.DataManagerComponents")
    @patch("src.web.pages.data_managers.SeedsReducerManager")
    @patch("src.web.pages.data_managers.OutlierRemoverManager")
    @patch("src.web.pages.data_managers.PreprocessorManager")
    @patch("src.web.pages.data_managers.MixerManager")
    @patch("src.web.pages.data_managers.st")
    def test_with_data_renders_tabs(
        self,
        mock_st: MagicMock,
        mock_mixer_cls: MagicMock,
        mock_preproc_cls: MagicMock,
        mock_outlier_cls: MagicMock,
        mock_seeds_cls: MagicMock,
        mock_dm_components: MagicMock,
        mock_history: MagicMock,
    ) -> None:
        from src.web.pages.data_managers import show_data_managers_page

        api = MagicMock()
        api.state_manager.has_data.return_value = True
        data = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        api.state_manager.get_data.return_value = data

        # Set name properties on manager instances
        for cls in [mock_seeds_cls, mock_outlier_cls, mock_preproc_cls, mock_mixer_cls]:
            cls.return_value.name = "Manager"

        # Mock tabs as context managers
        tab = MagicMock()
        tab.__enter__ = MagicMock(return_value=tab)
        tab.__exit__ = MagicMock(return_value=False)
        mock_st.tabs.return_value = [tab] * 7

        show_data_managers_page(api)

        mock_st.tabs.assert_called_once()
