import numpy as np
import pandas as pd
import pytest

from src.core.services.shapers.impl.normalize import Normalize


@pytest.fixture
def base_data():
    return pd.DataFrame(
        {
            "config": ["baseline", "test", "baseline", "test"],
            "bench": ["b1", "b1", "b2", "b2"],
            "metric": [10.0, 20.0, 50.0, 25.0],
            "metric.sd": [1.0, 2.0, 5.0, 2.5],
            "other": ["x", "y", "z", "w"],
        }
    )


def test_init_validation():
    # Missing required params
    # Now handled in Normalize._verify_params and raised in BaseShaper constructor
    with pytest.raises(ValueError, match="Missing required parameter 'normalizeVars'"):
        Normalize({})

    with pytest.raises(ValueError, match="Missing required parameter 'normalizerColumn'"):
        Normalize({"normalizeVars": ["m"]})

    # Valid init
    n = Normalize(
        {
            "normalizeVars": ["metric"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )
    # Testing that it correctly initialized internal attributes
    assert n._normalizer_vars == ["metric"]


def test_verify_preconditions_missing_col(base_data):
    n = Normalize(
        {
            "normalizeVars": ["missing"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )
    with pytest.raises(ValueError, match="not found"):
        n._verify_preconditions(base_data)


def test_verify_preconditions_non_numeric(base_data):
    n = Normalize(
        {
            "normalizeVars": ["other"],  # non-numeric
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )
    with pytest.raises(ValueError, match="must be numeric"):
        n._verify_preconditions(base_data)


def test_verify_preconditions_multiple_normalizers():
    df = pd.DataFrame(
        {
            "config": ["baseline", "baseline", "test"],
            "bench": ["b1", "b1", "b1"],
            "metric": [10.0, 10.0, 20.0],
        }
    )
    n = Normalize(
        {
            "normalizeVars": ["metric"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )
    with pytest.raises(ValueError, match="Ambiguous baseline"):
        n._verify_preconditions(df)


def test_normalization_logic(base_data):
    n = Normalize(
        {
            "normalizeVars": ["metric"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )

    result = n(base_data)

    # Verify columns exist
    assert (
        "bench" in result.columns
    ), f"Column 'bench' not found. Available: {result.columns.tolist()}"
    assert "config" in result.columns
    assert "metric" in result.columns

    # Bench b1: baseline=10. test=20. Ratio should be 1.0 and 2.0
    b1 = result[result["bench"] == "b1"]
    assert b1[b1["config"] == "baseline"]["metric"].iloc[0] == 1.0
    assert b1[b1["config"] == "test"]["metric"].iloc[0] == 2.0

    # Bench b2: baseline=50. test=25. Ratio should be 1.0 and 0.5
    b2 = result[result["bench"] == "b2"]
    assert b2[b2["config"] == "baseline"]["metric"].iloc[0] == 1.0
    assert b2[b2["config"] == "test"]["metric"].iloc[0] == 0.5


def test_normalization_sd(base_data):
    n = Normalize(
        {
            "normalizeVars": ["metric"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
            "normalizeSd": True,
        }
    )

    result = n(base_data)

    # Verify columns exist
    assert (
        "bench" in result.columns
    ), f"Column 'bench' not found. Available: {result.columns.tolist()}"
    assert "config" in result.columns
    assert "metric.sd" in result.columns

    # Bench b1: baseline=10 (metric).
    b1 = result[result["bench"] == "b1"]
    np.testing.assert_almost_equal(b1[b1["config"] == "baseline"]["metric.sd"].iloc[0], 0.1)
    np.testing.assert_almost_equal(b1[b1["config"] == "test"]["metric.sd"].iloc[0], 0.2)


def test_zero_division():
    df = pd.DataFrame(
        {
            "config": ["baseline", "test"],
            "bench": ["b1", "b1"],
            "metric": [0.0, 10.0],  # Baseline is 0
        }
    )

    n = Normalize(
        {
            "normalizeVars": ["metric"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )

    result = n(df)

    # Should result in 0 instead of inf/nan
    assert result["metric"].iloc[0] == 0.0
    assert result["metric"].iloc[1] == 0.0


def test_different_normalizer_vars():
    # Use 'norm_base' col to normalize 'metric' col
    df = pd.DataFrame(
        {
            "config": ["baseline", "test"],
            "bench": ["b1", "b1"],
            "metric": [100.0, 200.0],
            "norm_base": [10.0, 20.0],
        }
    )

    # Explicitly providing normalizerVars
    n = Normalize(
        {
            "normalizeVars": ["metric"],
            "normalizerVars": ["norm_base"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )

    result = n(df)

    # Baseline normalizer value = 10.0 (from norm_base)
    # metric normalized: 100/10 = 10, 200/10 = 20
    assert result["metric"].iloc[0] == 10.0
    assert result["metric"].iloc[1] == 20.0


# ─── Additional Coverage Tests ──────────────────────────────────────────────


class TestValidateInitTypes:
    """Tests for _validate_init_types — type validation at construction."""

    def test_normalize_vars_must_be_list(self) -> None:
        with pytest.raises(TypeError, match="normalizeVars must be a list"):
            Normalize(
                {
                    "normalizeVars": "metric",  # should be list
                    "normalizerColumn": "config",
                    "normalizerValue": "baseline",
                    "groupBy": ["bench"],
                }
            )

    def test_group_by_must_be_list(self) -> None:
        with pytest.raises(TypeError, match="groupBy must be a list"):
            Normalize(
                {
                    "normalizeVars": ["metric"],
                    "normalizerColumn": "config",
                    "normalizerValue": "baseline",
                    "groupBy": "bench",  # should be list
                }
            )

    def test_normalizer_column_must_be_string(self) -> None:
        with pytest.raises(TypeError, match="normalizerColumn must be a string"):
            Normalize(
                {
                    "normalizeVars": ["metric"],
                    "normalizerColumn": 123,  # should be str
                    "normalizerValue": "baseline",
                    "groupBy": ["bench"],
                }
            )

    def test_normalize_sd_must_be_bool(self) -> None:
        with pytest.raises(TypeError, match="normalizeSd must be a boolean"):
            Normalize(
                {
                    "normalizeVars": ["metric"],
                    "normalizerColumn": "config",
                    "normalizerValue": "baseline",
                    "groupBy": ["bench"],
                    "normalizeSd": "yes",  # should be bool
                }
            )


class TestNormalizeSdDisabled:
    """Test that normalizeSd=False leaves .sd columns untouched."""

    def test_sd_columns_not_normalized(self) -> None:
        df = pd.DataFrame(
            {
                "config": ["baseline", "test", "baseline", "test"],
                "bench": ["b1", "b1", "b2", "b2"],
                "metric": [10.0, 20.0, 50.0, 25.0],
                "metric.sd": [1.0, 2.0, 5.0, 2.5],
            }
        )
        n = Normalize(
            {
                "normalizeVars": ["metric"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",
                "groupBy": ["bench"],
                "normalizeSd": False,
            }
        )
        result = n(df)
        # .sd columns should remain unchanged
        np.testing.assert_array_equal(result["metric.sd"].values, [1.0, 2.0, 5.0, 2.5])


class TestComputeDataFingerprint:
    """Tests for _compute_data_fingerprint."""

    def test_returns_string(self) -> None:
        df = pd.DataFrame({"config": ["a"], "bench": ["b"], "metric": [1.0]})
        params = {
            "normalizeVars": ["metric"],
            "normalizerColumn": "config",
            "groupBy": ["bench"],
        }
        fp = Normalize._compute_data_fingerprint(df, params)
        assert isinstance(fp, str)
        assert len(fp) == 16  # md5 hex[:16]

    def test_same_data_same_fingerprint(self) -> None:
        df = pd.DataFrame({"config": ["a", "b"], "bench": ["b1", "b1"], "m": [1.0, 2.0]})
        params = {"normalizeVars": ["m"], "normalizerColumn": "config", "groupBy": ["bench"]}
        fp1 = Normalize._compute_data_fingerprint(df, params)
        fp2 = Normalize._compute_data_fingerprint(df, params)
        assert fp1 == fp2

    def test_different_data_different_fingerprint(self) -> None:
        df1 = pd.DataFrame({"config": ["a"], "bench": ["b"], "m": [1.0]})
        df2 = pd.DataFrame({"config": ["a"], "bench": ["b"], "m": [2.0]})
        params = {"normalizeVars": ["m"], "normalizerColumn": "config", "groupBy": ["bench"]}
        fp1 = Normalize._compute_data_fingerprint(df1, params)
        fp2 = Normalize._compute_data_fingerprint(df2, params)
        assert fp1 != fp2


class TestVerifyPreconditionsEdgeCases:
    """Additional edge cases for _verify_preconditions."""

    def test_baseline_value_not_found(self) -> None:
        """When normalizerValue doesn't exist in the column."""
        df = pd.DataFrame(
            {
                "config": ["test", "test"],
                "bench": ["b1", "b1"],
                "metric": [10.0, 20.0],
            }
        )
        n = Normalize(
            {
                "normalizeVars": ["metric"],
                "normalizerColumn": "config",
                "normalizerValue": "baseline",  # not in data
                "groupBy": ["bench"],
            }
        )
        with pytest.raises(ValueError, match="not found"):
            n._verify_preconditions(df)

    def test_normalizer_column_not_found(self) -> None:
        """When normalizerColumn doesn't exist in DataFrame."""
        df = pd.DataFrame(
            {
                "bench": ["b1"],
                "metric": [10.0],
            }
        )
        n = Normalize(
            {
                "normalizeVars": ["metric"],
                "normalizerColumn": "missing_col",
                "normalizerValue": "baseline",
                "groupBy": ["bench"],
            }
        )
        with pytest.raises(ValueError, match="not found"):
            n._verify_preconditions(df)
