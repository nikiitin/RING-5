"""Real numeric-pattern matching bounds and parser error propagation contracts."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.common.safe_regex import (
    MAX_INPUT_LENGTH,
    MAX_PATTERN_LENGTH,
    SafeRegexError,
    numeric_pattern_id,
)
from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork, VarsDictType
from src.parsing.gem5.types.type_mapper import TypeMapper
from src.parsing.gem5.types.vector import Vector

_HOSTILE_PATTERN = "cpu" + r"\d+" * 50
_HOSTILE_NAME = "cpu" + "1" * 1000 + "x" + "1" * 1000


@pytest.mark.parametrize("resolve", [numeric_pattern_id, Gem5ParseWork._numeric_pattern_id])
def test_numeric_capture_matching_enforces_the_real_execution_bound(
    resolve: Callable[[str, str], str | None],
) -> None:
    assert len(_HOSTILE_PATTERN) < MAX_PATTERN_LENGTH
    assert len(_HOSTILE_NAME) < MAX_INPUT_LENGTH
    with pytest.raises(SafeRegexError, match="matching exceeded 50 ms"):
        resolve(_HOSTILE_PATTERN, _HOSTILE_NAME)


def test_derived_capture_expansion_keeps_the_original_source_length_contract() -> None:
    pattern = "cpu" + (r"\d+." * 120) + "ipc"
    name = "cpu" + "1." * 120 + "ipc"
    assert len(pattern) <= MAX_PATTERN_LENGTH
    assert numeric_pattern_id(pattern, name) == "_".join(["1"] * 120)


@pytest.mark.parametrize(
    ("pattern", "name", "expected"),
    [
        (r"system.cpu\d+.cache\d+.ipc", "system.cpu012.cache3.ipc", "012_3"),
        (r"system\.cpu\d+\.ipc", "system.cpu12.ipc", "12"),
        (r"system.cpu\d+.ipc", "system.gpu12.ipc", None),
        (r"system.cpu\d+.ipc", "system.cpu١.ipc", None),
        ("system.cpu.ipc", "system.cpu.ipc", None),
    ],
)
def test_numeric_capture_matching_preserves_valid_and_unmatched_names(
    pattern: str, name: str, expected: str | None
) -> None:
    assert numeric_pattern_id(pattern, name) == expected


def test_numeric_capture_source_and_name_bounds_still_apply() -> None:
    with pytest.raises(SafeRegexError, match="between 1 and 512"):
        numeric_pattern_id("a" * (MAX_PATTERN_LENGTH + 1), "a")
    with pytest.raises(SafeRegexError, match="Stat name exceeds"):
        numeric_pattern_id(r"cpu\d+", "a" * (MAX_INPUT_LENGTH + 1))


def test_invalid_literal_lookup_keys_keep_their_nonmatching_behavior() -> None:
    assert Gem5ParseWork._numeric_pattern_id("Output label (IPC)", "cpu0") is None
    config = StatConfig("Output label (IPC)", "vector", params={"entries": ["0"]})
    assert not TypeMapper.is_scalar_pattern_vector(config, ["cpu0"])


def test_legacy_source_inference_does_not_hide_a_capture_timeout() -> None:
    config = StatConfig(_HOSTILE_PATTERN, "vector", params={"entries": ["0"]})
    with pytest.raises(SafeRegexError, match="matching exceeded 50 ms"):
        TypeMapper.is_scalar_pattern_vector(config, [_HOSTILE_NAME])


def test_async_worker_exposes_capture_timeout_before_perl_submission(tmp_path: Path) -> None:
    source = tmp_path / "stats.txt"
    source.write_text("simTicks 1\n", encoding="utf-8")
    vector = Vector(entries=["0"])
    work = Gem5ParseWork(str(source), {_HOSTILE_PATTERN: vector, _HOSTILE_NAME: vector})
    with patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool") as pool:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(work)
            with pytest.raises(SafeRegexError, match="matching exceeded 50 ms"):
                future.result(timeout=5)
        pool.assert_not_called()
    assert vector.content == {"0": []}


def test_scalar_alias_processing_exposes_capture_timeout_before_balancing() -> None:
    vector = Vector(entries=["0"])
    variables: VarsDictType = {_HOSTILE_PATTERN: vector, _HOSTILE_NAME: vector}
    work = Gem5ParseWork("unused", variables)
    with pytest.raises(SafeRegexError, match="matching exceeded 50 ms"):
        work._processOutput(f"scalar/{_HOSTILE_NAME}/1\n", variables)
    assert vector.content == {"0": []}
