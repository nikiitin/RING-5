from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.application_api import ApplicationAPI
from src.core.models import ScanResult
from src.core.models.data_models import ParseVariableConfig
from src.web.components.data_source.data_source_components import DataSourceComponents
from src.web.components.data_source.variable_editor import VariableEditor
from tests.conftest import columns_side_effect


class TestScannerFix:
    @pytest.fixture
    def mock_api(self) -> Any:
        """Mock the ApplicationAPI."""
        api = MagicMock(spec=ApplicationAPI)
        api.state_manager = MagicMock()
        # Ensure 'backend' attribute does NOT exist to strictly verify the fix
        del api.backend
        return api

    @pytest.fixture
    def mock_streamlit(self) -> Generator[dict[str, Any], None, None]:
        """Mock streamlit in all relevant modules."""
        with (
            patch("src.web.components.data_source.data_source_components.st") as mock_st_ds,
            patch("src.web.components.data_source.variable_editor.st") as mock_st_ve,
        ):

            for m in [mock_st_ds, mock_st_ve]:
                m.columns.side_effect = columns_side_effect
                m.spinner.return_value.__enter__.return_value = None
                m.button.side_effect = MagicMock().button.side_effect
                m.file_uploader.return_value = MagicMock().file_uploader.return_value
                # Fragment passthrough — execute the decorated function directly
                m.fragment.side_effect = lambda func: func
                m.session_state = {}

            yield {"ds": mock_st_ds, "ve": mock_st_ve}

    def test_render_csv_pool_calls_api_directly(self, mock_api: Any, mock_streamlit: Any) -> None:
        """Test that render_csv_pool calls api.load_csv_pool, not api.backend.load_csv_pool"""
        # Setup
        mock_api.load_csv_pool.return_value = []
        mock_api.state_manager.get_csv_pool.return_value = []
        # Execute
        try:
            DataSourceComponents.render_csv_pool(mock_api)
        except AttributeError as e:
            pytest.fail(f"AttributeError raised: {e}. Fix not applied correctly.")

        # Verify
        mock_api.load_csv_pool.assert_called_once()

    def test_render_parser_config_calls_api_directly(
        self, mock_api: Any, mock_streamlit: Any
    ) -> None:
        """Test that scanner calls api.submit_scan_async, not api.backend..."""
        # Setup
        mock_api.state_manager.get_simulator.return_value = "gem5"
        mock_api.state_manager.get_stats_path.return_value = str(Path.cwd())
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
        mock_api.finalize_scan.return_value = ScanResult(variables=[])

        # Execute
        try:
            with patch(
                "src.web.components.data_source.data_source_components.as_completed",
                side_effect=lambda fs, **_kwargs: fs,
            ):
                DataSourceComponents.render_parser_config(mock_api)
        except AttributeError as e:
            if "'ApplicationAPI' object has no attribute 'backend'" in str(e):
                pytest.fail(f"Regression detected: {e}")
            else:
                pytest.fail(f"AttributeError raised: {e}")

        # Verify
        mock_api.submit_scan_async.assert_called_once()
        mock_api.finalize_scan.assert_called_once()

    def test_variable_editor_deep_scan_calls_api_directly(
        self, mock_api: Any, mock_streamlit: Any
    ) -> None:
        """Test that VariableEditor deep scan calls api.submit_scan_async"""
        # [test->req~ring5.ingestion.scan-presets-progress~1]
        # Setup
        variables = cast(
            list[ParseVariableConfig], [{"name": "test_var", "type": "vector", "_id": "123"}]
        )
        mock_api.state_manager.get_scanned_variables.return_value = []

        # Simulate "Deep Scan" button click
        mock_streamlit["ve"].button.side_effect = lambda label, **kwargs: "Deep Scan" in label
        mock_streamlit["ve"].columns.side_effect = lambda spec, **kwargs: [
            MagicMock() for _ in range(spec if isinstance(spec, int) else len(spec))
        ]
        # Radio order: parse_mode then entry_mode
        mock_streamlit["ve"].segmented_control.return_value = "Entries Only"
        mock_streamlit["ve"].pills.return_value = "Manual Entry Names"
        # The variable-type selector must take the vector path.
        mock_streamlit["ve"].selectbox.return_value = "vector"

        # Mock futures
        mock_future = MagicMock()
        mock_future.result.return_value = []
        mock_api.submit_scan_async.return_value = [mock_future]
        mock_api.finalize_scan.return_value = ScanResult(variables=[])

        # Stabilize generated identifiers independently of the supplied fixture ID.
        with patch(
            "src.core.services.data_services.variable_service.VariableService.generate_variable_id",
            return_value="123",
        ):
            VariableEditor.render(api=mock_api, variables=variables, stats_path=str(Path.cwd()))

        # Verify call to api.submit_scan_async (NOT backend)
        mock_api.submit_scan_async.assert_called()

    def test_parse_action_submits_background_job_with_strategy_type(
        self, mock_api: Any, mock_streamlit: Any
    ) -> None:
        """The parse action submits immediately through the session job API."""
        mock_api.state_manager.get_parser_strategy.return_value = "simple"
        mock_api.state_manager.get_simulator.return_value = "gem5"
        mock_api.state_manager.get_stats_path.return_value = str(Path.cwd())
        mock_api.state_manager.get_stats_pattern.return_value = "stats.txt"
        mock_api.state_manager.get_parse_variables.return_value = []
        mock_api.state_manager.get_scanned_variables.return_value = []
        mock_api.get_active_parse_job.return_value = None
        snapshot = MagicMock(job_id="job-1")
        mock_api.submit_parse_job.return_value = snapshot

        mock_streamlit["ds"].pills.return_value = "gem5"
        mock_streamlit["ds"].segmented_control.return_value = "simple"
        mock_streamlit["ds"].text_input.side_effect = [str(Path.cwd()), "stats.txt"]
        mock_streamlit["ds"].checkbox.side_effect = [True, False]
        mock_streamlit["ds"].button.side_effect = (
            lambda label, **_kwargs: label == "Parse gem5 Stats Files"
        )

        with (
            patch(
                "src.web.components.data_source.data_source_components.validate_web_stats_path",
                return_value=Path.cwd(),
            ),
            patch("src.web.components.data_source.parse_job_status.st") as job_status_st,
        ):
            job_status_st.session_state = {}
            DataSourceComponents.render_parser_config(mock_api)

        mock_api.submit_parse_job.assert_called_once()
        _, kwargs = mock_api.submit_parse_job.call_args
        assert "strategy_type" in kwargs, f"Expected 'strategy_type' kwarg, got {kwargs.keys()}"
        assert "strategy" not in kwargs, "Should NOT use 'strategy' legacy kwarg"
        assert kwargs["simulator"] == "gem5"
        assert kwargs["incremental"] is True
        assert job_status_st.session_state["_ring5_parse_job_id"] == "job-1"
        mock_api.finalize_parsing.assert_not_called()
