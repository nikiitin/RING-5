"""Real gem5 expected failures release producers while their Futures remain held."""

from __future__ import annotations

import gc
import weakref
from concurrent.futures import wait
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

import pytest

from src.core.models.parse_failure_models import (
    ParseDataRuntimeError,
    ParseDataValueError,
    ParseFailureFacts,
)
from src.core.models.parsed_output_models import ParsedFileResult
from src.core.models.parsing_models import StatConfig
from src.parsing.framework import result_admission
from src.parsing.framework.work_pool import WorkPool
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.source_bindings import SourcePlan
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.impl.strategies import gem5_parse_work, perl_worker_pool

pytestmark = pytest.mark.xdist_group("perl_pool")


def _drain_workers() -> None:
    barrier = Barrier(2)
    futures = [WorkPool.get_instance().submit(lambda: barrier.wait(timeout=5)) for _ in range(2)]
    assert not wait(futures, timeout=5).not_done


def test_actual_invalid_utf8_worker_output_has_bounded_cause_and_releases_failed_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    script = tmp_path / "invalid-output.pl"
    script.write_text(
        'use strict; use warnings; $|=1; print "READY source-events-1\\n";\n'
        "while (my $line = <STDIN>) {\n"
        "  last if $line =~ /^SHUTDOWN/;\n"
        '  print "scalar/v/" . ("x" x 200000) . "\\xff\\nEND_PARSE\\n" if $line =~ /^PARSE/;\n'
        "}\n"
    )
    real_worker = perl_worker_pool.PerlWorker

    def own_worker(
        *, worker_id: int, script_path: str, perl_exe: str
    ) -> perl_worker_pool.PerlWorker:
        return real_worker(worker_id, str(script), perl_exe)

    monkeypatch.setattr(perl_worker_pool, "PerlWorker", own_worker)
    pool = perl_worker_pool.PerlWorkerPool(pool_size=2)
    monkeypatch.setattr(gem5_parse_work, "get_worker_pool", lambda: pool)
    refs = []
    original_init = Gem5ParseWork.__init__

    def track(
        self: Gem5ParseWork,
        file_to_parse: str,
        accumulators: gem5_parse_work.VarsDictType,
        plan: SourcePlan,
    ) -> None:
        original_init(self, file_to_parse, accumulators, plan)
        refs.append(weakref.ref(self))

    monkeypatch.setattr(Gem5ParseWork, "__init__", track)
    source = tmp_path / "inputs" / "stats.txt"
    source.parent.mkdir()
    source.write_text("v 1\n")
    output = tmp_path / "out"
    output.mkdir()
    previous = output / "results.csv"
    previous.write_bytes(b"previous complete output")
    try:
        batch = Gem5Parser.submit_parse_async(
            str(source.parent),
            "stats.txt",
            [StatConfig("v", "scalar", params={"source_type": "scalar"})],
            str(output),
        )
        error = batch.futures[0].exception(timeout=15)
        assert type(error) is ParseDataRuntimeError and len(str(error)) <= 1024
        assert error.__cause__ is error.__context__ is None
        facts = error.__dict__["failure_facts"]
        assert isinstance(facts, ParseFailureFacts)
        assert facts.source_path == str(source)
        assert "UnicodeDecodeError" in facts.cause and "invalid start byte" in facts.cause
        assert "gem5_parse_work._run_perl_script:" in facts.origin
        assert "not valid UTF-8" in facts.cause
        assert len(facts.cause) <= 1024 and len(facts.origin) <= 2048
        _drain_workers()
        gc.collect()
        assert len(refs) == 1 and refs[0]() is None
        assert previous.read_bytes() == b"previous complete output"
        assert all(record.exc_info is None for record in caplog.records)
        for record in caplog.records:
            arguments = record.args
            assert type(arguments) is tuple
            assert all(
                type(value) in (str, int) and (type(value) is not str or len(value) <= 1024)
                for value in arguments
            )
    finally:
        pool.shutdown()


def test_invalid_utf8_startup_reaps_blocked_child_and_releases_work_while_future_is_held(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    script = tmp_path / "invalid-startup.pl"
    script.write_text(
        'use strict; use warnings; $|=1; print "\\xff" . ("x" x 200000) . "\\n";\n'
        "while (<STDIN>) { last if /^SHUTDOWN/; }\n"
    )
    real_retire = perl_worker_pool.PerlWorker._retire_generation
    processes, worker_refs = [], []

    def retire(
        self: perl_worker_pool.PerlWorker, generation: perl_worker_pool._WorkerGeneration
    ) -> None:
        processes.append((generation.process, generation.reader_thread, generation.stderr_thread))
        worker_refs.append(weakref.ref(self))
        return real_retire(self, generation)

    monkeypatch.setattr(perl_worker_pool.PerlWorker, "_retire_generation", retire)

    class Work:
        source_path = "source"

        def __call__(self) -> ParsedFileResult:
            perl_worker_pool.PerlWorker(0, str(script), "perl")
            pytest.fail("Invalid startup bytes were admitted")

    work = Work()
    work_ref = weakref.ref(work)
    wrapper = result_admission.AdmittedParseWork(
        work, result_admission.ResultAdmission(("source",))
    )
    del work
    future = WorkPool.get_instance().submit(wrapper)
    error = future.exception(timeout=15)
    assert type(error) is ParseDataRuntimeError
    assert "startup output is not valid UTF-8" in str(error)
    facts = error.__dict__["failure_facts"]
    assert isinstance(facts, ParseFailureFacts)
    assert "UnicodeDecodeError" in facts.cause
    assert "_start_worker:" in facts.origin
    assert error.__cause__ is error.__context__ is None
    _drain_workers()
    gc.collect()
    assert work_ref() is None and len(worker_refs) == 1 and worker_refs[0]() is None
    process, reader, stderr = processes[0]
    assert process.poll() is not None
    assert all(
        pipe is not None and pipe.closed for pipe in (process.stdin, process.stdout, process.stderr)
    )
    assert reader is not None and stderr is not None
    assert not reader.is_alive() and not stderr.is_alive()


@pytest.mark.parametrize(
    "mode", ["excess_observations", "malformed_config", "invalid_encoding", "metadata_collision"]
)
def test_real_expected_failure_releases_work_raw_frames_and_partial_typed_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, mode: str
) -> None:
    worker_refs, result_refs = [], []
    original_init, original_call = Gem5ParseWork.__init__, Gem5ParseWork.__call__

    def tracked_init(
        self: Gem5ParseWork,
        file_to_parse: str,
        accumulators: gem5_parse_work.VarsDictType,
        plan: SourcePlan,
    ) -> None:
        original_init(self, file_to_parse, accumulators, plan)
        worker_refs.append(weakref.ref(self))

    def tracked_call(self: Gem5ParseWork) -> ParsedFileResult:
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
    if mode == "metadata_collision":
        with (
            patch.object(
                Gem5Parser,
                "_build_work_items",
                side_effect=AssertionError("Invalid schema reached work construction"),
            ) as build_work,
            patch.object(
                WorkPool,
                "get_instance",
                side_effect=AssertionError("Invalid schema reached worker submission"),
            ) as work_pool,
            pytest.raises(ParseDataValueError) as failure,
        ):
            Gem5Parser.submit_parse_async(
                str(inputs), "stats.txt", variables, str(output), "config_aware"
            )
        assert type(failure.value) is ParseDataValueError
        assert str(failure.value) == "Duplicate planned physical column: 'sim_path'."
        build_work.assert_not_called()
        work_pool.assert_not_called()
        assert worker_refs == result_refs == []
        assert previous.read_bytes() == b"previous complete output"
        assert tuple(output.iterdir()) == (previous,)
        return
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
        expected = ParseDataRuntimeError
        assert type(error) is expected
        assert error.__cause__ is error.__context__ is None
        assert all(type(value) is str and len(value) <= 1024 for value in error.args)
        facts = error.__dict__["failure_facts"]
        assert isinstance(facts, ParseFailureFacts)
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
        arguments = record.args
        assert type(arguments) is tuple
        assert all(type(value) in (str, int, float) for value in arguments)
        assert all(len(value) <= 1024 for value in arguments if type(value) is str)
    assert previous.read_bytes() == b"previous complete output"
    with pytest.raises(ValueError, match="non-empty"):
        Gem5Parser.finalize_parsing(batch, [])
