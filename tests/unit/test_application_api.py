"""
Unit tests for the ApplicationAPI (Layer B Orchestrator).
Verifies that the API correctly orchestrates the internal StateManager and ServicesAPI.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI


@pytest.fixture
def application_api():
    """Create ApplicationAPI with mocked internals."""
    with patch("src.core.application_api.RepositoryStateManager") as mock_sm_cls:
        with patch("src.core.application_api.DefaultServicesAPI") as mock_svc_cls:
            api = ApplicationAPI()
            api.state_manager = mock_sm_cls.return_value
            # Expose mock services for assertions
            api._mock_services = mock_svc_cls.return_value
            yield api


class TestApplicationAPI:
    """Tests for the Application Entry Point."""

    def test_initialization_creates_state_manager(self):
        """Verify initialization creates a default state manager."""
        with patch("src.core.application_api.RepositoryStateManager") as mock_sm:
            with patch("src.core.application_api.DefaultServicesAPI"):
                api = ApplicationAPI()
                mock_sm.assert_called_once()
                assert api.state_manager == mock_sm.return_value

    def test_load_data_success(self, application_api):
        """
        Test the orchestration of loading data:
        1. Call data services to load file
        2. Call StateManager to save it
        """
        # Arrange
        path = "/test/data.csv"
        df = pd.DataFrame({"col": [1, 2]})
        mock_data = application_api._mock_services.data
        mock_data.load_csv_file.return_value = df

        # Act
        application_api.load_data(path)

        # Assert
        mock_data.load_csv_file.assert_called_once_with(path)
        application_api.state_manager.set_data.assert_called_once_with(df)
        application_api.state_manager.set_processed_data.assert_called_once_with(None)
        application_api.state_manager.set_csv_path.assert_called_once_with(path)

    def test_load_from_pool(self, application_api):
        """Test loading data from the CSV pool."""
        # Arrange
        path = "/pool/data.csv"
        df = pd.DataFrame({"pool": [1]})
        mock_data = application_api._mock_services.data
        mock_data.load_csv_file.return_value = df

        # Act
        application_api.load_from_pool(path)

        # Assert
        mock_data.load_csv_file.assert_called_once_with(path)
        application_api.state_manager.set_data.assert_called_once_with(df)

    def test_get_current_view_assembly(self, application_api):
        """
        Verify that the API assembles the view state for the UI.
        """
        # Arrange
        application_api.state_manager.get_data.return_value = "raw_df"
        application_api.state_manager.get_processed_data.return_value = "proc_df"
        application_api.state_manager.get_config.return_value = {"conf": 1}

        # Act
        view = application_api.get_current_view()

        # Assert
        assert view["raw_data"] == "raw_df"
        assert view["processed_data"] == "proc_df"
        assert view["config"] == {"conf": 1}

    def test_reset_session(self, application_api):
        """Test session reset orchestration."""
        application_api.reset_session()
        application_api.state_manager.clear_data.assert_called_once()
        application_api.state_manager.clear_all.assert_called_once()
