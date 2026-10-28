"""Worker failures and exact concrete-source filters retain their owned provenance."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.models.parsed_output_models import ParsedCell
from src.core.models.parse_failure_models import ParseDataRuntimeError, ParseDataValueError
from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork
from src.parsing.gem5.types.type_mapper import TypeMapper


def _work(path: Path) -> Gem5ParseWork:
    plan = resolve_sources(
        [
            StatConfig(
                "result", "scalar", source_name="system.cpu0.ipc", params={"source_type": "scalar"}
            )
        ],
        [],
        file_count=1,
        metadata_columns=(),
    )
    return Gem5ParseWork(str(path), {"result": TypeMapper.create_stat(plan.accumulators[0])}, plan)


def test_source_path_and_text_are_exact(tmp_path: Path) -> None:
    work = _work(tmp_path / "stats.txt")
    assert work.source_path == str(tmp_path / "stats.txt")
    assert str(work) == f"Gem5ParseWork({tmp_path / 'stats.txt'})"


def test_missing_input_rejects_before_pool(tmp_path: Path) -> None:
    with patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool") as pool:
        with pytest.raises(FileNotFoundError):
            _work(tmp_path / "missing")._run_perl_script()
        pool.assert_not_called()


@pytest.mark.parametrize(
    "exception, message, wrapped",
    [
        (TimeoutError("slow"), "Parser timeout", True),
        (OSError("I/O"), "Worker pool parse failed", True),
        (ParseDataRuntimeError("failed source"), "Worker pool parse failed", True),
        (ParseDataValueError("invalid source"), "Worker pool parse failed", True),
        (RuntimeError("failed"), "failed", False),
        (ValueError("invalid"), "invalid", False),
    ],
)
def test_worker_errors_preserve_original_cause(
    tmp_path: Path, exception: Exception, message: str, wrapped: bool
) -> None:
    path = tmp_path / "stats.txt"
    path.write_text("system.cpu0.ipc 3\n", encoding="utf-8")
    with patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool") as pool:
        pool.return_value.parse_file.side_effect = exception
        expected = ParseDataRuntimeError if wrapped else type(exception)
        with pytest.raises(expected, match=message) as caught:
            _work(path)()
        if wrapped:
            assert caught.value.__cause__ is exception
        else:
            assert caught.value is exception
            assert caught.value.__cause__ is None


def test_pool_receives_literal_concrete_source_filters_and_result_provenance(
    tmp_path: Path,
) -> None:
    path = tmp_path / "stats.txt"
    path.write_text("system.cpu0.ipc 3\n", encoding="utf-8")
    with patch("src.parsing.gem5.impl.strategies.gem5_parse_work.get_worker_pool") as pool:
        pool.return_value.parse_file.return_value = [
            (
                '{"event":"measurement","name":"system.cpu0.ipc","shape":"sca'
                'lar","entry":null,"value":"3"}\n{"event":"source","name":"sys'
                'tem.cpu0.ipc","source_evidence":{"state":"resolved","kind":"'
                'scalar","basis":"wire_contract"},"entries":[]}'
            )
        ]
        work = _work(path)
        result = work()
        pool.return_value.parse_file.assert_called_once_with(
            str(path), [r"system\.cpu0\.ipc"], timeout=120.0
        )
    assert result.source_path == str(path)
    assert tuple(variable.name for variable in result.variables) == ("result",)
    variable = result.variables[0]
    assert variable.kind == "number" and variable.shape == "scalar"
    assert variable.cells == (ParsedCell("result", "number", 3.0),)
    assert variable.missing_measurements == 0
    assert work._accumulators["result"].is_balanced
    assert work._accumulators["result"].is_reduced
