"""Source category ordering and missing-aware trace selection contracts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.web.pages.ui.plotting.types._trace_helpers import group_mask
from src.web.pages.ui.plotting.utils.ordering import observed_order, order_with_overrides


@pytest.mark.parametrize("configured", [None, [], (), "a", {"a": 0}])
def test_unspecified_preference_preserves_encounter_order(configured: object) -> None:
    source = pd.Series(["b", "a", "b", "c"], index=[4, 8, 12, 16])
    assert observed_order(source, configured) == ["b", "a", "c"]
    assert source.tolist() == ["b", "a", "b", "c"]
    assert source.index.tolist() == [4, 8, 12, 16]


def test_preferred_labels_select_only_observed_values_and_keep_remaining_source_order() -> None:
    source = pd.Series([30, 10, 20, 30, 40], dtype="int32")
    values = observed_order(source, ["20", "absent"])
    assert values == [20, 30, 10, 40]
    assert all(isinstance(value, int) for value in values)
    assert source.dtype == "int32"


@pytest.mark.parametrize("missing", [None, np.nan, pd.NA, pd.NaT])
def test_missing_categories_remain_selectable_without_changing_input(missing: object) -> None:
    source = pd.Series(["b", missing, "a", missing], index=[4, 8, 12, 16], dtype=object)
    values = observed_order(source, ["a"])
    assert values[0] == "a" and values[1] == "b" and pd.isna(values[2])
    assert group_mask(source, values[2]).tolist() == [False, True, False, True]
    assert group_mask(source, "b").tolist() == [True, False, False, False]
    assert source.isna().tolist() == [False, True, False, True]
    assert source.index.tolist() == [4, 8, 12, 16]


def test_group_selection_keeps_actual_numeric_and_string_identities() -> None:
    source = pd.Series([1, "1", 2, "2"], dtype=object)
    assert observed_order(source) == [1, "1", 2, "2"]
    assert group_mask(source, 1).tolist() == [True, False, False, False]
    assert group_mask(source, "1").tolist() == [False, True, False, False]


def test_encounter_and_lexical_order_are_distinct_plot_policies() -> None:
    source = pd.Series(["b", "c", "a"])
    assert observed_order(source, ["c"]) == ["c", "b", "a"]
    assert order_with_overrides(source, ["c"]) == ["c", "a", "b"]


def test_categorical_selection_keeps_scalar_values_and_unused_levels_absent() -> None:
    source = pd.Series(pd.Categorical(["b", "a", "b"], categories=["unused", "a", "b"]))
    assert observed_order(source, ["unused", "a"]) == ["a", "b"]
    assert group_mask(source, "b").tolist() == [True, False, True]
    assert source.cat.categories.tolist() == ["unused", "a", "b"]
