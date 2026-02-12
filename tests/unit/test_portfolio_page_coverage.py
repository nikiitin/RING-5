"""Tests for portfolio page — 57% → 90%+ coverage."""

from unittest.mock import MagicMock, patch

import pandas as pd


def _make_col_mock() -> MagicMock:
    col = MagicMock()
    col.__enter__ = MagicMock(return_value=col)
    col.__exit__ = MagicMock(return_value=False)
    return col


def _columns_side_effect(n: int) -> list:
    return [_make_col_mock() for _ in range(n)]


class TestShowPortfolioPage:
    """Tests for show_portfolio_page."""

    @patch("src.web.pages.portfolio.st")
    def test_save_no_data(self, mock_st: MagicMock) -> None:
        """Save button with no data shows error."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = []
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        mock_st.error.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_save_success(self, mock_st: MagicMock) -> None:
        """Save portfolio with data succeeds."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = True
        api.state_manager.get_data.return_value = pd.DataFrame({"a": [1]})
        api.state_manager.get_plots.return_value = []
        api.state_manager.get_config.return_value = {}
        api.state_manager.get_plot_counter.return_value = 0
        api.state_manager.get_csv_path.return_value = None
        api.state_manager.get_parse_variables.return_value = None
        api.data_services.list_portfolios.return_value = []
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.text_input.return_value = "test_portfolio"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.data_services.save_portfolio.assert_called_once()

    @patch("src.web.pages.portfolio.st")
    def test_save_exception(self, mock_st: MagicMock) -> None:
        """Save portfolio exception is handled."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = True
        api.state_manager.get_data.return_value = pd.DataFrame({"a": [1]})
        api.data_services.save_portfolio.side_effect = IOError("disk full")
        api.data_services.list_portfolios.return_value = []
        api.state_manager.get_plots.return_value = []
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        mock_st.error.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_load_portfolio(self, mock_st: MagicMock) -> None:
        """Load portfolio triggers restore_session."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = ["p1"]
        api.data_services.load_portfolio.return_value = {"data": {"a": [1]}}
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.selectbox.return_value = "p1"
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.state_manager.restore_session.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_load_portfolio_error(self, mock_st: MagicMock) -> None:
        """Load portfolio error is handled."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = ["p1"]
        api.data_services.load_portfolio.side_effect = ValueError("corrupt")
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.selectbox.return_value = "p1"
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        mock_st.error.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_no_portfolios_warning(self, mock_st: MagicMock) -> None:
        """No portfolios shows warning."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = []
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = False
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        # At least one warning or info was called
        assert mock_st.warning.called or mock_st.info.called

    @patch("src.web.pages.portfolio.st")
    def test_delete_portfolio(self, mock_st: MagicMock) -> None:
        """Delete button triggers delete_portfolio."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = ["p1"]
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.selectbox.return_value = "p1"
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.data_services.delete_portfolio.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_save_pipeline(self, mock_st: MagicMock) -> None:
        """Save pipeline from plot."""
        from src.web.pages.portfolio import show_portfolio_page

        plot = MagicMock()
        plot.name = "Plot1"
        plot.pipeline = [{"type": "rename", "config": {}}]

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = [plot]
        api.data_services.list_portfolios.return_value = []
        api.shapers.list_pipelines.return_value = []

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.selectbox.return_value = "Plot1"
        mock_st.text_input.return_value = "my_pipeline"
        mock_st.multiselect.return_value = []

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.shapers.save_pipeline.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_apply_pipeline(self, mock_st: MagicMock) -> None:
        """Apply pipeline to target plots."""
        from src.web.pages.portfolio import show_portfolio_page

        plot1 = MagicMock()
        plot1.name = "Plot1"
        plot1.pipeline = []
        plot2 = MagicMock()
        plot2.name = "Plot2"
        plot2.pipeline = []

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = [plot1, plot2]
        api.data_services.list_portfolios.return_value = []
        api.shapers.list_pipelines.return_value = ["saved_pipe"]
        api.shapers.load_pipeline.return_value = {
            "pipeline": [{"type": "rename", "config": {"a": "b"}}]
        }

        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.selectbox.side_effect = ["Plot1", "saved_pipe"]
        mock_st.text_input.return_value = "test"
        mock_st.multiselect.return_value = ["Plot1"]

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.shapers.load_pipeline.assert_called()
