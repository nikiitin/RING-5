"""Integration tests for advanced pipeline operations.

Covers Scenarios #13 (Pipeline round-trip save/load/apply) and
#15 (Multi-step complex pipelines).

Tests:
    - Pipeline save → load → apply round-trip
    - Complex multi-step pipeline: select → normalize → mean → sort
    - Pipeline applied to loaded data vs. applied on load
    - Shaper chaining correctness (output of one is input to next)
    - ItemSelector and ConditionSelector integration
"""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.pipeline_service import PipelineService

# ===========================================================================
# Test Class 1: Pipeline save → load → apply round-trip
# ===========================================================================


class TestPipelineRoundTrip:
    """Test pipeline save/load/apply cycle with real data."""

    def test_save_and_load_pipeline(self, tmp_path: Path) -> None:
        """Saved pipeline loads back with identical config."""
        service = PipelineService(tmp_path / "pipelines")

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "config_description", "system.cpu.ipc"],
            },
            {
                "type": "normalize",
                "normalizeVars": ["system.cpu.ipc"],
                "normalizerColumn": "config_description",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark_name"],
            },
        ]

        service.save_pipeline("test_pipe", pipeline, description="Test description")

        loaded: Dict[str, Any] = service.load_pipeline("test_pipe")

        assert loaded["name"] == "test_pipe"
        assert loaded["description"] == "Test description"
        assert len(loaded["pipeline"]) == 2
        assert loaded["pipeline"][0]["type"] == "columnSelector"
        assert loaded["pipeline"][1]["type"] == "normalize"

    def test_save_load_and_apply(
        self,
        rich_sample_data: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Saved pipeline → load → apply to data produces correct result."""
        service = PipelineService(tmp_path / "pipelines")

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "config_description", "system.cpu.ipc"],
            },
            {
                "type": "sort",
                "order_dict": {
                    "benchmark_name": ["xalancbmk", "omnetpp", "mcf"],
                },
            },
        ]

        # Save
        service.save_pipeline("apply_test", pipeline)

        # Load
        loaded: Dict[str, Any] = service.load_pipeline("apply_test")

        # Apply loaded pipeline to data
        result: pd.DataFrame = PipelineService.process_pipeline(
            rich_sample_data, loaded["pipeline"]
        )

        assert list(result.columns) == [
            "benchmark_name",
            "config_description",
            "system.cpu.ipc",
        ]
        assert result["benchmark_name"].unique().tolist() == ["xalancbmk", "omnetpp", "mcf"]

    def test_list_and_delete_pipeline(self, tmp_path: Path) -> None:
        """Saved pipelines appear in list, deleted ones disappear."""
        service = PipelineService(tmp_path / "pipelines")

        service.save_pipeline("alpha", [{"type": "columnSelector", "columns": ["a"]}])
        service.save_pipeline("beta", [{"type": "columnSelector", "columns": ["b"]}])

        names: List[str] = service.list_pipelines()
        assert "alpha" in names
        assert "beta" in names

        service.delete_pipeline("alpha")

        names_after: List[str] = service.list_pipelines()
        assert "alpha" not in names_after
        assert "beta" in names_after

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        """Loading a pipeline that doesn't exist raises FileNotFoundError."""
        service = PipelineService(tmp_path / "pipelines")

        with pytest.raises(FileNotFoundError, match="not found"):
            service.load_pipeline("nonexistent")


# ===========================================================================
# Test Class 2: Complex multi-step pipelines
# ===========================================================================


class TestComplexPipelines:
    """Test multi-step pipelines with realistic scientific workflows."""

    def test_select_normalize_sort_pipeline(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Pipeline: columnSelector → normalize → sort."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ],
            },
            {
                "type": "normalize",
                "normalizeVars": ["system.cpu.ipc"],
                "normalizerColumn": "config_description",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark_name"],
            },
            {
                "type": "sort",
                "order_dict": {
                    "benchmark_name": ["mcf", "omnetpp", "xalancbmk"],
                },
            },
        ]

        result: pd.DataFrame = loaded_facade.apply_shapers(data, pipeline)

        # Check columns
        assert list(result.columns) == [
            "benchmark_name",
            "config_description",
            "system.cpu.ipc",
        ]

        # Check normalization
        baseline_rows = result[result["config_description"] == "baseline"]
        for val in baseline_rows["system.cpu.ipc"]:
            assert abs(val - 1.0) < 1e-6

        # Check sort order
        bench_order: list[str] = result["benchmark_name"].unique().tolist()
        assert bench_order == ["mcf", "omnetpp", "xalancbmk"]

    def test_select_mean_pipeline(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Pipeline: columnSelector → mean aggregation."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ],
            },
            {
                "type": "mean",
                "meanVars": ["system.cpu.ipc"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["config_description"],
                "replacingColumn": "benchmark_name",
            },
        ]

        result: pd.DataFrame = loaded_facade.apply_shapers(data, pipeline)

        # Should have original rows + mean rows
        assert len(result) > len(data)

        # Mean rows should exist
        mean_rows = result[result["benchmark_name"] == "arithmean"]
        assert len(mean_rows) > 0

        # Mean of baseline IPC: (2.10 + 1.45 + 1.78) / 3 ≈ 1.7767
        baseline_mean = mean_rows[mean_rows["config_description"] == "baseline"][
            "system.cpu.ipc"
        ].iloc[0]
        expected: float = (2.10 + 1.45 + 1.78) / 3
        assert abs(baseline_mean - expected) < 0.01

    def test_full_scientific_pipeline(
        self,
        loaded_facade: ApplicationAPI,
    ) -> None:
        """Full scientific pipeline: select → normalize → mean → sort."""
        data: pd.DataFrame = loaded_facade.state_manager.get_data()

        pipeline: List[Dict[str, Any]] = [
            {
                "type": "columnSelector",
                "columns": [
                    "benchmark_name",
                    "config_description",
                    "system.cpu.ipc",
                ],
            },
            {
                "type": "normalize",
                "normalizeVars": ["system.cpu.ipc"],
                "normalizerColumn": "config_description",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark_name"],
            },
            {
                "type": "mean",
                "meanVars": ["system.cpu.ipc"],
                "meanAlgorithm": "geomean",
                "groupingColumns": ["config_description"],
                "replacingColumn": "benchmark_name",
            },
            {
                "type": "sort",
                "order_dict": {
                    "benchmark_name": [
                        "mcf",
                        "omnetpp",
                        "xalancbmk",
                        "geomean",
                    ],
                },
            },
        ]

        result: pd.DataFrame = loaded_facade.apply_shapers(data, pipeline)

        # Verify geomean row exists
        geomean_rows = result[result["benchmark_name"] == "geomean"]
        assert len(geomean_rows) > 0

        # Baseline geomean should be ~1.0 (all baselines are 1.0 after normalize)
        baseline_geomean = geomean_rows[geomean_rows["config_description"] == "baseline"][
            "system.cpu.ipc"
        ].iloc[0]
        assert abs(baseline_geomean - 1.0) < 1e-6

        # Check sort order
        expected_order = ["mcf", "omnetpp", "xalancbmk", "geomean"]
        actual_order: list[str] = result["benchmark_name"].unique().tolist()
        assert actual_order == expected_order


# ===========================================================================
# Test Class 3: Individual shaper integration
# ===========================================================================


class TestShaperIntegration:
    """Test individual shapers with realistic data."""

    def test_item_selector(self, rich_sample_data: pd.DataFrame) -> None:
        """ItemSelector filters rows by column value."""
        shaper = ShaperFactory.create_shaper(
            "itemSelector",
            {
                "column": "config_description",
                "strings": ["baseline", "optimized"],
            },
        )
        result: pd.DataFrame = shaper(rich_sample_data)

        assert set(result["config_description"].unique()) == {"baseline", "optimized"}
        # 'aggressive' should be filtered out
        assert "aggressive" not in result["config_description"].values

    def test_condition_selector(self, rich_sample_data: pd.DataFrame) -> None:
        """ConditionSelector filters rows by numeric condition."""
        shaper = ShaperFactory.create_shaper(
            "conditionSelector",
            {
                "column": "system.cpu.ipc",
                "condition": ">=",
                "value": 2.0,
            },
        )
        result: pd.DataFrame = shaper(rich_sample_data)

        # All remaining IPC values should be >= 2.0
        assert all(result["system.cpu.ipc"] >= 2.0)
        assert len(result) < len(rich_sample_data)

    def test_transformer_type_conversion(self, rich_sample_data: pd.DataFrame) -> None:
        """Transformer converts column type to categorical factor."""
        shaper = ShaperFactory.create_shaper(
            "transformer",
            {
                "column": "benchmark_name",
                "target_type": "factor",
                "order": ["mcf", "omnetpp", "xalancbmk"],
            },
        )
        result: pd.DataFrame = shaper(rich_sample_data)

        assert result["benchmark_name"].dtype.name == "category"
        assert list(result["benchmark_name"].cat.categories) == ["mcf", "omnetpp", "xalancbmk"]

    def test_chaining_shapers_manually(self, rich_sample_data: pd.DataFrame) -> None:
        """Manually chaining shapers produces expected cascading result."""
        # Step 1: Select columns
        s1 = ShaperFactory.create_shaper(
            "columnSelector",
            {"columns": ["benchmark_name", "config_description", "system.cpu.ipc"]},
        )
        data1: pd.DataFrame = s1(rich_sample_data)
        assert len(data1.columns) == 3

        # Step 2: Filter to baseline only
        s2 = ShaperFactory.create_shaper(
            "itemSelector",
            {"column": "config_description", "strings": ["baseline"]},
        )
        data2: pd.DataFrame = s2(data1)
        assert all(data2["config_description"] == "baseline")
        assert len(data2) == 3  # 3 benchmarks

        # Step 3: Sort
        s3 = ShaperFactory.create_shaper(
            "sort",
            {"order_dict": {"benchmark_name": ["xalancbmk", "omnetpp", "mcf"]}},
        )
        data3: pd.DataFrame = s3(data2)
        assert data3["benchmark_name"].tolist() == ["xalancbmk", "omnetpp", "mcf"]
