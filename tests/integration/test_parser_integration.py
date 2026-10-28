"""A real vector crosses UI compilation, worker finalization and typed loading."""

from pathlib import Path

from src.core.application_api import ApplicationAPI
from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.data_models import ParseVariableConfig


def test_parser_integration(tmp_path: Path) -> None:
    variables: list[ParseVariableConfig] = [
        {
            "name": "test_vector",
            "type": "vector",
            "params": {"source_type": "vector", "entries": ["entry1", "entry2"]},
        }
    ]
    stats_dir = tmp_path / "stats"
    stats_dir.mkdir()
    (stats_dir / "stats.txt").write_text(
        "test_vector::entry1 100\ntest_vector::entry2 200\n", encoding="utf-8"
    )
    output_dir = tmp_path / "output"
    facade = ApplicationAPI()
    try:
        batch = facade.submit_parse_async(
            stats_path=str(stats_dir),
            stats_pattern="stats.txt",
            variables=facade.compile_parse_variables(variables),
            output_dir=str(output_dir),
        )
        output = facade.finalize_parsing(
            batch, [future.result(timeout=10) for future in batch.futures]
        )
        assert Path(output.csv_path).is_file()
        assert ParsedOutputIO.to_frame(output).to_dict("list") == {
            "test_vector..entry1": [100.0],
            "test_vector..entry2": [200.0],
        }
    finally:
        facade.close(wait=True)
