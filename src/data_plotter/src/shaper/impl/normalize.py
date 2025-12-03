#!/usr/bin/env python3
from typing import Any
from src.data_plotter.src.shaper.uniDfShaper import UniDfShaper
import src.utils.utils as utils
import pandas as pd
import numpy as np


class Normalize(UniDfShaper):
    """
    Normalize is a Shaper that normalizes the data in a dataframe.
    It can be used to scale data before further processing or analysis.
    """

# Getters and setters
    @property # Configuration columns
    def config_columns(self) -> dict:
        return self.config_columns_data
    @config_columns.setter
    def config_columns(self, value: Any) -> None:
        utils.checkVarType(value, dict)
        self.config_columns_data = value
    @property # Group by columns
    def group_by(self) -> list:
        return self.group_by_data
    @group_by.setter
    def group_by(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for item in value:
            utils.checkVarType(item, str)
        self.group_by_data = value


    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self.config_columns = utils.getElementValue(self._params, "config_columns")
        self.group_by = utils.getElementValue(self._params, "group_by")

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        # Checks for meanSrcVars
        utils.checkElementExists(self._params, "config_columns")
        utils.checkElementExists(self._params, "group_by")
        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        verified = super()._verifyPreconditions(data_frame)
        # Check that reference rows exist in the data frame
        for col in self.config_columns.keys():
            if col not in data_frame.columns:
                raise ValueError(f"The config_column {col} does not exist in the data frame! Stopping")
            value = self.config_columns[col]
            if value not in data_frame[col].unique():
                raise ValueError(f"The config_column value {value} does not exist in the column {col}! Stopping")
        
        # Check that the group_by columns exist in the data frame
        for col in self.group_by:
            if col not in data_frame.columns:
                raise ValueError(f"The group_by column {col} does not exist in the data frame! Stopping")
        
        # Get the groupings from the data frame
        groups = data_frame.groupby(self.group_by)
        if len(groups) == 0:
            raise ValueError("No groups found for normalization! Stopping")
        
        # For every group, check that there is one and only one reference row
        for name, group in groups:
            mask = np.logical_and.reduce([
                group[col] == val for col, val in self.config_columns.items()
            ])
            if mask.sum() != 1:
                raise ValueError(f"Group {name} has {mask.sum()} reference rows! Stopping")
        
        # Check that there are statistical columns to normalize
        if data_frame.select_dtypes(include=np.number).empty:
            raise ValueError("No statistical columns found for normalization! Stopping")

        return verified

    def normalize_group(self, group):
        """Normalize a single group."""
        # Find reference row(s) matching the configuration
        mask = np.logical_and.reduce([
            group[col] == val for col, val in self.config_columns.items()
        ])
        reference_rows = group[mask]
        
        # Extract reference values (use first matching row)
        ref_values = reference_rows.iloc[0][self._stat_columns]
        
        # Normalize statistical columns
        group[self._stat_columns] = group[self._stat_columns] / ref_values.values

        return group

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        data_frame = super().__call__(data_frame)
        
        # Identify statistical columns (all numeric columns)
        self._stat_columns = data_frame.select_dtypes(include=np.number).columns.tolist()
        
        # Group by the specified column(s)
        grouped = data_frame.groupby(self.group_by, group_keys=False)
        
        # Apply normalization to each group
        return grouped.apply(lambda x: self.normalize_group(x))
    
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
        'config_columns': {'system_id' : 'S1', 'config_param': 'A2' },
        'group_by': ['benchmark'],
        'srcCsv': 'normtest.csv',
        'dstCsv': 'output_data.csv'
    }
    print("input: ")
    print(df)
    norm_shaper = Normalize(params)
    df = norm_shaper(df)
    print("result: ")
    print(df)