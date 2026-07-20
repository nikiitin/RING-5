"""Tests for deterministic small-multiples panel discovery."""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.services.visualization.small_multiples_service import (
    create_small_multiples_spec,
)


def _data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "architecture": ["x86", "arm", "x86", "arm"],
            "mode": ["fast", "fast", "safe", "safe"],
            "benchmark": ["A", "A", "B", "B"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )


def test_discovers_multicolumn_panels_in_stable_order_with_labels() -> None:
    # [test->req~ring5.plots.small-multiples~1]
    spec = create_small_multiples_spec(
        7,
        _data(),
        ["architecture", "mode"],
        columns=2,
        order=[("arm", "safe")],
        labels={("arm", "safe"): "ARM — safe mode"},
        title="Comparison",
        panel_height=280,
    )

    assert [panel.values for panel in spec.panels] == [
        ("arm", "safe"),
        ("x86", "fast"),
        ("arm", "fast"),
        ("x86", "safe"),
    ]
    assert spec.panels[0].title == "ARM — safe mode"
    assert spec.panels[1].title == "architecture: x86 · mode: fast"
    assert (spec.rows, spec.columns, spec.height) == (2, 2, 560)


def test_single_column_order_accepts_scalars_and_missing_values_are_explicit() -> None:
    data = pd.DataFrame({"arch": ["x86", None, "arm"], "value": [1, 2, 3]})

    spec = create_small_multiples_spec(1, data, "arch", order=[None, "arm"])

    assert [panel.values for panel in spec.panels] == [(None,), ("arm",), ("x86",)]
    assert spec.panels[0].title == "arch: Missing"


@pytest.mark.parametrize(
    ("data", "by", "kwargs", "message"),
    [
        (_data(), [], {}, "at least one"),
        (_data(), ["missing"], {}, "Unknown facet"),
        (_data(), ["value"], {}, "categorical"),
        (_data().iloc[:0], ["architecture"], {}, "empty data"),
        (_data().query("architecture == 'x86'"), ["architecture"], {}, "at least two"),
        (_data(), ["architecture"], {"order": ["mips"]}, "unknown group"),
        (_data(), ["architecture"], {"order": ["arm", "arm"]}, "duplicate"),
        (_data(), ["architecture"], {"labels": {"mips": "MIPS"}}, "unknown group"),
    ],
)
def test_rejects_invalid_facet_requests(
    data: pd.DataFrame,
    by: list[str],
    kwargs: dict[str, object],
    message: str,
) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        create_small_multiples_spec(1, data, by, **kwargs)  # type: ignore[arg-type]


def test_boolean_columns_are_valid_categories() -> None:
    data = pd.DataFrame({"enabled": [True, False], "value": [1.0, 2.0]})

    spec = create_small_multiples_spec(2, data, ["enabled"])

    assert [panel.values for panel in spec.panels] == [(True,), (False,)]
