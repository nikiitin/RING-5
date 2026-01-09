import numpy as np
import pandas as pd
import pytest

from src.web.services.shapers.impl.normalize import Normalize


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
    # BaseShaper uses utils.checkElementExists which raises Exception
    with pytest.raises(Exception, match="normalizeVars"):
        Normalize({})

    with pytest.raises(Exception, match="normalizerColumn"):
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
    assert n._normalizerVars == ["metric"]  # Defaults to normalizeVars


def test_verify_preconditions_missing_col(base_data):
    n = Normalize(
        {
            "normalizeVars": ["missing"],
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )
    with pytest.raises(ValueError, match="does not exist"):
        n._verifyPreconditions(base_data)


def test_verify_preconditions_non_numeric(base_data):
    n = Normalize(
        {
            "normalizeVars": ["other"],  # non-numeric
            "normalizerColumn": "config",
            "normalizerValue": "baseline",
            "groupBy": ["bench"],
        }
    )
    with pytest.raises(ValueError, match="is not numeric"):
        n._verifyPreconditions(base_data)


def test_verify_preconditions_multiple_normalizers():
    df = pd.DataFrame(
        {
            "config": ["baseline", "baseline", "test"],
            "bench": ["b1", "b1", "b1"],
            "metric": [10, 10, 20],
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
    with pytest.raises(ValueError, match="expected 1"):
        n._verifyPreconditions(df)


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

    # Bench b1: baseline=10 (metric).
    # SD should be divided by same baseline (10).
    # b1 baseline sd=1.0 -> 0.1
    # b1 test sd=2.0 -> 0.2

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
