from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.impl.source_bindings import resolve_sources
from src.parsing.gem5.impl.gem5_parser import Gem5Parser
from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy


@pytest.fixture
def mock_variables() -> list[StatConfig]:
    return [
        StatConfig(name="sim_seconds", type="scalar", params={"source_type": "scalar"}),
        StatConfig(
            name="system.cpu.dcache.overall_misses", type="scalar", params={"source_type": "scalar"}
        ),
    ]


class TestSimpleStatsStrategy:

    @patch("src.parsing.gem5.impl.gem5_parser.os.path.getsize", return_value=10)
    @patch("src.parsing.gem5.impl.gem5_parser.find_stats_files")
    # [test->req~ring5.ingestion.simple-strategy~1]
    def test_get_work_items_one_per_file(
        self, mock_find: MagicMock, _mock_size: MagicMock, mock_variables: list[StatConfig]
    ) -> None:
        # The parser supplies selected sources; the strategy builds one callable per source;
        # the worker pool that runs them is owned by Gem5Parser, not the strategy.
        from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork

        mock_find.return_value = ["/fake/path/1/stats.txt", "/fake/path/2/stats.txt"]

        strategy = SimpleStatsStrategy()

        work_items = list(
            strategy.get_work_items(
                tuple(mock_find.return_value),
                resolve_sources(mock_variables, [], file_count=2, metadata_columns=()),
            )
        )

        assert len(work_items) == 2
        assert all(isinstance(w, Gem5ParseWork) for w in work_items)

    def test_variable_mapping_logic(self) -> None:
        strategy = SimpleStatsStrategy()
        vars = [StatConfig(name="foo", type="scalar", params={"source_type": "scalar"})]

        # This is internal logic but crucial to verify before submission
        var_map = strategy._map_variables(
            resolve_sources(vars, [], file_count=1, metadata_columns=()).accumulators
        )
        assert "foo" in var_map
        # The result is now a StatType object (Scalar), not a dict or StatConfig
        # We need to verify it is the correct type of object
        assert var_map["foo"].__class__.__name__ == "Scalar"
        assert var_map["foo"].repeat == 1

    def test_multiple_aliases_have_no_shared_mutable_accumulator(self) -> None:
        configs = [
            StatConfig(name, "scalar", source_name="cpu0", params={"source_type": "scalar"})
            for name in ("first", "second")
        ]
        plan = resolve_sources(configs, [], file_count=1, metadata_columns=())
        values = SimpleStatsStrategy()._map_variables(plan.accumulators)
        assert set(values) == {"first", "second"}
        assert values["first"] is not values["second"]
        assert [
            (target.output_name, target.entry_name) for target in plan.routes["cpu0"].targets
        ] == [
            ("first", None),
            ("second", None),
        ]

    @patch("src.parsing.gem5.impl.gem5_parser.find_stats_files")
    def test_file_count_limit_fails_before_submission(
        self, mock_find: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.gem5_parser.MAX_PARSE_FILES", 1)
        mock_find.return_value = ["one/stats.txt", "two/stats.txt"]

        with pytest.raises(RuntimeError, match="2 files exceed"):
            Gem5Parser._select_files(".", "stats.txt")

    @patch("src.parsing.gem5.impl.gem5_parser.os.path.getsize", return_value=11)
    @patch("src.parsing.gem5.impl.gem5_parser.find_stats_files")
    def test_per_file_byte_limit_fails_before_submission(
        self, mock_find: MagicMock, _mock_size: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.gem5_parser.MAX_PARSE_FILE_BYTES", 10)
        mock_find.return_value = ["one/stats.txt"]

        with pytest.raises(RuntimeError, match="per-file byte limit"):
            Gem5Parser._select_files(".", "stats.txt")

    @patch("src.parsing.gem5.impl.gem5_parser.os.path.getsize", return_value=10)
    @patch("src.parsing.gem5.impl.gem5_parser.find_stats_files")
    def test_aggregate_byte_limit_fails_before_submission(
        self, mock_find: MagicMock, _mock_size: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.gem5_parser.MAX_PARSE_TOTAL_BYTES", 15)
        mock_find.return_value = ["one/stats.txt", "two/stats.txt"]

        with pytest.raises(RuntimeError, match="aggregate byte limit"):
            Gem5Parser._select_files(".", "stats.txt")

    def test_file_variable_matrix_limit_fails_before_submission(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.source_bindings.MAX_PARSE_MATRIX_CELLS", 1)
        with pytest.raises(ValueError, match="source-binding workload"):
            resolve_sources(
                [StatConfig(name="v", type="scalar", params={"source_type": "scalar"})],
                [],
                file_count=2,
                metadata_columns=(),
            )

    def test_source_binding_limit_rejects_before_strategy_allocation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.source_bindings.MAX_PARSE_VARIABLES", 1)
        with pytest.raises(RuntimeError, match="2 source bindings"):
            resolve_sources(
                [
                    StatConfig(name, "scalar", params={"source_type": "scalar"})
                    for name in ("first", "second")
                ],
                [],
                file_count=1,
                metadata_columns=(),
            )


class TestConfigAwareStrategy:

    # [test->req~ring5.ingestion.config-aware-strategy~1]
    def test_augment_results(self, tmp_path: Path) -> None:
        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("ipc 1.5\n", encoding="utf-8")
        (tmp_path / "config.ini").write_text("[system]\ncores = 4\n", encoding="utf-8")
        batch = Gem5Parser.submit_parse_async(
            str(tmp_path),
            "stats.txt",
            [StatConfig("ipc", "scalar", params={"source_type": "scalar"})],
            str(tmp_path / "output"),
            strategy_type="config_aware",
        )
        results = [future.result(timeout=10) for future in batch.futures]

        assert len(results) == 1
        assert results[0].variables[0].cells[0].value == 1.5
        assert results[0].source_path == str(stats_path)
        assert results[0].metadata[0].column == "sim_path"
        assert results[0].metadata[0].value == str(stats_path)
        assert results[0].metadata[1].column == "config_json"
        assert results[0].metadata[1].value == '{"system":{"cores":"4"}}'
