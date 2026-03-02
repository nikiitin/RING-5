"""End-to-end integration test: Load → Transform → Verify.

Tests the full pipeline from data loading through a multi-shaper
transformation chain. Verifies that shapers compose correctly and
produce expected output when chained together.
"""

from typing import cast

import pandas as pd
import pytest

from src.core.models.data_models import PipelineStep
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.pipeline_service import PipelineService


@pytest.fixture
def pipeline_data() -> pd.DataFrame:
    """Rich dataset suitable for multi-shaper pipeline testing.

    3 benchmarks × 3 configs with IPC, cycles, and energy columns.
    """
    return pd.DataFrame(
        {
            "benchmark_name": [
                "mcf",
                "mcf",
                "mcf",
                "omnetpp",
                "omnetpp",
                "omnetpp",
                "xalancbmk",
                "xalancbmk",
                "xalancbmk",
            ],
            "config_description": [
                "baseline",
                "optimized",
                "aggressive",
                "baseline",
                "optimized",
                "aggressive",
                "baseline",
                "optimized",
                "aggressive",
            ],
            "system.cpu.ipc": [
                2.10,
                2.35,
                2.50,
                1.45,
                1.62,
                1.70,
                1.78,
                1.98,
                2.05,
            ],
            "system.cpu.numCycles": [
                321000.0,
                289000.0,
                270000.0,
                789000.0,
                712000.0,
                680000.0,
                567000.0,
                510000.0,
                490000.0,
            ],
            "simTicks": [
                3210000000.0,
                2890000000.0,
                2700000000.0,
                7890000000.0,
                7120000000.0,
                6800000000.0,
                5670000000.0,
                5100000000.0,
                4900000000.0,
            ],
        }
    )


class TestPipelineEndToEnd:
    """Full pipeline integration tests."""

    def test_column_select_then_sort(self, pipeline_data: pd.DataFrame) -> None:
        """Pipeline: select columns → sort benchmarks in custom order."""
        pipeline_config = [
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
        result = PipelineService.process_pipeline(
            pipeline_data, cast(list[ShaperStepConfig], pipeline_config)
        )

        # Should have only 3 columns
        assert list(result.columns) == [
            "benchmark_name",
            "config_description",
            "system.cpu.ipc",
        ]
        # Should be sorted in custom order: xalancbmk first, mcf last
        benchmarks = result["benchmark_name"].tolist()
        assert benchmarks[:3] == ["xalancbmk"] * 3
        assert benchmarks[3:6] == ["omnetpp"] * 3
        assert benchmarks[6:] == ["mcf"] * 3
        # Row count preserved
        assert len(result) == 9

    def test_filter_then_normalize(self, pipeline_data: pd.DataFrame) -> None:
        """Pipeline: filter configs → normalize against baseline."""
        pipeline_config = [
            {
                "type": "conditionSelector",
                "column": "config_description",
                "values": ["baseline", "optimized"],
            },
            {
                "type": "normalize",
                "normalizeVars": ["system.cpu.ipc"],
                "normalizerColumn": "config_description",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark_name"],
            },
        ]
        result = PipelineService.process_pipeline(
            pipeline_data, cast(list[ShaperStepConfig], pipeline_config)
        )

        # Filtered to 2 configs × 3 benchmarks = 6 rows
        assert len(result) == 6
        # Baseline rows should have normalized IPC = 1.0
        baseline_rows = result[result["config_description"] == "baseline"]
        for val in baseline_rows["system.cpu.ipc"]:
            assert val == pytest.approx(1.0)
        # Optimized should be > 1.0
        optimized_rows = result[result["config_description"] == "optimized"]
        for val in optimized_rows["system.cpu.ipc"]:
            assert val > 1.0

    def test_filter_normalize_mean(self, pipeline_data: pd.DataFrame) -> None:
        """Pipeline: filter → normalize → compute geometric mean."""
        pipeline_config = [
            {
                "type": "conditionSelector",
                "column": "config_description",
                "values": ["baseline", "optimized"],
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
        ]
        result = PipelineService.process_pipeline(
            pipeline_data, cast(list[ShaperStepConfig], pipeline_config)
        )

        # Original 6 rows + 2 mean rows (one per config)
        assert len(result) == 8
        # Mean rows should be identifiable
        mean_rows = result[result["benchmark_name"] == "geomean"]
        assert len(mean_rows) == 2
        # Baseline geomean should be 1.0 (all baselines normalized to 1.0)
        baseline_mean = mean_rows[mean_rows["config_description"] == "baseline"]
        assert baseline_mean["system.cpu.ipc"].iloc[0] == pytest.approx(1.0)
        # Optimized geomean should be > 1.0
        optimized_mean = mean_rows[mean_rows["config_description"] == "optimized"]
        assert optimized_mean["system.cpu.ipc"].iloc[0] > 1.0

    def test_item_select_then_columns(self, pipeline_data: pd.DataFrame) -> None:
        """Pipeline: item select benchmarks → select columns."""
        pipeline_config = [
            {
                "type": "itemSelector",
                "column": "benchmark_name",
                "strings": ["mcf", "omnetpp"],
            },
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "system.cpu.ipc"],
            },
        ]
        result = PipelineService.process_pipeline(
            pipeline_data, cast(list[ShaperStepConfig], pipeline_config)
        )

        assert list(result.columns) == ["benchmark_name", "system.cpu.ipc"]
        assert len(result) == 6
        assert set(result["benchmark_name"]) == {"mcf", "omnetpp"}

    def test_empty_pipeline_returns_original(self, pipeline_data: pd.DataFrame) -> None:
        """An empty pipeline should return the original data unchanged."""
        result = PipelineService.process_pipeline(pipeline_data, [])
        pd.testing.assert_frame_equal(result, pipeline_data)

    def test_pipeline_with_skip_null_type(self, pipeline_data: pd.DataFrame) -> None:
        """Pipeline entries with no type should be skipped gracefully."""
        pipeline_config = [
            {"type": None},  # type: ignore[typeddict-item]
            {
                "type": "columnSelector",
                "columns": ["benchmark_name", "system.cpu.ipc"],
            },
        ]
        result = PipelineService.process_pipeline(pipeline_data, pipeline_config)
        assert list(result.columns) == ["benchmark_name", "system.cpu.ipc"]

    def test_pipeline_invalid_shaper_raises(self, pipeline_data: pd.DataFrame) -> None:
        """Pipeline with an unknown shaper type should raise ValueError."""
        pipeline_config = [
            {"type": "nonexistent_shaper"},
        ]
        with pytest.raises(ValueError, match="nonexistent_shaper"):
            PipelineService.process_pipeline(
                pipeline_data, cast(list[ShaperStepConfig], pipeline_config)
            )


class TestPipelinePersistence:
    """Test pipeline save/load/delete cycle."""

    def test_save_load_delete_cycle(self, tmp_path) -> None:
        """Full persistence lifecycle: save → list → load → delete."""
        svc = PipelineService(tmp_path / "pipelines")

        config = [
            {"id": 0, "type": "sort", "order_dict": {"benchmark": ["a", "b"]}},
            {"id": 1, "type": "columnSelector", "columns": ["benchmark", "ipc"]},
        ]
        svc.save_pipeline(
            "test_pipeline", cast(list[PipelineStep], config), description="Test pipeline"
        )

        # List
        pipelines = svc.list_pipelines()
        assert "test_pipeline" in pipelines

        # Load
        loaded = svc.load_pipeline("test_pipeline")
        assert loaded["name"] == "test_pipeline"
        assert loaded.get("description") == "Test pipeline"
        assert len(loaded["pipeline"]) == 2
        assert loaded["pipeline"][0]["type"] == "sort"

        # Prepare
        steps, counter = PipelineService.prepare_loaded_pipeline(loaded)
        assert counter == 2  # max id (1) + 1
        assert steps[0] is not loaded["pipeline"][0]  # deep copy

        # Delete
        svc.delete_pipeline("test_pipeline")
        assert "test_pipeline" not in svc.list_pipelines()

    def test_load_nonexistent_raises(self, tmp_path) -> None:
        svc = PipelineService(tmp_path / "pipelines")
        with pytest.raises(FileNotFoundError, match="not found"):
            svc.load_pipeline("does_not_exist")
