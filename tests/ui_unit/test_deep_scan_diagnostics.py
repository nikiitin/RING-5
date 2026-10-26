"""Deep scan diagnostics expose incomplete discovery while retaining useful sources."""

from collections.abc import Generator
from concurrent.futures import Future
from inspect import unwrap
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.application_api import ApplicationAPI
from src.core.models.parsing_models import ScannedVariable, ScanFileResult, SourceInstance
from src.core.models.source_evidence import ResolvedSourceKind
from src.core.services.data_services.variable_service import VariableService
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.registry import GEM5_INFO
from src.web.components.data_source.variable_editor import VariableEditor


@pytest.fixture
def streamlit() -> Generator[MagicMock, None, None]:
    """Capture only the dialog's presentation without a browser or worker pool."""
    with patch("src.web.components.data_source.variable_editor.st") as mocked:
        mocked.button.return_value = False
        yield mocked


@pytest.fixture
def api() -> MagicMock:
    """Retain real aggregation and entry selection behind the mocked state boundary."""
    mocked = MagicMock(spec=ApplicationAPI)
    mocked.state_manager = MagicMock()
    mocked.get_simulator_info.return_value = GEM5_INFO
    mocked.finalize_scan.side_effect = Gem5Parser.aggregate_scan_results
    mocked.data_services.aggregate_discovered_entries.side_effect = (
        VariableService.aggregate_discovered_entries
    )
    return mocked


def _variable(name: str, kind: str, entries: list[str] | None = None) -> ScannedVariable:
    return ScannedVariable(
        name,
        kind,
        entries or [],
        source_evidence=ResolvedSourceKind(kind, "wire_contract"),
        instances=(SourceInstance(name, ()),),
    )


def _completed(result: ScanFileResult | Exception) -> Future[ScanFileResult]:
    future: Future[ScanFileResult] = Future()
    if isinstance(result, Exception):
        future.set_exception(result)
    else:
        future.set_result(result)
    return future


def _show(api: MagicMock, futures: list[Future[ScanFileResult]], distribution: bool) -> None:
    unwrap(VariableEditor._show_scan_dialog)(
        VariableEditor, cast(ApplicationAPI, api), "good", "current", futures, distribution
    )


@pytest.mark.parametrize("distribution", [False, True])
@pytest.mark.parametrize("outcome", ["contradiction", "partial", "exception", "clean"])
def test_deep_scan_reports_all_errors_and_preserves_unrelated_observations(
    streamlit: MagicMock, api: MagicMock, distribution: bool, outcome: str
) -> None:
    good = _variable("good", "vector", ["a", "b"])
    first = ScanFileResult("first", [good])
    results: list[ScanFileResult | Exception] = [first]
    expected_diagnostics: set[str] = set()
    if outcome == "contradiction":
        first.variables.append(_variable("bad", "scalar"))
        results.append(ScanFileResult("second", [_variable("bad", "configuration")]))
        assert all(isinstance(result, ScanFileResult) and result.ok for result in results)
        expected_diagnostics = {"first", "second"}
    elif outcome == "partial":
        results[0] = ScanFileResult("first", [good], error="bad source measurement")
        expected_diagnostics = {"first", "bad source measurement"}
    elif outcome == "exception":
        results.append(RuntimeError("worker decoder failed"))
        expected_diagnostics = {"worker decoder failed"}

    _show(api, [_completed(result) for result in results], distribution)

    saved = api.state_manager.set_scanned_variables.call_args.args[0]
    assert saved == [good.to_dict()]
    api.data_services.aggregate_discovered_entries.assert_called_once_with(
        saved, "good", GEM5_INFO.internal_stats
    )
    warnings = [call.args[0] for call in streamlit.warning.call_args_list]
    assert all(any(text in warning for warning in warnings) for text in expected_diagnostics)
    expected_warning_count = 2 if outcome == "contradiction" else int(outcome != "clean")
    assert len(warnings) == expected_warning_count
    status = streamlit.status.return_value.__enter__.return_value
    status.update.assert_called_once()
    update = status.update.call_args.kwargs
    assert update["state"] == ("complete" if outcome == "clean" else "error")
    assert update["label"] == (
        ("Source evidence scanned" if distribution else "Discovered 2 entries")
        if outcome == "clean"
        else "Scan finished with errors"
    )
    assert streamlit.success.called is (outcome == "clean" and not distribution)
    api.release_settled_scans.assert_called_once_with()


def test_no_successful_future_preserves_catalog_and_releases_settled_scans(
    streamlit: MagicMock, api: MagicMock
) -> None:
    _show(api, [_completed(RuntimeError("worker decoder failed"))], True)
    assert [call.args[0] for call in streamlit.warning.call_args_list] == [
        "Scan worker failed: worker decoder failed",
        "No results found.",
    ]
    api.finalize_scan.assert_not_called()
    api.state_manager.set_scanned_variables.assert_not_called()
    api.release_settled_scans.assert_called_once_with()


def test_timeout_cancels_only_owned_futures_and_releases_settled_scans(
    streamlit: MagicMock, api: MagicMock
) -> None:
    owned: Future[ScanFileResult] = Future()
    foreign: Future[ScanFileResult] = Future()
    foreign.set_running_or_notify_cancel()
    with patch(
        "src.web.components.data_source.variable_editor.as_completed", side_effect=TimeoutError
    ):
        _show(api, [owned], False)
    assert owned.cancelled() and foreign.running()
    streamlit.error.assert_called_once_with("Scan batch exceeded the five-minute limit.")
    api.state_manager.set_scanned_variables.assert_not_called()
    api.release_settled_scans.assert_called_once_with()


def test_aggregation_exception_releases_settled_scans_without_replacing_catalog(
    streamlit: MagicMock, api: MagicMock
) -> None:
    error = ValueError("invalid aggregate metadata")
    api.finalize_scan.side_effect = error
    with pytest.raises(ValueError) as caught:
        _show(api, [_completed(ScanFileResult("first", [_variable("good", "scalar")]))], True)
    assert caught.value is error
    api.state_manager.set_scanned_variables.assert_not_called()
    api.release_settled_scans.assert_called_once_with()
