from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.web.pages.ui.components.data_source_components import DataSourceComponents
from src.web.pages.ui.components.upload_components import UploadComponents
from src.web.pages.ui.components.variable_editor import VariableEditor


class TestScannerFix:
    @pytest.fixture
    def mock_api(self):
        """Mock the ApplicationAPI."""
        api = MagicMock(spec=ApplicationAPI)
        api.state_manager = MagicMock()
        # Ensure 'backend' attribute does NOT exist to strictly verify the fix
        del api.backend
        return api

    @pytest.fixture
    def mock_streamlit(self):
        """Mock streamlit in all relevant modules."""
        with patch("src.web.pages.ui.components.data_source_components.st") as mock_st_ds, patch(
            "src.web.pages.ui.components.variable_editor.st"
        ) as mock_st_ve, patch("src.web.pages.ui.components.upload_components.st") as mock_st_uc:

            # Configure common mocks for all of them to be the same magic mock
            # so we can set side effects on one and have it affect others if needed
            # But for simplicity, we can just configure them individually or return a dict.
            # Ideally they should be the same object if we want to share side_effects easily.

            # Let's make them share the same underlying mock for simplicity in setting side effects
            mock_st = MagicMock()

            # Side effect for columns to return correct number of items
            def columns_side_effect(spec, **kwargs):
                if isinstance(spec, int):
                    count = spec
                else:
                    count = len(spec)
                return [MagicMock() for _ in range(count)]

            # Helper to link the patches to our central mock
            for m in [mock_st_ds, mock_st_ve, mock_st_uc]:
                m.columns.side_effect = columns_side_effect
                m.spinner.return_value.__enter__.return_value = None
                m.button.side_effect = mock_st.button.side_effect
                m.file_uploader.return_value = mock_st.file_uploader.return_value
                # Link other common methods if needed

            # We return a specific one to set side effects on,
            # but we need to ensure the code under test uses the patched ones.
            # Since patch replaces the object in the module,
            # and we want to control behavior via `mock_st` in the test...

            # Actually, `patch` returns the Mock object it placed.
            # We can't easily unify them into *one* object unless we patch `streamlit` globally
            # but that might affect pytest itself if it uses streamlit (unlikely but possible).

            # Revised approach: Return the individual mocks for control
            yield {"ds": mock_st_ds, "ve": mock_st_ve, "uc": mock_st_uc}

    def test_render_csv_pool_calls_api_directly(self, mock_api, mock_streamlit):
        """Test that render_csv_pool calls api.load_csv_pool, not api.backend.load_csv_pool"""
        # Setup
        mock_api.load_csv_pool.return_value = []

        # Execute
        try:
            DataSourceComponents.render_csv_pool(mock_api)
        except AttributeError as e:
            pytest.fail(f"AttributeError raised: {e}. Fix not applied correctly.")

        # Verify
        mock_api.load_csv_pool.assert_called_once()

    def test_render_parser_config_calls_api_directly(self, mock_api, mock_streamlit):
        """Test that scanner calls api.submit_scan_async, not api.backend..."""
        # Setup
        mock_api.state_manager.get_stats_path.return_value = "/tmp"
        mock_api.state_manager.get_stats_pattern.return_value = "stats.txt"
        mock_api.state_manager.get_parser_strategy.return_value = "simple"

        # Simulate "Quick Scan" button click
        # Order of buttons: 1. Quick Scan, 2. Add Variable, 3. Parse stats
        # We want Quick Scan to be True
        mock_streamlit["ds"].button.side_effect = lambda label, **kwargs: "Quick Scan" in label
        mock_streamlit["ds"].columns.return_value = [MagicMock(), MagicMock()]

        # Mock future results
        mock_future = MagicMock()
        mock_future.result.return_value = []
        mock_api.submit_scan_async.return_value = [mock_future]
        mock_api.finalize_scan.return_value = []

        # Execute
        try:
            DataSourceComponents.render_parser_config(mock_api)
        except AttributeError as e:
            if "'ApplicationAPI' object has no attribute 'backend'" in str(e):
                pytest.fail(f"Regression detected: {e}")
            else:
                pytest.fail(f"AttributeError raised: {e}")

        # Verify
        mock_api.submit_scan_async.assert_called_once()
        mock_api.finalize_scan.assert_called_once()

    def test_variable_editor_deep_scan_calls_api_directly(self, mock_api, mock_streamlit):
        """Test that VariableEditor deep scan calls api.submit_scan_async"""
        # Setup
        variables = [{"name": "test_var", "type": "vector", "_id": "123"}]
        mock_api.state_manager.get_scanned_variables.return_value = []

        # Simulate "Deep Scan" button click
        mock_streamlit["ve"].button.side_effect = lambda label, **kwargs: "Deep Scan" in label
        mock_streamlit["ve"].columns.side_effect = lambda spec, **kwargs: [
            MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        # st.radio needs to return a valid string for logic checks
        mock_streamlit["ve"].radio.return_value = "Manual Entry Names"
        # st.selectbox needs to return "vector" for var_type check
        # Use side effect to be safe, or just return "vector" if simple
        mock_streamlit["ve"].selectbox.return_value = "vector"

        # Mock futures
        mock_future = MagicMock()
        mock_future.result.return_value = []
        mock_api.submit_scan_async.return_value = [mock_future]
        mock_api.finalize_scan.return_value = []

        # Mocking UUID generation just in case, though we provided _id
        with patch(
            "src.core.services.variable_service.VariableService.generate_variable_id",
            return_value="123",
        ):
            VariableEditor.render(api=mock_api, variables=variables, stats_path="/tmp")

        # Verify call to api.submit_scan_async (NOT backend)
        mock_api.submit_scan_async.assert_called()

    def test_upload_components_calls_api_directly(self, mock_api, mock_streamlit):
        """Test that UploadComponents calls api.load_data (not load_csv_file)"""
        # Setup
        # Mock file uploader returning a file
        mock_file = MagicMock()
        mock_file.name = "test.csv"
        mock_file.getbuffer.return_value = b"data"
        mock_streamlit["uc"].file_uploader.return_value = mock_file

        # Mock temp dir setup
        mock_api.state_manager.get_temp_dir.return_value = "/tmp"

        # Mock built-in open
        with patch("builtins.open", MagicMock()):
            try:
                UploadComponents.render_file_upload_tab(mock_api)
            except AttributeError as e:
                pytest.fail(f"AttributeError raised: {e}")

        # Verify - API now uses load_data instead of load_csv_file
        mock_api.load_data.assert_called_once()

    def test_parser_dialog_calls_finalize_parsing_correctly(self, mock_api, mock_streamlit):
        """Test that _show_parse_dialog calls finalize_parsing with
        correct keyword arg 'strategy_type'.
        """
        # Setup - mock all required API methods
        mock_api.state_manager.get_parser_strategy.return_value = "simple"
        mock_api.finalize_parsing.return_value = "/tmp/out/final.csv"
        mock_api.add_to_csv_pool.return_value = "/pool/final.csv"
        mock_api.load_csv_file.return_value = pd.DataFrame({"col": [1, 2]})
        output_dir = "/tmp/out"

        # Create a future that returns a result
        mock_future = MagicMock()
        mock_future.result.return_value = {"some": "data"}
        futures = [mock_future]

        # Patch streamlit imports and dialog decorator at module level
        with patch("streamlit.dialog", lambda *a, **k: lambda f: f):
            # Re-import to get fresh version with patched decorator
            import importlib

            import src.web.pages.ui.components.data_source_components as dsc_module

            importlib.reload(dsc_module)

            # Patch as_completed and Path.exists
            with patch("concurrent.futures.as_completed", return_value=futures), patch(
                "pathlib.Path.exists", return_value=True
            ):

                # Mock Streamlit objects
                mock_progress = MagicMock()
                mock_status = MagicMock()

                with patch(
                    "src.web.pages.ui.components.data_source_components.st.progress",
                    return_value=mock_progress,
                ), patch(
                    "src.web.pages.ui.components.data_source_components.st.empty",
                    return_value=mock_status,
                ), patch(
                    "src.web.pages.ui.components.data_source_components.st.write"
                ), patch(
                    "src.web.pages.ui.components.data_source_components.st.success"
                ):

                    dsc_module.DataSourceComponents._show_parse_dialog(
                        mock_api, futures, output_dir
                    )

        # Verify finalize_parsing called with correct arguments
        mock_api.finalize_parsing.assert_called_once()

        # Inspect kwargs to ensure 'strategy_type' was used
        _, kwargs = mock_api.finalize_parsing.call_args
        assert "strategy_type" in kwargs, f"Expected 'strategy_type' kwarg, got {kwargs.keys()}"
        assert "strategy" not in kwargs, "Should NOT use 'strategy' legacy kwarg"
