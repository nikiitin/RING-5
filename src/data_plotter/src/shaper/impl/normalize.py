#!/usr/bin/env python3
from typing import Any
from src.data_plotter.src.shaper.uniDfShaper import UniDfShaper
import src.utils.utils as utils
import pandas as pd
import numpy as np


class Normalize(UniDfShaper):
    """
    Normalize is a Shaper that normalizes the data in a dataframe.
    It groups data and normalizes numeric columns relative to a baseline configuration.
    """

# Getters and setters
    @property # Variables (columns) that will be summed to create the normalizer
    def _normalizerVars(self) -> list:
        return self._normalizerVars_data
    @_normalizerVars.setter
    def _normalizerVars(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for item in value:
            utils.checkVarType(item, str)
        self._normalizerVars_data = value
    
    @property # Variables (columns) to normalize
    def _normalizeVars(self) -> list:
        return self._normalizeVars_data
    @_normalizeVars.setter
    def _normalizeVars(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for item in value:
            utils.checkVarType(item, str)
        self._normalizeVars_data = value
    
    @property # Column that contains the normalizer configuration
    def _normalizerColumn(self) -> str:
        return self._normalizerColumn_data
    @_normalizerColumn.setter
    def _normalizerColumn(self, value: Any) -> None:
        utils.checkVarType(value, str)
        self._normalizerColumn_data = value
    
    @property # Value in normalizerColumn to use as baseline
    def _normalizerValue(self) -> str:
        return self._normalizerValue_data
    @_normalizerValue.setter
    def _normalizerValue(self, value: Any) -> None:
        utils.checkVarType(value, str)
        self._normalizerValue_data = value
    
    @property # Columns to group by
    def _groupBy(self) -> list:
        return self._groupBy_data
    @_groupBy.setter
    def _groupBy(self, value: Any) -> None:
        utils.checkVarType(value, list)
        for item in value:
            utils.checkVarType(item, str)
        self._groupBy_data = value
    
    @property # Whether to auto-normalize SD columns
    def _normalizeSd(self) -> bool:
        return self._normalizeSd_data
    @_normalizeSd.setter
    def _normalizeSd(self, value: Any) -> None:
        utils.checkVarType(value, bool)
        self._normalizeSd_data = value


    def __init__(self, params: dict) -> None:
        super().__init__(params)
        # normalizeVars is required
        self._normalizeVars = utils.getElementValue(self._params, "normalizeVars", optional=False)
        # normalizerVars defaults to normalizeVars if not provided
        if "normalizerVars" in self._params:
            self._normalizerVars = utils.getElementValue(self._params, "normalizerVars", optional=False)
        else:
            self._normalizerVars = self._normalizeVars
        self._normalizerColumn = utils.getElementValue(self._params, "normalizerColumn", optional=False)
        self._normalizerValue = utils.getElementValue(self._params, "normalizerValue", optional=False)
        self._groupBy = utils.getElementValue(self._params, "groupBy", optional=False)
        # normalizeSd is optional, defaults to True
        if "normalizeSd" in self._params:
            self._normalizeSd = utils.getElementValue(self._params, "normalizeSd", optional=True)
            if self._normalizeSd is None:
                self._normalizeSd = True
        else:
            self._normalizeSd = True

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        # Check for required parameters (normalizerVars is optional, defaults to normalizeVars)
        utils.checkElementExists(self._params, "normalizeVars")
        utils.checkElementExists(self._params, "normalizerColumn")
        utils.checkElementExists(self._params, "normalizerValue")
        utils.checkElementExists(self._params, "groupBy")
        # normalizeSd is optional with default True
        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        verified = super()._verifyPreconditions(data_frame)
        
        # Check that normalizerVars columns exist
        for col in self._normalizerVars:
            if col not in data_frame.columns:
                raise ValueError(f"The normalizer variable column '{col}' does not exist in the data frame! Stopping")
            if not pd.api.types.is_numeric_dtype(data_frame[col]):
                raise ValueError(f"The normalizer variable column '{col}' is not numeric! Stopping")
        
        # Check that normalizeVars columns exist
        for col in self._normalizeVars:
            if col not in data_frame.columns:
                raise ValueError(f"The normalize variable column '{col}' does not exist in the data frame! Stopping")
            if not pd.api.types.is_numeric_dtype(data_frame[col]):
                raise ValueError(f"The normalize variable column '{col}' is not numeric! Stopping")
        
        # Check that normalizerColumn exists
        if self._normalizerColumn not in data_frame.columns:
            raise ValueError(f"The normalizer column '{self._normalizerColumn}' does not exist in the data frame! Stopping")
        
        # Check that normalizerValue exists in the normalizerColumn
        if self._normalizerValue not in data_frame[self._normalizerColumn].values:
            raise ValueError(f"The normalizer value '{self._normalizerValue}' does not exist in column '{self._normalizerColumn}'! Stopping")
        
        # Check that groupBy columns exist
        for col in self._groupBy:
            if col not in data_frame.columns:
                raise ValueError(f"The groupBy column '{col}' does not exist in the data frame! Stopping")
        
        # Check that each group has exactly one normalizer row
        groups = data_frame.groupby(self._groupBy)
        if len(groups) == 0:
            raise ValueError("No groups found for normalization! Stopping")
        
        for name, group in groups:
            normalizer_rows = group[group[self._normalizerColumn] == self._normalizerValue]
            if len(normalizer_rows) != 1:
                raise ValueError(f"Group {name} has {len(normalizer_rows)} normalizer rows (expected 1)! Stopping")

        return verified
    
    def normalize_group(self, group):
        """
        Normalize a single group by dividing variables by the sum of normalizer variables.
        The normalizer is computed as the sum of all normalizerVars from the baseline row.
        """
        # Create a copy to avoid SettingWithCopyWarning
        result = group.copy()
        
        # Find the normalizer row
        normalizer_row = result[result[self._normalizerColumn] == self._normalizerValue]
        
        if len(normalizer_row) == 0:
            # No normalizer in this group, return unchanged
            return result
        
        # Calculate the normalizer value as the sum of normalizer variables
        normalizer_value = sum(normalizer_row.iloc[0][col] for col in self._normalizerVars)
        
        if normalizer_value == 0:
            # Avoid division by zero - set all normalized columns to 0
            for var in self._normalizeVars:
                result[var] = 0
            if self._normalizeSd:
                for var in self._normalizeVars:
                    sd_col = f"{var}.sd"
                    if sd_col in result.columns:
                        result[sd_col] = 0
            return result
        
        # Normalize each variable by dividing by the normalizer sum
        for var in self._normalizeVars:
            result[var] = result[var] / normalizer_value
        
        # Auto-normalize .sd columns if enabled
        if self._normalizeSd:
            # SD columns should be normalized using the SAME normalizer as their base statistic
            # (not the SD of the normalizer variables)
            for var in self._normalizeVars:
                sd_col = f"{var}.sd"
                if sd_col in result.columns:
                    result[sd_col] = result[sd_col] / normalizer_value

        return result

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        super().__call__(data_frame)  # Just for precondition checking
        
        # Create a copy to avoid modifying the original
        result = data_frame.copy()
        
        # Group by the specified columns and apply normalization
        grouped = result.groupby(self._groupBy, group_keys=False)
        
        # Apply normalization - the normalize_group method preserves all columns
        # Note: pandas will issue FutureWarning about operating on grouping columns,
        # but this is intentional - we want to preserve all columns in the result
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=FutureWarning, 
                                  message='.*DataFrameGroupBy.apply operated on the grouping columns.*')
            result = grouped.apply(lambda x: self.normalize_group(x))
        
        return result


# Main function to test the Normalize class
def test():
    # Create a sample data frame
    df = pd.DataFrame({
        'config': ['baseline', 'baseline', 'baseline', 'config2', 'config2', 'config2'],
        'benchmark': ['B1', 'B2', 'B3', 'B1', 'B2', 'B3'],
        'metric1': [100, 200, 300, 150, 250, 450],
        'metric2': [10, 20, 30, 15, 25, 45]
    })
    params = {
        'normalizeVars': ['metric1', 'metric2'],
        'normalizerColumn': 'config',
        'normalizerValue': 'baseline',
        'groupBy': ['benchmark'],
        'srcCsv': 'normtest.csv',
        'dstCsv': 'output_data.csv'
    }
    print("Input:")
    print(df)
    print("\n" + "="*80 + "\n")
    norm_shaper = Normalize(params)
    df = norm_shaper(df)
    print("Result (normalized by 'baseline'):")
    print(df)
    print("\n" + "="*80 + "\n")
    print("Verification:")
    print("- Each variable is normalized by its own baseline value")
    print("- Baseline rows should have value = 1.0 for each normalized variable")
    baseline = df[df['config'] == 'baseline']
    print("\nBaseline rows:")
    print(baseline)
    print(f"\nBaseline metric1 values (should be 1.0): {baseline['metric1'].values}")
    print(f"Baseline metric2 values (should be 1.0): {baseline['metric2'].values}")


if __name__ == "__main__":
    test()
