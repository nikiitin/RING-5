"""Tests for ApplicationAPI delegation, conversion, and error handling."""

from src.core.models.parsing_models import SourceInstance
from collections.abc import Generator
from concurrent.futures import Future
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.models.data_models import ParseVariableConfig
from src.core.models.history_models import OperationRecord
from src.core.models.preview_models import ActivePreviewInputs
from src.core.models.parsing_models import (
    ParseBatchResult,
    ScanFileResult,
    ScanResult,
    ScannedVariable,
)
from tests.helpers.parsed_values import completed_future, numeric_file, numeric_output


@pytest.fixture
def api() -> Generator[ApplicationAPI, None, None]:
    """Create ApplicationAPI with mocked internals."""
    with (
        patch("src.core.application_api.RepositoryStateManager") as mock_sm_cls,
        patch("src.core.application_api.DefaultServicesAPI") as mock_svc_cls,
        patch("src.core.application_api.SimulatorRegistry"),
    ):
        inst = ApplicationAPI()
        inst.state_manager = mock_sm_cls.return_value
        inst._services = mock_svc_cls.return_value
        inst._parser = MagicMock()
        yield inst
        inst.close(wait=True)


class TestPropertyAccess:
    # [test->req~ring5.quality.application-facade~1]

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
        cast(MagicMock, api._services.data_services.load_csv_file).side_effect = FileNotFoundError(
            "missing"
        )
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
        cast(Any, api._parser.submit_parse_async).return_value = MagicMock(futures=[])
        api.submit_parse_async(
            "/path",
            "stats.txt",
            api.compile_parse_variables(
                [
                    cast(
                        ParseVariableConfig,
                        {
                            "name": "simTicks",
                            "type": "scalar",
                            "params": {"source_type": "scalar"},
                        },
                    )
                ]
            ),
            "/out",
        )
        args_tuple = cast(MagicMock, api._parser.submit_parse_async).call_args
        configs = args_tuple[0][2]
        assert len(configs) == 1
        assert configs[0].name == "simTicks"
        assert configs[0].type == "scalar"
        job = api.list_background_jobs()[0]
        assert job.kind == "parse"
        assert job.label == "Parse: path"
        assert job.status == "completed"
        assert not job.retryable

    def test_dict_variable_with_alias(self, api: ApplicationAPI) -> None:
        """Dict variable with alias uses alias as name."""
        # [test->req~ring5.ingestion.output-aliases~1]
        cast(Any, api._parser.submit_parse_async).return_value = MagicMock(futures=[])
        api.submit_parse_async(
            "/path",
            "stats.txt",
            api.compile_parse_variables(
                [
                    cast(
                        ParseVariableConfig,
                        {
                            "source_name": "system.cpu.ipc",
                            "type": "scalar",
                            "name": "IPC",
                            "params": {"source_type": "scalar"},
                        },
                    )
                ]
            ),
            "/out",
        )
        args_tuple = cast(MagicMock, api._parser.submit_parse_async).call_args
        configs = args_tuple[0][2]
        assert configs[0].name == "IPC"
        assert configs[0].source_name == "system.cpu.ipc"
        assert configs[0].params == {"source_type": "scalar"}

    def test_dict_regex_with_alias_preserves_source_pattern(self, api: ApplicationAPI) -> None:
        """Regex detection uses the source statistic rather than its alias."""
        cast(Any, api._parser.submit_parse_async).return_value = MagicMock(futures=[])
        api.submit_parse_async(
            "/path",
            "stats.txt",
            api.compile_parse_variables(
                [
                    cast(
                        ParseVariableConfig,
                        {
                            "source_name": r"system.cpu\d+.ipc",
                            "type": "scalar",
                            "name": "IPC",
                            "params": {"source_type": "scalar"},
                        },
                    )
                ]
            ),
            "/out",
        )

        configs = cast(MagicMock, api._parser.submit_parse_async).call_args[0][2]
        assert configs[0].name == "IPC"
        assert configs[0].source_name == r"system.cpu\d+.ipc"
        assert configs[0].is_regex is True
        assert "parsed_ids" not in configs[0].params

    def test_dict_variable_with_regex(self, api: ApplicationAPI) -> None:
        r"""Variable with \\d+ in name is marked as regex."""
        cast(Any, api._parser.submit_parse_async).return_value = MagicMock(futures=[])
        api.submit_parse_async(
            "/path",
            "stats.txt",
            api.compile_parse_variables(
                [
                    cast(
                        ParseVariableConfig,
                        {
                            "name": "system.cpu\\d+.ipc",
                            "type": "vector",
                            "params": {"entries": ["0"], "source_type": "vector"},
                        },
                    )
                ]
            ),
            "/out",
        )
        args_tuple = cast(MagicMock, api._parser.submit_parse_async).call_args
        configs = args_tuple[0][2]
        assert configs[0].is_regex is True

    def test_dict_variable_statistics_only(self, api: ApplicationAPI) -> None:
        """statistics_only flag is passed through."""
        cast(Any, api._parser.submit_parse_async).return_value = MagicMock(futures=[])
        api.submit_parse_async(
            "/path",
            "stats.txt",
            api.compile_parse_variables(
                [
                    cast(
                        ParseVariableConfig,
                        {
                            "name": "hist",
                            "type": "histogram",
                            "statistics_only": True,
                            "params": {"statistics": ["mean"], "source_type": "histogram"},
                        },
                    )
                ]
            ),
            "/out",
        )
        args_tuple = cast(MagicMock, api._parser.submit_parse_async).call_args
        configs = args_tuple[0][2]
        assert configs[0].statistics_only is True

    def test_scanned_variable_object_is_not_a_runnable_configuration(
        self, api: ApplicationAPI
    ) -> None:
        """Discovery objects cannot bypass the explicit runnable model."""
        scanned = MagicMock()
        scanned.name = "system.cpu.ipc"
        scanned.type = "scalar"
        with pytest.raises(TypeError, match="StatConfig instances"):
            api.submit_parse_async("/path", "stats.txt", [scanned], "/out")
        cast(MagicMock, api._parser.submit_parse_async).assert_not_called()

    def test_stat_config_passthrough(self, api: ApplicationAPI) -> None:
        """StatConfig objects pass through unchanged."""
        from src.core.models.parsing_models import StatConfig

        sc = StatConfig(name="test", type="scalar", params={"source_type": "scalar"})
        cast(Any, api._parser.submit_parse_async).return_value = MagicMock(futures=[])
        api.submit_parse_async("/path", "stats.txt", [sc], "/out")
        args_tuple = cast(MagicMock, api._parser.submit_parse_async).call_args
        configs = args_tuple[0][2]
        assert configs[0] == sc
        assert configs[0] is not sc

    def test_scanned_vars_kwarg_forwarded(self, api: ApplicationAPI) -> None:
        """scanned_vars kwarg is forwarded to the parser."""
        from src.core.models.parsing_models import ScannedVariable

        cast(Any, api._parser.submit_parse_async).return_value = MagicMock(futures=[])
        sv = ScannedVariable(
            name="test_var",
            type="scalar",
            entries=[],
            source_type="scalar",
            instances=(SourceInstance("test_var", ()),),
        )
        scanned = [sv]
        api.submit_parse_async("/path", "stats.txt", [], "/out", scanned_vars=scanned)
        args_tuple = cast(MagicMock, api._parser.submit_parse_async).call_args
        forwarded = args_tuple[0][5]
        assert forwarded is not None
        assert len(forwarded) == 1
        assert forwarded[0].name == "test_var"


class TestFinalizeParsing:
    """Test typed finalization delegates its complete immutable plan."""

    def test_delegates_to_parser(self, api: ApplicationAPI, tmp_path: Path) -> None:
        value = numeric_file("source", {"x": 1.0})
        batch = ParseBatchResult(
            (completed_future(value),), ("x",), ("source",), str(tmp_path), "simple"
        )
        output = numeric_output(tmp_path / "result.csv", {"x": 1.0})
        cast(Any, api._parser.finalize_parsing).return_value = output
        result = api.finalize_parsing(batch, [value])
        assert result is output

    def test_with_batch_variable_order(self, api: ApplicationAPI, tmp_path: Path) -> None:
        value = numeric_file("source", {"a": 1.0, "b": 2.0})
        batch = ParseBatchResult(
            (completed_future(value),), ("a", "b"), ("source",), str(tmp_path), "simple"
        )
        output = numeric_output(tmp_path / "r.csv", {"a": 1.0, "b": 2.0})
        cast(Any, api._parser.finalize_parsing).return_value = output
        api.finalize_parsing(batch, [value])
        call_args = cast(MagicMock, api._parser.finalize_parsing).call_args
        assert call_args.args == (batch, [value])
        assert call_args.args[0].var_names == ("a", "b")
        assert call_args.kwargs == {"complete": True}


class TestIncrementalParsing:
    """Incremental requests share normalization and delegate their complete plan."""

    @pytest.mark.parametrize("complete", [True, False])
    def test_submit_and_finalize_delegate_to_parser(
        self, api: ApplicationAPI, tmp_path: Path, complete: bool
    ) -> None:
        # [test->req~ring5.ingestion.incremental-parsing~1]
        from src.core.models.parsing_models import (
            IncrementalParseBatchResult,
            IncrementalParseResult,
        )

        batch = IncrementalParseBatchResult(
            futures=(),
            var_names=("IPC",),
            output_dir="/out",
            strategy_type="simple",
            cache_path="/out/cache.json",
            configuration_hash="a" * 64,
            fingerprints=(("/inputs/stats.txt", "b" * 64),),
            cached_results=(numeric_file("/inputs/stats.txt", {"IPC": 1.0}),),
            changed_files=(),
            removed_files=(),
        )
        result = IncrementalParseResult(
            numeric_output(tmp_path / "results.csv", {"IPC": 1.0}), 0, 1, 0, 1
        )
        cast(Any, api._parser.submit_incremental_parse_async).return_value = batch
        cast(Any, api._parser.finalize_incremental_parsing).return_value = result

        submitted = api.submit_incremental_parse_async(
            "/inputs",
            "stats.txt",
            api.compile_parse_variables(
                [
                    cast(
                        ParseVariableConfig,
                        {
                            "source_name": "cpu.ipc",
                            "name": "IPC",
                            "type": "scalar",
                            "params": {"source_type": "scalar"},
                        },
                    )
                ]
            ),
            "/out",
            cache_path="/out/cache.json",
        )
        finalized = api.finalize_incremental_parsing(submitted, [], complete=complete)

        assert submitted is batch
        assert finalized is result
        assert api.list_background_jobs()[0].label == "Incremental parse: inputs"
        configs = cast(MagicMock, api._parser.submit_incremental_parse_async).call_args.args[2]
        assert configs[0].name == "IPC"
        assert configs[0].source_name == "cpu.ipc"
        cast(MagicMock, api._parser.finalize_incremental_parsing).assert_called_once_with(
            batch, [], complete=complete
        )


class TestParserPlayground:
    """Configuration tests normalize once and preserve the async parser contract."""

    def test_submit_and_finalize_delegate_to_parser(self, api: ApplicationAPI) -> None:
        # [test->req~ring5.ingestion.parser-playground~1]
        from src.core.models.parsing_models import (
            ParserPlaygroundBatchResult,
            ParserPlaygroundResult,
        )

        batch = ParserPlaygroundBatchResult(
            futures=(
                completed_future(numeric_file("/inputs/a/stats.txt", {"IPC": 1.0})),
                completed_future(numeric_file("/inputs/b/stats.txt", {"IPC": 2.0})),
            ),
            var_names=("IPC",),
            output_dir="/out",
            strategy_type="simple",
            matched_file_count=2,
            sampled_files=("/inputs/a/stats.txt", "/inputs/b/stats.txt"),
        )
        result = ParserPlaygroundResult(
            matched_file_count=2,
            sampled_files=batch.sampled_files,
            columns=("IPC",),
            rows=((1.0,), (2.0,)),
            missing_variables=(),
            diagnostics=("The sampled configuration is ready for a full parse.",),
            ready_for_full_parse=True,
        )
        cast(Any, api._parser.submit_parser_playground_async).return_value = batch
        cast(Any, api._parser.finalize_parser_playground).return_value = result

        submitted = api.submit_parser_playground_async(
            "/inputs",
            "stats.txt",
            api.compile_parse_variables(
                [
                    cast(
                        ParseVariableConfig,
                        {
                            "source_name": "cpu.ipc",
                            "name": "IPC",
                            "type": "scalar",
                            "params": {"source_type": "scalar"},
                        },
                    )
                ]
            ),
            "/out",
        )
        values = [future.result() for future in submitted.futures]
        finalized = api.finalize_parser_playground(submitted, values)

        assert submitted is batch
        assert finalized is result
        assert api.list_background_jobs()[0].label == "Test parser: inputs"
        configs = cast(MagicMock, api._parser.submit_parser_playground_async).call_args.args[2]
        assert configs[0].name == "IPC"
        assert configs[0].source_name == "cpu.ipc"
        cast(MagicMock, api._parser.finalize_parser_playground).assert_called_once_with(
            batch, values
        )


class TestScanMethods:
    """Test scan delegation."""

    def test_submit_scan_async(self, api: ApplicationAPI) -> None:
        pending: Future[Any] = Future()
        cast(Any, api._parser.submit_scan_async).return_value = [pending]
        result = api.submit_scan_async("/path")
        assert len(result) == 1
        job = api.list_background_jobs()[0]
        assert job.kind == "scan"
        assert job.label == "Scan: path"
        assert not job.retryable
        pending.set_result(MagicMock(error=None))
        assert api.list_background_jobs()[0].status == "completed"
        api.reset_session()
        assert api.list_background_jobs() == ()

    def test_finalize_scan(self, api: ApplicationAPI) -> None:
        variable = ScannedVariable(
            "value", "scalar", source_type="scalar", instances=(SourceInstance("value", ()),)
        )
        value = ScanFileResult("source", [variable])
        aggregate = ScanResult([variable], scanned_files=1)
        cast(Any, api._parser.aggregate_scan_results).return_value = aggregate
        result = api.finalize_scan([value])
        assert result is aggregate
        assert len(result.variables) == 1
        cast(MagicMock, api._parser.aggregate_scan_results).assert_called_once_with([value])


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
    # [test->req~ring5.quality.application-facade~1]

    """Test scoped preview operations route through their required service boundary."""

    def test_capture_preview_inputs(self, api: ApplicationAPI) -> None:
        with patch("src.core.application_api.WorkspaceInputService") as service_type:
            result = api.capture_preview_inputs(("baseline", "candidate"))
        service_type.assert_called_once_with(api.state_manager)
        service_type.return_value.capture_preview_inputs.assert_called_once_with(
            ("baseline", "candidate")
        )
        assert result is service_type.return_value.capture_preview_inputs.return_value

    def test_set_preview(self, api: ApplicationAPI) -> None:
        dummy_df = pd.DataFrame({"col": ["data"]})
        inputs = ActivePreviewInputs("source", 0)
        with patch("src.core.application_api.WorkspaceInputService") as service_type:
            api.set_preview("op", dummy_df, operation_config={}, inputs=inputs)
        service_type.assert_called_once_with(api.state_manager)
        service_type.return_value.set_preview.assert_called_once_with(
            "op", dummy_df, operation_config={}, inputs=inputs
        )

    def test_get_preview(self, api: ApplicationAPI) -> None:
        with patch("src.core.application_api.WorkspaceInputService") as service_type:
            result = api.get_preview("op")
        service_type.assert_called_once_with(api.state_manager)
        service_type.return_value.get_preview.assert_called_once_with("op")
        assert result is service_type.return_value.get_preview.return_value

    def test_has_preview(self, api: ApplicationAPI) -> None:
        api.has_preview("op")
        cast(MagicMock, api.state_manager.has_preview).assert_called_once_with("op")

    def test_clear_preview(self, api: ApplicationAPI) -> None:
        api.clear_preview("op")
        cast(MagicMock, api.state_manager.clear_preview).assert_called_once_with("op")


class TestHistoryDelegation:
    """Test history methods delegate to state manager."""

    def test_add_manager_history_record(self, api: ApplicationAPI) -> None:
        record = OperationRecord(
            source_columns=[], dest_columns=[], operation="test", timestamp="2024-01-01T00:00:00"
        )
        api.add_manager_history_record(record)
        cast(MagicMock, api.state_manager.add_manager_history_record).assert_called_once_with(
            record
        )
        cast(MagicMock, api.state_manager.add_portfolio_history_record).assert_called_once_with(
            record
        )

    def test_get_manager_history(self, api: ApplicationAPI) -> None:
        cast(MagicMock, api.state_manager.get_manager_history).return_value = []
        result = api.get_manager_history()
        assert result == []

    def test_get_portfolio_history(self, api: ApplicationAPI) -> None:
        cast(MagicMock, api.state_manager.get_portfolio_history).return_value = []
        result = api.get_portfolio_history()
        assert result == []

    def test_remove_manager_history_record(self, api: ApplicationAPI) -> None:
        record = OperationRecord(
            source_columns=[], dest_columns=[], operation="test", timestamp="2024-01-01T00:00:00"
        )
        api.remove_manager_history_record(record)
        cast(MagicMock, api.state_manager.remove_manager_history_record).assert_called_once_with(
            record
        )
        cast(MagicMock, api.state_manager.remove_portfolio_history_record).assert_called_once_with(
            record
        )


def test_close_can_upgrade_background_wait_policy() -> None:
    api = ApplicationAPI()
    try:
        with patch.object(api._background_jobs, "close") as close_jobs:
            api.close()
            api.close(wait=True)
            assert close_jobs.call_args_list == [call(wait=False), call(wait=True)]
    finally:
        api.close(wait=True)
