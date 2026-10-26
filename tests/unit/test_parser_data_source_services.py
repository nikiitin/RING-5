"""Tests for parser, pattern-index, work-pool, and data-source services."""

import configparser
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from src.core.common.parsed_output import ParsedOutputIO
from src.core.models.parsed_output_models import ParsedCell, ParsedFileResult, ParsedVariableResult
from src.core.models.parsing_models import ParseBatchResult
from src.parsing.gem5.impl.strategies.config_aware import ConfigAwareParseWork
from tests.helpers.parsed_values import completed_future, numeric_file


@dataclass(frozen=True)
class _TypedWork:
    source_path: str
    result: ParsedFileResult

    def __call__(self) -> ParsedFileResult:
        return self.result


# Scanned-variable serialization


# Strategy creation


class TestStrategyFactory:
    """Tests for strategy selection and invalid names."""

    def test_create_simple(self) -> None:
        from src.parsing.gem5.impl.strategies.factory import StrategyFactory

        strategy = StrategyFactory.create("simple")
        assert strategy is not None
        assert strategy.__class__.__name__ == "SimpleStatsStrategy"

    def test_create_config_aware(self) -> None:
        from src.parsing.gem5.impl.strategies.factory import StrategyFactory

        strategy = StrategyFactory.create("config_aware")
        assert strategy is not None
        assert strategy.__class__.__name__ == "ConfigAwareStrategy"

    def test_create_unknown_raises(self) -> None:
        from src.parsing.gem5.impl.strategies.factory import StrategyFactory

        with pytest.raises(ValueError, match="Unknown strategy type"):
            StrategyFactory.create("nonexistent")


# Configuration-aware parsing


class TestConfigAwareStrategy:
    """Configuration metadata is resolved by the source-owned typed worker."""

    def test_work_rejects_mismatched_source_provenance(self) -> None:
        value = numeric_file("other-source", {"data": 123.0})
        with pytest.raises(ValueError, match="invalid source provenance"):
            ConfigAwareParseWork(_TypedWork("planned-source", value))()

    def test_work_config_found(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text("[system]\ncpu_type = O3CPU\nnum_cpus = 4\n", encoding="utf-8")
        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("dummy", encoding="utf-8")
        value = numeric_file(str(stats_path), {"data": 123.0})
        result = ConfigAwareParseWork(_TypedWork(str(stats_path), value))()
        metadata = {cell.column: cell.value for cell in result.metadata}
        assert len(result.variables) == 1
        assert metadata["sim_path"] == str(stats_path)
        assert '"cpu_type":"O3CPU"' in str(metadata["config_json"])

    def test_work_config_not_found(self, tmp_path: Path) -> None:
        stats_path = tmp_path / "stats.txt"
        stats_path.write_text("dummy", encoding="utf-8")
        value = numeric_file(str(stats_path), {"data": 123.0})
        with pytest.raises(FileNotFoundError, match="config.ini not found"):
            ConfigAwareParseWork(_TypedWork(str(stats_path), value))()

    def test_parse_config_error_handling(self, tmp_path: Path) -> None:
        """A valid configuration retains its exact section and option values."""
        config_path = tmp_path / "config.ini"
        config_path.write_text("[section1]\nkey1 = value1\n", encoding="utf-8")
        result = json.loads(ConfigAwareParseWork._read_config(config_path))
        assert isinstance(result, dict)
        assert "section1" in result
        assert result["section1"]["key1"] == "value1"

    def test_parse_config_unreadable(self, tmp_path: Path) -> None:
        """An empty configuration is rejected rather than silently emitted."""
        config_path = tmp_path / "bad_config.ini"
        config_path.write_text("", encoding="utf-8")
        with pytest.raises(RuntimeError, match="contains no sections"):
            ConfigAwareParseWork._read_config(config_path)


class TestParseServiceFinalize:
    """Finalization validates its complete plan before canonical CSV publication."""

    def test_finalize_parsing_no_results(self, tmp_path: Path) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        value = numeric_file("source", {"x": 1.0})
        batch = ParseBatchResult(
            (completed_future(value),), ("x",), ("source",), str(tmp_path), "simple"
        )
        with pytest.raises(ValueError, match="non-empty file result"):
            Gem5Parser.finalize_parsing(batch, [])
        assert not (tmp_path / "results.csv").exists()

    @patch("src.parsing.gem5.impl.gem5_parser.StrategyFactory")
    def test_finalize_parsing_validates_strategy(
        self, mock_factory: MagicMock, tmp_path: Path
    ) -> None:
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        value = numeric_file("source", {"x": 1.0})
        batch = ParseBatchResult(
            (completed_future(value),), ("x",), ("source",), str(tmp_path), "config_aware"
        )
        output = Gem5Parser.finalize_parsing(batch, [value])
        mock_factory.create.assert_called_once_with("config_aware")
        assert ParsedOutputIO.to_frame(output).to_dict("records") == [{"x": 1.0}]

    def test_typed_csv_empty_rejects_before_publication(self, tmp_path: Path) -> None:
        output = tmp_path / "results.csv"
        with pytest.raises(ValueError, match="non-empty file result"):
            ParsedOutputIO.publish(output, ParsedOutputIO.resolve([], [], ("source",)))
        assert not output.exists()

    def test_typed_csv_with_data(self, tmp_path: Path) -> None:
        value = ParsedFileResult(
            "source",
            (
                ParsedVariableResult(
                    "varA",
                    "number",
                    "entries",
                    (ParsedCell("varA..e0", "number", 1.0), ParsedCell("varA..e1", "number", 2.5)),
                ),
            ),
        )
        output = ParsedOutputIO.publish(
            tmp_path / "results.csv", ParsedOutputIO.resolve([value], ["varA"], ("source",))
        )
        csv_path = Path(output.csv_path)
        assert csv_path.is_file()
        content = csv_path.read_text(encoding="utf-8")
        assert "varA..e0" in content
        assert "varA..e1" in content
        assert "1.0" in content

    def test_typed_csv_scalar_no_entries(self, tmp_path: Path) -> None:
        value = numeric_file("source", {"scalarVar": 42.0})
        output = ParsedOutputIO.publish(
            tmp_path / "results.csv", ParsedOutputIO.resolve([value], ["scalarVar"], ("source",))
        )
        assert Path(output.csv_path).is_file()
        content = Path(output.csv_path).read_text(encoding="utf-8")
        assert "scalarVar" in content
        assert "42" in content

    def test_typed_csv_missing_numeric_measurement(self, tmp_path: Path) -> None:
        value = numeric_file("source", {"a": 10.0, "missing_var": math.nan})
        output = ParsedOutputIO.publish(
            tmp_path / "results.csv",
            ParsedOutputIO.resolve([value], ["a", "missing_var"], ("source",)),
        )
        assert Path(output.csv_path).is_file()
        content = Path(output.csv_path).read_text(encoding="utf-8")
        assert "NaN" in content

    def test_typed_csv_literal_configuration(self, tmp_path: Path) -> None:
        value = ParsedFileResult(
            "source",
            (
                ParsedVariableResult(
                    "configVar", "text", "scalar", (ParsedCell("configVar", "text", "benchmark_x"),)
                ),
            ),
        )
        output = ParsedOutputIO.publish(
            tmp_path / "results.csv", ParsedOutputIO.resolve([value], ["configVar"], ("source",))
        )
        assert Path(output.csv_path).is_file()
        content = Path(output.csv_path).read_text(encoding="utf-8")
        assert "benchmark_x" in content
        with pytest.raises(TypeError, match="ParsedFileResult"):
            ParsedOutputIO.resolve(
                [{"configVar": "benchmark_x"}],  # type: ignore[list-item]
                ["configVar"],
                ("source",),
            )


# Pattern-index selection


# Data-source components


class TestDataSourceComponents:
    """Tests for recent CSV controls and parse dialogs."""

    @patch("src.web.components.data_source.data_source_components.st")
    def test_render_csv_pool_empty(self, mock_st: MagicMock) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = []
        api.data_services.load_csv_pool.return_value = []

        DataSourceComponents.render_csv_pool(api)
        mock_st.warning.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_with_files(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, False, False)

        DataSourceComponents.render_csv_pool(api)
        mock_st.info.assert_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_file_not_exists(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [
            {"path": "/nonexistent/file.csv", "name": "file.csv"}
        ]
        mock_card.file_info_card.return_value = (False, False, False)

        DataSourceComponents.render_csv_pool(api)
        api.state_manager.set_csv_pool.assert_called_once_with([])
        mock_card.file_info_card.assert_not_called()
        mock_st.warning.assert_called_once()
        mock_st.error.assert_not_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_load_clicked(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (True, False, False)  # load_clicked=True
        mock_st.session_state = {}

        with patch.object(DataSourceComponents, "render_import_preview") as render_preview:
            DataSourceComponents.render_csv_pool(api)

        render_preview.assert_called_once_with(api, str(csv_file))
        api.data_services.load_csv_file.assert_not_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_load_exception(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (True, False, False)
        mock_st.session_state = {}

        with patch.object(DataSourceComponents, "render_import_preview") as render_preview:
            DataSourceComponents.render_csv_pool(api)

        render_preview.assert_called_once_with(api, str(csv_file))
        api.data_services.load_csv_file.assert_not_called()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_preview_clicked(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, True, False)  # preview_clicked
        mock_st.session_state = {}

        with patch.object(DataSourceComponents, "render_import_preview") as render_preview:
            DataSourceComponents.render_csv_pool(api)

        render_preview.assert_called_once_with(api, str(csv_file))

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_delete_clicked(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, False, True)  # delete_clicked
        api.data_services.delete_from_csv_pool.return_value = True

        DataSourceComponents.render_csv_pool(api)
        api.data_services.delete_from_csv_pool.assert_called_once()

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_delete_failed(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, False, True)
        api.data_services.delete_from_csv_pool.return_value = False

        DataSourceComponents.render_csv_pool(api)
        mock_st.error.assert_called()


# gem5 parser expansion and finalization


# Dataframe shaper validation


class TestUniDfShaper:
    """Tests for dataframe input validation."""

    def test_none_input_raises(self) -> None:
        from src.core.services.shapers.impl.sort import Sort

        shaper = Sort({"order_dict": {}})
        with pytest.raises(ValueError, match="cannot be None"):
            shaper(cast(Any, None))

    def test_non_dataframe_input_raises(self) -> None:
        from src.core.services.shapers.impl.sort import Sort

        shaper = Sort({"order_dict": {}})
        with pytest.raises(ValueError, match="Expected pandas DataFrame"):
            shaper(cast(Any, "not a dataframe"))


# Selector validation


class TestSelectorValidation:
    """Concrete registered selectors validate parameters and data preconditions."""

    def test_abstract_base_cannot_execute(self) -> None:
        from src.core.services.shapers.impl.selector import Selector

        with pytest.raises(TypeError, match="abstract"):
            Selector({"column": "x"})  # type: ignore[abstract]

    def test_missing_column_raises(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.condition_selector import (
            ConditionSelector,
        )

        with pytest.raises(ValueError, match="Missing required parameters"):
            ConditionSelector({"mode": "equals", "value": 1})

    def test_empty_column_raises(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.condition_selector import (
            ConditionSelector,
        )

        with pytest.raises(ValueError, match="column"):
            ConditionSelector({"column": "", "mode": "equals", "value": 1})

    def test_column_not_in_dataframe_raises(self) -> None:
        import pandas as pd
        from src.core.services.shapers.impl.selector_algorithms.condition_selector import (
            ConditionSelector,
        )

        selector = ConditionSelector({"column": "nonexistent", "mode": "equals", "value": 1})
        with pytest.raises(ValueError, match="not found in dataframe"):
            selector(pd.DataFrame({"a": [1]}))


# Shaper API delegation


class TestDefaultShapersAPI:
    """Tests for shaper API delegation."""

    def test_get_available_shaper_types(self) -> None:
        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI()
        types = api.get_available_shaper_types()
        assert isinstance(types, list)
        assert len(types) > 0


# Data-source page modes


class TestDataSourcePage:
    """Tests for data-source page modes."""

    @patch("src.web.pages.data_source.st")
    @patch("src.web.pages.data_source.DataSourceComponents")
    def test_render_parse_mode(self, mock_dsc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.data_source import DataSourcePage

        api = MagicMock()
        api.state_manager.is_using_parser.return_value = False

        mock_st.segmented_control.return_value = "Parse gem5 Stats Files"
        page = DataSourcePage(api)
        page.render()
        mock_dsc.render_parser_config.assert_called_once()

    @patch("src.web.pages.data_source.st")
    @patch("src.web.pages.data_source.DataSourceComponents")
    def test_render_load_recent(self, mock_dsc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.data_source import DataSourcePage

        api = MagicMock()
        mock_st.segmented_control.return_value = "Load from Recent"
        page = DataSourcePage(api)
        page.render()
        mock_dsc.render_csv_pool.assert_called_once()

    @patch("src.web.pages.data_source.st")
    @patch("src.web.pages.data_source.DataSourceComponents")
    def test_render_csv_mode(self, mock_dsc: MagicMock, mock_st: MagicMock) -> None:
        from src.web.pages.data_source import DataSourcePage

        api = MagicMock()
        api.state_manager.is_using_parser.return_value = True
        mock_st.segmented_control.return_value = "Upload data or portfolio"
        page = DataSourcePage(api)
        page.render()
        api.state_manager.set_use_parser.assert_not_called()
        mock_st.success.assert_called()
        mock_dsc.render_browser_upload.assert_called_once_with(api)


# DataManager abstract contract


class TestDataManagerBase:
    """Tests for dataframe access through a data manager."""

    def test_get_data_delegates(self) -> None:
        import pandas as pd

        from src.web.components.data_managers.data_manager import DataManager

        class ConcreteManager(DataManager):
            @property
            def name(self) -> str:
                return "test"

            def render(self) -> None:
                pass

        api = MagicMock()
        df = pd.DataFrame({"a": [1]})
        api.state_manager.get_data.return_value = df

        mgr = ConcreteManager(api)
        result = mgr.get_data()
        assert result is not None
        api.state_manager.get_data.assert_called()

    def test_set_data_delegates(self) -> None:
        import pandas as pd

        from src.web.components.data_managers.data_manager import DataManager

        class ConcreteManager(DataManager):
            @property
            def name(self) -> str:
                return "test"

            def render(self) -> None:
                pass

        api = MagicMock()
        df = pd.DataFrame({"a": [1]})
        mgr = ConcreteManager(api)
        mgr.set_data(df)
        api.update_selected_dataset.assert_called_once_with(df, operation="Update dataset")


# Additional data-source actions


class TestDataSourceComponentsExtra:
    """Data-source component error and empty-state behavior."""

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.CardComponents")
    @patch("src.web.components.data_source.data_source_components.DataComponents")
    def test_render_csv_pool_preview_exception(
        self,
        mock_data_comp: MagicMock,
        mock_card: MagicMock,
        mock_st: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        csv_file = tmp_path / "test.csv"
        csv_file.write_text("a,b\n1,2\n")

        api = MagicMock()
        api.state_manager.get_csv_pool.return_value = [{"path": str(csv_file), "name": "test.csv"}]
        mock_card.file_info_card.return_value = (False, True, False)
        mock_st.session_state = {}

        with patch.object(
            DataSourceComponents,
            "render_import_preview",
            side_effect=RuntimeError("preview error"),
        ):
            with pytest.raises(RuntimeError, match="preview error"):
                DataSourceComponents.render_csv_pool(api)

    @patch("src.web.components.data_source.data_source_components.st")
    @patch("src.web.components.data_source.data_source_components.VariableEditor")
    def test_render_parser_config(self, mock_editor: MagicMock, mock_st: MagicMock) -> None:
        """Cover render_parser_config fragment (partially)."""
        from src.web.components.data_source.data_source_components import (
            DataSourceComponents,
        )

        api = MagicMock()
        api.state_manager.get_simulator.return_value = "gem5"
        api.state_manager.get_stats_path.return_value = "/tmp/stats"
        api.state_manager.get_stats_pattern.return_value = "stats.txt"
        api.state_manager.get_parser_strategy.return_value = "simple"
        api.state_manager.get_scanned_variables.return_value = []
        api.state_manager.get_parse_variables.return_value = []

        # Mock the fragment decorator to just call the function
        def fragment_bypass(func: Any) -> Any:
            return func

        mock_st.fragment = fragment_bypass

        def _make_cols(n: Any) -> list[MagicMock]:
            count = len(n) if isinstance(n, list) else int(n)
            cols = []
            for _ in range(count):
                c = MagicMock()
                c.__enter__ = MagicMock(return_value=c)
                c.__exit__ = MagicMock(return_value=False)
                cols.append(c)
            return cols

        mock_st.columns.side_effect = _make_cols
        mock_st.text_input.return_value = "/tmp/stats"
        mock_st.segmented_control.return_value = "simple"
        mock_st.checkbox.return_value = False
        mock_st.button.return_value = False

        mock_editor.render.return_value = []

        DataSourceComponents.render_parser_config(api)


# Seed reduction


class TestReductionService:
    """Tests for seed reduction and input validation."""

    def test_reduce_seeds_empty(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        result = ReductionService.reduce_seeds(pd.DataFrame(), ["cat"], ["val"])
        assert result.empty

    def test_reduce_seeds_basic(self) -> None:
        # [test->req~ring5.data.seed-reduction~1]
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        df = pd.DataFrame(
            {
                "bench": ["a", "a", "b", "b"],
                "ipc": [1.0, 2.0, 3.0, 4.0],
            }
        )
        result = ReductionService.reduce_seeds(df, ["bench"], ["ipc"])
        assert "ipc" in result.columns
        assert "ipc.sd" in result.columns
        assert len(result) == 2

    def test_validate_no_categorical(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(pd.DataFrame({"a": [1]}), [], ["a"])
        assert any("categorical" in e.lower() for e in errors)

    def test_validate_no_statistic(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(pd.DataFrame({"a": [1]}), ["a"], [])
        assert any("statistic" in e.lower() for e in errors)

    def test_validate_missing_columns(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(
            pd.DataFrame({"a": [1]}), ["missing_cat"], ["missing_stat"]
        )
        assert len(errors) >= 2

    def test_validate_non_numeric_stat(self) -> None:
        import pandas as pd

        from src.core.services.managers.reduction_service import ReductionService

        errors = ReductionService.validate_seeds_reducer_inputs(
            pd.DataFrame({"cat": ["a"], "val": ["text"]}), ["cat"], ["val"]
        )
        assert any("numeric" in e.lower() for e in errors)


# Arithmetic operations


class TestArithmeticService:
    """Tests for arithmetic operation dispatch."""

    # [test->req~ring5.data.arithmetic~1]

    def test_division(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Division", "a", "b", "c")
        assert result["c"].iloc[0] == 5.0

    def test_sum(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Sum", "a", "b", "c")
        assert result["c"].iloc[0] == 12.0

    def test_subtraction(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Subtraction", "a", "b", "c")
        assert result["c"].iloc[0] == 8.0

    def test_multiplication(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        result = ArithmeticService.apply_operation(df, "Multiplication", "a", "b", "c")
        assert result["c"].iloc[0] == 20.0

    def test_unknown_op_raises(self) -> None:
        import pandas as pd

        from src.core.services.managers.arithmetic_service import ArithmeticService

        df = pd.DataFrame({"a": [10.0], "b": [2.0]})
        with pytest.raises(ValueError, match="Unknown operation"):
            ArithmeticService.apply_operation(df, "Modulo", "a", "b", "c")


# Shaper validation


class TestShaperBase:
    """Tests for base shaper parameters and preconditions."""

    def test_non_dict_params_raises(self) -> None:
        from src.core.services.shapers.impl.sort import Sort

        with pytest.raises(ValueError, match="must be a dictionary"):
            Sort("not_a_dict")  # type: ignore[arg-type]

    def test_preconditions_none_df(self) -> None:
        from src.core.services.shapers.impl.sort import Sort

        shaper = Sort({"order_dict": {}})
        with pytest.raises(ValueError, match="cannot be None"):
            shaper._verify_preconditions(None)  # type: ignore[arg-type]

    def test_preconditions_empty_df(self) -> None:
        import pandas as pd
        from src.core.services.shapers.impl.sort import Sort

        shaper = Sort({"order_dict": {}})
        with pytest.raises(ValueError, match="empty"):
            shaper._verify_preconditions(pd.DataFrame())

    def test_call_delegates_to_preconditions(self) -> None:
        import pandas as pd
        from src.core.services.shapers.impl.sort import Sort

        shaper = Sort({"order_dict": {}})
        df = pd.DataFrame({"a": [1]})
        result = shaper(df)
        pd.testing.assert_frame_equal(result, df)


# Item selection


class TestItemSelectorVerify:
    """Tests for item-selector parameter validation."""

    def test_missing_strings_raises(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.item_selector import (
            ItemSelector,
        )

        with pytest.raises(ValueError, match="strings"):
            ItemSelector({"column": "x"})

    def test_non_list_strings_raises(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.item_selector import (
            ItemSelector,
        )

        with pytest.raises(TypeError, match="must be a list"):
            ItemSelector({"column": "x", "strings": "not_a_list"})

    def test_valid_params(self) -> None:
        from src.core.services.shapers.impl.selector_algorithms.item_selector import (
            ItemSelector,
        )

        sel = ItemSelector({"column": "a", "strings": ["x", "y"]})
        assert sel.column == "a"
        assert sel.strings == ["x", "y"]


# Repository state


class TestRepositoryStateManager:
    """Tests for repository data validation and clearing."""

    def test_set_data_preserves_typed_values_independently_of_editor(self) -> None:
        """Mutable editor declarations cannot recast published typed frame columns."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        mgr._session_repo.parser_repo.set_parse_variables(
            cast(Any, [{"name": "benchmark", "type": "configuration"}])
        )

        df = pd.DataFrame({"benchmark": [1, 2, 3], "ipc": [1.0, 2.0, 3.0]})
        mgr.set_data(df)

        result = mgr.get_data()
        assert result is not None
        assert pd.api.types.is_integer_dtype(result["benchmark"])
        assert result["benchmark"].tolist() == [1, 2, 3]

    def test_set_data_skip_same_object(self) -> None:
        """Setting the same DataFrame object again should be a no-op."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        df = pd.DataFrame({"a": [1]})
        mgr.set_data(df)
        mgr.set_data(df)  # No error expected

    def test_clear_data_with_temp_dir(self, tmp_path: Path) -> None:
        """clear_data removes temp directory."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        temp_dir = tmp_path / "temp_parsed"
        temp_dir.mkdir()

        mgr._session_repo.config_repo.set_temp_dir(str(temp_dir))
        mgr.set_data(pd.DataFrame({"a": [1]}))

        mgr.clear_data()
        assert mgr.get_data() is None

    def test_clear_data_no_temp_dir(self) -> None:
        """clear_data when no temp dir exists."""
        import pandas as pd

        from src.core.state.repository_state_manager import RepositoryStateManager

        mgr = RepositoryStateManager()
        mgr.set_data(pd.DataFrame({"a": [1]}))
        mgr.clear_data()
        assert mgr.get_data() is None


# Pipeline delegation


class TestDefaultShapersAPIProcessPipeline:
    """Tests for pipeline delegation."""

    def test_process_pipeline_empty(self) -> None:
        import pandas as pd

        from src.core.services.shapers.shapers_impl import DefaultShapersAPI

        api = DefaultShapersAPI()
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = api.process_pipeline(df, [])
        pd.testing.assert_frame_equal(result, df)


# Configuration parsing failures


class TestConfigAwareParseConfigException:
    """Tests for configuration parsing failures."""

    def test_parse_config_with_exception(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.ini"
        config_path.write_text("[section]\nkey = val\n")

        with patch("src.parsing.gem5.impl.strategies.config_aware._LiteralConfigParser") as mock_cp:
            mock_parser = MagicMock()
            mock_parser.read_string.side_effect = configparser.Error("parse error")
            mock_cp.return_value = mock_parser

            with pytest.raises(RuntimeError, match="parse error"):
                ConfigAwareParseWork._read_config(config_path)
