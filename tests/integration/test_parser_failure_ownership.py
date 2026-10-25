"""Real gem5 expected failures release producers while their Futures remain held."""

from __future__ import annotations

import gc
import weakref
from concurrent.futures import wait
from pathlib import Path
from threading import Barrier

import pytest

from src.core.models.parse_failure_models import ParseDataRuntimeError, ParseDataValueError
from src.core.models.parsing_models import StatConfig
from src.parsing.framework import result_admission
from src.parsing.framework.work_pool import WorkPool
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork

pytestmark = pytest.mark.xdist_group("perl_pool")


def _drain_workers() -> None:
    barrier = Barrier(2)
    futures = [WorkPool.get_instance().submit(lambda: barrier.wait(timeout=5)) for _ in range(2)]
    assert not wait(futures, timeout=5).not_done


@pytest.mark.parametrize(
    "mode", ["excess_observations", "malformed_config", "invalid_encoding", "metadata_collision"]
)
def test_real_expected_failure_releases_work_raw_frames_and_partial_typed_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, mode: str
) -> None:
    worker_refs, result_refs = [], []
    original_init, original_call = Gem5ParseWork.__init__, Gem5ParseWork.__call__

    def tracked_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        worker_refs.append(weakref.ref(self))

    def tracked_call(self):
        result = original_call(self)
        result_refs.append(weakref.ref(result))
        return result

    monkeypatch.setattr(Gem5ParseWork, "__init__", tracked_init)
    monkeypatch.setattr(Gem5ParseWork, "__call__", tracked_call)
    monkeypatch.setattr(result_admission, "MAX_PARSE_MATRIX_CELLS", 1)
    monkeypatch.setattr(result_admission, "MAX_PARSE_RESULT_BYTES", 1)
    inputs = tmp_path / "inputs"
    for index in range(3):
        directory = inputs / str(index)
        directory.mkdir(parents=True)
        if mode == "excess_observations":
            body = "".join(f"v {value}\n" for value in range(8))
        else:
            body = "v::a 1\nv::b 2\n"
            if mode == "invalid_encoding":
                (directory / "config.ini").write_bytes(b"[system]\npad=" + b"\xff" * 100_000)
            else:
                (directory / "config.ini").write_text(
                    "[system]\npad="
                    + "x" * 100_000
                    + ("\ninvalid " + "z" * 100_000 if mode == "malformed_config" else "")
                    + "\n"
                )
        (directory / "stats.txt").write_text(body)
    variables = [
        (
            StatConfig("v", "scalar", params={"source_type": "scalar"})
            if mode == "excess_observations"
            else StatConfig("v", "vector", params={"source_type": "vector", "entries": ["a", "b"]})
        )
    ]
    if mode == "metadata_collision":
        variables.append(
            StatConfig(
                "sim_path",
                "configuration",
                source_name="literal",
                params={"source_type": "configuration", "on_empty": "NA"},
            )
        )
    output = tmp_path / "output"
    output.mkdir()
    previous = output / "results.csv"
    previous.write_bytes(b"previous complete output")
    batch = Gem5Parser.submit_parse_async(
        str(inputs),
        "stats.txt",
        variables,
        str(output),
        "simple" if mode == "excess_observations" else "config_aware",
    )
    assert not wait(batch.futures, timeout=15).not_done
    for future in batch.futures:
        error = future.exception()
        expected = ParseDataValueError if mode == "metadata_collision" else ParseDataRuntimeError
        assert type(error) is expected
        assert error.__cause__ is error.__context__ is None
        assert all(type(value) is str and len(value) <= 1024 for value in error.args)
        facts = error.failure_facts
        assert facts.source_path in batch.source_paths
        assert len(facts.origin) <= 2048 and len(facts.cause) <= 1024
        if mode == "excess_observations":
            assert "More values (8) than expected (1)" in str(error)
            assert "scalar._balance:" in facts.origin
        elif mode == "malformed_config":
            assert "Source contains parsing errors" in str(error)
            assert "[truncated]" in str(error)
            assert "config_aware._read_config:" in facts.origin
            assert "ParsingError" in facts.cause
        elif mode == "invalid_encoding":
            assert "invalid start byte" in str(error)
            assert "UnicodeDecodeError" in facts.cause
            assert "config_aware._read_config:" in facts.origin
        else:
            assert "Metadata column collision" in str(error)
            assert "config_aware.__call__:" in facts.origin
        node = error.__traceback__
        while node:
            assert node.tb_frame.f_code.co_filename.endswith(
                ("work_pool.py", "result_admission.py", "concurrent/futures/thread.py")
            )
            node = node.tb_next
    _drain_workers()
    gc.collect()
    assert len(worker_refs) == 3 and all(ref() is None for ref in worker_refs)
    assert all(ref() is None for ref in result_refs)
    assert len(result_refs) == (0 if mode == "excess_observations" else 3)
    for record in caplog.records:
        assert record.exc_info is None
        assert all(type(value) in (str, int, float) for value in record.args)
        assert all(len(value) <= 1024 for value in record.args if type(value) is str)
    assert previous.read_bytes() == b"previous complete output"
    with pytest.raises(ValueError, match="non-empty"):
        Gem5Parser.finalize_parsing(batch, [])
