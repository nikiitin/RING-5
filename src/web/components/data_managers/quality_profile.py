"""Data-manager UI for dataset quality profiling."""

from typing import Literal

import pandas as pd
import streamlit as st

from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import WidgetKeyBuilder


class QualityProfileManager(DataManager):
    """Configure expected types and render a data-quality report."""

    @property
    def name(self) -> str:
        """Return the manager's display name."""
        return "Data Quality"

    def render(self) -> None:
        """Render expected-type controls and quality measurements."""
        # [impl->req~ring5.data.quality-profiler~1]
        st.markdown("### Data Quality")
        st.info(
            "Inspect missing cells, duplicate rows, constant columns, infinite values, "
            "IQR outliers, and values that do not match an expected type."
        )
        data = self.get_data()
        if data is None:
            st.warning("Load a dataset before profiling it.")
            return

        columns = list(data.columns)
        numeric_defaults = [
            column
            for column in columns
            if pd.api.types.is_numeric_dtype(data[column].dtype)
            and not pd.api.types.is_bool_dtype(data[column].dtype)
        ]
        boolean_defaults = [
            column for column in columns if pd.api.types.is_bool_dtype(data[column].dtype)
        ]
        datetime_defaults = [
            column for column in columns if pd.api.types.is_datetime64_any_dtype(data[column].dtype)
        ]
        string_defaults = [
            column
            for column in columns
            if pd.api.types.is_string_dtype(data[column].dtype) or data[column].dtype == object
        ]

        numeric = st.multiselect(
            "Expected numeric columns",
            columns,
            default=numeric_defaults,
            key=WidgetKeyBuilder.manager_key("quality", "numeric"),
        )
        boolean = st.multiselect(
            "Expected boolean columns",
            columns,
            default=boolean_defaults,
            key=WidgetKeyBuilder.manager_key("quality", "boolean"),
        )
        datetime = st.multiselect(
            "Expected datetime columns",
            columns,
            default=datetime_defaults,
            key=WidgetKeyBuilder.manager_key("quality", "datetime"),
        )
        strings = st.multiselect(
            "Expected text columns",
            columns,
            default=string_defaults,
            key=WidgetKeyBuilder.manager_key("quality", "string"),
        )

        if not st.button(
            "Profile Dataset",
            type="primary",
            key=WidgetKeyBuilder.manager_key("quality", "profile"),
        ):
            return

        selections = numeric + boolean + datetime + strings
        duplicates = sorted({column for column in selections if selections.count(column) > 1})
        if duplicates:
            st.error(f"Columns have more than one expected type: {', '.join(duplicates)}.")
            return
        expected: dict[str, Literal["numeric", "integer", "boolean", "datetime", "string"]] = {}
        expected.update(dict.fromkeys(numeric, "numeric"))
        expected.update(dict.fromkeys(boolean, "boolean"))
        expected.update(dict.fromkeys(datetime, "datetime"))
        expected.update(dict.fromkeys(strings, "string"))
        try:
            report = self.api.managers.profile_data(data, expected_types=expected)
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
            return

        containers = st.columns(6)
        values = (
            ("Rows", report.row_count),
            ("Columns", report.column_count),
            ("Missing cells", report.missing_cells),
            ("Duplicate rows", report.duplicate_rows),
            ("IQR outliers", report.iqr_outlier_cells),
            ("Schema violations", report.schema_violations),
        )
        for container, (label, value) in zip(containers, values, strict=True):
            with container:
                st.metric(label, value)
        if report.constant_columns:
            st.warning(f"Constant columns: {', '.join(report.constant_columns)}")
        for error in report.schema_errors:
            st.error(error)
        profile = report.to_frame()
        st.dataframe(profile, width="stretch")
        st.download_button(
            "Download quality profile",
            profile.to_csv(index=False),
            file_name="ring5-data-quality.csv",
            mime="text/csv",
            key=WidgetKeyBuilder.manager_key("quality", "download"),
        )
