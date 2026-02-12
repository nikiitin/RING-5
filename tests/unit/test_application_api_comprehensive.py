"""Tests for ApplicationAPI edge cases and uncovered methods."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.models.history_models import OperationRecord


@pytest.fixture
def api() -> ApplicationAPI:
    """Create ApplicationAPI with mocked internals."""
    with (
        patch("src.core.application_api.RepositoryStateManager") as mock_sm_cls,
        patch("src.core.application_api.DefaultServicesAPI") as mock_svc_cls,
    ):
        inst = ApplicationAPI()
        inst.state_manager = mock_sm_cls.return_value
        inst._services = mock_svc_cls.return_value
        yield inst


class TestPropertyAccess:
    """Test sub-API property accessors."""

    def test_managers_property(self, api: ApplicationAPI) -> None:
        result = api.managers
        assert result == api._services.managers

    def test_data_services_property(self, api: ApplicationAPI) -> None:
        result = api.data_services
        assert result == api._services.data_services

    def test_shapers_property(self, api: ApplicationAPI) -> None:
        result = api.shapers
        assert result == api._services.shapers


class TestLoadData:
    """Test load_data error handling."""

    def test_load_data_raises_on_failure(self, api: ApplicationAPI) -> None:
        api._services.data_services.load_csv_file.side_effect = FileNotFoundError("missing")
        with pytest.raises(FileNotFoundError, match="missing"):
            api.load_data("/nonexistent.csv")


class TestFindStatsFiles:
    """Test find_stats_files edge cases."""

    def test_nonexistent_path_returns_empty(self, api: ApplicationAPI) -> None:
        result = api.find_stats_files("/no/such/path")
        assert result == []

    def test_existing_path_with_stats(self, api: ApplicationAPI, tmp_path: object) -> None:
        """Finds stats.txt files in a real directory tree."""
        import pathlib

        assert isinstance(tmp_path, pathlib.Path)
        sub = tmp_path / "bench1" / "seed0"
        sub.mkdir(parents=True)
        (sub / "stats.txt").write_text("simTicks 100\n")

        result = api.find_stats_files(str(tmp_path), "stats.txt")
        assert len(result) == 1
        assert "stats.txt" in result[0]


class TestSubmitParseAsync:
    """Test variable conversion in submit_parse_async."""

    def test_dict_variable_basic(self, api: ApplicationAPI) -> None:
        """Dict variable is converted to StatConfig."""
        api._services = MagicMock()
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.submit_parse_async.return_value = MagicMock()
            api.submit_parse_async(
                "/path",
                "stats.txt",
                [{"name": "simTicks", "type": "scalar"}],
                "/out",
            )
            args = mock_ps.submit_parse_async.call_args[0]
            configs = args[2]
            assert len(configs) == 1
            assert configs[0].name == "simTicks"
            assert configs[0].type == "scalar"

    def test_dict_variable_with_alias(self, api: ApplicationAPI) -> None:
        """Dict variable with alias uses alias as name."""
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.submit_parse_async.return_value = MagicMock()
            api.submit_parse_async(
                "/path",
                "stats.txt",
                [{"name": "system.cpu.ipc", "type": "scalar", "alias": "IPC"}],
                "/out",
            )
            configs = mock_ps.submit_parse_async.call_args[0][2]
            assert configs[0].name == "IPC"
            assert configs[0].params["parsed_ids"] == ["system.cpu.ipc"]

    def test_dict_variable_with_regex(self, api: ApplicationAPI) -> None:
        r"""Variable with \\d+ in name is marked as regex."""
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.submit_parse_async.return_value = MagicMock()
            api.submit_parse_async(
                "/path",
                "stats.txt",
                [{"name": r"system.cpu\d+.ipc", "type": "vector"}],
                "/out",
            )
            configs = mock_ps.submit_parse_async.call_args[0][2]
            assert configs[0].is_regex is True

    def test_dict_variable_statistics_only(self, api: ApplicationAPI) -> None:
        """statistics_only flag is passed through."""
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.submit_parse_async.return_value = MagicMock()
            api.submit_parse_async(
                "/path",
                "stats.txt",
                [{"name": "hist", "type": "histogram", "statistics_only": True}],
                "/out",
            )
            configs = mock_ps.submit_parse_async.call_args[0][2]
            assert configs[0].statistics_only is True

    def test_scanned_variable_object(self, api: ApplicationAPI) -> None:
        """ScannedVariable-like object is converted to StatConfig."""
        scanned = MagicMock()
        scanned.name = "system.cpu.ipc"
        scanned.type = "scalar"
        scanned.entries = ["0", "1"]
        # Remove params attr so it triggers the elif branch
        del scanned.params

        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.submit_parse_async.return_value = MagicMock()
            api.submit_parse_async("/path", "stats.txt", [scanned], "/out")
            configs = mock_ps.submit_parse_async.call_args[0][2]
            assert configs[0].name == "system.cpu.ipc"
            assert configs[0].params["entries"] == ["0", "1"]

    def test_stat_config_passthrough(self, api: ApplicationAPI) -> None:
        """StatConfig objects pass through unchanged."""
        from src.core.models import StatConfig

        sc = StatConfig(name="test", type="scalar")
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.submit_parse_async.return_value = MagicMock()
            api.submit_parse_async("/path", "stats.txt", [sc], "/out")
            configs = mock_ps.submit_parse_async.call_args[0][2]
            assert configs[0] is sc

    def test_scanned_vars_kwarg_forwarded(self, api: ApplicationAPI) -> None:
        """scanned_vars kwarg is forwarded to ParseService."""
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.submit_parse_async.return_value = MagicMock()
            scanned = [MagicMock()]
            api.submit_parse_async("/path", "stats.txt", [], "/out", scanned_vars=scanned)
            kwargs_passed = mock_ps.submit_parse_async.call_args
            assert kwargs_passed[0][5] is scanned  # positional arg #6


class TestFinalizeParsing:
    """Test finalize_parsing delegation."""

    def test_delegates_to_parse_service(self, api: ApplicationAPI) -> None:
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.finalize_parsing.return_value = "/out/result.csv"
            result = api.finalize_parsing("/out", [MagicMock()])
            assert result == "/out/result.csv"

    def test_with_var_names(self, api: ApplicationAPI) -> None:
        with patch("src.core.application_api.ParseService") as mock_ps:
            mock_ps.finalize_parsing.return_value = "/out/r.csv"
            api.finalize_parsing("/out", [], var_names=["a", "b"])
            call_kwargs = mock_ps.finalize_parsing.call_args[1]
            assert call_kwargs["var_names"] == ["a", "b"]


class TestScanMethods:
    """Test scan delegation."""

    def test_submit_scan_async(self, api: ApplicationAPI) -> None:
        with patch("src.core.application_api.ScannerService") as mock_ss:
            mock_ss.submit_scan_async.return_value = [MagicMock()]
            result = api.submit_scan_async("/path")
            assert len(result) == 1

    def test_finalize_scan(self, api: ApplicationAPI) -> None:
        with patch("src.core.application_api.ScannerService") as mock_ss:
            mock_ss.aggregate_scan_results.return_value = [MagicMock()]
            result = api.finalize_scan([[MagicMock()]])
            assert len(result) == 1

    def test_status_methods(self, api: ApplicationAPI) -> None:
        assert api.get_parse_status() == "idle"
        assert api.get_scanner_status() == "idle"


class TestShapersDelegation:
    """Test apply_shapers delegation."""

    def test_apply_shapers(self, api: ApplicationAPI) -> None:
        df = pd.DataFrame({"x": [1, 2]})
        pipeline = [{"type": "selector", "columns": ["x"]}]
        api.apply_shapers(df, pipeline)
        api._services.shapers.process_pipeline.assert_called_once_with(df, pipeline)


class TestConfigurationManagement:
    """Test config CRUD delegation."""

    def test_save_configuration(self, api: ApplicationAPI) -> None:
        api.save_configuration("name", "desc", [], "/path.csv")
        api._services.data_services.save_configuration.assert_called_once_with(
            "name", "desc", [], "/path.csv"
        )

    def test_load_configuration(self, api: ApplicationAPI) -> None:
        api.load_configuration("/config.json")
        api._services.data_services.load_configuration.assert_called_once_with("/config.json")

    def test_load_csv_pool(self, api: ApplicationAPI) -> None:
        api.load_csv_pool()
        api._services.data_services.load_csv_pool.assert_called_once()

    def test_load_saved_configs(self, api: ApplicationAPI) -> None:
        api.load_saved_configs()
        api._services.data_services.load_saved_configs.assert_called_once()

    def test_delete_configuration(self, api: ApplicationAPI) -> None:
        api.delete_configuration("/cfg.json")
        api._services.data_services.delete_configuration.assert_called_once_with("/cfg.json")

    def test_add_to_csv_pool(self, api: ApplicationAPI) -> None:
        api.add_to_csv_pool("/data.csv")
        api._services.data_services.add_to_csv_pool.assert_called_once_with("/data.csv")

    def test_delete_from_pool(self, api: ApplicationAPI) -> None:
        api.delete_from_pool("/data.csv")
        api._services.data_services.delete_from_csv_pool.assert_called_once_with("/data.csv")

    def test_delete_from_csv_pool_alias(self, api: ApplicationAPI) -> None:
        """delete_from_csv_pool is an alias for delete_from_pool."""
        api.delete_from_csv_pool("/data.csv")
        api._services.data_services.delete_from_csv_pool.assert_called_once_with("/data.csv")

    def test_load_csv_file(self, api: ApplicationAPI) -> None:
        api.load_csv_file("/data.csv")
        api._services.data_services.load_csv_file.assert_called_once_with("/data.csv")


class TestGetColumnInfo:
    """Test get_column_info with different inputs."""

    def test_none_returns_empty(self, api: ApplicationAPI) -> None:
        result = api.get_column_info(None)
        assert result["total_columns"] == 0
        assert result["total_rows"] == 0
        assert result["numeric_columns"] == []
        assert result["categorical_columns"] == []

    def test_mixed_dataframe(self, api: ApplicationAPI) -> None:
        df = pd.DataFrame({"name": ["A", "B"], "value": [1, 2], "score": [3.0, 4.0]})
        result = api.get_column_info(df)
        assert result["total_columns"] == 3
        assert result["total_rows"] == 2
        assert "value" in result["numeric_columns"]
        assert "score" in result["numeric_columns"]
        assert "name" in result["categorical_columns"]

    def test_empty_dataframe(self, api: ApplicationAPI) -> None:
        df = pd.DataFrame()
        result = api.get_column_info(df)
        assert result["total_columns"] == 0
        assert result["total_rows"] == 0


class TestPreviewDelegation:
    """Test preview methods delegate to state manager."""

    def test_set_preview(self, api: ApplicationAPI) -> None:
        api.set_preview("op", "data")
        api.state_manager.set_preview.assert_called_once_with("op", "data")

    def test_get_preview(self, api: ApplicationAPI) -> None:
        api.get_preview("op")
        api.state_manager.get_preview.assert_called_once_with("op")

    def test_has_preview(self, api: ApplicationAPI) -> None:
        api.has_preview("op")
        api.state_manager.has_preview.assert_called_once_with("op")

    def test_clear_preview(self, api: ApplicationAPI) -> None:
        api.clear_preview("op")
        api.state_manager.clear_preview.assert_called_once_with("op")


class TestHistoryDelegation:
    """Test history methods delegate to state manager."""

    def test_add_manager_history_record(self, api: ApplicationAPI) -> None:
        record = OperationRecord(operation="test", description="desc")
        api.add_manager_history_record(record)
        api.state_manager.add_manager_history_record.assert_called_once_with(record)
        api.state_manager.add_portfolio_history_record.assert_called_once_with(record)

    def test_get_manager_history(self, api: ApplicationAPI) -> None:
        api.state_manager.get_manager_history.return_value = []
        result = api.get_manager_history()
        assert result == []

    def test_get_portfolio_history(self, api: ApplicationAPI) -> None:
        api.state_manager.get_portfolio_history.return_value = []
        result = api.get_portfolio_history()
        assert result == []

    def test_remove_manager_history_record(self, api: ApplicationAPI) -> None:
        record = OperationRecord(operation="test", description="desc")
        api.remove_manager_history_record(record)
        api.state_manager.remove_manager_history_record.assert_called_once_with(record)
        api.state_manager.remove_portfolio_history_record.assert_called_once_with(record)
