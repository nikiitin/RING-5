"""
Data Components for RING-5.
Handles data visualization, inspection, and export.
"""

import tempfile

import pandas as pd
import streamlit as st


class DataComponents:
    """Reusable components for data visualization and export."""

    @staticmethod
    def show_data_preview(data: pd.DataFrame, title: str = "Data Preview", rows: int = 20) -> None:
        """
        Display a data preview with statistics.

        Args:
            data: DataFrame to preview
            title: Title for the preview section
            rows: Number of rows to show
        """
        st.markdown(f"### {title}")
        st.dataframe(data.head(rows), width="stretch")

        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Rows", len(data))
        with col2:
            st.metric("Columns", len(data.columns))
        with col3:
            numeric_cols = data.select_dtypes(include=["number"]).columns
            st.metric("Numeric Columns", len(numeric_cols))
        with col4:
            categorical_cols = data.select_dtypes(include=["object", "string"]).columns
            st.metric("Categorical Columns", len(categorical_cols))

    @staticmethod
    def show_column_details(data: pd.DataFrame) -> None:
        """
        Display detailed column information in an expander.

        Args:
            data: DataFrame to analyze
        """
        with st.expander("Column Details"):
            col_info = pd.DataFrame(
                {
                    "Column": data.columns,
                    "Type": data.dtypes.astype(str),
                    "Non-Null": data.count(),
                    "Null": data.isnull().sum(),
                    "Unique": [data[col].nunique() for col in data.columns],
                }
            )
            st.dataframe(col_info, width="stretch")

    @staticmethod
    def download_buttons(data: pd.DataFrame, prefix: str = "processed_data") -> None:
        """
        Display download buttons for different formats.

        Args:
            data: DataFrame to download
            prefix: Filename prefix
        """
        st.markdown("### Download Data")

        col1, col2, col3 = st.columns(3)

        with col1:
            csv_data = data.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name=f"{prefix}.csv",
                mime="text/csv",
                width="stretch",
            )

        with col2:
            json_data = data.to_json(orient="records", indent=2).encode("utf-8")
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name=f"{prefix}.json",
                mime="application/json",
                width="stretch",
            )

        with col3:
            excel_buffer = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            data.to_excel(excel_buffer.name, index=False, engine="openpyxl")
            with open(excel_buffer.name, "rb") as f:
                excel_data = f.read()

            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=f"{prefix}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
