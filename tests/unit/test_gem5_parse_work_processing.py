"""Worker pool errors and exact source-filter submission remain visible."""

from unittest.mock import patch

import pytest

from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.strategies.file_parser_strategy import INTERNAL_SIM_PATH_KEY
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.types.type_mapper import TypeMapper


def _work(path):
    plan = resolve_sources(
        [
            StatConfig(
                "result", "scalar", source_name="system.cpu0.ipc", params={"source_type": "scalar"}
            )
        ],
        [],
    )
    return Gem5ParseWork(str(path), {"result": TypeMapper.create_stat(plan.accumulators[0])}, plan)


def test_source_path_and_text_are_exact(tmp_path):
    work = _work(tmp_path / "stats.txt")
    assert work.source_path == str(tmp_path / "stats.txt")
    assert str(work) == f"Gem5ParseWork({tmp_path / 'stats.txt'})"


def test_missing_input_rejects_before_pool(tmp_path):
    with patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool") as pool:
        with pytest.raises(FileNotFoundError):
            _work(tmp_path / "missing")._run_perl_script()
        pool.assert_not_called()


@pytest.mark.parametrize(
    "exception, message",
    [
        (TimeoutError("slow"), "Parser timeout"),
        (OSError("I/O"), "Worker pool parse failed"),
        (RuntimeError("failed"), "Worker pool parse failed"),
        (ValueError("invalid"), "Worker pool parse failed"),
    ],
)
def test_worker_errors_preserve_original_cause(tmp_path, exception, message):
    path = tmp_path / "stats.txt"
    path.write_text("system.cpu0.ipc 3\n")
    with patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool") as pool:
        pool.return_value.parse_file.side_effect = exception
        with pytest.raises(RuntimeError, match=message) as caught:
            _work(path)()
        assert caught.value.__cause__ is exception


def test_pool_receives_literal_concrete_source_filters_and_result_provenance(tmp_path):
    path = tmp_path / "stats.txt"
    path.write_text("system.cpu0.ipc 3\n")
    with patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool") as pool:
        pool.return_value.parse_file.return_value = ["scalar/system.cpu0.ipc/3"]
        result = _work(path)()
        pool.return_value.parse_file.assert_called_once_with(
            str(path), [r"system\.cpu0\.ipc"], timeout=120.0
        )
    assert set(result) == {"result", INTERNAL_SIM_PATH_KEY}
    assert result["result"].content == [3.0]
    assert result[INTERNAL_SIM_PATH_KEY] == str(path)
