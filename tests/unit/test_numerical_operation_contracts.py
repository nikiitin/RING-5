"""Scientific value and uncertainty contracts shared by arithmetic entry points."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.core.services.managers.arithmetic_service import ArithmeticService
from src.core.services.shapers.impl.derive_column import DeriveColumn


@pytest.mark.parametrize(
    ("operation", "symbol", "expected"),
    [
        ("Sum", "+", [8, np.nan, -4, 2]),
        ("Subtraction", "-", [4, np.nan, -8, -2]),
        ("Multiplication", "*", [12, np.nan, -12, 0]),
        ("Division", "/", [3, np.nan, -3, 0]),
    ],
)
def test_binary_manager_and_scalar_shaper_share_elementwise_values(
    operation: str, symbol: str, expected: list[float]
) -> None:
    # [test->req~ring5.data.arithmetic~1]
    # [test->req~ring5.shaping.derive-column~1]
    frame = pd.DataFrame({"a": [6.0, np.nan, -6.0, 0.0], "b": 2.0}, index=[4, 8, 12, 16])
    original = frame.copy(deep=True)
    manager = ArithmeticService.apply_operation(frame, operation, "a", "b", "out")
    shaper = DeriveColumn(
        {
            "type": "deriveColumn",
            "op": "scalar",
            "dest": "out",
            "sources": ["a"],
            "scalar": 2.0,
            "scalar_op": symbol,
        }
    )(frame)
    np.testing.assert_allclose(manager["out"], expected, equal_nan=True)
    pd.testing.assert_series_equal(manager["out"], shaper["out"])
    pd.testing.assert_frame_equal(frame, original)


def test_row_sums_skip_missing_while_binary_addition_propagates_it() -> None:
    # [test->req~ring5.data.numeric-mixer~1]
    # [test->req~ring5.shaping.derive-column~1]
    frame = pd.DataFrame({"a": [1.0, np.nan, np.nan], "b": [np.nan, 2.0, np.nan]})
    original = frame.copy(deep=True)
    manager = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], "Sum")
    shaper = DeriveColumn(
        {"type": "deriveColumn", "op": "sum", "dest": "out", "sources": ["a", "b"]}
    )(frame)
    np.testing.assert_allclose(manager["out"], [1, 2, 0])
    pd.testing.assert_series_equal(manager["out"], shaper["out"])
    assert ArithmeticService.apply_operation(frame, "Sum", "a", "b", "out")["out"].isna().all()
    pd.testing.assert_frame_equal(frame, original)


def test_ratio_zero_policies_and_scalar_raw_division_remain_distinct() -> None:
    frame = pd.DataFrame({"a": [-1.0, 0.0, 1.0, np.nan], "b": 0.0})
    original = frame.copy(deep=True)
    default_ratio = DeriveColumn(
        {"type": "deriveColumn", "op": "ratio", "dest": "out", "sources": ["a", "b"]}
    )(frame)
    manager = ArithmeticService.apply_operation(frame, "Division", "a", "b", "out")
    pd.testing.assert_series_equal(manager["out"], default_ratio["out"])
    assert default_ratio["out"].isna().all()
    raw_ratio = DeriveColumn(
        {
            "type": "deriveColumn",
            "op": "ratio",
            "dest": "out",
            "sources": ["a", "b"],
            "zero_denominator": "propagate",
        }
    )(frame)
    scalar = DeriveColumn(
        {
            "type": "deriveColumn",
            "op": "scalar",
            "dest": "out",
            "sources": ["a"],
            "scalar": 0.0,
            "scalar_op": "/",
        }
    )(frame)
    np.testing.assert_allclose(raw_ratio["out"], [-np.inf, np.nan, np.inf, np.nan], equal_nan=True)
    pd.testing.assert_series_equal(raw_ratio["out"], scalar["out"])
    pd.testing.assert_frame_equal(frame, original)


def test_concatenation_remains_shared_and_missing_safe() -> None:
    frame = pd.DataFrame({"a": ["label", None], "b": [1.0, np.nan]}, index=[7, 9])
    original = frame.copy(deep=True)
    manager = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], "Concatenate", ":")
    shaper = DeriveColumn(
        {
            "type": "deriveColumn",
            "op": "concat",
            "dest": "out",
            "sources": ["a", "b"],
            "separator": ":",
        }
    )(frame)
    assert manager["out"].tolist() == ["label:1.0", ":"]
    pd.testing.assert_series_equal(manager["out"], shaper["out"])
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize(
    ("operation", "values", "deviations"),
    [
        ("Sum", [3, 1, 2, 0, 0], [np.nan, 0.3, 0.4, 0, np.nan]),
        ("Mean", [1.5, 1, 2, np.nan, 0], [np.nan, 0.3, 0.4, np.nan, np.nan]),
    ],
)
def test_mixer_uncertainty_uses_only_contributing_values_and_keeps_unknown_sd(
    operation: str, values: list[float], deviations: list[float]
) -> None:
    # [test->req~ring5.data.error-propagation~2]
    frame = pd.DataFrame(
        {
            "a": [1.0, 1.0, np.nan, np.nan, 0.0],
            "a.sd": [np.nan, 0.3, 99.0, 99.0, np.nan],
            "b": [2.0, np.nan, 2.0, np.nan, 0.0],
            "b.sd": [0.4, 99.0, 0.4, 99.0, 0.0],
        },
        index=["unknown", "only-a", "only-b", "empty", "measured-zero"],
    )
    original = frame.copy(deep=True)
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], operation)
    np.testing.assert_allclose(result["out"], values, equal_nan=True)
    np.testing.assert_allclose(result["out.sd"], deviations, equal_nan=True)
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("operation", ["Sum", "Mean"])
def test_partial_sd_companions_record_only_available_variance(operation: str) -> None:
    frame = pd.DataFrame(
        {"a": [1.0, np.nan, 1.0], "a.sd": [0.3, 99.0, np.nan], "b": [np.nan, 4.0, 2.0]}
    )
    original = frame.copy(deep=True)
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], operation)
    np.testing.assert_allclose(result["out.sd"], [0.3, 0, np.nan], equal_nan=True)
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("destination", ["a", "a.sd"])
def test_overwriting_a_source_or_sd_column_reads_original_measurements(destination: str) -> None:
    frame = pd.DataFrame(
        {"a": [np.nan, 1.0], "a.sd": [99.0, 0.3], "b": [2.0, 2.0], "b.sd": [0.4, 0.4]}
    )
    original = frame.copy(deep=True)
    result = ArithmeticService.apply_mixer(frame, destination, ["a", "b"], "Sum")
    np.testing.assert_allclose(result[destination], [2, 3])
    np.testing.assert_allclose(result[f"{destination}.sd"], [0.4, 0.5])
    pd.testing.assert_frame_equal(frame, original)


def test_nullable_measurements_preserve_unknown_uncertainty() -> None:
    frame = pd.DataFrame(
        {"a": [1.0, pd.NA], "a.sd": [pd.NA, 99.0], "b": [2.0, 2.0], "b.sd": [0.4, 0.4]},
        dtype="Float64",
    )
    original = frame.copy(deep=True)
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], "Mean")
    pd.testing.assert_series_equal(
        result["out.sd"], pd.Series([pd.NA, 0.4], dtype="Float64", name="out.sd")
    )
    pd.testing.assert_frame_equal(frame, original)


def test_value_only_shaper_keeps_its_distinct_uncertainty_contract() -> None:
    frame = pd.DataFrame({"a": [1.0], "a.sd": [0.3], "b": [2.0], "b.sd": [0.4]})
    original = frame.copy(deep=True)
    manager = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], "Sum")
    shaper = DeriveColumn(
        {"type": "deriveColumn", "op": "sum", "dest": "out", "sources": ["a", "b"]}
    )(frame)
    pd.testing.assert_series_equal(manager["out"], shaper["out"])
    assert manager["out.sd"].iloc[0] == pytest.approx(0.5)
    assert "out.sd" not in shaper.columns
    pd.testing.assert_frame_equal(frame, original)


def test_ratio_rejects_an_unsupported_zero_denominator_policy() -> None:
    with pytest.raises(ValueError, match="zero_denominator"):
        DeriveColumn(
            {
                "type": "deriveColumn",
                "op": "ratio",
                "dest": "out",
                "sources": ["a", "b"],
                "zero_denominator": "guess",
            }
        )


@pytest.mark.parametrize("operation", ["Sum", "Mean"])
@pytest.mark.parametrize("source_sd", [5_000_000_000, 1e308, 1e-300])
def test_mixer_extreme_sd_scales_do_not_overflow_or_underflow(
    operation: str, source_sd: int | float
) -> None:
    # [test->req~ring5.data.error-propagation~2]
    frame = pd.DataFrame({"a": [1.0], "a.sd": [source_sd], "b": [2.0], "b.sd": [source_sd]})
    original = frame.copy(deep=True)
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], operation)
    expected = math.hypot(source_sd, source_sd) / (2 if operation == "Mean" else 1)
    assert result["out.sd"].iloc[0] == pytest.approx(expected, rel=1e-14, abs=0)
    pd.testing.assert_frame_equal(frame, original)


def test_infinite_sd_cannot_hide_an_unknown_contributing_sd() -> None:
    frame = pd.DataFrame({"a": [1.0], "a.sd": [np.nan], "b": [2.0], "b.sd": [np.inf]})
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], "Sum")
    assert result["out.sd"].isna().all()


def test_mean_stays_finite_when_its_unscaled_sum_would_overflow() -> None:
    frame = pd.DataFrame({f"x{index}": [float(index)] for index in range(4)})
    for index in range(4):
        frame[f"x{index}.sd"] = 1e308
    result = ArithmeticService.apply_mixer(
        frame, "out", [f"x{index}" for index in range(4)], "Mean"
    )
    assert result["out.sd"].iloc[0] == pytest.approx(5e307, rel=1e-14, abs=0)


def test_mean_preserves_the_smallest_representable_sd() -> None:
    # [test->req~ring5.data.error-propagation~2]
    smallest = np.nextafter(0.0, 1.0)
    frame = pd.DataFrame({"a": [1.0], "a.sd": [smallest], "b": [2.0], "b.sd": [smallest]})
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], "Mean")
    assert result["out.sd"].iloc[0] == smallest


@pytest.mark.parametrize(("operation", "value", "deviation"), [("Sum", 10, 4), ("Mean", 5, 2)])
def test_repeated_source_weights_are_fully_correlated(
    operation: str, value: float, deviation: float
) -> None:
    # [test->req~ring5.data.error-propagation~2]
    frame = pd.DataFrame({"a": [5.0], "a.sd": [2.0]})
    original = frame.copy(deep=True)
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "a"], operation)
    assert result["out"].iloc[0] == value
    assert result["out.sd"].iloc[0] == deviation
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize(
    ("operation", "value", "deviation"), [("Sum", 17, 5), ("Mean", 17 / 3, 5 / 3)]
)
def test_weighted_distinct_sources_remain_independent(
    operation: str, value: float, deviation: float
) -> None:
    frame = pd.DataFrame({"a": [5.0], "a.sd": [2.0], "b": [7.0], "b.sd": [3.0]})
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "a", "b"], operation)
    assert result["out"].iloc[0] == pytest.approx(value)
    assert result["out.sd"].iloc[0] == pytest.approx(deviation)


@pytest.mark.parametrize("dtype", ["float64", "Float64"])
@pytest.mark.parametrize("operation", ["Sum", "Mean"])
def test_an_undefined_estimate_keeps_its_uncertainty_missing(dtype: str, operation: str) -> None:
    # [test->req~ring5.data.error-propagation~2]
    frame = pd.DataFrame({"a": [np.inf], "a.sd": [1.0], "b": [-np.inf], "b.sd": [1.0]}, dtype=dtype)
    with np.errstate(invalid="ignore"):
        result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], operation)
    assert pd.isna(result["out"].iloc[0])
    assert pd.isna(result["out.sd"].iloc[0])


@pytest.mark.parametrize("operation", ["Sum", "Mean"])
def test_zero_sd_scale_and_known_infinite_sd_remain_defined(operation: str) -> None:
    frame = pd.DataFrame(
        {"a": [1.0, 1.0], "a.sd": [0.0, np.inf], "b": [2.0, 2.0], "b.sd": [0.0, 1.0]}
    )
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], operation)
    assert result["out.sd"].iloc[0] == 0
    assert result["out.sd"].iloc[1] == np.inf


@pytest.mark.parametrize("missing", [None, pd.NA, np.nan])
def test_missing_sd_object_values_remain_unknown(missing: object) -> None:
    frame = pd.DataFrame(
        {"a": [1.0], "a.sd": pd.Series([missing], dtype=object), "b": [2.0], "b.sd": [0.4]}
    )
    original = frame.copy(deep=True)
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "b"], "Sum")
    assert pd.isna(result["out.sd"].iloc[0])
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize(
    ("operation", "values", "deviations"),
    [("Sum", [17, 10], [4, 4]), ("Mean", [17 / 3, 5], [4 / 3, 2])],
)
def test_repeated_sources_preserve_partial_companion_policy(
    operation: str, values: list[float], deviations: list[float]
) -> None:
    frame = pd.DataFrame({"a": [5.0, 5.0], "a.sd": [2.0, 2.0], "b": [7.0, np.nan]})
    result = ArithmeticService.apply_mixer(frame, "out", ["a", "a", "b"], operation)
    np.testing.assert_allclose(result["out"], values)
    np.testing.assert_allclose(result["out.sd"], deviations)
