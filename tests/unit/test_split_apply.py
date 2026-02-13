"""
Tests for the SplitApply composite shaper.

Validates:
    1. Parameter validation (joinColumns, groups structure, overlap detection).
    2. Precondition checks (columns exist in DataFrame).
    3. Independent Mean application per group (no duplicate rows).
    4. Independent Normalize application per group (correct baselines).
    5. Combined Mean + Normalize sub-pipelines.
    6. SD columns are carried through automatically.
    7. Empty sub-pipeline passes data through unchanged.
    8. Merge correctness on join columns.
    9. Factory registration and instantiation.
"""

from typing import Any, Dict

import pandas as pd
import pytest

from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.impl.split_apply import SplitApply

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dual_axis_data() -> pd.DataFrame:
    """DataFrame similar to a dual-axis plot scenario.

    Two benchmarks × two configs, with IPC (bars) and numCycles (dots).
    """
    return pd.DataFrame(
        {
            "benchmark": ["mcf", "mcf", "omnetpp", "omnetpp"],
            "config": ["base", "opt", "base", "opt"],
            "ipc": [1.2, 1.5, 1.4, 1.6],
            "numCycles": [3210, 2890, 7890, 7120],
        }
    )


@pytest.fixture
def dual_axis_data_with_sd() -> pd.DataFrame:
    """Same as dual_axis_data but with .sd columns."""
    return pd.DataFrame(
        {
            "benchmark": ["mcf", "mcf", "omnetpp", "omnetpp"],
            "config": ["base", "opt", "base", "opt"],
            "ipc": [1.2, 1.5, 1.4, 1.6],
            "ipc.sd": [0.1, 0.12, 0.08, 0.09],
            "numCycles": [3210, 2890, 7890, 7120],
            "numCycles.sd": [50, 40, 100, 80],
        }
    )


@pytest.fixture
def mean_split_config() -> Dict[str, Any]:
    """SplitApply config: arithmean for IPC, geomean for numCycles."""
    return {
        "joinColumns": ["benchmark", "config"],
        "groups": [
            {
                "columns": ["ipc"],
                "pipeline": [
                    {
                        "type": "mean",
                        "meanVars": ["ipc"],
                        "meanAlgorithm": "arithmean",
                        "groupingColumns": ["config"],
                        "replacingColumn": "benchmark",
                    }
                ],
            },
            {
                "columns": ["numCycles"],
                "pipeline": [
                    {
                        "type": "mean",
                        "meanVars": ["numCycles"],
                        "meanAlgorithm": "arithmean",
                        "groupingColumns": ["config"],
                        "replacingColumn": "benchmark",
                    }
                ],
            },
        ],
    }


@pytest.fixture
def normalize_split_config() -> Dict[str, Any]:
    """SplitApply config: normalize each axis variable independently."""
    return {
        "joinColumns": ["benchmark", "config"],
        "groups": [
            {
                "columns": ["ipc"],
                "pipeline": [
                    {
                        "type": "normalize",
                        "normalizeVars": ["ipc"],
                        "normalizerVars": ["ipc"],
                        "normalizerColumn": "config",
                        "normalizerValue": "base",
                        "groupBy": ["benchmark"],
                    }
                ],
            },
            {
                "columns": ["numCycles"],
                "pipeline": [
                    {
                        "type": "normalize",
                        "normalizeVars": ["numCycles"],
                        "normalizerVars": ["numCycles"],
                        "normalizerColumn": "config",
                        "normalizerValue": "base",
                        "groupBy": ["benchmark"],
                    }
                ],
            },
        ],
    }


# ============================================================================
# Parameter Validation
# ============================================================================


class TestSplitApplyValidation:
    """Parameter and precondition validation."""

    def test_missing_join_columns_raises(self) -> None:
        """Must provide joinColumns."""
        with pytest.raises(ValueError, match="joinColumns"):
            SplitApply(
                {
                    "joinColumns": [],
                    "groups": [
                        {"columns": ["a"], "pipeline": []},
                        {"columns": ["b"], "pipeline": []},
                    ],
                }
            )

    def test_single_group_raises(self) -> None:
        """Must have at least 2 groups."""
        with pytest.raises(ValueError, match="at least 2 groups"):
            SplitApply(
                {
                    "joinColumns": ["x"],
                    "groups": [{"columns": ["a"], "pipeline": []}],
                }
            )

    def test_empty_group_columns_raises(self) -> None:
        """Groups must have non-empty columns."""
        with pytest.raises(ValueError, match="non-empty"):
            SplitApply(
                {
                    "joinColumns": ["x"],
                    "groups": [
                        {"columns": [], "pipeline": []},
                        {"columns": ["b"], "pipeline": []},
                    ],
                }
            )

    def test_overlapping_columns_raises(self) -> None:
        """Same column in two groups is not allowed."""
        with pytest.raises(ValueError, match="multiple groups"):
            SplitApply(
                {
                    "joinColumns": ["x"],
                    "groups": [
                        {"columns": ["a", "b"], "pipeline": []},
                        {"columns": ["b", "c"], "pipeline": []},
                    ],
                }
            )

    def test_missing_join_column_in_dataframe_raises(self, dual_axis_data: pd.DataFrame) -> None:
        """Join column not in DataFrame raises ValueError."""
        shaper = SplitApply(
            {
                "joinColumns": ["benchmark", "nonexistent"],
                "groups": [
                    {"columns": ["ipc"], "pipeline": []},
                    {"columns": ["numCycles"], "pipeline": []},
                ],
            }
        )
        with pytest.raises(ValueError, match="nonexistent"):
            shaper(dual_axis_data)

    def test_missing_group_column_in_dataframe_raises(self, dual_axis_data: pd.DataFrame) -> None:
        """Group referencing nonexistent column raises ValueError."""
        shaper = SplitApply(
            {
                "joinColumns": ["benchmark", "config"],
                "groups": [
                    {"columns": ["ipc"], "pipeline": []},
                    {"columns": ["missing_col"], "pipeline": []},
                ],
            }
        )
        with pytest.raises(ValueError, match="missing_col"):
            shaper(dual_axis_data)


# ============================================================================
# Core Functionality: Independent Mean
# ============================================================================


class TestSplitApplyMean:
    """Mean sub-pipeline produces correct, non-duplicated results."""

    def test_independent_mean_no_duplicate_rows(
        self,
        dual_axis_data: pd.DataFrame,
        mean_split_config: Dict[str, Any],
    ) -> None:
        """Each group gets its own mean row; no duplicate mean rows."""
        shaper = SplitApply(mean_split_config)
        result = shaper(dual_axis_data)

        # Original 4 rows + 2 mean rows (one per config group)
        mean_rows = result[result["benchmark"] == "arithmean"]
        assert len(mean_rows) == 2, f"Expected 2 mean rows (one per config), got {len(mean_rows)}"

    def test_mean_values_are_correct_per_axis(
        self,
        dual_axis_data: pd.DataFrame,
        mean_split_config: Dict[str, Any],
    ) -> None:
        """Mean values are computed independently for each variable."""
        shaper = SplitApply(mean_split_config)
        result = shaper(dual_axis_data)

        mean_base = result[(result["benchmark"] == "arithmean") & (result["config"] == "base")]
        mean_opt = result[(result["benchmark"] == "arithmean") & (result["config"] == "opt")]

        # IPC mean for base: (1.2 + 1.4) / 2 = 1.3
        assert abs(mean_base["ipc"].iloc[0] - 1.3) < 1e-6
        # IPC mean for opt: (1.5 + 1.6) / 2 = 1.55
        assert abs(mean_opt["ipc"].iloc[0] - 1.55) < 1e-6

        # numCycles mean for base: (3210 + 7890) / 2 = 5550
        assert abs(mean_base["numCycles"].iloc[0] - 5550) < 1e-6
        # numCycles mean for opt: (2890 + 7120) / 2 = 5005
        assert abs(mean_opt["numCycles"].iloc[0] - 5005) < 1e-6

    def test_original_rows_preserved(
        self,
        dual_axis_data: pd.DataFrame,
        mean_split_config: Dict[str, Any],
    ) -> None:
        """Original data rows are unchanged after split-apply."""
        shaper = SplitApply(mean_split_config)
        result = shaper(dual_axis_data)

        non_mean = (
            result[result["benchmark"] != "arithmean"]
            .sort_values(["benchmark", "config"])
            .reset_index(drop=True)
        )

        original = dual_axis_data.sort_values(["benchmark", "config"]).reset_index(drop=True)

        # check_dtype=False because outer merge may promote int → float
        pd.testing.assert_frame_equal(non_mean, original, check_dtype=False)

    def test_total_row_count_with_mean(
        self,
        dual_axis_data: pd.DataFrame,
        mean_split_config: Dict[str, Any],
    ) -> None:
        """4 originals + 2 means = 6 total rows."""
        shaper = SplitApply(mean_split_config)
        result = shaper(dual_axis_data)
        assert len(result) == 6


# ============================================================================
# Core Functionality: Independent Normalize
# ============================================================================


class TestSplitApplyNormalize:
    """Normalize sub-pipeline produces correct per-axis baselines."""

    def test_normalized_values_independent(
        self,
        dual_axis_data: pd.DataFrame,
        normalize_split_config: Dict[str, Any],
    ) -> None:
        """Each variable is normalized by its own baseline value."""
        shaper = SplitApply(normalize_split_config)
        result = shaper(dual_axis_data)

        # Baselines should be 1.0
        base_mcf = result[(result["benchmark"] == "mcf") & (result["config"] == "base")]
        assert abs(base_mcf["ipc"].iloc[0] - 1.0) < 1e-6
        assert abs(base_mcf["numCycles"].iloc[0] - 1.0) < 1e-6

        # IPC for mcf/opt: 1.5 / 1.2 = 1.25
        opt_mcf = result[(result["benchmark"] == "mcf") & (result["config"] == "opt")]
        assert abs(opt_mcf["ipc"].iloc[0] - 1.25) < 1e-6

        # numCycles for mcf/opt: 2890 / 3210 ≈ 0.9003
        assert abs(opt_mcf["numCycles"].iloc[0] - (2890 / 3210)) < 1e-4

    def test_normalize_row_count_unchanged(
        self,
        dual_axis_data: pd.DataFrame,
        normalize_split_config: Dict[str, Any],
    ) -> None:
        """Normalize doesn't add or remove rows."""
        shaper = SplitApply(normalize_split_config)
        result = shaper(dual_axis_data)
        assert len(result) == len(dual_axis_data)


# ============================================================================
# Combined Pipeline: Mean + Normalize
# ============================================================================


class TestSplitApplyCombined:
    """Mean then Normalize in a sub-pipeline works correctly."""

    def test_mean_then_normalize_per_axis(self, dual_axis_data: pd.DataFrame) -> None:
        """Apply Mean then Normalize independently per group."""
        config: Dict[str, Any] = {
            "joinColumns": ["benchmark", "config"],
            "groups": [
                {
                    "columns": ["ipc"],
                    "pipeline": [
                        {
                            "type": "mean",
                            "meanVars": ["ipc"],
                            "meanAlgorithm": "arithmean",
                            "groupingColumns": ["config"],
                            "replacingColumn": "benchmark",
                        },
                        {
                            "type": "normalize",
                            "normalizeVars": ["ipc"],
                            "normalizerVars": ["ipc"],
                            "normalizerColumn": "config",
                            "normalizerValue": "base",
                            "groupBy": ["benchmark"],
                        },
                    ],
                },
                {
                    "columns": ["numCycles"],
                    "pipeline": [
                        {
                            "type": "mean",
                            "meanVars": ["numCycles"],
                            "meanAlgorithm": "arithmean",
                            "groupingColumns": ["config"],
                            "replacingColumn": "benchmark",
                        },
                        {
                            "type": "normalize",
                            "normalizeVars": ["numCycles"],
                            "normalizerVars": ["numCycles"],
                            "normalizerColumn": "config",
                            "normalizerValue": "base",
                            "groupBy": ["benchmark"],
                        },
                    ],
                },
            ],
        }

        shaper = SplitApply(config)
        result = shaper(dual_axis_data)

        # 4 original + 2 mean = 6 rows
        assert len(result) == 6

        # All base values should be 1.0 (normalized)
        base_rows = result[result["config"] == "base"]
        for _, row in base_rows.iterrows():
            assert abs(row["ipc"] - 1.0) < 1e-6, f"IPC for {row['benchmark']}/base should be 1.0"
            assert (
                abs(row["numCycles"] - 1.0) < 1e-6
            ), f"numCycles for {row['benchmark']}/base should be 1.0"

        # Mean rows should also be separately normalized
        mean_rows = result[result["benchmark"] == "arithmean"]
        assert len(mean_rows) == 2


# ============================================================================
# SD Columns
# ============================================================================


class TestSplitApplySD:
    """Standard deviation columns are auto-included."""

    def test_sd_columns_included_automatically(self, dual_axis_data_with_sd: pd.DataFrame) -> None:
        """SD columns matching group columns are carried through."""
        config: Dict[str, Any] = {
            "joinColumns": ["benchmark", "config"],
            "groups": [
                {"columns": ["ipc"], "pipeline": []},
                {"columns": ["numCycles"], "pipeline": []},
            ],
        }
        shaper = SplitApply(config)
        result = shaper(dual_axis_data_with_sd)

        assert "ipc.sd" in result.columns
        assert "numCycles.sd" in result.columns


# ============================================================================
# Empty Pipeline
# ============================================================================


class TestSplitApplyPassthrough:
    """Empty sub-pipeline passes data through unchanged."""

    def test_no_pipeline_returns_original_data(self, dual_axis_data: pd.DataFrame) -> None:
        """With empty pipelines, result equals original data."""
        config: Dict[str, Any] = {
            "joinColumns": ["benchmark", "config"],
            "groups": [
                {"columns": ["ipc"], "pipeline": []},
                {"columns": ["numCycles"], "pipeline": []},
            ],
        }
        shaper = SplitApply(config)
        result = shaper(dual_axis_data)

        # Same rows and columns (order may differ)
        assert len(result) == len(dual_axis_data)
        assert set(result.columns) == set(dual_axis_data.columns)

        # Values match
        result_sorted = result.sort_values(["benchmark", "config"]).reset_index(drop=True)
        original_sorted = dual_axis_data.sort_values(["benchmark", "config"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(result_sorted, original_sorted)


# ============================================================================
# Factory Registration
# ============================================================================


class TestSplitApplyFactory:
    """SplitApply is registered and instantiable via ShaperFactory."""

    def test_registered_in_factory(self) -> None:
        """splitApply type is available in the factory."""
        assert "splitApply" in ShaperFactory.get_available_types()

    def test_factory_creates_instance(self) -> None:
        """Factory.create_shaper produces a SplitApply instance."""
        params: Dict[str, Any] = {
            "joinColumns": ["x"],
            "groups": [
                {"columns": ["a"], "pipeline": []},
                {"columns": ["b"], "pipeline": []},
            ],
        }
        shaper = ShaperFactory.create_shaper("splitApply", params)
        assert isinstance(shaper, SplitApply)

    def test_display_name_exists(self) -> None:
        """splitApply has a display name in the factory."""
        name = ShaperFactory.get_display_name("splitApply")
        assert "Split" in name


# ============================================================================
# Sub-pipeline Error Handling
# ============================================================================


class TestSplitApplyErrors:
    """Sub-pipeline errors propagate with group context."""

    def test_sub_pipeline_error_includes_group_info(self, dual_axis_data: pd.DataFrame) -> None:
        """Errors from sub-pipeline include which group failed."""
        config: Dict[str, Any] = {
            "joinColumns": ["benchmark", "config"],
            "groups": [
                {
                    "columns": ["ipc"],
                    "pipeline": [
                        {
                            "type": "mean",
                            "meanVars": ["nonexistent_col"],
                            "meanAlgorithm": "arithmean",
                            "groupingColumns": ["config"],
                            "replacingColumn": "benchmark",
                        }
                    ],
                },
                {"columns": ["numCycles"], "pipeline": []},
            ],
        }
        shaper = SplitApply(config)
        with pytest.raises(ValueError, match="group 0"):
            shaper(dual_axis_data)


# ============================================================================
# Three-Group Split (Extensibility)
# ============================================================================


class TestSplitApplyThreeGroups:
    """SplitApply supports more than 2 groups."""

    def test_three_groups_merge_correctly(self) -> None:
        """Three groups with Mean each produce correct merged result."""
        data = pd.DataFrame(
            {
                "bench": ["a", "b"],
                "cfg": ["x", "x"],
                "v1": [10.0, 20.0],
                "v2": [100.0, 200.0],
                "v3": [1000.0, 2000.0],
            }
        )
        config: Dict[str, Any] = {
            "joinColumns": ["bench", "cfg"],
            "groups": [
                {
                    "columns": ["v1"],
                    "pipeline": [
                        {
                            "type": "mean",
                            "meanVars": ["v1"],
                            "meanAlgorithm": "arithmean",
                            "groupingColumns": ["cfg"],
                            "replacingColumn": "bench",
                        }
                    ],
                },
                {
                    "columns": ["v2"],
                    "pipeline": [
                        {
                            "type": "mean",
                            "meanVars": ["v2"],
                            "meanAlgorithm": "arithmean",
                            "groupingColumns": ["cfg"],
                            "replacingColumn": "bench",
                        }
                    ],
                },
                {
                    "columns": ["v3"],
                    "pipeline": [
                        {
                            "type": "mean",
                            "meanVars": ["v3"],
                            "meanAlgorithm": "arithmean",
                            "groupingColumns": ["cfg"],
                            "replacingColumn": "bench",
                        }
                    ],
                },
            ],
        }

        shaper = SplitApply(config)
        result = shaper(data)

        # 2 original + 1 mean = 3 rows
        assert len(result) == 3

        mean_row = result[result["bench"] == "arithmean"]
        assert len(mean_row) == 1
        assert abs(mean_row["v1"].iloc[0] - 15.0) < 1e-6
        assert abs(mean_row["v2"].iloc[0] - 150.0) < 1e-6
        assert abs(mean_row["v3"].iloc[0] - 1500.0) < 1e-6
