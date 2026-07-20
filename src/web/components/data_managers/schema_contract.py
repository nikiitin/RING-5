"""Human-first editor and validator for dataset schema contracts."""

from __future__ import annotations

import math
from typing import cast

import pandas as pd
import streamlit as st

from src.core.models import ColumnContract, DatasetSchemaContract
from src.core.models.schema_contract_models import ContractValue, SchemaDataType
from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import WidgetKeyBuilder

_DATA_TYPES = ["any", "numeric", "integer", "boolean", "datetime", "string"]


class SchemaContractManager(DataManager):
    """Edit explicit column rules and validate the active dataset."""

    @property
    def name(self) -> str:
        """Return the manager's display name."""
        return "Schema Contract"

    def render(self) -> None:
        """Render an inferred contract as an editable validation table."""
        # [impl->req~ring5.data.schema-contracts~1]
        st.markdown("### Dataset Schema Contract")
        st.info(
            "Define the table shape that downstream analysis may rely on. Start from inferred "
            "rules, then make required columns, nullability, numeric bounds, and accepted "
            "categories explicit. Validation never changes the dataset."
        )
        data = self.get_data()
        if data is None:
            st.warning("Load a dataset before defining its schema contract.")
            return

        contract_name = st.text_input(
            "Contract name",
            value="active_dataset_contract",
            key=WidgetKeyBuilder.manager_key("schema_contract", "name"),
        )
        allow_extra = st.toggle(
            "Allow columns not listed below",
            value=True,
            key=WidgetKeyBuilder.manager_key("schema_contract", "allow_extra"),
        )
        inferred = self.api.managers.infer_schema_contract(data, name=contract_name)
        edited = st.data_editor(
            inferred.to_frame(),
            width="stretch",
            hide_index=True,
            num_rows="fixed",
            disabled=["column"],
            column_config={
                "column": st.column_config.TextColumn("Column", help="Source column name"),
                "required": st.column_config.CheckboxColumn("Required"),
                "data_type": st.column_config.SelectboxColumn(
                    "Type",
                    options=_DATA_TYPES,
                ),
                "nullable": st.column_config.CheckboxColumn("Allow missing"),
                "minimum": st.column_config.NumberColumn("Minimum"),
                "maximum": st.column_config.NumberColumn("Maximum"),
                "accepted_values": st.column_config.TextColumn(
                    "Accepted values",
                    help="Optional comma-separated categorical values",
                ),
            },
            key=WidgetKeyBuilder.manager_key("schema_contract", "rules"),
        )
        st.caption(
            "Minimum and maximum apply only to numeric or integer rules. Row numbers in failures "
            "are zero-based positions, so duplicate dataframe indexes remain unambiguous."
        )

        if not st.button(
            "Validate Schema Contract",
            type="primary",
            key=WidgetKeyBuilder.manager_key("schema_contract", "validate"),
        ):
            return
        try:
            contract = self._build_contract(contract_name, bool(allow_extra), edited)
            report = self.api.managers.validate_schema(data, contract)
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
            return

        status, issues, affected = st.columns(3)
        with status:
            st.metric("Contract status", "Valid" if report.valid else "Needs attention")
        with issues:
            st.metric("Failed rules", report.issue_count)
        with affected:
            st.metric("Affected rows", report.affected_value_count)
        if report.valid:
            st.success("The active dataset satisfies every schema rule.")
            return
        st.error("The active dataset does not satisfy this contract.")
        st.dataframe(report.to_frame(), width="stretch", hide_index=True)

    @classmethod
    def _build_contract(
        cls,
        name: str,
        allow_extra_columns: bool,
        edited: pd.DataFrame,
    ) -> DatasetSchemaContract:
        columns = tuple(cls._build_column(row) for _, row in edited.iterrows())
        return DatasetSchemaContract(
            name=name,
            columns=columns,
            allow_extra_columns=allow_extra_columns,
        )

    @classmethod
    def _build_column(cls, row: pd.Series) -> ColumnContract:
        data_type = cast(SchemaDataType, str(row["data_type"]))
        return ColumnContract(
            name=str(row["column"]),
            required=bool(row["required"]),
            data_type=data_type,
            nullable=bool(row["nullable"]),
            minimum=cls._optional_number(row["minimum"]),
            maximum=cls._optional_number(row["maximum"]),
            accepted_values=cls._accepted_values(row["accepted_values"], data_type),
        )

    @staticmethod
    def _optional_number(value: object) -> float | None:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        return float(cast(float | int | str, value))

    @staticmethod
    def _accepted_values(value: object, data_type: SchemaDataType) -> tuple[ContractValue, ...]:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ()
        tokens = [token.strip() for token in str(value).split(",") if token.strip()]
        if data_type == "integer":
            return tuple(int(token) for token in tokens)
        if data_type == "numeric":
            return tuple(float(token) for token in tokens)
        if data_type == "boolean":
            normalized = {"true": True, "false": False}
            try:
                return tuple(normalized[token.lower()] for token in tokens)
            except KeyError as exc:
                raise ValueError("Boolean accepted values must be true or false.") from exc
        return tuple(tokens)
