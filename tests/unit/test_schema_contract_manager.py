"""Tests for the human-first schema contract editor."""

from unittest.mock import MagicMock, patch

import pandas as pd

from src.core.models import (
    ColumnSemantics,
    DatasetSchemaContract,
    DatasetSemantics,
    SchemaValidationReport,
)
from src.web.components.data_managers.schema_contract import SchemaContractManager


def test_build_contract_parses_editor_values() -> None:
    edited = pd.DataFrame(
        {
            "column": ["score", "status", "active"],
            "required": [True, True, False],
            "data_type": ["numeric", "string", "boolean"],
            "nullable": [False, True, False],
            "minimum": [0.0, None, None],
            "maximum": [10.0, None, None],
            "accepted_values": ["1.5, 2", "stable, experimental", "true, false"],
            "semantic_label": ["Score", "Release status", "Enabled"],
            "unit": ["%", "", ""],
        }
    )

    contract = SchemaContractManager._build_contract("results", False, edited)

    assert contract.name == "results"
    assert contract.allow_extra_columns is False
    assert contract.columns[0].minimum == 0.0
    assert contract.columns[0].accepted_values == (1.5, 2.0)
    assert contract.columns[1].accepted_values == ("stable", "experimental")
    assert contract.columns[2].accepted_values == (True, False)
    assert contract.columns[0].semantic_label == "Score"
    assert contract.columns[0].unit == "%"


@patch("src.web.components.data_managers.schema_contract.st")
def test_render_validates_edited_contract(mock_st: MagicMock) -> None:
    data = pd.DataFrame({"value": [1, 2]})
    api = MagicMock()
    api.state_manager.get_data.return_value = data
    inferred = MagicMock()
    inferred.to_frame.return_value = pd.DataFrame(
        {
            "column": ["value"],
            "required": [True],
            "data_type": ["integer"],
            "nullable": [False],
            "minimum": [None],
            "maximum": [None],
            "accepted_values": [""],
        }
    )
    api.managers.infer_schema_contract.return_value = inferred
    api.managers.validate_schema.return_value = SchemaValidationReport(
        contract_name="active_dataset_contract",
        row_count=2,
        column_count=1,
        violations=(),
    )
    mock_st.text_input.return_value = "active_dataset_contract"
    mock_st.toggle.return_value = True
    mock_st.data_editor.return_value = inferred.to_frame.return_value
    mock_st.button.return_value = True
    containers = [MagicMock() for _ in range(3)]
    for container in containers:
        container.__enter__ = MagicMock(return_value=container)
        container.__exit__ = MagicMock(return_value=False)
    mock_st.columns.return_value = containers

    SchemaContractManager(api).render()

    api.managers.validate_schema.assert_called_once()
    built = api.managers.validate_schema.call_args.args[1]
    assert isinstance(built, DatasetSchemaContract)
    mock_st.success.assert_called_once()


@patch("src.web.components.data_managers.schema_contract.st")
def test_render_applies_semantic_metadata_to_active_data(mock_st: MagicMock) -> None:
    # [test->req~ring5.data.semantic-units~1]
    data = pd.DataFrame({"latency": [1.0, 2.0]})
    edited = pd.DataFrame(
        {
            "column": ["latency"],
            "required": [True],
            "data_type": ["numeric"],
            "nullable": [False],
            "minimum": [None],
            "maximum": [None],
            "accepted_values": [""],
            "semantic_label": ["Mean latency"],
            "unit": ["ms"],
        }
    )
    api = MagicMock()
    api.state_manager.get_data.return_value = data
    inferred = MagicMock()
    inferred.to_frame.return_value = edited
    api.managers.infer_schema_contract.return_value = inferred
    api.managers.attach_semantics.return_value = data
    api.managers.inspect_semantics.return_value = DatasetSemantics(
        (ColumnSemantics("latency", "Mean latency", "ms"),)
    )
    api.managers.supported_units.return_value = ("ms", "s")
    mock_st.text_input.return_value = "latency"
    mock_st.toggle.return_value = True
    mock_st.data_editor.return_value = edited
    mock_st.selectbox.side_effect = ["latency", "ms"]
    mock_st.button.side_effect = lambda label, **_: label == "Apply Labels and Units"

    SchemaContractManager(api).render()

    applied = api.managers.attach_semantics.call_args.args[1]
    assert applied == DatasetSemantics((ColumnSemantics("latency", "Mean latency", "ms"),))
    api.update_selected_dataset.assert_called_once_with(
        data,
        operation="Apply semantic labels and units",
    )
    mock_st.success.assert_called_once()
