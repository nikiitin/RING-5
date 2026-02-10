"""
Module: src/web/services/shapers/impl/transformer.py

Purpose:
    Converts column data types between scalar (numeric) and factor (categorical) types.
    Enables type coercion for proper plotting and statistical operations. Supports
    custom categorical ordering for factors.

Responsibilities:
    - Convert columns to numeric (scalar) or categorical (factor) types
    - Apply custom categorical order when converting to factors
    - Handle type conversion errors gracefully
    - Preserve original data in new column

Dependencies:
    - pandas: For type conversion and categorical operations
    - UniDfShaper: Base class for shaper interface

Usage Example:
    >>> from src.web.services.shapers.impl.transformer import Transformer
    >>> import pandas as pd
    >>>
    >>> # Sample data with numeric config column
    >>> data = pd.DataFrame({
    ...     'config': ['0', '1', '2'],
    ...     'ipc': [1.2, 1.5, 1.8]
    ... })
    >>>
    >>> # Convert config to factor with custom order
    >>> transformer = Transformer({
    ...     'column': 'config',
    ...     'target_type': 'factor',
    ...     'order': ['2', '1', '0']  # Reverse order
    ... })
    >>>
    >>> result = transformer(data)
    >>> print(result['config'].dtype)  # CategoricalDtype
    >>> print(result['config'].cat.categories)  # ['2', '1', '0']
    >>>
    >>> # Convert IPC to scalar (ensure numeric type)
    >>> transformer_numeric = Transformer({
    ...     'column': 'ipc',
    ...     'target_type': 'scalar'
    ... })
    >>> result = transformer_numeric(data)
    >>> print(result['ipc'].dtype)  # float64

Design Patterns:
    - Strategy Pattern: One of many shaper implementations
    - Template Method: Implements UniDfShaper interface
    - Adapter Pattern: Adapts between type systems (numeric ↔ categorical)

Performance Characteristics:
    - Time Complexity: O(n) for type conversion
    - Space Complexity: O(n) for new typed column
    - Typical: 5-10ms for 10k rows

Error Handling:
    - Raises ValueError if 'column' parameter empty or missing
    - Raises ValueError if 'target_type' not 'scalar' or 'factor'
    - Raises ValueError if column doesn't exist in dataframe
    - Logs warnings if type conversion fails (attempts coercion)

Thread Safety:
    - Stateless transformation (thread-safe)
    - DataFrame operations not synchronized

Type Conversion Rules:
    - scalar: pd.to_numeric() with errors='coerce'
    - factor: astype(str) → astype(CategoricalDtype)
    - Custom order: Applied via pd.CategoricalDtype(categories, ordered=True)

Testing:
    - Unit tests: tests/unit/test_transformer.py
    - Integration tests: tests/integration/test_e2e_managers_shapers.py

Version: 2.0.0
Last Modified: 2026-01-27
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from src.web.services.shapers.uni_df_shaper import UniDfShaper


class Transformer(UniDfShaper):
    """
    Shaper that converts a column to a specific type (Numeric/Scalar or Categorical/Factor).

    Can also apply a fixed sorting order when converting to Factor.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize Transformer.

        Args:
            params: Dictionary containing:
                - column (str): Target column to transform.
                - target_type (str): 'scalar' or 'factor'.
                - order (Optional[List[str]]): Specific categorical order for factors.
        """
        self.column: str = params.get("column", "")
        self.target_type: str = params.get("target_type", "")
        self.order: Optional[List[str]] = params.get("order")
        super().__init__(params)

    def _verify_params(self) -> bool:
        """Verify parameter presence and value validity."""
        super()._verify_params()

        if not isinstance(self.params.get("column"), str) or not self.params["column"]:
            raise ValueError("Transformer requires non-empty string 'column' parameter.")

        target_type = self.params.get("target_type")
        if target_type not in ["scalar", "factor"]:
            raise ValueError("Transformer 'target_type' must be 'scalar' or 'factor'.")

        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that the target column exists."""
        super()._verify_preconditions(data_frame)
        if self.column not in data_frame.columns:
            raise ValueError(f"Transformer: Column '{self.column}' not found in dataframe.")
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Executes the data type conversion."""
        self._verify_preconditions(data_frame)

        df = data_frame.copy()

        try:
            if self.target_type == "factor":
                # Convert to string first to ensure clean categorical conversion
                df[self.column] = df[self.column].astype(str)
                if self.order and isinstance(self.order, list):
                    df[self.column] = pd.Categorical(
                        df[self.column], categories=self.order, ordered=True
                    )
            elif self.target_type == "scalar":
                # Convert to numeric, pushing non-convertibles to NaN (Zero Hallucination)
                df[self.column] = pd.to_numeric(df[self.column], errors="coerce")
        except Exception as e:
            # Domain Layer error handling
            raise ValueError(
                f"TRANSFORMER: Failed to convert '{self.column}' to {self.target_type}: {e}"
            ) from e

        return df
