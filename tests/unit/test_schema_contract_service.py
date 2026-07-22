"""Tests for explicit dataset schema contracts."""

import pandas as pd
import pytest

from src.core.models import ColumnContract, DatasetSchemaContract
from src.core.services.managers.schema_contract_service import SchemaContractService


def test_contract_reports_required_type_null_range_category_and_extra_rules() -> None:
    # [test->req~ring5.data.schema-contracts~1]
    data = pd.DataFrame(
        {
            "score": [-1.0, 5.0, 11.0, None],
            "count": [1, 2.5, "bad", 4],
            "category": ["a", "b", "other", "a"],
            "extra": [1, 2, 3, 4],
        }
    )
    original = data.copy(deep=True)
    contract = DatasetSchemaContract(
        name="experiment results",
        allow_extra_columns=False,
        columns=(
            ColumnContract("benchmark", data_type="string"),
            ColumnContract(
                "score",
                data_type="numeric",
                nullable=False,
                minimum=0,
                maximum=10,
            ),
            ColumnContract("count", data_type="integer"),
            ColumnContract(
                "category",
                data_type="string",
                accepted_values=("a", "b"),
            ),
            ColumnContract("optional", required=False),
        ),
    )

    report = SchemaContractService.validate(data, contract)

    assert report.valid is False
    assert report.row_count == 4
    assert report.issue_count == 7
    assert {(item.rule, item.column) for item in report.violations} == {
        ("required", "benchmark"),
        ("nullable", "score"),
        ("minimum", "score"),
        ("maximum", "score"),
        ("data_type", "count"),
        ("accepted_values", "category"),
        ("extra_column", "extra"),
    }
    count_issue = next(item for item in report.violations if item.column == "count")
    assert count_issue.affected_rows == 2
    assert count_issue.sample_row_numbers == (1, 2)
    assert list(report.to_frame().columns) == [
        "rule",
        "column",
        "message",
        "affected_rows",
        "sample_row_numbers",
    ]
    pd.testing.assert_frame_equal(data, original)


def test_inferred_contract_accepts_current_data_and_preserves_nullability() -> None:
    data = pd.DataFrame(
        {
            "count": pd.Series([1, 2], dtype="int64"),
            "ratio": [1.5, None],
            "active": [True, False],
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "label": ["a", "b"],
        }
    )

    contract = SchemaContractService.infer(data, name="inferred")
    report = SchemaContractService.validate(data, contract)

    assert report.valid is True
    assert report.to_frame().empty
    assert [rule.data_type for rule in contract.columns] == [
        "integer",
        "numeric",
        "boolean",
        "datetime",
        "string",
    ]
    assert [rule.nullable for rule in contract.columns] == [False, True, False, False, False]


def test_boolean_and_string_type_rules() -> None:
    data = pd.DataFrame(
        {
            "flag": [True, "yes", "invalid", None],
            "label": ["a", 2, "c", None],
        }
    )
    contract = DatasetSchemaContract(
        "types",
        (
            ColumnContract("flag", data_type="boolean", nullable=True),
            ColumnContract("label", data_type="string", nullable=True),
        ),
    )

    report = SchemaContractService.validate(data, contract)
    assert [(item.column, item.affected_rows) for item in report.violations] == [
        ("flag", 1),
        ("label", 1),
    ]


@pytest.mark.parametrize(
    "factory, message",
    [
        (lambda: ColumnContract(""), "column names"),
        (lambda: ColumnContract("x", data_type="currency"), "Invalid schema data type"),
        (lambda: ColumnContract("x", data_type="string", minimum=0), "Numeric ranges"),
        (
            lambda: ColumnContract("x", data_type="numeric", minimum=2, maximum=1),
            "minimum cannot exceed",
        ),
        (lambda: ColumnContract("x", accepted_values=("a", "a")), "must be unique"),
        (lambda: DatasetSchemaContract("", (ColumnContract("x"),)), "contract names"),
        (lambda: DatasetSchemaContract("empty", ()), "at least one"),
        (
            lambda: DatasetSchemaContract("duplicate", (ColumnContract("x"), ColumnContract("x"))),
            "must be unique",
        ),
    ],
)
def test_contract_declarations_reject_invalid_rules(factory: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        factory()  # type: ignore[operator]


def test_validation_rejects_invalid_inputs() -> None:
    contract = DatasetSchemaContract("schema", (ColumnContract("x"),))
    with pytest.raises(TypeError, match="pandas DataFrame"):
        SchemaContractService.validate("invalid", contract)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="DatasetSchemaContract"):
        SchemaContractService.validate(pd.DataFrame({"x": [1]}), object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unique column names"):
        SchemaContractService.validate(pd.DataFrame([[1, 2]], columns=["x", "x"]), contract)
