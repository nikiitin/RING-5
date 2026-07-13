"""
Data Components for RING-5.
Handles data visualization, inspection, and export.
"""

import tempfile

import pandas as pd
import streamlit as st


def detect_column_types(data: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Classify DataFrame columns into ``(numeric_cols, categorical_cols)``.

    The one shared classifier for the whole web layer — categorical includes
    ``object``/``string``/``category`` so categorical-dtype columns are never missed.
    """
    numeric = data.select_dtypes(include=["number"]).columns.tolist()
    categorical = data.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    return numeric, categorical


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
            st.metric("Rows", len(data), border=True)
        with col2:
            st.metric("Columns", len(data.columns), border=True)
        numeric_cols, categorical_cols = detect_column_types(data)
        with col3:
            st.metric("Numeric Columns", len(numeric_cols), border=True)
        with col4:
            st.metric("Categorical Columns", len(categorical_cols), border=True)

        DataComponents.show_missing_data_notice(data)

    @staticmethod
    def show_missing_data_notice(data: pd.DataFrame) -> None:
        """Warn when numeric columns contain missing (NaN) values.

        Missing/unmeasured stats are kept as NaN rather than fabricated as 0,
        so surface them here for traceability: the affected columns are named,
        and the parser logs name the specific source files.
        """
        numeric = data.select_dtypes(include=["number"])
        if numeric.empty:
            return
        na_counts = numeric.isna().sum()
        affected = na_counts[na_counts > 0]
        if affected.empty:
            return

        st.warning(
            f"⚠️ {len(affected)} column(s) contain missing values (kept as NaN, not 0) — "
            "these stats were absent or incomplete in some runs. See the parser logs for the "
            "specific files."
        )
        with st.expander(f"Missing-value details ({len(affected)} column(s))"):
            detail = (
                affected.rename("Missing rows")
                .rename_axis("Column")
                .reset_index()
                .sort_values("Missing rows", ascending=False)
            )
            st.dataframe(detail, width="stretch", hide_index=True)

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
                on_click="ignore",
            )

        with col2:
            json_str = data.to_json(orient="records", indent=2) or ""
            json_data = json_str.encode("utf-8")
            st.download_button(
                label="Download JSON",
                data=json_data,
                file_name=f"{prefix}.json",
                mime="application/json",
                width="stretch",
                on_click="ignore",
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
                on_click="ignore",
            )
