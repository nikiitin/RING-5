"""Tests for Normalize shaper — additional branch coverage.

Focus: zero denominator, sd column normalization, fingerprint caching,
precondition checks (ambiguous baseline, non-numeric).
"""

from typing import Any, Dict

import pandas as pd
import pytest

from src.core.services.shapers.impl.normalize import Normalize


def _make_params(**kwargs: Any) -> Dict[str, Any]:
    base = {
        "normalizeVars": ["cycles"],
        "normalizerColumn": "config",
        "normalizerValue": "baseline",
        "groupBy": ["bench"],
    }
    base.update(kwargs)
    return base


class TestNormalizeZeroDenominator:
    """When baseline value is 0, division by zero must be handled."""

    def test_zero_baseline_zeros_normalized(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "eval"],
                "bench": ["B1", "B1"],
                "cycles": [0, 100],
            }
        )
        n = Normalize(_make_params())
        result = n(df)
        assert result["cycles"].iloc[0] == 0.0
        assert result["cycles"].iloc[1] == 0.0


class TestNormalizeSdColumns:
    """Test normalization of .sd companion columns."""

    def test_sd_columns_normalized(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "eval"],
                "bench": ["B1", "B1"],
                "cycles": [100.0, 200.0],
                "cycles.sd": [10.0, 20.0],
            }
        )
        n = Normalize(_make_params())
        result = n(df)
        assert result["cycles.sd"].iloc[0] == pytest.approx(0.1)
        assert result["cycles.sd"].iloc[1] == pytest.approx(0.2)

    def test_sd_columns_disabled(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "eval"],
                "bench": ["B1", "B1"],
                "cycles": [100.0, 200.0],
                "cycles.sd": [10.0, 20.0],
            }
        )
        n = Normalize(_make_params(normalizeSd=False))
        result = n(df)
        # sd columns should remain unchanged
        assert result["cycles.sd"].iloc[0] == 10.0

    def test_sd_columns_zero_denominator(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "eval"],
                "bench": ["B1", "B1"],
                "cycles": [0.0, 200.0],
                "cycles.sd": [10.0, 20.0],
            }
        )
        n = Normalize(_make_params())
        result = n(df)
        assert result["cycles.sd"].iloc[0] == 0.0


class TestNormalizePreconditions:
    """Test _verify_preconditions error branches."""

    def test_missing_numeric_column(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "eval"],
                "bench": ["B1", "B1"],
            }
        )
        n = Normalize(_make_params())
        with pytest.raises(ValueError, match="not found in dataframe"):
            n(df)

    def test_non_numeric_column(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "eval"],
                "bench": ["B1", "B1"],
                "cycles": ["abc", "def"],  # string, not numeric
            }
        )
        n = Normalize(_make_params())
        with pytest.raises(ValueError, match="must be numeric"):
            n(df)

    def test_missing_normalizer_column(self) -> None:
        df = pd.DataFrame(
            {
                "bench": ["B1", "B1"],
                "cycles": [100, 200],
            }
        )
        n = Normalize(_make_params())
        with pytest.raises(ValueError, match="not found"):
            n(df)

    def test_baseline_value_not_found(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["eval1", "eval2"],
                "bench": ["B1", "B1"],
                "cycles": [100, 200],
            }
        )
        n = Normalize(_make_params())
        with pytest.raises(ValueError, match="not found in column"):
            n(df)

    def test_ambiguous_baseline(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "baseline", "eval"],
                "bench": ["B1", "B1", "B1"],
                "cycles": [100, 110, 200],
            }
        )
        n = Normalize(_make_params())
        with pytest.raises(ValueError, match="Ambiguous baseline"):
            n(df)


class TestNormalizeTypeValidation:
    """Test _validate_init_types error branches."""

    def test_normalize_vars_not_list(self) -> None:
        with pytest.raises(TypeError, match="must be a list"):
            Normalize(_make_params(normalizeVars="cycles"))

    def test_group_by_not_list(self) -> None:
        with pytest.raises(TypeError, match="must be a list"):
            Normalize(_make_params(groupBy="bench"))

    def test_normalizer_column_not_string(self) -> None:
        with pytest.raises(TypeError, match="must be a string"):
            Normalize(_make_params(normalizerColumn=123))

    def test_normalize_sd_not_bool(self) -> None:
        with pytest.raises(TypeError, match="must be a boolean"):
            Normalize(_make_params(normalizeSd="yes"))


class TestComputeDataFingerprint:
    """Test _compute_data_fingerprint."""

    def test_same_data_same_fingerprint(self) -> None:
        df = pd.DataFrame({"config": ["baseline"], "bench": ["B1"], "cycles": [1]})
        params = _make_params()
        fp1 = Normalize._compute_data_fingerprint(df, params)
        fp2 = Normalize._compute_data_fingerprint(df, params)
        assert fp1 == fp2

    def test_different_data_different_fingerprint(self) -> None:
        df1 = pd.DataFrame({"config": ["baseline"], "bench": ["B1"], "cycles": [1]})
        df2 = pd.DataFrame({"config": ["baseline"], "bench": ["B1"], "cycles": [999]})
        params = _make_params()
        fp1 = Normalize._compute_data_fingerprint(df1, params)
        fp2 = Normalize._compute_data_fingerprint(df2, params)
        assert fp1 != fp2

    def test_empty_dataframe(self) -> None:
        df = pd.DataFrame()
        params = _make_params()
        fp = Normalize._compute_data_fingerprint(df, params)
        assert isinstance(fp, str)
        assert len(fp) == 16


class TestNormalizeMultipleVars:
    """Test normalization with normalizerVars different from normalizeVars."""

    def test_sum_normalizer_vars(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "eval"],
                "bench": ["B1", "B1"],
                "cycles": [100.0, 200.0],
                "energy": [50.0, 60.0],
            }
        )
        n = Normalize(
            _make_params(
                normalizeVars=["cycles"],
                normalizerVars=["cycles", "energy"],
            )
        )
        result = n(df)
        # Denominator = 100 + 50 = 150
        assert result["cycles"].iloc[1] == pytest.approx(200.0 / 150.0)
