"""Public global shutdown drains file work before closing backend processes."""

from __future__ import annotations

import csv
import threading
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import ring5
from ring5.errors import JobError
from src.core.models import StatConfig
from src.parsing.framework.work_pool import WorkPool
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.strategies.perl_worker_pool import get_worker_pool

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("perl_pool")]


def test_global_shutdown_closes_perl_only_after_accepted_work_settles() -> None:
    # [test->req~ring5.api.process-lifecycle~1]
    ring5.shutdown()
    pool = WorkPool.get_instance()
    started = threading.Event()
    release = threading.Event()
    draining = threading.Event()
    perl_closed = threading.Event()
    errors: list[Exception] = []

    def work() -> int:
        started.set()
        assert release.wait(5)
        return 7

    def close() -> None:
        try:
            ring5.shutdown()
        except Exception as error:
            errors.append(error)

    original_drain = pool._drain_executor

    def drain(executor: Any) -> None:
        draining.set()
        original_drain(executor)

    future = pool.submit(work)
    closer = threading.Thread(target=close)
    try:
        assert started.wait(3)
        with (
            patch.object(pool, "_drain_executor", side_effect=drain),
            patch(
                "src.parsing.gem5.impl.strategies.perl_worker_pool.shutdown_worker_pool",
                side_effect=perl_closed.set,
            ),
        ):
            closer.start()
            assert draining.wait(3)
            assert not perl_closed.is_set()
            assert closer.is_alive()
            release.set()
            closer.join(3)
        assert not closer.is_alive()
        assert not errors
        assert future.result(timeout=3) == 7
        assert perl_closed.is_set()
    finally:
        release.set()
        if closer.ident is not None:
            closer.join(3)
        ring5.shutdown()


def test_global_shutdown_failure_is_typed_and_keeps_dependencies_open() -> None:
    # [test->req~ring5.api.typed-errors~1]
    ring5.shutdown()
    pool = WorkPool.get_instance()
    try:
        with patch(
            "src.parsing.gem5.impl.strategies.perl_worker_pool.shutdown_worker_pool"
        ) as close_perl:
            future = pool.submit(ring5.shutdown)
            with pytest.raises(JobError, match="own shutdown"):
                future.result(timeout=3)
            close_perl.assert_not_called()
        assert pool.submit(lambda: "usable").result(timeout=3) == "usable"
    finally:
        ring5.shutdown()


def test_real_parse_survives_global_shutdown_and_recreates_both_pools(tmp_path: Path) -> None:
    # [test->req~ring5.api.process-lifecycle~1]
    ring5.shutdown()
    stats = tmp_path / "stats.txt"
    previous_executor = None
    previous_perl = None
    try:
        for value in [3, 5]:
            stats.write_text(f"ipc {value}\n", encoding="utf-8")
            batch = Gem5Parser.submit_parse_async(
                str(tmp_path),
                "stats.txt",
                [StatConfig("ipc", "scalar")],
                str(tmp_path / str(value)),
            )
            executor = WorkPool.get_instance()._thread_executor
            perl = get_worker_pool()
            if previous_executor is not None:
                assert executor is not previous_executor
                assert perl is not previous_perl
            ring5.shutdown()
            assert all(future.done() for future in batch.futures)
            results = [future.result(timeout=3) for future in batch.futures]
            output = Gem5Parser.finalize_parsing(
                str(tmp_path / str(value)), results, var_names=batch.var_names
            )
            assert output is not None
            with Path(output).open(encoding="utf-8", newline="") as stream:
                assert next(csv.DictReader(stream))["ipc"] == f"{value}.0"
            previous_executor, previous_perl = executor, perl
    finally:
        ring5.shutdown()
