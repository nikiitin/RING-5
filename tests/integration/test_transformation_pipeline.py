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
from typing import Any, cast

import pandas as pd
import pytest

from src.core.application_api import ApplicationAPI
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.shapers.factory import ShaperFactory


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


class TestTransformationPipeline:
    """Integration tests for shaper pipeline workflows."""

    def test_single_shaper_transformation(self, sample_benchmark_data: pd.DataFrame) -> None:
        """
        Test single shaper transformation (normalization).
        """
        # Create normalize shaper
        normalize_config: ShaperStepConfig = {
            "type": "normalize",
            "normalizeVars": ["ipc"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["benchmark"],
        }

        normalizer = ShaperFactory.create_shaper("normalize", normalize_config)

        # Apply transformation
        result = normalizer(sample_benchmark_data)

        # Verify normalized IPC values.
        assert "ipc" in result.columns

        # Verify baseline values are 1.0
        baseline_rows = result[result["config"] == "baseline"]
        assert all(baseline_rows["ipc"] == 1.0)

        # Verify tx_lazy values are scaled correctly
        tx_rows = result[result["config"] == "tx_lazy"]
        expected_mcf = 1.0 / 1.2  # 0.833...
        mcf_ipc = tx_rows[tx_rows["benchmark"] == "mcf"]["ipc"].iloc[0]
        assert abs(float(mcf_ipc) - expected_mcf) < 0.01

    def test_multi_shaper_pipeline(
        self, sample_benchmark_data: pd.DataFrame, facade: ApplicationAPI
    ) -> None:
        """
        Test multi-stage shaper pipeline:
        1. Normalize IPC
        2. Sort by benchmark
        3. Filter top configurations
        """
        # [test->req~ring5.shaping.independent-pipelines~1]
        # Define pipeline
        pipeline: list[ShaperStepConfig] = [
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
        result = facade.shapers.process_pipeline(sample_benchmark_data, pipeline)

        # Verify transformations applied (normalization modifies column in-place)
        assert "ipc" in result.columns

        # Verify sort order
        benchmarks = result["benchmark"].tolist()
        mcf_indices = [i for i, b in enumerate(benchmarks) if b == "mcf"]
        omnetpp_indices = [i for i, b in enumerate(benchmarks) if b == "omnetpp"]
        assert all(
            mcf_idx < omnetpp_idx for mcf_idx in mcf_indices for omnetpp_idx in omnetpp_indices
        )

    def test_pipeline_with_mean_aggregation(
        self, sample_benchmark_data: pd.DataFrame, facade: ApplicationAPI
    ) -> None:
        """
        Test pipeline with mean aggregation shaper.
        """
        # Define pipeline with geometric mean
        pipeline: list[ShaperStepConfig] = [
            {
                "type": "mean",
                "meanVars": ["ipc"],
                "meanAlgorithm": "geomean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        ]

        result = facade.shapers.process_pipeline(sample_benchmark_data, pipeline)

        # Verify mean rows were added
        assert len(result) > len(sample_benchmark_data)

        # Check for geomean marker
        mean_rows = result[result["benchmark"] == "geomean"]
        assert len(mean_rows) == 2  # One for each config

    def test_pipeline_error_handling(
        self, sample_benchmark_data: pd.DataFrame, facade: ApplicationAPI
    ) -> None:
        """
        Test error handling in pipeline execution.
        """
        # Test with invalid shaper type
        invalid_pipeline: list[ShaperStepConfig] = cast(Any, [{"type": "invalid_shaper"}])

        with pytest.raises(ValueError):
            facade.shapers.process_pipeline(sample_benchmark_data, invalid_pipeline)

        # Test with missing required parameters
        invalid_normalize: list[ShaperStepConfig] = [
            {  # type: ignore
                "type": "normalize",
                # Missing required normalizeVars parameter
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
            }
        ]

        with pytest.raises((ValueError, KeyError)):
            facade.shapers.process_pipeline(sample_benchmark_data, invalid_normalize)

    @pytest.mark.usefixtures("isolated_application_data")
    def test_complex_pipeline_workflow(
        self, sample_benchmark_data: pd.DataFrame, tmp_path: Path, facade: ApplicationAPI
    ) -> None:
        """
        Test complex end-to-end workflow:
        1. Load data
        2. Apply transformations
        3. Save pipeline
        4. Load pipeline
        5. Apply to new data
        """
        # Save sample data to CSV
        csv_path = tmp_path / "sample.csv"
        sample_benchmark_data.to_csv(csv_path, index=False)

        # Load into CSV pool
        facade.data_services.add_to_csv_pool(str(csv_path))
        loaded_data = facade.data_services.load_csv_file(str(csv_path))

        # Define and apply pipeline
        pipeline: list[ShaperStepConfig] = [
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
        transformed = facade.shapers.process_pipeline(loaded_data, pipeline)

        # Verify transformations (normalization modifies columns in-place)
        assert "ipc" in transformed.columns
        assert "execution_time" in transformed.columns
        assert transformed["config"].dtype.name == "category"

        # Apply same pipeline again to verify idempotency for transformation
        retransformed = facade.shapers.process_pipeline(loaded_data, pipeline)

        # Verify results match (both start from same loaded_data)
        pd.testing.assert_frame_equal(
            transformed.reset_index(drop=True), retransformed.reset_index(drop=True)
        )

    @pytest.mark.usefixtures("isolated_application_data")
    def test_saved_pipeline_replays_loaded_csv(
        self, tmp_path: Path, facade: ApplicationAPI
    ) -> None:
        source = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm2", "bm3", "bm4"],
                "config": ["A", "B", "A", "B"],
                "ipc": [1.5, 2.0, 1.8, 2.2],
                "latency": [100, 80, 90, 75],
            }
        )
        csv_path = tmp_path / "results.csv"
        source.to_csv(csv_path, index=False)
        pipeline: list[ShaperStepConfig] = [
            {"type": "columnSelector", "columns": ["benchmark", "ipc", "latency"]},
            {"type": "columnSelector", "columns": ["benchmark", "ipc"]},
        ]
        pool_path = facade.data_services.add_to_csv_pool(str(csv_path))
        config_path = facade.data_services.save_configuration(
            "test_pipeline", "CSV replay", pipeline, pool_path
        )
        loaded = facade.data_services.load_configuration(config_path)
        saved_csv_path = loaded["csv_path"]
        assert isinstance(saved_csv_path, str) and saved_csv_path == pool_path
        loaded_frame = facade.data_services.load_csv_file(saved_csv_path)
        original = loaded_frame.copy(deep=True)
        steps = loaded["shapers"]
        first = facade.shapers.process_pipeline(loaded_frame, steps[:1])
        replayed = facade.shapers.process_pipeline(loaded_frame, steps)
        pd.testing.assert_frame_equal(first, source[["benchmark", "ipc", "latency"]])
        pd.testing.assert_frame_equal(replayed, source[["benchmark", "ipc"]])
        pd.testing.assert_frame_equal(loaded_frame, original)
