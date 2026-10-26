"""Current parser contracts are admitted before work or provenance publication."""

from __future__ import annotations

from dataclasses import replace
from enum import Enum
from pathlib import Path
import time
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.common.source_context_codec import SourceContextCodec
from src.core.models.parsing_models import (
    PARSER_RESULT_VERSION,
    StatConfig,
    require_current_parser_contract,
)
from src.core.models.parse_job_models import ParseJobStatus
import src.core.services.parse_job_service as parse_job_service
from src.core.services.parse_job_service import ParseJobService, build_parse_job_request
from src.core.services.parse_job_workspace import ParseJobRuntimeWorkspace
from src.parsing.parser_protocol import SimulationParser
from tests.helpers.public_typed_parser import ExampleParser

pytestmark = pytest.mark.xdist_group("perl_pool")


@pytest.fixture(autouse=True)
def isolated_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[None, None, None]:
    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(ParseJobRuntimeWorkspace, "_instance", None)
    yield
    workspace = ParseJobRuntimeWorkspace._instance
    if workspace is not None:
        workspace.close()


def _variables() -> list[StatConfig]:
    return [StatConfig("value", "scalar", params={"source_type": "scalar"})]


class _Version(str, Enum):
    CURRENT = str(PARSER_RESULT_VERSION)


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "unsupported",
        str(PARSER_RESULT_VERSION - 1),
        PARSER_RESULT_VERSION,
        True,
        _Version.CURRENT,
    ],
)
def test_version_admission_does_not_coerce_missing_old_or_nonnative_identifiers(
    value: object,
) -> None:
    with pytest.raises(ValueError, match="contract.*unsupported"):
        require_current_parser_contract(value)


def test_version_admission_never_runs_untrusted_string_or_equality_hooks() -> None:
    class Hooks:
        def __str__(self) -> str:
            raise AssertionError("Unexpected string hook")

        def __eq__(self, other: object) -> bool:
            raise AssertionError("Unexpected equality hook")

    with pytest.raises(ValueError, match="unsupported"):
        require_current_parser_contract(Hooks())
    require_current_parser_contract(str(PARSER_RESULT_VERSION))


@pytest.mark.parametrize("value", [None, "unsupported", str(PARSER_RESULT_VERSION - 1)])
def test_builder_rejects_before_discovery_fingerprinting_or_request_publication(
    tmp_path: Path, value: Any
) -> None:
    with (
        patch.object(parse_job_service, "normalize_user_path") as resolve,
        patch.object(parse_job_service, "find_stats_files") as discover,
        patch.object(parse_job_service, "fingerprint_inputs") as fingerprint,
    ):
        with pytest.raises(ValueError, match="contract.*unsupported"):
            build_parse_job_request(
                stats_path=str(tmp_path),
                stats_pattern="stats.txt",
                variables=_variables(),
                strategy_type="simple",
                parser_contract_version=value,
            )
    resolve.assert_not_called()
    discover.assert_not_called()
    fingerprint.assert_not_called()


@pytest.mark.parametrize("injected", [False, True])
def test_public_rejection_precedes_lazy_workspace_and_preserves_loaded_state(
    tmp_path: Path, injected: bool
) -> None:
    backend = MagicMock(spec=SimulationParser) if injected else None
    api = ApplicationAPI(parser=backend)
    try:
        frame = pd.DataFrame({"existing": [2.5]})
        api.state_manager.set_data(frame)
        before_origin = api.state_manager.get_loaded_origin()
        before_editor = api.state_manager.get_parse_variables()
        with patch.object(api, "_get_parse_job_service") as create_service:
            with pytest.raises(ValueError, match="contract.*unsupported"):
                api.submit_parse_job(
                    str(tmp_path), "stats.txt", _variables(), parser_contract_version="unsupported"
                )
        create_service.assert_not_called()
        assert api._parse_jobs is None
        retained = api.state_manager.get_data()
        assert retained is not None
        pd.testing.assert_frame_equal(retained, frame)
        assert api.state_manager.get_loaded_origin() == before_origin
        assert api.state_manager.get_parse_variables() == before_editor
        assert not (tmp_path / "storage" / "jobs").exists()
        if backend is not None:
            backend.submit_parse_async.assert_not_called()
            backend.submit_incremental_parse_async.assert_not_called()
    finally:
        api.close(wait=True)


def test_persisted_callback_rejects_before_any_backend_or_cache_work(tmp_path: Path) -> None:
    backend = MagicMock(spec=SimulationParser)
    api = ApplicationAPI(parser=backend)
    source = SourceContextCodec.parser(
        stats_path=str(tmp_path),
        stats_pattern="stats.txt",
        strategy_type="simple",
        variables=_variables(),
        scanned_variables=[],
        simulator="declared",
        scan_limit=None,
        strict=False,
        parser_contract_version="unsupported",
    )
    try:
        for incremental in (False, True):
            with pytest.raises(ValueError, match="unsupported"):
                api._submit_background_parse(source, str(tmp_path / "attempt"), incremental)
        backend.submit_parse_async.assert_not_called()
        backend.submit_incremental_parse_async.assert_not_called()
        assert not (tmp_path / "attempt").exists()
        assert source.parser_contract_version == "unsupported"
    finally:
        api.close(wait=True)


@pytest.mark.parametrize("injected", [False, True])
@pytest.mark.parametrize("explicit", [False, True])
def test_actual_current_backend_job_retains_the_executed_contract(
    tmp_path: Path, injected: bool, explicit: bool
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "stats.txt").write_text("1.25" if injected else "value 1.25\n")
    backend = ExampleParser() if injected else None
    api = ApplicationAPI(parser=backend)
    try:
        if explicit:
            snapshot = api.submit_parse_job(
                str(inputs),
                "stats.txt",
                _variables(),
                simulator="example" if injected else None,
                parser_contract_version=str(PARSER_RESULT_VERSION),
            )
        else:
            snapshot = api.submit_parse_job(
                str(inputs),
                "stats.txt",
                _variables(),
                simulator="example" if injected else None,
            )
        deadline = time.monotonic() + 15
        while not snapshot.status.is_terminal and time.monotonic() < deadline:
            time.sleep(0.01)
            current = api.get_parse_job(snapshot.job_id)
            assert current is not None
            snapshot = current
        assert snapshot.status == ParseJobStatus.SUCCEEDED
        receipt = api.consume_parse_job(snapshot.job_id)
        assert receipt.source_context.parser_contract_version == str(PARSER_RESULT_VERSION)
        assert receipt.source_context.simulator == ("example" if injected else "gem5")
        frame = api.state_manager.get_data()
        assert frame is not None and frame.to_dict("records") == [{"value": 1.25}]
        origin = api.state_manager.get_loaded_origin()
        assert origin is not None and origin.source == receipt.source_context
    finally:
        api.close(wait=True)
        if backend is not None:
            backend.close()


def test_retry_of_an_unsupported_stored_request_preserves_the_existing_attempt(
    tmp_path: Path,
) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "stats.txt").write_text("value 1.25\n")
    request = build_parse_job_request(
        stats_path=str(inputs),
        stats_pattern="stats.txt",
        variables=_variables(),
        strategy_type="simple",
    )
    request = replace(
        request,
        source_context=replace(
            request.source_context, parser_contract_version=str(PARSER_RESULT_VERSION - 1)
        ),
    )
    workspace = ParseJobRuntimeWorkspace(tmp_path / "runtime")
    submit, finalize, publish = MagicMock(), MagicMock(), MagicMock()
    service = ParseJobService(submit, finalize, publish, runtime_workspace=workspace)
    try:
        attempt = service.session_dir / "attempts" / "old"
        attempt.mkdir()
        marker = attempt / "owned-input"
        marker.write_text("preserve")
        before = service._store.create_job(
            "old", request, attempt, 1, status=ParseJobStatus.FAILED, phase="Stored failure"
        )
        with (
            patch.object(service._store, "delete_job", wraps=service._store.delete_job) as delete,
            patch.object(parse_job_service, "find_stats_files") as discover,
            patch.object(parse_job_service, "fingerprint_inputs") as fingerprint,
        ):
            with pytest.raises(ValueError, match="contract.*unsupported"):
                service.retry("old")
        delete.assert_not_called()
        discover.assert_not_called()
        fingerprint.assert_not_called()
        submit.assert_not_called()
        finalize.assert_not_called()
        publish.assert_not_called()
        assert service.get("old") == before
        assert service._store.get_request("old") == request
        assert service._store.get_attempt_dir("old") == attempt
        assert marker.read_text() == "preserve"
    finally:
        service.close()
        workspace.close()
