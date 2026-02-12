"""Unit tests for service facade delegation layers.

Tests DefaultDataServicesAPI and DefaultManagersAPI to verify they
correctly delegate every method to the appropriate sub-service.
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.services.data_services.data_services_impl import DefaultDataServicesAPI
from src.core.services.managers.managers_impl import DefaultManagersAPI

# ===================================================================
# DefaultDataServicesAPI
# ===================================================================


class TestDefaultDataServicesAPI:
    """Verify every method delegates to the correct sub-service."""

    @pytest.fixture
    def api(self) -> DefaultDataServicesAPI:
        sm = MagicMock()
        return DefaultDataServicesAPI(sm)

    # -- CSV Pool delegation --

    @patch("src.core.services.data_services.data_services_impl.CsvPoolService")
    def test_load_csv_pool(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.load_pool.return_value = [{"name": "a.csv"}]
        result = api.load_csv_pool()
        mock_svc.load_pool.assert_called_once()
        assert result == [{"name": "a.csv"}]

    @patch("src.core.services.data_services.data_services_impl.CsvPoolService")
    def test_add_to_csv_pool(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.add_to_pool.return_value = "/pool/a.csv"
        result = api.add_to_csv_pool("/data/a.csv")
        mock_svc.add_to_pool.assert_called_once_with("/data/a.csv")
        assert result == "/pool/a.csv"

    @patch("src.core.services.data_services.data_services_impl.CsvPoolService")
    def test_delete_from_csv_pool(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.delete_from_pool.return_value = True
        assert api.delete_from_csv_pool("/pool/a.csv") is True
        mock_svc.delete_from_pool.assert_called_once_with("/pool/a.csv")

    @patch("src.core.services.data_services.data_services_impl.CsvPoolService")
    def test_load_csv_file(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        df = pd.DataFrame({"x": [1]})
        mock_svc.load_csv_file.return_value = df
        result = api.load_csv_file("/data/test.csv")
        mock_svc.load_csv_file.assert_called_once_with("/data/test.csv")
        pd.testing.assert_frame_equal(result, df)

    @patch("src.core.services.data_services.data_services_impl.CsvPoolService")
    def test_get_cache_stats(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.get_cache_stats.return_value = {"hits": 5}
        assert api.get_cache_stats() == {"hits": 5}

    @patch("src.core.services.data_services.data_services_impl.CsvPoolService")
    def test_clear_caches(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        api.clear_caches()
        mock_svc.clear_caches.assert_called_once()

    # -- Config delegation --

    @patch("src.core.services.data_services.data_services_impl.ConfigService")
    def test_save_configuration(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.save_configuration.return_value = "/configs/test.json"
        result = api.save_configuration("test", "desc", [{"type": "sort"}], "/data.csv")
        mock_svc.save_configuration.assert_called_once_with(
            "test", "desc", [{"type": "sort"}], "/data.csv"
        )
        assert result == "/configs/test.json"

    @patch("src.core.services.data_services.data_services_impl.ConfigService")
    def test_load_configuration(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.load_configuration.return_value = {"name": "test"}
        result = api.load_configuration("/configs/test.json")
        assert result == {"name": "test"}

    @patch("src.core.services.data_services.data_services_impl.ConfigService")
    def test_load_saved_configs(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.load_saved_configs.return_value = [{"name": "cfg1"}]
        assert api.load_saved_configs() == [{"name": "cfg1"}]

    @patch("src.core.services.data_services.data_services_impl.ConfigService")
    def test_delete_configuration(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.delete_configuration.return_value = True
        assert api.delete_configuration("/configs/test.json") is True

    # -- Variable delegation --

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_generate_variable_id(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.generate_variable_id.return_value = "uuid-123"
        assert api.generate_variable_id() == "uuid-123"

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_add_variable(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.add_variable.return_value = [{"name": "ipc"}]
        result = api.add_variable([], {"name": "ipc"})
        mock_svc.add_variable.assert_called_once_with([], {"name": "ipc"})
        assert result == [{"name": "ipc"}]

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_update_variable(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        vars_list = [{"name": "old"}]
        mock_svc.update_variable.return_value = [{"name": "new"}]
        result = api.update_variable(vars_list, 0, {"name": "new"})
        mock_svc.update_variable.assert_called_once_with(vars_list, 0, {"name": "new"})
        assert result == [{"name": "new"}]

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_delete_variable(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.delete_variable.return_value = []
        assert api.delete_variable([{"name": "x"}], 0) == []

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_ensure_variable_ids(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        inp = [{"name": "x"}]
        mock_svc.ensure_variable_ids.return_value = [{"name": "x", "_id": "id1"}]
        result = api.ensure_variable_ids(inp)
        assert result[0]["_id"] == "id1"

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_filter_internal_stats(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.filter_internal_stats.return_value = ["ipc"]
        assert api.filter_internal_stats(["ipc", "::total"]) == ["ipc"]

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_find_variable_by_name(self, mock_svc: MagicMock, api: DefaultDataServicesAPI) -> None:
        mock_svc.find_variable_by_name.return_value = {"name": "ipc"}
        result = api.find_variable_by_name([{"name": "ipc"}], "ipc")
        mock_svc.find_variable_by_name.assert_called_once_with([{"name": "ipc"}], "ipc", True)
        assert result == {"name": "ipc"}

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_aggregate_discovered_entries(
        self, mock_svc: MagicMock, api: DefaultDataServicesAPI
    ) -> None:
        mock_svc.aggregate_discovered_entries.return_value = ["0", "1"]
        result = api.aggregate_discovered_entries([], "cpu")
        assert result == ["0", "1"]

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_aggregate_distribution_range(
        self, mock_svc: MagicMock, api: DefaultDataServicesAPI
    ) -> None:
        mock_svc.aggregate_distribution_range.return_value = (0.0, 100.0)
        result = api.aggregate_distribution_range([], "dist_var")
        assert result == (0.0, 100.0)

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_parse_comma_separated_entries(
        self, mock_svc: MagicMock, api: DefaultDataServicesAPI
    ) -> None:
        mock_svc.parse_comma_separated_entries.return_value = ["a", "b"]
        assert api.parse_comma_separated_entries("a,b") == ["a", "b"]

    @patch("src.core.services.data_services.data_services_impl.VariableService")
    def test_format_entries_as_string(
        self, mock_svc: MagicMock, api: DefaultDataServicesAPI
    ) -> None:
        mock_svc.format_entries_as_string.return_value = "a, b"
        assert api.format_entries_as_string(["a", "b"]) == "a, b"

    # -- Portfolio delegation --

    def test_list_portfolios(self, api: DefaultDataServicesAPI) -> None:
        api._portfolio_service = MagicMock()
        api._portfolio_service.list_portfolios.return_value = ["p1"]
        assert api.list_portfolios() == ["p1"]

    def test_save_portfolio(self, api: DefaultDataServicesAPI) -> None:
        api._portfolio_service = MagicMock()
        df = pd.DataFrame({"x": [1]})
        api.save_portfolio("p1", df, [], {}, 0)
        api._portfolio_service.save_portfolio.assert_called_once_with(
            "p1", df, [], {}, 0, None, None
        )

    def test_load_portfolio(self, api: DefaultDataServicesAPI) -> None:
        api._portfolio_service = MagicMock()
        api._portfolio_service.load_portfolio.return_value = {"name": "p1"}
        assert api.load_portfolio("p1") == {"name": "p1"}

    def test_delete_portfolio(self, api: DefaultDataServicesAPI) -> None:
        api._portfolio_service = MagicMock()
        api.delete_portfolio("p1")
        api._portfolio_service.delete_portfolio.assert_called_once_with("p1")


# ===================================================================
# DefaultManagersAPI
# ===================================================================


class TestDefaultManagersAPI:
    """Verify every method delegates to the correct sub-service."""

    @pytest.fixture
    def api(self) -> DefaultManagersAPI:
        return DefaultManagersAPI()

    @pytest.fixture
    def df(self) -> pd.DataFrame:
        return pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0], "cat": ["x", "x", "y"]})

    @patch("src.core.services.managers.managers_impl.ArithmeticService")
    def test_list_operators(self, mock_svc: MagicMock, api: DefaultManagersAPI) -> None:
        mock_svc.list_operators.return_value = ["+", "-", "*", "/"]
        result = api.list_operators()
        assert "+" in result

    @patch("src.core.services.managers.managers_impl.ArithmeticService")
    def test_apply_operation(
        self, mock_svc: MagicMock, api: DefaultManagersAPI, df: pd.DataFrame
    ) -> None:
        expected = df.copy()
        expected["c"] = expected["a"] + expected["b"]
        mock_svc.apply_operation.return_value = expected
        result = api.apply_operation(df, "+", "a", "b", "c")
        mock_svc.apply_operation.assert_called_once_with(df, "+", "a", "b", "c")
        assert "c" in result.columns

    @patch("src.core.services.managers.managers_impl.ArithmeticService")
    def test_apply_mixer(
        self, mock_svc: MagicMock, api: DefaultManagersAPI, df: pd.DataFrame
    ) -> None:
        mock_svc.apply_mixer.return_value = df
        api.apply_mixer(df, "merged", ["a", "b"], "Sum", "_")
        mock_svc.apply_mixer.assert_called_once_with(df, "merged", ["a", "b"], "Sum", "_")

    @patch("src.core.services.managers.managers_impl.ArithmeticService")
    def test_validate_merge_inputs(
        self, mock_svc: MagicMock, api: DefaultManagersAPI, df: pd.DataFrame
    ) -> None:
        mock_svc.validate_merge_inputs.return_value = []
        errors = api.validate_merge_inputs(df, ["a", "b"], "Sum", "merged")
        assert errors == []

    @patch("src.core.services.managers.managers_impl.OutlierService")
    def test_remove_outliers(
        self, mock_svc: MagicMock, api: DefaultManagersAPI, df: pd.DataFrame
    ) -> None:
        mock_svc.remove_outliers.return_value = df
        api.remove_outliers(df, "a", ["cat"])
        mock_svc.remove_outliers.assert_called_once_with(df, "a", ["cat"])

    @patch("src.core.services.managers.managers_impl.OutlierService")
    def test_validate_outlier_inputs(
        self, mock_svc: MagicMock, api: DefaultManagersAPI, df: pd.DataFrame
    ) -> None:
        mock_svc.validate_outlier_inputs.return_value = []
        errors = api.validate_outlier_inputs(df, "a", ["cat"])
        assert errors == []

    @patch("src.core.services.managers.managers_impl.ReductionService")
    def test_reduce_seeds(
        self, mock_svc: MagicMock, api: DefaultManagersAPI, df: pd.DataFrame
    ) -> None:
        mock_svc.reduce_seeds.return_value = df
        api.reduce_seeds(df, ["cat"], ["a", "b"])
        mock_svc.reduce_seeds.assert_called_once_with(df, ["cat"], ["a", "b"])

    @patch("src.core.services.managers.managers_impl.ReductionService")
    def test_validate_seeds_reducer_inputs(
        self, mock_svc: MagicMock, api: DefaultManagersAPI, df: pd.DataFrame
    ) -> None:
        mock_svc.validate_seeds_reducer_inputs.return_value = []
        errors = api.validate_seeds_reducer_inputs(df, ["cat"], ["a"])
        assert errors == []
