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


def test_validated_join_reports_duplicates_unmatched_rows_and_cardinality() -> None:
    # [test->req~ring5.data.validated-joins~1]
    left = pd.DataFrame({"key": [1, 2, 2, 4], "left": [10, 20, 21, 40]})
    right = pd.DataFrame({"key": [1, 2, 3, 3], "right": [100, 200, 300, 301]})
    original_left = left.copy(deep=True)
    original_right = right.copy(deep=True)

    diagnostics = DatasetWorkspaceService.diagnose_join(
        left,
        right,
        ["key"],
        cardinality="one_to_one",
    )

    assert diagnostics.cardinality_valid is False
    assert diagnostics.left_duplicate_key_rows == 2
    assert diagnostics.right_duplicate_key_rows == 2
    assert diagnostics.left_duplicate_key_groups == 1
    assert diagnostics.right_duplicate_key_groups == 1
    assert diagnostics.left_unmatched_rows == 1
    assert diagnostics.right_unmatched_rows == 2
    assert diagnostics.matched_key_count == 2

    with pytest.raises(ValueError, match="Expected a one-to-one join"):
        DatasetWorkspaceService.validated_join(
            left,
            right,
            ["key"],
            cardinality="one_to_one",
        )

    result, accepted = DatasetWorkspaceService.validated_join(
        left,
        right,
        ["key"],
        cardinality="many_to_many",
        how="outer",
    )
    assert accepted.cardinality_valid is True
    assert len(result) == 6
    pd.testing.assert_frame_equal(left, original_left)
    pd.testing.assert_frame_equal(right, original_right)


def test_one_to_many_and_many_to_one_validate_the_unique_side() -> None:
    one = pd.DataFrame({"key": [1, 2], "name": ["a", "b"]})
    many = pd.DataFrame({"key": [1, 1, 2], "value": [10, 11, 20]})

    one_to_many = DatasetWorkspaceService.diagnose_join(
        one,
        many,
        ["key"],
        cardinality="one_to_many",
    )
    many_to_one = DatasetWorkspaceService.diagnose_join(
        many,
        one,
        ["key"],
        cardinality="many_to_one",
    )
    wrong_direction = DatasetWorkspaceService.diagnose_join(
        many,
        one,
        ["key"],
        cardinality="one_to_many",
    )

    assert one_to_many.cardinality_valid is True
    assert many_to_one.cardinality_valid is True
    assert wrong_direction.cardinality_valid is False


def test_invalid_cardinality_and_incompatible_key_types_are_rejected() -> None:
    left = pd.DataFrame({"key": [1]})
    right = pd.DataFrame({"key": ["1"]})
    with pytest.raises(ValueError, match="Invalid join cardinality"):
        DatasetWorkspaceService.diagnose_join(
            left,
            left,
            ["key"],
            cardinality="sometimes",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="cannot be compared"):
        DatasetWorkspaceService.diagnose_join(
            left,
            right,
            ["key"],
            cardinality="one_to_one",
        )
