from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import StatConfig
from src.parsing.gem5.impl.strategies.config_aware import ConfigAwareStrategy
from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy


@pytest.fixture
def mock_variables() -> list[StatConfig]:
    return [
        StatConfig(name="sim_seconds", type="scalar"),
        StatConfig(name="system.cpu.dcache.overall_misses", type="scalar"),
    ]


class TestSimpleStatsStrategy:

    @patch("src.parsing.gem5.impl.strategies.simple.os.path.getsize", return_value=10)
    @patch("src.parsing.gem5.impl.strategies.simple.find_stats_files")
    # [test->req~ring5.ingestion.simple-strategy~1]
    def test_get_work_items_one_per_file(
        self, mock_find: MagicMock, _mock_size: MagicMock, mock_variables: list[StatConfig]
    ) -> None:
        # The strategy discovers files and builds one ParseWork unit per file;
        # the worker pool that runs them is owned by Gem5Parser, not the strategy.
        from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork

        mock_find.return_value = ["/fake/path/1/stats.txt", "/fake/path/2/stats.txt"]

        strategy = SimpleStatsStrategy()

        work_items = list(strategy.get_work_items("/fake/path", "stats.txt", mock_variables))

        assert len(work_items) == 2
        assert all(isinstance(w, Gem5ParseWork) for w in work_items)

    def test_variable_mapping_logic(self) -> None:
        strategy = SimpleStatsStrategy()
        vars = [StatConfig(name="foo", type="scalar")]

        # This is internal logic but crucial to verify before submission
        var_map = strategy._map_variables(vars)
        assert "foo" in var_map
        # The result is now a StatType object (Scalar), not a dict or StatConfig
        # We need to verify it is the correct type of object
        assert var_map["foo"].__class__.__name__ == "Scalar"
        assert var_map["foo"].repeat == 1

    def _ids(self, name: str, n: int) -> StatConfig:
        return StatConfig(
            name=name, type="scalar", params={"parsed_ids": [f"{name}{i}" for i in range(n)]}
        )

    def test_repeat_cap_rejects_huge_pattern_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A regex var expanding past the cap fails visibly before allocation."""
        monkeypatch.delenv("RING5_MAX_VAR_REPEAT", raising=False)  # default cap = 1024
        strategy = SimpleStatsStrategy()
        with pytest.raises(RuntimeError, match="expands to 2704"):
            strategy._map_variables(
                [self._ids("normal.cpu", 64), self._ids("monster.matrix", 2704)]
            )

    def test_repeat_cap_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RING5_MAX_VAR_REPEAT tightens the cap; 0 disables it entirely."""
        strategy = SimpleStatsStrategy()

        monkeypatch.setenv("RING5_MAX_VAR_REPEAT", "100")
        with pytest.raises(RuntimeError, match="cap of 100"):
            strategy._map_variables([self._ids("v", 64), self._ids("big", 2704)])

        monkeypatch.setenv("RING5_MAX_VAR_REPEAT", "0")  # aggregate limit still applies
        var_map = strategy._map_variables([self._ids("big", 1500)])
        assert "big" in var_map and var_map["big"].repeat == 1500
        with pytest.raises(RuntimeError, match="logical variables and aliases"):
            strategy._map_variables([self._ids("too_big", 2704)])

    def test_duplicate_aliases_are_deduplicated_before_repeat_count(self) -> None:
        strategy = SimpleStatsStrategy()
        config = StatConfig(
            name="pattern",
            type="scalar",
            params={"parsed_ids": ["cpu0", "cpu0", "cpu1"]},
        )

        var_map = strategy._map_variables([config])

        assert var_map["pattern"].repeat == 2
        assert set(var_map) == {"pattern", "cpu0", "cpu1"}

    def test_alias_collision_is_rejected(self) -> None:
        strategy = SimpleStatsStrategy()

        with pytest.raises(RuntimeError, match="Duplicate variable or alias"):
            strategy._map_variables(
                [
                    StatConfig(name="cpu0", type="scalar"),
                    StatConfig(
                        name="pattern",
                        type="scalar",
                        params={"parsed_ids": ["cpu0"]},
                    ),
                ]
            )

    @patch("src.parsing.gem5.impl.strategies.simple.find_stats_files")
    def test_file_count_limit_fails_before_submission(
        self, mock_find: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.strategies.simple.MAX_PARSE_FILES", 1)
        mock_find.return_value = ["one/stats.txt", "two/stats.txt"]

        with pytest.raises(RuntimeError, match="2 files exceed"):
            SimpleStatsStrategy()._get_files(".", "stats.txt")

    @patch("src.parsing.gem5.impl.strategies.simple.os.path.getsize", return_value=11)
    @patch("src.parsing.gem5.impl.strategies.simple.find_stats_files")
    def test_per_file_byte_limit_fails_before_submission(
        self, mock_find: MagicMock, _mock_size: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.strategies.simple.MAX_PARSE_FILE_BYTES", 10)
        mock_find.return_value = ["one/stats.txt"]

        with pytest.raises(RuntimeError, match="per-file limit"):
            SimpleStatsStrategy()._get_files(".", "stats.txt")

    @patch("src.parsing.gem5.impl.strategies.simple.os.path.getsize", return_value=10)
    @patch("src.parsing.gem5.impl.strategies.simple.find_stats_files")
    def test_aggregate_byte_limit_fails_before_submission(
        self, mock_find: MagicMock, _mock_size: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("src.parsing.gem5.impl.strategies.simple.MAX_PARSE_TOTAL_BYTES", 15)
        mock_find.return_value = ["one/stats.txt", "two/stats.txt"]

        with pytest.raises(RuntimeError, match="aggregate limit"):
            SimpleStatsStrategy()._get_files(".", "stats.txt")

    def test_file_variable_matrix_limit_fails_before_submission(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        strategy = SimpleStatsStrategy()
        monkeypatch.setattr(strategy, "_get_files", lambda *_args: ["one", "two"])
        monkeypatch.setattr("src.parsing.gem5.impl.strategies.simple.MAX_PARSE_MATRIX_CELLS", 1)

        with pytest.raises(RuntimeError, match="2 file-variable cells"):
            strategy.get_work_items(".", "stats.txt", [StatConfig(name="v", type="scalar")])

    def test_variable_and_alias_limit_fails_before_submission(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        strategy = SimpleStatsStrategy()
        monkeypatch.setattr(strategy, "_get_files", lambda *_args: ["one"])
        monkeypatch.setattr("src.parsing.gem5.impl.strategies.simple.MAX_PARSE_VARIABLES", 1)

        with pytest.raises(RuntimeError, match="2 logical variables and aliases"):
            strategy.get_work_items(".", "stats.txt", [self._ids("v", 1)])


class TestConfigAwareStrategy:

    # [test->req~ring5.ingestion.config-aware-strategy~1]
    def test_augment_results(self, tmp_path: Path) -> None:
        from src.parsing.gem5.impl.strategies.file_parser_strategy import (
            INTERNAL_SIM_PATH_KEY,
        )

        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("dummy")
        (tmp_path / "config.ini").write_text("[system]\ncores = 4\n")
        raw_results = [{INTERNAL_SIM_PATH_KEY: str(stats_path), "ipc": 1.5}]

        strategy = ConfigAwareStrategy()
        results = strategy.post_process(raw_results)

        assert len(results) == 1
        assert results[0]["ipc"] == 1.5
        assert results[0]["sim_path"] == str(stats_path)
        assert results[0]["config_json"] == '{"system":{"cores":"4"}}'
