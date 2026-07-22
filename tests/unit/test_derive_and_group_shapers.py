"""Unit tests for the scripting shapers: DeriveColumn, GroupCardinalitySelector,
GroupPredicateSelector (registered programmatic-only; used by the figure pipelines)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.impl.derive_column import DeriveColumn
from src.core.services.shapers.impl.selector_algorithms.group_cardinality_selector import (
    GroupCardinalitySelector,
)
from src.core.services.shapers.impl.selector_algorithms.group_predicate_selector import (
    GroupPredicateSelector,
)


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bench": ["a", "a", "b", "b", "c", "c"],
            "policy": ["base", "x", "base", "x", "base", "x"],
            "p": [2.0, 4.0, 0.0, 1.0, float("nan"), 5.0],
            "q": [1.0, float("nan"), 3.0, 1.0, 2.0, 5.0],
        }
    )


# DeriveColumn


def test_derive_sum_skips_nan_like_pandas():
    # [test->req~ring5.shaping.derive-column~1]
    out = DeriveColumn({"type": "deriveColumn", "op": "sum", "dest": "s", "sources": ["p", "q"]})(
        _df()
    )
    # row1 q is NaN → sum is just p (skipna); row4 → 0.0 + 3.0
    assert out["s"].tolist() == [3.0, 4.0, 3.0, 2.0, 2.0, 10.0]


def test_derive_ratio_zero_denominator_becomes_nan():
    # [test->req~ring5.shaping.derive-column~1]
    out = DeriveColumn({"type": "deriveColumn", "op": "ratio", "dest": "r", "sources": ["p", "q"]})(
        _df()
    )
    # row1: 4/NaN → NaN; all others p/q with q==0 → NaN
    vals = out["r"].tolist()
    assert vals[0] == pytest.approx(2.0)  # 2/1
    assert math.isnan(vals[1])  # 4/NaN
    assert vals[3] == pytest.approx(1.0)  # 1/1


def test_derive_scalar_and_concat_and_map():
    # [test->req~ring5.shaping.derive-column~1]
    base = _df()
    scaled = DeriveColumn(
        {
            "type": "deriveColumn",
            "op": "scalar",
            "dest": "g",
            "sources": ["p"],
            "scalar": 2.0,
            "scalar_op": "/",
        }
    )(base)
    assert scaled["g"].tolist()[0] == pytest.approx(1.0)  # 2/2

    cat = DeriveColumn(
        {
            "type": "deriveColumn",
            "op": "concat",
            "dest": "k",
            "sources": ["bench", "policy"],
            "separator": ".",
        }
    )(base)
    assert cat["k"].tolist()[0] == "a.base"

    mapped = DeriveColumn(
        {
            "type": "deriveColumn",
            "op": "map",
            "dest": "policy",
            "sources": ["policy"],
            "mapping": {"base": "BASE", "x": "X"},
        }
    )(base)
    assert set(mapped["policy"]) == {"BASE", "X"}


def test_derive_immutable_and_validation():
    base = _df()
    DeriveColumn({"type": "deriveColumn", "op": "sum", "dest": "s", "sources": ["p", "q"]})(base)
    assert "s" not in base.columns  # input untouched
    with pytest.raises(ValueError):
        DeriveColumn({"type": "deriveColumn", "op": "bogus", "dest": "x", "sources": ["p"]})
    with pytest.raises(ValueError):
        DeriveColumn({"type": "deriveColumn", "op": "ratio", "dest": "x", "sources": ["p"]})
    with pytest.raises(ValueError):
        DeriveColumn({"type": "deriveColumn", "op": "sum", "dest": "x", "sources": ["missing"]})(
            base
        )


# GroupCardinalitySelector


def test_group_cardinality_eq_keeps_complete_groups():
    # [test->req~ring5.shaping.group-cardinality-selector~1]
    df = _df().iloc[:-1]  # drop the last row → group "c" has only 1 policy
    out = GroupCardinalitySelector(
        {
            "type": "groupCardinalitySelector",
            "groupBy": ["bench"],
            "countColumn": "policy",
            "count": 2,
            "mode": "eq",
        }
    )(df)
    assert set(out["bench"]) == {"a", "b"}


def test_group_cardinality_modes_and_validation():
    # [test->req~ring5.shaping.group-cardinality-selector~1]
    df = _df().iloc[:-1]
    ge = GroupCardinalitySelector(
        {
            "type": "groupCardinalitySelector",
            "groupBy": ["bench"],
            "countColumn": "policy",
            "count": 2,
            "mode": "ge",
        }
    )(df)
    assert set(ge["bench"]) == {"a", "b"}
    with pytest.raises(ValueError):
        GroupCardinalitySelector(
            {"type": "groupCardinalitySelector", "groupBy": [], "countColumn": "policy", "count": 2}
        )


# GroupPredicateSelector


def test_group_predicate_drops_zero_baseline_group():
    # group "b" has base p == 0.0, group "c" has base p == NaN → both dropped
    # [test->req~ring5.shaping.group-predicate-selector~1]
    out = GroupPredicateSelector(
        {
            "type": "groupPredicateSelector",
            "groupBy": ["bench"],
            "baselineColumn": "policy",
            "baselineValue": "base",
            "predicateColumn": "p",
            "drop_when": "zero_or_nan",
            "action": "drop",
        }
    )(_df())
    assert set(out["bench"]) == {"a"}


def test_group_predicate_keep_action_and_validation():
    # [test->req~ring5.shaping.group-predicate-selector~1]
    kept = GroupPredicateSelector(
        {
            "type": "groupPredicateSelector",
            "groupBy": ["bench"],
            "baselineColumn": "policy",
            "baselineValue": "base",
            "predicateColumn": "p",
            "drop_when": "zero_or_nan",
            "action": "keep",
        }
    )(_df())
    assert set(kept["bench"]) == {"b", "c"}
    with pytest.raises(ValueError):
        GroupPredicateSelector(
            {
                "type": "groupPredicateSelector",
                "groupBy": ["bench"],
                "baselineColumn": "policy",
                "baselineValue": "base",
                "predicateColumn": "p",
                "drop_when": "bogus",
            }
        )


# Factory registration + UI selectability (registry + display name + config renderer)


def test_new_shapers_registered_and_ui_selectable():
    from src.web.pages.ui.shaper_config import CONFIG_DISPATCH

    available = ShaperFactory.get_available_types()
    selectable = set(ShaperFactory.get_display_name_map().values())
    for key in ("deriveColumn", "groupCardinalitySelector", "groupPredicateSelector"):
        assert key in available  # constructable via the factory
        assert key in selectable  # shown in the "Add transformation" dropdown
        assert key in CONFIG_DISPATCH  # has a UI config renderer
    shaper = ShaperFactory.create_shaper(
        "deriveColumn", {"type": "deriveColumn", "op": "sum", "dest": "s", "sources": ["p", "q"]}
    )
    assert isinstance(shaper, DeriveColumn)
