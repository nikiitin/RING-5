"""Edge case tests for shaper implementations.

Covers: unicode column names, numeric precision, NaN propagation chains,
extreme value ratios in normalization, large DataFrames, and mixed data types.
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.core.services.shapers.impl.mean import Mean
from src.core.services.shapers.impl.normalize import Normalize
from src.core.services.shapers.impl.selector_algorithms.column_selector import ColumnSelector
from src.core.services.shapers.impl.selector_algorithms.condition_selector import ConditionSelector
from src.core.services.shapers.impl.selector_algorithms.item_selector import ItemSelector

# ---------------------------------------------------------------------------
# 1. Unicode column names
# ---------------------------------------------------------------------------


class TestUnicodeColumns:
    """Verify shapers handle non-ASCII column names correctly."""

    def test_column_selector_unicode(self) -> None:
        df = pd.DataFrame({"café": [1, 2], "naïve": [3, 4], "Ω": [5, 6]})
        selector = ColumnSelector({"columns": ["café", "Ω"]})
        result = selector(df)
        assert list(result.columns) == ["café", "Ω"]
        assert len(result) == 2

    def test_item_selector_unicode_values(self) -> None:
        df = pd.DataFrame({"name": ["café", "naïve", "résumé"], "val": [1, 2, 3]})
        selector = ItemSelector({"column": "name", "strings": ["café", "résumé"]})
        result = selector(df)
        assert len(result) == 2
        assert set(result["name"]) == {"café", "résumé"}

    def test_condition_selector_contains_unicode(self) -> None:
        df = pd.DataFrame({"name": ["café", "naïve", "résumé"], "val": [1, 2, 3]})
        selector = ConditionSelector({"column": "name", "mode": "contains", "value": "é"})
        result = selector(df)
        assert len(result) == 2
        assert set(result["name"]) == {"café", "résumé"}

    def test_mean_unicode_grouping(self) -> None:
        df = pd.DataFrame(
            {
                "类型": ["A", "A", "B", "B"],
                "配置": ["base", "base", "base", "base"],
                "值": [10.0, 20.0, 30.0, 40.0],
            }
        )
        meaner = Mean(
            {
                "meanVars": ["值"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["类型"],
                "replacingColumn": "配置",
            }
        )
        result = meaner(df)
        assert len(result) == 6  # 4 originals + 2 mean rows
        mean_rows = result[result["配置"] == "arithmean"]
        assert len(mean_rows) == 2


# ---------------------------------------------------------------------------
# 2. Numeric precision
# ---------------------------------------------------------------------------


class TestNumericPrecision:
    """Verify shapers maintain numeric precision for edge cases."""

    def test_normalize_very_small_baseline(self) -> None:
        """Normalization with a very small baseline denominator."""
        df = pd.DataFrame(
            {
                "config": ["baseline", "test"],
                "bench": ["B1", "B1"],
                "metric": [1e-15, 1e-10],
            }
        )
        normalizer = Normalize(
            {
                "normalizeVars": ["metric"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["bench"],
            }
        )
        result = normalizer(df)
        test_row = result[result["config"] == "test"]
        # 1e-10 / 1e-15 = 1e5
        assert abs(test_row["metric"].iloc[0] - 1e5) < 1.0

    def test_normalize_very_large_ratio(self) -> None:
        """Normalization where test value is 1e6x the baseline."""
        df = pd.DataFrame(
            {
                "config": ["baseline", "test"],
                "bench": ["B1", "B1"],
                "metric": [1.0, 1e6],
            }
        )
        normalizer = Normalize(
            {
                "normalizeVars": ["metric"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["bench"],
            }
        )
        result = normalizer(df)
        test_row = result[result["config"] == "test"]
        assert test_row["metric"].iloc[0] == pytest.approx(1e6)

    def test_mean_precision_many_values(self) -> None:
        """Arithmetic mean with values that could suffer from float accumulation."""
        n = 1000
        df = pd.DataFrame(
            {
                "benchmark": [f"bm{i}" for i in range(n)],
                "config": ["base"] * n,
                "metric": [0.1] * n,  # sum = 100.0 exactly in IEEE 754
            }
        )
        meaner = Mean(
            {
                "meanVars": ["metric"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )
        result = meaner(df)
        mean_row = result[result["benchmark"] == "arithmean"]
        assert mean_row["metric"].iloc[0] == pytest.approx(0.1, abs=1e-10)


# ---------------------------------------------------------------------------
# 3. NaN propagation through shaper chains
# ---------------------------------------------------------------------------


class TestNaNPropagation:
    """Verify correct NaN handling when shapers are chained."""

    def test_normalize_all_nan_baseline(self) -> None:
        """If baseline value is NaN, normalized values should be 0 (zero-denominator path)."""
        df = pd.DataFrame(
            {
                "config": ["baseline", "test"],
                "bench": ["B1", "B1"],
                "metric": [float("nan"), 5.0],
            }
        )
        normalizer = Normalize(
            {
                "normalizeVars": ["metric"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["bench"],
            }
        )
        result = normalizer(df)
        test_row = result[result["config"] == "test"]
        assert test_row["metric"].iloc[0] == 0.0

    def test_geomean_all_nan(self) -> None:
        """Geometric mean of all NaN values returns NaN."""
        df = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm2"],
                "config": ["base", "base"],
                "metric": [float("nan"), float("nan")],
            }
        )
        meaner = Mean(
            {
                "meanVars": ["metric"],
                "meanAlgorithm": "geomean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )
        result = meaner(df)
        mean_row = result[result["benchmark"] == "geomean"]
        assert math.isnan(mean_row["metric"].iloc[0])

    def test_hmean_with_zero_values(self) -> None:
        """Harmonic mean with zero values returns NaN (non-positive guard)."""
        df = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm2", "bm3"],
                "config": ["base", "base", "base"],
                "metric": [0.0, 1.0, 2.0],
            }
        )
        meaner = Mean(
            {
                "meanVars": ["metric"],
                "meanAlgorithm": "hmean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )
        result = meaner(df)
        mean_row = result[result["benchmark"] == "hmean"]
        assert math.isnan(mean_row["metric"].iloc[0])


# ---------------------------------------------------------------------------
# 4. Large DataFrame performance smoke test
# ---------------------------------------------------------------------------


class TestLargeDataFrame:
    """Verify shapers work correctly on larger datasets."""

    @pytest.fixture
    def large_df(self) -> pd.DataFrame:
        rng = np.random.default_rng(42)
        n = 10_000
        return pd.DataFrame(
            {
                "benchmark": [f"bm{i % 100}" for i in range(n)],
                "config": [f"cfg{i % 10}" for i in range(n)],
                "metric": rng.standard_normal(n) + 100,
            }
        )

    def test_column_selector_large(self, large_df: pd.DataFrame) -> None:
        selector = ColumnSelector({"columns": ["benchmark", "metric"]})
        result = selector(large_df)
        assert len(result) == 10_000
        assert list(result.columns) == ["benchmark", "metric"]

    def test_condition_selector_large(self, large_df: pd.DataFrame) -> None:
        selector = ConditionSelector(
            {"column": "metric", "mode": "greater_than", "threshold": 100.0}
        )
        result = selector(large_df)
        assert isinstance(result, pd.DataFrame)
        assert all(v > 100.0 for v in result["metric"])


# ---------------------------------------------------------------------------
# 5. Mixed numeric types
# ---------------------------------------------------------------------------


class TestMixedNumericTypes:
    """Verify shapers handle mixed int/float columns correctly."""

    def test_normalize_int_column(self) -> None:
        """Normalize should work on integer columns without type errors."""
        df = pd.DataFrame(
            {
                "config": ["baseline", "test"],
                "bench": ["B1", "B1"],
                "cycles": [1000, 1500],  # integers, not floats
            }
        )
        normalizer = Normalize(
            {
                "normalizeVars": ["cycles"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["bench"],
            }
        )
        result = normalizer(df)
        test_row = result[result["config"] == "test"]
        assert test_row["cycles"].iloc[0] == pytest.approx(1.5)

    def test_mean_int_column(self) -> None:
        """Mean should work on integer columns."""
        df = pd.DataFrame(
            {
                "benchmark": ["bm1", "bm2"],
                "config": ["base", "base"],
                "cycles": [100, 200],
            }
        )
        meaner = Mean(
            {
                "meanVars": ["cycles"],
                "meanAlgorithm": "arithmean",
                "groupingColumns": ["config"],
                "replacingColumn": "benchmark",
            }
        )
        result = meaner(df)
        mean_row = result[result["benchmark"] == "arithmean"]
        assert mean_row["cycles"].iloc[0] == pytest.approx(150.0)
