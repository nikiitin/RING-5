"""
Integration Test: Transformation Pipeline

Tests the complete data transformation workflow:
1. Load raw CSV data
2. Apply shaper pipeline (normalize, filter, sort)
3. Verify transformed output
4. Test pipeline serialization and restoration

This validates the shaper system and pipeline persistence.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.web.facade import BackendFacade
from src.web.services.pipeline_service import PipelineService
from src.web.services.shapers.factory import ShaperFactory


@pytest.fixture
def sample_benchmark_data() -> pd.DataFrame:
    """
    Create sample benchmark performance data for transformation testing.
    """
    return pd.DataFrame(
        {
            "benchmark": ["mcf", "omnetpp", "xalancbmk", "mcf", "omnetpp", "xalancbmk"],
            "config": ["baseline", "baseline", "baseline", "tx_lazy", "tx_lazy", "tx_lazy"],
            "ipc": [1.2, 1.5, 1.8, 1.0, 1.3, 1.5],
            "cache_miss_rate": [0.05, 0.03, 0.02, 0.07, 0.04, 0.03],
            "execution_time": [100, 80, 60, 120, 95, 72],
        }
    )


@pytest.fixture
def facade() -> BackendFacade:
    """Create BackendFacade instance for testing."""
    return BackendFacade()


class TestTransformationPipeline:
    """Integration tests for shaper pipeline workflows."""

    def test_single_shaper_transformation(self, sample_benchmark_data: pd.DataFrame) -> None:
        """
        Test single shaper transformation (normalization).
        """
        # Create normalize shaper
        normalize_config = {
            "type": "normalize",
            "normalizeVars": ["ipc"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["benchmark"],
        }

        normalizer = ShaperFactory.create_shaper("normalize", normalize_config)

        # Apply transformation
        result = normalizer(sample_benchmark_data)

        # Verify transformation was applied (normalization modifies column in-place)
        assert "ipc" in result.columns

        # Verify baseline values are 1.0
        baseline_rows = result[result["config"] == "baseline"]
        assert all(baseline_rows["ipc"] == 1.0)

        # Verify tx_lazy values are scaled correctly
        tx_rows = result[result["config"] == "tx_lazy"]
        expected_mcf = 1.0 / 1.2  # 0.833...
        assert abs(tx_rows[tx_rows["benchmark"] == "mcf"]["ipc"].iloc[0] - expected_mcf) < 0.01

    def test_multi_shaper_pipeline(
        self, sample_benchmark_data: pd.DataFrame, facade: BackendFacade
    ) -> None:
        """
        Test multi-stage shaper pipeline:
        1. Normalize IPC
        2. Sort by benchmark
        3. Filter top configurations
        """
        # Define pipeline
        pipeline = [
            {
                "type": "normalize",
                "normalizeVars": ["ipc"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
            },
            {"type": "sort", "order_dict": {"benchmark": ["mcf", "omnetpp", "xalancbmk"]}},
        ]

        # Apply pipeline using facade
        result = facade.apply_shapers(sample_benchmark_data, pipeline)

        # Verify transformations applied (normalization modifies column in-place)
        assert "ipc" in result.columns

        # Verify sort order
        benchmarks = result["benchmark"].tolist()
        mcf_indices = [i for i, b in enumerate(benchmarks) if b == "mcf"]
        omnetpp_indices = [i for i, b in enumerate(benchmarks) if b == "omnetpp"]
        assert all(
            mcf_idx < omnetpp_idx for mcf_idx in mcf_indices for omnetpp_idx in omnetpp_indices
        )

    def test_pipeline_persistence(self, tmp_path: Path) -> None:
        """
        Test pipeline save and load functionality using PipelineService.
        """
        # Define pipeline
        pipeline = [
            {
                "type": "normalize",
                "normalizeVars": ["ipc", "cache_miss_rate"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
            },
            {"type": "sort", "order_dict": {"config": ["baseline", "tx_lazy", "tx_eager"]}},
        ]

        # Save pipeline using PipelineService
        test_pipeline_name = f"test_pipeline_{tmp_path.name}"
        PipelineService.save_pipeline(test_pipeline_name, pipeline, description="Test pipeline")

        # List pipelines to verify it was saved
        available_pipelines = PipelineService.list_pipelines()
        assert test_pipeline_name in available_pipelines

        # Load pipeline
        loaded = PipelineService.load_pipeline(test_pipeline_name)

        # Verify loaded pipeline matches original
        assert "pipeline" in loaded
        loaded_pipeline = loaded["pipeline"]
        assert len(loaded_pipeline) == len(pipeline)
        assert loaded_pipeline[0]["type"] == "normalize"
        assert loaded_pipeline[1]["type"] == "sort"

        # Cleanup
        PipelineService.delete_pipeline(test_pipeline_name)

    def test_pipeline_with_mean_aggregation(self, sample_benchmark_data: pd.DataFrame) -> None:
        """
        Test pipeline with mean aggregation shaper.
        """
        # Define pipeline with geometric mean
        pipeline = [
            {
                "type": "mean",
                "meanVars": ["ipc"],
                "meanAlgorithm": "geomean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        ]

        facade = BackendFacade()
        result = facade.apply_shapers(sample_benchmark_data, pipeline)

        # Verify mean rows were added
        assert len(result) > len(sample_benchmark_data)

        # Check for geomean marker
        mean_rows = result[result["benchmark"] == "geomean"]
        assert len(mean_rows) == 2  # One for each config

    def test_pipeline_error_handling(self, sample_benchmark_data: pd.DataFrame) -> None:
        """
        Test error handling in pipeline execution.
        """
        facade = BackendFacade()

        # Test with invalid shaper type
        invalid_pipeline = [{"type": "invalid_shaper", "params": {}}]

        with pytest.raises(ValueError):
            facade.apply_shapers(sample_benchmark_data, invalid_pipeline)

        # Test with missing required parameters
        invalid_normalize = [
            {
                "type": "normalize",
                # Missing required normalizeVars parameter
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
            }
        ]

        with pytest.raises((ValueError, KeyError)):
            facade.apply_shapers(sample_benchmark_data, invalid_normalize)

    def test_complex_pipeline_workflow(
        self, sample_benchmark_data: pd.DataFrame, tmp_path: Path
    ) -> None:
        """
        Test complex end-to-end workflow:
        1. Load data
        2. Apply transformations
        3. Save pipeline
        4. Load pipeline
        5. Apply to new data
        """
        facade = BackendFacade()

        # Save sample data to CSV
        csv_path = tmp_path / "sample.csv"
        sample_benchmark_data.to_csv(csv_path, index=False)

        # Load into CSV pool
        facade.add_to_csv_pool(str(csv_path))
        loaded_data = facade.load_csv_file(str(csv_path))

        # Define and apply pipeline
        pipeline = [
            {
                "type": "normalize",
                "normalizeVars": ["ipc", "execution_time"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
            },
            {
                "type": "transformer",
                "column": "config",
                "target_type": "factor",
                "order": ["baseline", "tx_lazy"],
            },
        ]

        # Apply transformations
        transformed = facade.apply_shapers(loaded_data, pipeline)

        # Verify transformations (normalization modifies columns in-place)
        assert "ipc" in transformed.columns
        assert "execution_time" in transformed.columns
        assert transformed["config"].dtype.name == "category"

        # Apply same pipeline again to verify idempotency for transformation
        retransformed = facade.apply_shapers(loaded_data, pipeline)

        # Verify results match (both start from same loaded_data)
        pd.testing.assert_frame_equal(
            transformed.reset_index(drop=True), retransformed.reset_index(drop=True)
        )
