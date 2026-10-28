"""Canonical arithmetic tokens, numerical results, and uncertainty column identity."""

import numpy as np
import pandas as pd
import pytest

from src.core.models.arithmetic_models import ArithmeticOperation, MixerOperation
from src.core.services.managers.arithmetic_service import ArithmeticService


@pytest.mark.parametrize("operation", list(ArithmeticOperation))
def test_every_binary_operation_has_explicit_results(operation: ArithmeticOperation) -> None:
    data = pd.DataFrame({"a": [6, 0], "b": [3, 0]})
    expected = {
        "Division": [2, np.nan],
        "Sum": [9, 0],
        "Subtraction": [3, 0],
        "Multiplication": [18, 0],
    }
    result = ArithmeticService.apply_operation(data, operation, "a", "b", "result")
    np.testing.assert_allclose(result["result"], expected[operation], equal_nan=True)
    assert list(data.columns) == ["a", "b"]
    assert result is not data


@pytest.mark.parametrize("operation", list(MixerOperation))
def test_every_mixer_operation_has_explicit_results(operation: MixerOperation) -> None:
    data = pd.DataFrame({"a": [6, 0], "b": [3, 0]})
    expected = {"Sum": [9, 0], "Mean": [4.5, 0], "Concatenate": ["6_3", "0_0"]}
    result = ArithmeticService.apply_mixer(data, "result", ["a", "b"], operation)
    assert result["result"].tolist() == expected[operation]
    assert list(data.columns) == ["a", "b"]
    assert result is not data


@pytest.mark.parametrize(
    "operation", ["sum", "divide", "add", "+", "minus", "-", "multiply", "*", "/", " Division"]
)
def test_binary_aliases_are_rejected(operation: str) -> None:
    with pytest.raises(ValueError, match="Unknown operation"):
        ArithmeticService.apply_operation(
            pd.DataFrame({"a": [1], "b": [2]}), operation, "a", "b", "x"
        )


@pytest.mark.parametrize("operation", ["Mean (Average)", "mean", "sum", "concatenate"])
def test_mixer_aliases_are_rejected(operation: str) -> None:
    with pytest.raises(ValueError, match="Unknown mixer operation"):
        ArithmeticService.apply_mixer(
            pd.DataFrame({"a": [1], "b": [2]}), "x", ["a", "b"], operation
        )


def test_stdev_named_column_is_not_an_uncertainty_companion() -> None:
    data = pd.DataFrame({"a": [1, 2], "a_stdev": [3, 4]})
    result = ArithmeticService.apply_mixer(data, "x", ["a"], "Sum")
    assert "x.sd" not in result
    assert result["a_stdev"].tolist() == [3, 4]
