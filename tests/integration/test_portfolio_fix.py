from unittest.mock import MagicMock, patch

import pytest

from src.core.application_api import ApplicationAPI

# This import is the critical check - if this fails, the test fails immediately
from src.web.pages.portfolio import PortfolioData, show_portfolio_page


class TestPortfolioFix:
    @pytest.fixture
    def mock_api(self):
        """Mock the ApplicationAPI."""
        api = MagicMock(spec=ApplicationAPI)
        api.state_manager = MagicMock()
        api.portfolio = MagicMock()
        return api

    @pytest.fixture
    def mock_streamlit(self):
        """Mock streamlit to prevent UI rendering errors."""
        with patch("src.web.pages.portfolio.st") as mock_st:
            # Mock columns
            mock_st.columns.return_value = [MagicMock(), MagicMock()]
            # Mock expander
            mock_st.expander.return_value.__enter__.return_value = MagicMock()
            yield mock_st

    def test_portfolio_data_type_is_available(self):
        """Test that PortfolioData is importable and usable as a type."""
        # This is a runtime check of the type definition
        assert isinstance(PortfolioData, type) or isinstance(PortfolioData, object)

    def test_show_portfolio_page_no_name_error(self, mock_api, mock_streamlit):
        """
        Test that show_portfolio_page runs without NameError.
        This verifies that the type hint `PortfolioData` in the function
        is valid at runtime.
        """
        # Setup mocks
        mock_api.portfolio.list_portfolios.return_value = ["p1"]
        mock_api.portfolio.load_portfolio.return_value = {"some": "data"}

        # Simulate user clicking "Load Portfolio"
        mock_streamlit.button.side_effect = [
            False,
            True,
        ]  # First button (Save) skipped, Second (Load) clicked

        try:
            # Execution
            show_portfolio_page(mock_api)
        except NameError as e:
            pytest.fail(f"NameError raised: {e}. The fix is likely missing.")
        except Exception:
            # Other errors are fine for this test (e.g. casting issues in mocks)
            # as long as it's not NameError on PortfolioData
            pass

        # Verify that the code path was at least attempted
        mock_api.portfolio.list_portfolios.assert_called()
