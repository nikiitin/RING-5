"""The public parse boundary reports strict current configuration failures."""

from pathlib import Path
from unittest.mock import patch

import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]


@pytest.mark.parametrize("method", ["parse_submit", "parser_playground_submit"])
def test_invalid_runnable_configuration_is_typed_and_starts_no_parse_workers(
    tmp_path: Path, method: str
) -> None:
    (tmp_path / "stats.txt").write_text("simTicks 100\n", encoding="utf-8")
    with ring5.Session() as session:
        with patch.object(session.api, "submit_parse_async") as submit:
            with pytest.raises(ring5.ParseError, match="repeat must be a positive integer"):
                getattr(session, method)(
                    str(tmp_path), [ring5.StatConfig(name="simTicks", type="scalar", repeat=True)]
                )
            submit.assert_not_called()


def test_injected_backend_custom_options_survive_submission_and_saved_provenance() -> None:
    from concurrent.futures import Future
    from unittest.mock import MagicMock

    from src.core.models import ParseBatchResult, ScanFileResult, ScanResult, ScannedVariable
    from src.parsing.parser_protocol import SimulationParser

    parser = MagicMock(spec=SimulationParser)
    variable = ScannedVariable(name="source", type="custom_stat")
    future: Future[ScanFileResult] = Future()
    future.set_result(ScanFileResult("stats.txt", [variable]))
    parser.submit_scan_async.return_value = [future]
    parser.aggregate_scan_results.return_value = ScanResult([variable], scanned_files=1)
    parser.submit_parse_async.return_value = ParseBatchResult([], ["output"])
    configured = ring5.StatConfig(
        name="output",
        type="custom_stat",
        source_name="source",
        params={"scale": 2, "name": "backend operand"},
    )
    with ring5.Session(parser=parser) as session:
        session.parse_submit("/simulations", [configured])
        received = parser.submit_parse_async.call_args.args[2][0]
        assert received.name == "output"
        assert received.params["scale"] == 2
        assert received.params["name"] == "backend operand"
        draft = session.api.state_manager.get_parse_variables()[0]
        assert draft["params"] == received.params
        assert draft["name"] == "output"
