from typing import Any, cast
from unittest.mock import MagicMock, mock_open, patch

from src.core.application_api import ApplicationAPI
from src.core.models import ParseBatchResult
from src.core.models.data_models import ParseVariableConfig


class TestAliasing:
    @patch("builtins.open", new_callable=mock_open)
    def test_aliasing_config_generation(self, mock_file_open: Any) -> None:

        # Setup
        facade = ApplicationAPI()  # Use ApplicationAPI instead of BackendFacade
        stats_path = "/tmp/stats"
        stats_pattern = "stats.txt"

        # Define variables with Alias
        variables = cast(
            list[ParseVariableConfig],
            [
                {"name": "system.cpu.ipc", "type": "scalar", "alias": "IPC"},  # ALIAS!
                {
                    "name": "system.cpu.cpi",
                    "type": "scalar",
                    # No alias
                },
            ],
        )

        # Mock parser execution — ApplicationAPI uses self._parser via DI
        facade._parser = MagicMock()
        mock_submit = facade._parser.submit_parse_async

        # Mock futures properly
        mock_future = MagicMock()
        mock_future.result = MagicMock(return_value={"data": "test"})
        mock_submit.return_value = ParseBatchResult(
            futures=[mock_future], var_names=["IPC", "system.cpu.cpi"]
        )

        # Execute async parse
        batch = facade.submit_parse_async(stats_path, stats_pattern, variables, "/tmp")
        [f.result() for f in batch.futures]

        # Verify variables passed to parser
        call_args = mock_submit.call_args
        assert call_args is not None, "submit_parse_async not called"

        passed_vars = call_args[0][2]  # Third argument is variables
        assert len(passed_vars) == 2

        # Check Aliased Variable (use attribute access on StatConfig)
        ipc_var = next((v for v in passed_vars if v.name == "IPC"), None)
        assert ipc_var is not None, "Aliased variable IPC not found in config"
        assert ipc_var.params["parsed_ids"] == [
            "system.cpu.ipc"
        ], "Aliased variable does not map original name"

        # Check Non-Aliased Variable
        cpi_var = next((v for v in passed_vars if v.name == "system.cpu.cpi"), None)
        assert cpi_var is not None, "Non-aliased variable not found"
        assert "parsed_ids" not in cpi_var.params, "Non-aliased variable should not have parsed_ids"
