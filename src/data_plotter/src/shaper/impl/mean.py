#!/usr/bin/env python3
from typing import Any
from src.data_plotter.src.shaper.uniDfShaper import UniDfShaper
import src.utils.utils as utils
import pandas as pd
from scipy.stats import gmean, hmean
import numpy as np

class Mean(UniDfShaper):

# Getters and setters
    @property # Columns to calculate the mean for
    def _summaryColumns(self) -> list:
        return self._summaryColumns_data
    @_summaryColumns.setter
    def _summaryColumns(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for item in value:
            utils.checkVarType(item, str)
        self._summaryColumns_data = value
    @property # Algorithm to use for calculating the mean
    def _meanAlgorithm(self) -> str:
        return self._meanAlgorithm_function
    @_meanAlgorithm.setter
    def _meanAlgorithm(self, value: Any) -> None:
        utils.checkVarType(value, str)
        if value not in ["amean", "gmean", "hmean"]:
            raise ValueError("The 'meanAlgorithm' parameter must be one of 'amean', 'gmean', or 'hmean'.")
        self._meanAlgorithm_function = value
    @property # Name to replace the summary columns with in the new rows
    def _dstName(self) -> str:
        return self._dstName_data
    @_dstName.setter
    def _dstName(self, value: Any) -> None:
        utils.checkVarType(value, str)
        self._dstName_data = value

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._summaryColumns = utils.getElementValue(self._params, "summaryColumns")
        self._meanAlgorithm = utils.getElementValue(self._params, "meanAlgorithm")
        self._dstName = utils.getElementValue(self._params, "dstColumn")

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        # Checks for meanSrcVars
        utils.checkElementExists(self._params, "summaryColumns")
        utils.checkElementExists(self._params, "meanAlgorithm")
        utils.checkElementExists(self._params, "dstColumn")
        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        verified = super()._verifyPreconditions(data_frame)
        # Check that the summary columns exist in the data frame
        for col in self._summaryColumns:
            if col not in data_frame.columns:
                raise ValueError(f"The column {col} does not exist in the data frame! Stopping")
        if data_frame.select_dtypes(include=np.number).empty:
            raise ValueError("The data frame does not contain any numeric columns! Stopping")
        # Check that the dstName is not in the data frame
        if self._dstName in data_frame.columns:
            raise ValueError(f"The column {self._dstName} already exists in the data frame! Stopping")
        return verified

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        data_frame = super().__call__(data_frame)
        # Get the numeric columns
        numeric_cols = data_frame.select_dtypes(include=np.number).columns.tolist()
        # Get the non-numeric columns
        config_cols = [col for col in data_frame.columns
                       if col not in numeric_cols
                       and col not in self._summaryColumns]

        # For every combination of summary columns, calculate the mean
        # and add it to the data frame

        # Get the different combinations of summary columns
        summary_cols = data_frame[self._summaryColumns].drop_duplicates()

        # Calculate the mean for each combination of summary columns
        means_calculated = False  # Flag to track if any means were calculated
        all_means_rows = []  # Store the means rows for concatenation
        for _, row in summary_cols.iterrows():
            # Get the rows that match the current combination of summary columns
            sys_data = data_frame.loc[(data_frame[self._summaryColumns] == row).all(axis=1)]

            # Calculate the means for the numeric columns
            if self._meanAlgorithm == "amean":
                means = sys_data[numeric_cols].mean()
            elif self._meanAlgorithm == "gmean":
                means = sys_data[numeric_cols].apply(gmean)
            elif self._meanAlgorithm == "hmean":
                means = sys_data[numeric_cols].apply(hmean)
            else:
                raise ValueError("Unsupported mean algorithm")
            means_calculated = True

            # Create a new Series for the means row
            means_row = pd.Series(dtype='object')  # Create an empty series to start
            # Assign the mean values
            for col in numeric_cols:
                means_row[col] = means[col] if col in means else None

            # Assign the dstName value to the config columns
            for col in config_cols:
                means_row[col] = self._dstName

            # Assign the summary column values from the current row
            for col in self._summaryColumns:
                means_row[col] = row[col]  # Use the values from the 'row' Series

            all_means_rows.append(means_row) # Append means row
        
        if means_calculated:
            # Concatenate all means rows to original dataframe
            means_df = pd.DataFrame(all_means_rows)
            data_frame = pd.concat([data_frame, means_df], ignore_index=True)

        return data_frame

# Main function to test the Mean class
def test():
    # Create a sample data frame
    df = pd.DataFrame({
    'system_id': ['S1', 'S1', 'S1', 'S1', 'S2', 'S2', 'S2', 'S2', 'S3', 'S3', 'S3', 'S3'],
    'benchmark': ['B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2', 'B1', 'B2'],
    'throughput': [100, 105, 120, 118, 80, 82, 78, 85, 90, 95, 100, 102],
    'latency': [1.2, 1.1, 1.5, 1.4, 2.0, 1.9, 2.1, 2.2, 1.8, 1.7, 1.6, 1.5],
    'config_param': ['A1', 'A1', 'A2', 'A2', 'B1', 'B1', 'B2', 'B2', 'C1', 'C1', 'C2', 'C2']
    })
    params = {
        'summaryColumns': ['system_id', "config_param"],
        'meanAlgorithm': 'amean',
        'dstColumn': 'ALL',
        'srcCsv': 'meantest.csv',
        'dstCsv': 'output_data.csv'
    }
    print("input: ")
    print(df)
    mean_shaper = Mean(params)
    df = mean_shaper(df)
    print("result: ")
    print(df)