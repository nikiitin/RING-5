"""
Data Manager Parameters
Proper parameter classes for data managers that can work with both CLI and web interfaces.
"""
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import tempfile


@dataclass
class DataManagerParams:
    """
    Base parameters for all data managers.
    Replaces AnalyzerInfo with a proper, testable interface.
    """
    csv_path: str
    categorical_columns: List[str]
    statistic_columns: Optional[List[str]] = None
    
    def get_work_csv(self) -> str:
        """Get the path to the working CSV file."""
        return self.csv_path
    
    def get_categorical_columns(self) -> List[str]:
        """Get list of categorical columns."""
        return self.categorical_columns
    
    def get_statistic_columns(self) -> Optional[List[str]]:
        """Get list of statistic columns."""
        return self.statistic_columns


@dataclass
class SeedsReducerParams(DataManagerParams):
    """Parameters specific to Seeds Reducer."""
    enable_reduction: bool = True


@dataclass
class OutlierRemoverParams(DataManagerParams):
    """Parameters specific to Outlier Remover."""
    outlier_column: str = None
    group_by_columns: Optional[List[str]] = None


@dataclass
class PreprocessorParams(DataManagerParams):
    """Parameters specific to Preprocessor."""
    operations: dict = None  # {dst_col: {operator: str, src1: str, src2: str}}


def create_manager_params_from_cli(analyzer_info) -> DataManagerParams:
    """
    Factory function to create DataManagerParams from CLI's AnalyzerInfo.
    
    Args:
        analyzer_info: AnalyzerInfo object from argumentParser
        
    Returns:
        DataManagerParams instance
    """
    return DataManagerParams(
        csv_path=analyzer_info.getWorkCsv(),
        categorical_columns=analyzer_info.getCategoricalColumns(),
        statistic_columns=None  # Will be auto-detected
    )


def create_manager_params_from_dataframe(df, csv_path: Optional[str] = None) -> DataManagerParams:
    """
    Factory function to create DataManagerParams from a DataFrame.
    
    Args:
        df: pandas DataFrame
        csv_path: Optional path to save/load CSV. If None, creates temp file.
        
    Returns:
        DataManagerParams instance
    """
    import pandas as pd
    
    # Auto-detect categorical columns
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    # Remove random_seed from categorical if present
    if 'random_seed' in categorical_cols:
        categorical_cols.remove('random_seed')
    
    # Auto-detect numeric/statistic columns
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if 'random_seed' in numeric_cols:
        numeric_cols.remove('random_seed')
    
    # Create temp CSV if path not provided
    if csv_path is None:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        csv_path = tmp.name
        tmp.close()
        df.to_csv(csv_path, index=False, sep=' ')
    
    return DataManagerParams(
        csv_path=csv_path,
        categorical_columns=categorical_cols,
        statistic_columns=numeric_cols
    )
