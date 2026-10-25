"""Regression tests for numerical shapers and parser result handling."""

import math
import os
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest


class TestMeanNaNHandling:
    """Verify the Mean shaper correctly handles NaN values for all algorithms."""

    def _build_df(self) -> pd.DataFrame:
        """Build a small DataFrame with NaN values for testing."""
        return pd.DataFrame(
            {
                "benchmark": ["bm1", "bm2", "bm3"],
                "config": ["base", "base", "base"],
                "ipc": [1.5, float("nan"), 2.0],
            }
        )

    def test_arithmean_with_nan_values(self) -> None:
        """Arithmetic mean should propagate NaN via pandas default behavior."""
        # [test->req~ring5.shaping.mean~1]
        from src.core.services.shapers.impl.mean import Mean

        df = self._build_df()
        meaner = Mean(
            {
                "meanVars": ["ipc"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )

        result = meaner(df)

        # The mean row should exist
        mean_row = result[result["benchmark"] == "arithmean"]
        assert len(mean_row) == 1

        # pandas .mean() skips NaN by default, so result is (1.5 + 2.0) / 2
        mean_val = mean_row["ipc"].iloc[0]
        assert not math.isnan(mean_val)
        assert mean_val == pytest.approx(1.75)

    def test_geomean_with_nan_skips_nan(self) -> None:
        """Geometric mean should skip NaN and compute from remaining values."""
        from src.core.services.shapers.impl.mean import Mean

        df = self._build_df()
        meaner = Mean(
            {
                "meanVars": ["ipc"],
                "meanAlgorithm": "geomean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )

        result = meaner(df)
        mean_row = result[result["benchmark"] == "geomean"]
        assert len(mean_row) == 1

        mean_val = mean_row["ipc"].iloc[0]
        # _safe_gmean drops NaN, computes gmean(1.5, 2.0)
        from scipy.stats import gmean

        expected = float(gmean([1.5, 2.0]))
        assert mean_val == pytest.approx(expected, rel=1e-6)

    def test_hmean_with_nan_skips_nan(self) -> None:
        """Harmonic mean should skip NaN and compute from remaining values."""
        from src.core.services.shapers.impl.mean import Mean

        df = self._build_df()
        meaner = Mean(
            {
                "meanVars": ["ipc"],
                "meanAlgorithm": "hmean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )

        result = meaner(df)
        mean_row = result[result["benchmark"] == "hmean"]
        assert len(mean_row) == 1

        mean_val = mean_row["ipc"].iloc[0]
        # _safe_hmean drops NaN, computes hmean(1.5, 2.0)
        from scipy.stats import hmean

        expected = float(hmean([1.5, 2.0]))
        assert mean_val == pytest.approx(expected, rel=1e-6)

    def test_geomean_with_zero_returns_nan(self) -> None:
        """Geometric mean with zero values should return NaN (non-positive guard)."""
        from src.core.services.shapers.impl.mean import Mean

        df = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm2"],
                "config": ["base", "base"],
                "ipc": [0.0, 2.0],
            }
        )

        meaner = Mean(
            {
                "meanVars": ["ipc"],
                "meanAlgorithm": "geomean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )

        result = meaner(df)
        mean_row = result[result["benchmark"] == "geomean"]
        mean_val = mean_row["ipc"].iloc[0]
        assert math.isnan(mean_val)

    def test_safe_gmean_all_nan_returns_nan(self) -> None:
        """_safe_gmean on an all-NaN series should return NaN (empty after dropna)."""
        from src.core.services.shapers.impl.mean import _safe_gmean

        series = pd.Series([float("nan"), float("nan")])
        result = _safe_gmean(series)
        assert math.isnan(result)

    def test_safe_hmean_all_nan_returns_nan(self) -> None:
        """_safe_hmean on an all-NaN series should return NaN (empty after dropna)."""
        from src.core.services.shapers.impl.mean import _safe_hmean

        series = pd.Series([float("nan"), float("nan")])
        result = _safe_hmean(series)
        assert math.isnan(result)

    def test_safe_hmean_with_zero_returns_nan(self) -> None:
        """_safe_hmean with zero values should return NaN (non-positive guard)."""
        from src.core.services.shapers.impl.mean import _safe_hmean

        series = pd.Series([0.0, 1.0, 2.0])
        result = _safe_hmean(series)
        assert math.isnan(result)


class TestScalarReduceDuplicatesNaN:
    """Verify Scalar.reduce_duplicates returns math.nan for empty content."""

    def test_empty_content_produces_nan_not_string(self) -> None:
        """Balancing an absent scalar pads NaN rather than a fabricated value."""
        from src.parsing.gem5.types.scalar import Scalar

        scalar = Scalar(repeat=1)
        scalar.balance_content()
        scalar.reduce_duplicates()
        assert isinstance(scalar.reduced_content, float)
        assert math.isnan(scalar.reduced_content)

    def test_abstract_base_does_not_publish_a_text_missing_value(self) -> None:
        """The base is abstract; concrete empty numeric reduction remains NaN."""
        from src.parsing.gem5.types.base import StatType
        from src.parsing.gem5.types.scalar import Scalar

        with pytest.raises(TypeError, match="abstract"):
            StatType(repeat=1)
        scalar = Scalar(repeat=1)
        scalar.balance_content()
        scalar.reduce_duplicates()
        assert isinstance(scalar.reduced_content, float)
        assert math.isnan(scalar.reduced_content)

    def test_single_value_reduces_correctly(self) -> None:
        """A Scalar with one value should reduce to that value."""
        from src.parsing.gem5.types.scalar import Scalar

        scalar = Scalar(repeat=1)
        scalar.add_observation(42)
        scalar.balance_content()
        scalar.reduce_duplicates()

        assert scalar.reduced_content == pytest.approx(42.0)

    def test_multiple_repeats_average(self) -> None:
        """A Scalar with repeat=2 should average the two values."""
        from src.parsing.gem5.types.scalar import Scalar

        scalar = Scalar(repeat=2)
        scalar.add_observation(10)
        scalar.add_observation(20)
        scalar.balance_content()
        scalar.reduce_duplicates()

        assert scalar.reduced_content == pytest.approx(15.0)


class TestDistributionMathFsum:
    """Verify Distribution uses math.fsum for numerical precision."""

    def test_fractional_observation_preserves_precision(self) -> None:
        """A typed complete frequency frame retains its fractional measurement."""
        from src.parsing.gem5.types.distribution import Distribution

        dist = Distribution(repeat=1, minimum=0, maximum=1)
        dist.add_observation({"underflows": 0.6, "0": 1.0, "1": 2.0, "overflows": 0.0})
        assert dist.content["underflows"] == [pytest.approx(0.6)]

    def test_reduce_duplicates_uses_fsum(self) -> None:
        """reduce_duplicates should use math.fsum for precision in averaging."""
        from src.parsing.gem5.types.distribution import Distribution

        dist = Distribution(repeat=2, minimum=0, maximum=0)

        # First content set (repeat 1)
        dist.add_observation({"underflows": 0.30000000000000004, "0": 100.0, "overflows": 0.0})
        # Second content set (repeat 2)
        dist.add_observation({"underflows": 0.3, "0": 200.0, "overflows": 0.0})

        dist.balance_content()
        dist.reduce_duplicates()

        reduced = dist.reduced_content
        # Bucket "0" had values [100.0, 200.0] across 2 repeats
        assert reduced["0"] == pytest.approx(150.0)

    def test_reduce_duplicates_empty_bucket(self) -> None:
        """Measured zero boundaries remain zero through numeric reduction."""
        from src.parsing.gem5.types.distribution import Distribution

        dist = Distribution(repeat=1, minimum=0, maximum=0)
        # All required buckets are explicitly measured in this frame.
        dist.add_observation({"underflows": 0.0, "0": 5.0, "overflows": 0.0})

        dist.balance_content()
        dist.reduce_duplicates()

        reduced = dist.reduced_content
        assert reduced["underflows"] == pytest.approx(0.0)
        assert reduced["0"] == pytest.approx(5.0)
        assert reduced["overflows"] == pytest.approx(0.0)


class TestExtractWithPattern:
    """Verify extract_with_pattern handles edge cases gracefully."""

    def test_invalid_regex_returns_original(self) -> None:
        """An invalid regex pattern should return the original value."""
        from src.core.services.shapers.impl.pivot import extract_with_pattern

        result = extract_with_pattern("hello_world", "[invalid(regex", [1])
        assert result == "hello_world"

    def test_non_matching_input_returns_original(self) -> None:
        """A valid regex that does not match should return the original value."""
        from src.core.services.shapers.impl.pivot import extract_with_pattern

        result = extract_with_pattern("no_match_here", r"^(foo)_(bar)$", [1])
        assert result == "no_match_here"

    def test_matching_input_extracts_single_group(self) -> None:
        """A matching regex should extract the requested group."""
        from src.core.services.shapers.impl.pivot import extract_with_pattern

        result = extract_with_pattern("cpu0_ipc", r"(cpu\d+)_(.*)", [1])
        assert result == "cpu0"

    def test_matching_input_extracts_multiple_groups(self) -> None:
        """Multiple group indices should be joined with the separator."""
        from src.core.services.shapers.impl.pivot import extract_with_pattern

        result = extract_with_pattern(
            "cpu0_ipc_total", r"(cpu\d+)_(\w+)_(\w+)", [1, 3], separator="/"
        )
        assert result == "cpu0/total"

    def test_out_of_range_group_index_skipped(self) -> None:
        """Group indices beyond the number of groups should be silently skipped."""
        from src.core.services.shapers.impl.pivot import extract_with_pattern

        # Pattern has 2 groups, but we request group 5
        result = extract_with_pattern("cpu0_ipc", r"(cpu\d+)_(.*)", [1, 5])
        assert result == "cpu0"

    def test_all_groups_out_of_range_returns_original(self) -> None:
        """If all requested groups are out of range, return original value."""
        from src.core.services.shapers.impl.pivot import extract_with_pattern

        result = extract_with_pattern("cpu0_ipc", r"(cpu\d+)_(.*)", [10, 20])
        assert result == "cpu0_ipc"

    def test_custom_separator(self) -> None:
        """Custom separator should be used when joining multiple groups."""
        from src.core.services.shapers.impl.pivot import extract_with_pattern

        result = extract_with_pattern(
            "system_cpu0_l2cache", r"(\w+)_(\w+)_(\w+)", [1, 2, 3], separator="::"
        )
        assert result == "system::cpu0::l2cache"


class TestConstructFinalCsvHeaderUnion:
    """Verify construct_final_csv builds the header from the union of results."""

    def test_header_union_from_multiple_results(self, tmp_path: Path) -> None:
        """
        When the first result lacks a variable that later results have,
        the header should still include columns for that variable.
        """
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        # Result 1 has varA but not varB
        var_a1 = MagicMock()
        var_a1.entries = []
        var_a1.balance_content = MagicMock()
        var_a1.reduce_duplicates = MagicMock()
        var_a1.reduced_content = "10"

        # Result 2 has both varA and varB
        var_a2 = MagicMock()
        var_a2.entries = []
        var_a2.balance_content = MagicMock()
        var_a2.reduce_duplicates = MagicMock()
        var_a2.reduced_content = "20"

        var_b2 = MagicMock()
        var_b2.entries = []
        var_b2.balance_content = MagicMock()
        var_b2.reduce_duplicates = MagicMock()
        var_b2.reduced_content = "30"

        results = [
            {"varA": var_a1},
            {"varA": var_a2, "varB": var_b2},
        ]

        csv_path = Gem5Parser.construct_final_csv(
            str(tmp_path), results, var_names=["varA", "varB"]
        )

        assert csv_path is not None
        assert os.path.exists(csv_path)

        with open(csv_path) as f:
            lines = f.readlines()

        header = lines[0].strip()
        assert "varA" in header
        assert "varB" in header

        # Row 1 should have NaN for missing varB
        row1 = lines[1].strip()
        assert "10" in row1
        assert "NaN" in row1

        # Row 2 should have both values
        row2 = lines[2].strip()
        assert "20" in row2
        assert "30" in row2

    def test_header_union_with_entries(self, tmp_path: Path) -> None:
        """
        Variables with entries expand into multiple columns.
        The header should reflect the entries even if the variable
        appears only in a later result.
        """
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        # Result 1 has only scalar_var
        scalar_var = MagicMock()
        scalar_var.entries = []
        scalar_var.balance_content = MagicMock()
        scalar_var.reduce_duplicates = MagicMock()
        scalar_var.reduced_content = "99"

        # Result 2 has scalar_var and dist_var (with entries)
        scalar_var2 = MagicMock()
        scalar_var2.entries = []
        scalar_var2.balance_content = MagicMock()
        scalar_var2.reduce_duplicates = MagicMock()
        scalar_var2.reduced_content = "100"

        dist_var = MagicMock()
        dist_var.entries = ["bucket_0", "bucket_1"]
        dist_var.balance_content = MagicMock()
        dist_var.reduce_duplicates = MagicMock()
        dist_var.reduced_content = {"bucket_0": "5.0", "bucket_1": "15.0"}

        results = [
            {"scalar_var": scalar_var},
            {"scalar_var": scalar_var2, "dist_var": dist_var},
        ]

        csv_path = Gem5Parser.construct_final_csv(
            str(tmp_path), results, var_names=["scalar_var", "dist_var"]
        )

        assert csv_path is not None

        with open(csv_path) as f:
            lines = f.readlines()

        header = lines[0].strip()
        assert "scalar_var" in header
        assert "dist_var..bucket_0" in header
        assert "dist_var..bucket_1" in header

    def test_empty_results_returns_none(self) -> None:
        """An empty results list should return None."""
        from src.parsing.gem5.impl.gem5_parser import Gem5Parser

        result = Gem5Parser.construct_final_csv("/tmp/nonexistent", [])
        assert result is None


class TestNormalizeNaNBaseline:
    """Verify Normalize handles NaN and zero baselines safely."""

    def test_nan_baseline_keeps_normalized_columns_missing(self) -> None:
        """When the baseline denominator is NaN, normalized values remain missing."""
        from src.core.services.shapers.impl.normalize import Normalize

        df = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm1"],
                "config": ["baseline", "test"],
                "cycles": [float("nan"), 1500.0],
            }
        )

        normalizer = Normalize(
            {
                "normalizeVars": ["cycles"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
            }
        )

        result = normalizer(df)
        # Both ratios are undefined because the baseline is unknown.
        assert result["cycles"].isna().all()

    def test_zero_baseline_keeps_normalized_columns_missing(self) -> None:
        """When the baseline denominator is zero, normalized values remain missing."""
        from src.core.services.shapers.impl.normalize import Normalize

        df = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm1"],
                "config": ["baseline", "test"],
                "cycles": [0.0, 1500.0],
            }
        )

        normalizer = Normalize(
            {
                "normalizeVars": ["cycles"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["benchmark"],
            }
        )

        result = normalizer(df)
        assert result["cycles"].isna().all()
