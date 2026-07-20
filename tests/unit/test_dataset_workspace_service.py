"""Tests for named-dataset composition operations."""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.services.managers.dataset_workspace_service import DatasetWorkspaceService


def test_append_and_join_create_results_without_mutating_sources() -> None:
    # [test->req~ring5.data.multi-dataset-workspace~1]
    left = pd.DataFrame({"key": [1, 2], "left": [10, 20], "shared": [1.0, 2.0]})
    right = pd.DataFrame({"key": [2, 3], "right": [30, 40], "shared": [3.0, 4.0]})
    original_left = left.copy(deep=True)
    original_right = right.copy(deep=True)

    appended = DatasetWorkspaceService.append([left, right], join="outer")
    joined = DatasetWorkspaceService.join(left, right, ["key"], how="outer")

    assert len(appended) == 4
    assert list(appended.columns) == ["key", "left", "shared", "right"]
    assert joined["key"].tolist() == [1, 2, 3]
    assert {"shared_left", "shared_right"} <= set(joined.columns)
    pd.testing.assert_frame_equal(left, original_left)
    pd.testing.assert_frame_equal(right, original_right)


def test_append_inner_keeps_shared_columns_and_fresh_index() -> None:
    first = pd.DataFrame({"a": [1], "shared": [2]}, index=[8])
    second = pd.DataFrame({"shared": [3], "b": [4]}, index=[9])

    result = DatasetWorkspaceService.append([first, second], join="inner")

    assert result.to_dict("list") == {"shared": [2, 3]}
    assert result.index.tolist() == [0, 1]


@pytest.mark.parametrize(
    ("datasets", "kwargs", "message"),
    [
        ([pd.DataFrame({"a": [1]})], {}, "at least two"),
        (
            [pd.DataFrame({"a": [1]}), pd.DataFrame({"a": [2]})],
            {"join": "sideways"},
            "outer.*inner",
        ),
        (
            [
                pd.DataFrame([[1, 2]], columns=["a", "a"]),
                pd.DataFrame({"a": [2]}),
            ],
            {},
            "unique column names",
        ),
        (
            [pd.DataFrame({1: [1]}), pd.DataFrame({"a": [2]})],
            {},
            "string column names",
        ),
    ],
)
def test_invalid_append_inputs_are_rejected(
    datasets: list[pd.DataFrame], kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        DatasetWorkspaceService.append(
            datasets,
            **kwargs,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("on", "kwargs", "message"),
    [
        ([], {}, "at least one"),
        ([""], {}, "non-empty string"),
        (["key", "key"], {}, "Duplicate join keys"),
        (["missing"], {}, "Left dataset is missing"),
        (["right_missing"], {}, "Left dataset is missing"),
        (["key"], {"how": "sideways"}, "Join mode"),
        (["key"], {"suffixes": ("_x", "_x")}, "distinct"),
        (["key"], {"suffixes": ("", "_y")}, "distinct"),
        (["key"], {"suffixes": None}, "distinct"),
    ],
)
def test_invalid_join_inputs_are_rejected(
    on: list[str], kwargs: dict[str, object], message: str
) -> None:
    left = pd.DataFrame({"key": [1], "left": [2]})
    right = pd.DataFrame({"key": [1], "right_missing": [3]})
    with pytest.raises(ValueError, match=message):
        DatasetWorkspaceService.join(
            left,
            right,
            on,
            **kwargs,  # type: ignore[arg-type]
        )


def test_right_missing_join_key_is_reported() -> None:
    left = pd.DataFrame({"key": [1]})
    right = pd.DataFrame({"other": [1]})

    with pytest.raises(ValueError, match="Right dataset is missing join keys: key"):
        DatasetWorkspaceService.join(left, right, ["key"])
