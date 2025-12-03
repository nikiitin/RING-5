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


    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self._normalizeVars = utils.getElementValue(self._params, "normalizeVars")
        self._normalizerColumn = utils.getElementValue(self._params, "normalizerColumn")
        self._normalizerValue = utils.getElementValue(self._params, "normalizerValue")
        self._groupBy = utils.getElementValue(self._params, "groupBy")

    def _verifyParams(self) -> bool:
        verified = super()._verifyParams()
        # Check for required parameters
        utils.checkElementExists(self._params, "normalizeVars")
        utils.checkElementExists(self._params, "normalizerColumn")
        utils.checkElementExists(self._params, "normalizerValue")
        utils.checkElementExists(self._params, "groupBy")
        return verified

    def _verifyPreconditions(self, data_frame: pd.DataFrame) -> bool:
        verified = super()._verifyPreconditions(data_frame)
        
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
        Normalize a single group by dividing all values by the sum of the normalizer row.
        This ensures that the baseline configuration sums to 1.0 across all normalized variables.
        """
        # Create a copy to avoid SettingWithCopyWarning
        result = group.copy()
        
        # Find the normalizer row
        normalizer_row = result[result[self._normalizerColumn] == self._normalizerValue]
        
        if len(normalizer_row) == 0:
            # No normalizer in this group, return unchanged
            return result
        
        # Extract normalizer values for the variables to normalize
        normalizer_values = normalizer_row.iloc[0][self._normalizeVars]
        
        # Calculate the sum of all normalizer values (total normalizer)
        normalizer_sum = normalizer_values.sum()
        
        # Normalize: divide each value by the total sum
        if normalizer_sum != 0:
            for var in self._normalizeVars:
                result[var] = result[var] / normalizer_sum
        else:
            # Avoid division by zero
            for var in self._normalizeVars:
                result[var] = 0

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
    print("Baseline rows (sum of all normalized vars should = 1.0):")
    baseline = df[df['config'] == 'baseline']
    print(baseline)
    print(f"\nSum of metrics for first baseline row: {baseline.iloc[0][['metric1', 'metric2']].sum():.6f}")
    print("Expected: 1.0")


if __name__ == "__main__":
    test()
