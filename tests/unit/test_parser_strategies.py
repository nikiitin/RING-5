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

    @patch("src.parsing.gem5.impl.strategies.simple.normalize_user_path")
    def test_get_work_items_one_per_file(
        self, mock_normalize: MagicMock, mock_variables: list[StatConfig]
    ) -> None:
        # The strategy discovers files and builds one ParseWork unit per file;
        # the worker pool that runs them is owned by Gem5Parser, not the strategy.
        from src.parsing.gem5.impl.strategies.gem5_parse_work import Gem5ParseWork

        mock_path_obj = MagicMock()
        mock_normalize.return_value = mock_path_obj
        mock_path_obj.glob.return_value = ["/fake/path/1/stats.txt", "/fake/path/2/stats.txt"]

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


class TestConfigAwareStrategy:

    def test_augment_results(self) -> None:
        # Arrange
        raw_results = [{"sim_path": "/data/run1/stats.txt", "ipc": 1.5}]

        strategy = ConfigAwareStrategy()

        # Act
        with patch.object(strategy, "_parse_config") as mock_parse_config:
            with patch("src.parsing.gem5.impl.strategies.config_aware.Path") as mock_path_cls:
                mock_config_path = MagicMock()
                mock_config_path.exists.return_value = True
                mock_path_cls.return_value.parent.__truediv__.return_value = mock_config_path

                mock_parse_config.return_value = {"system": {"cores": "4"}}

                results = strategy.post_process(raw_results)

                # Assert
                assert len(results) == 1
                assert results[0]["ipc"] == 1.5
                assert results[0]["config"]["system"]["cores"] == "4"
