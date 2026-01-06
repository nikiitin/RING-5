#!/usr/bin/env python3
from typing import Any

import pandas as pd
from scipy.stats import gmean, hmean

import src.utils.utils as utils
from src.processing.shapers.uni_df_shaper import UniDfShaper


class Mean(UniDfShaper):

    # Getters and setters
    @property  # Numeric columns to calculate the mean for
    def _meanVars(self) -> list:
        return self._meanVars_data

    @_meanVars.setter
    def _meanVars(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for item in value:
            utils.checkVarType(item, str)
        self._meanVars_data = value

    @property  # Algorithm to use for calculating the mean
    def _meanAlgorithm(self) -> str:
        return self._meanAlgorithm_function

    @_meanAlgorithm.setter
    def _meanAlgorithm(self, value: Any) -> None:
        utils.checkVarType(value, str)
        if value not in ["arithmean", "geomean", "hmean"]:
            raise ValueError(
                "The 'meanAlgorithm' parameter must be one of 'arithmean', 'geomean', or 'hmean'."
            )
        self._meanAlgorithm_function = value

    @property  # Columns to group by (e.g., config_description_abbrev)
    def _groupingColumns(self) -> list:
        return self._groupingColumns_data

    @_groupingColumns.setter
    def _groupingColumns(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for val in value:
            utils.checkVarType(val, str)
        self._groupingColumns_data = value

    @property  # Column to replace with mean algorithm name (e.g., benchmark_name)
    def _replacingColumn(self) -> str:
        return self._replacingColumn_data

    @_replacingColumn.setter
    def _replacingColumn(self, value: Any) -> None:
        utils.checkVarType(value, str)
        self._replacingColumn_data = value

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._meanVars = utils.getElementValue(self._params, "meanVars")
        self._meanAlgorithm = utils.getElementValue(self._params, "meanAlgorithm")
        
        # Handle legacy or new param
        if "groupingColumns" in self._params:
            self._groupingColumns = utils.getElementValue(self._params, "groupingColumns")
        else:
            # Legacy fallback
            col = utils.getElementValue(self._params, "groupingColumn")
            self._groupingColumns = [col]
            
        self._replacingColumn = utils.getElementValue(self._params, "replacingColumn")

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        # Checks for required parameters
        utils.checkElementExists(self._params, "meanVars")
        utils.checkElementExists(self._params, "meanAlgorithm")
        if "groupingColumns" not in self._params and "groupingColumn" not in self._params:
             raise ValueError("Missing grouping parameter (groupingColumns or groupingColumn)")
        utils.checkElementExists(self._params, "replacingColumn")
        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        verified = super()._verifyPreconditions(data_frame)
        # Check that the meanVars columns exist in the data frame
        for col in self._meanVars:
            if col not in data_frame.columns:
                raise ValueError(
                    f"The mean variable column '{col}' does not exist in the data frame! Stopping"
                )

        # Check that the grouping columns exist
        for col in self._groupingColumns:
            if col not in data_frame.columns:
                raise ValueError(
                    f"The grouping column '{col}' does not exist in the data frame! "
                    "Stopping"
                )

        # Check that the replacing column exists
        if self._replacingColumn not in data_frame.columns:
            raise ValueError(
                f"The replacing column '{self._replacingColumn}' does not exist in the data frame! "
                "Stopping"
            )

        # Check that meanVars are numeric
        for col in self._meanVars:
            if not pd.api.types.is_numeric_dtype(data_frame[col]):
                raise ValueError(f"The mean variable column '{col}' is not numeric! Stopping")

        return verified

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        data_frame = super().__call__(data_frame)

        # Create a copy to avoid modifying the original
        result = data_frame.copy()

        # Group by the grouping columns
        grouped = result.groupby(self._groupingColumns)

        # Calculate the mean based on the algorithm
        if self._meanAlgorithm == "arithmean":
            mean_df = grouped[self._meanVars].mean().reset_index()
        elif self._meanAlgorithm == "geomean":
            mean_df = grouped[self._meanVars].agg(gmean).reset_index()
        elif self._meanAlgorithm == "hmean":
            mean_df = grouped[self._meanVars].agg(hmean).reset_index()
        else:
            raise ValueError(f"Unsupported mean algorithm: {self._meanAlgorithm}")

        # Set the replacing column to the algorithm name
        mean_df[self._replacingColumn] = self._meanAlgorithm

        # For all other columns (not meanVars, not groupingColumn, not replacingColumn),
        # fill with appropriate values from the first row of each group
        other_cols = [
            col
            for col in result.columns
            if col not in self._meanVars
            and col not in self._groupingColumns
            and col != self._replacingColumn
        ]

        for col in other_cols:
            # Get the first value from each group for this column
            first_values = grouped[col].first().reset_index()
            # Merge back to mean_df on grouping columns
            mean_df = mean_df.merge(first_values, on=self._groupingColumns, how="left")

        # Concatenate the mean rows to the original dataframe
        result = pd.concat([result, mean_df], ignore_index=True)

        return result


# Main function to test the Mean class
def test():
    # Create a sample data frame
    df = pd.DataFrame(
        {
            "system_id": ["S1", "S1", "S1", "S1", "S2", "S2", "S2", "S2", "S3", "S3", "S3", "S3"],
            "benchmark": ["B1", "B2", "B1", "B2", "B1", "B2", "B1", "B2", "B1", "B2", "B1", "B2"],
            "throughput": [100, 105, 120, 118, 80, 82, 78, 85, 90, 95, 100, 102],
            "latency": [1.2, 1.1, 1.5, 1.4, 2.0, 1.9, 2.1, 2.2, 1.8, 1.7, 1.6, 1.5],
            "config_param": [
                "A1",
                "A1",
                "A2",
                "A2",
                "B1",
                "B1",
                "B2",
                "B2",
                "C1",
                "C1",
                "C2",
                "C2",
            ],
        }
    )
    params = {
        "meanVars": ["throughput", "latency"],
        "meanAlgorithm": "arithmean",
        "groupingColumns": ["system_id"],
        "replacingColumn": "benchmark",
        "srcCsv": "meantest.csv",
        "dstCsv": "output_data.csv",
    }
    print("Input:")
    print(df)
    print("\n" + "=" * 80 + "\n")
    mean_shaper = Mean(params)
    df = mean_shaper(df)
    print("Result:")
    print(df)
    print("\n" + "=" * 80 + "\n")
    print("Mean rows (where benchmark == 'arithmean'):")
    print(df[df["benchmark"] == "arithmean"])


if __name__ == "__main__":
    test()
