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

    @patch("src.parsing.gem5.impl.strategies.simple.find_stats_files")
    def test_get_work_items_one_per_file(
        self, mock_find: MagicMock, mock_variables: list[StatConfig]
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

    def test_repeat_cap_skips_huge_pattern_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A regex var expanding past the cap is skipped (not OOM-parsed)."""
        monkeypatch.delenv("RING5_MAX_VAR_REPEAT", raising=False)  # default cap = 1024
        strategy = SimpleStatsStrategy()
        var_map = strategy._map_variables(
            [self._ids("normal.cpu", 64), self._ids("monster.matrix", 2704)]
        )
        # normal var (+ its aliases) stays; monster var and its aliases are dropped
        assert "normal.cpu" in var_map and var_map["normal.cpu"].repeat == 64
        assert not any(k.startswith("monster.matrix") for k in var_map)

    def test_repeat_cap_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """RING5_MAX_VAR_REPEAT tightens the cap; 0 disables it entirely."""
        strategy = SimpleStatsStrategy()

        monkeypatch.setenv("RING5_MAX_VAR_REPEAT", "100")
        var_map = strategy._map_variables([self._ids("v", 64), self._ids("big", 2704)])
        assert "v" in var_map and "big" not in var_map  # 64 <= 100 < 2704

        monkeypatch.setenv("RING5_MAX_VAR_REPEAT", "0")  # 0 == unlimited
        var_map = strategy._map_variables([self._ids("big", 2704)])
        assert "big" in var_map and var_map["big"].repeat == 2704


class TestConfigAwareStrategy:

    def test_augment_results(self) -> None:
        raw_results = [{"sim_path": "/data/run1/stats.txt", "ipc": 1.5}]

        strategy = ConfigAwareStrategy()

        with patch.object(strategy, "_parse_config") as mock_parse_config:
            with patch("src.parsing.gem5.impl.strategies.config_aware.Path") as mock_path_cls:
                mock_config_path = MagicMock()
                mock_config_path.exists.return_value = True
                mock_path_cls.return_value.parent.__truediv__.return_value = mock_config_path

                mock_parse_config.return_value = {"system": {"cores": "4"}}

                results = strategy.post_process(raw_results)

                assert len(results) == 1
                assert results[0]["ipc"] == 1.5
                assert results[0]["config"]["system"]["cores"] == "4"
