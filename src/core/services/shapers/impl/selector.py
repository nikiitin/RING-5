"""
Module: src.core.services/shapers/impl/selector.py

Purpose:
    Abstract base class for data filtering shapers. Provides common infrastructure
    for selecting subsets of data based on column values. Concrete implementations
    include TopNSelector, BottomNSelector, and ValueSelector.

Responsibilities:
    - Validate 'column' parameter exists
    - Verify target column exists in dataframe
    - Provide template for filter implementations
    - Maintain immutability (return new DataFrame)

Dependencies:
    - pandas: For DataFrame operations
    - UniDfShaper: Base class for shaper interface

Usage Example:
    >>> # This is an abstract base class - use concrete implementations:
    >>> from src.core.services.shapers.impl.selector.selector_algorithms import TopNSelector
    >>>
    >>> # Select top 5 benchmarks by IPC
    >>> selector = TopNSelector({
    ...     'column': 'ipc',
    ...     'n': 5
    ... })
    >>>
    >>> filtered = selector(data)

Design Patterns:
    - Template Method Pattern: Defines validation skeleton for subclasses
    - Strategy Pattern: Different selection algorithms as subclasses
    - Abstract Base Class: Forces column validation in all selectors

Performance Characteristics:
    - Time Complexity: O(1) for validation, O(n) for filtering (subclass dependent)
    - Space Complexity: O(n) worst case (filtering can return full dataset)
    - Typical: <5ms for 10k rows

Error Handling:
    - Raises ValueError if 'column' parameter missing or empty
    - Raises ValueError if column doesn't exist in dataframe

Thread Safety:
    - Stateless validation (thread-safe)
    - DataFrame operations not synchronized

Extensibility:
    - Subclasses: TopNSelector, BottomNSelector, ValueSelector, RangeSelector
    - Location: src.core.services/shapers/impl/selector/selector_algorithms/

Testing:
    - Unit tests: tests/unit/test_selector*.py
    - Integration tests: tests/integration/test_e2e_managers_shapers.py

Version: 2.0.0
Last Modified: 2026-01-27
"""

from typing import Any, Dict

import pandas as pd

from src.core.services.shapers.uni_df_shaper import UniDfShaper


class Selector(UniDfShaper):
    """
    Abstract base for shapers that filter data by column values.
    """

    def __init__(self, params: Dict[str, Any]) -> None:
        """
        Initialize the selector.

        Args:
            params: Must contain 'column'.
        """
        super().__init__(params)
        self.column: str = params["column"]

    def _verify_params(self) -> bool:
        """Verify mandatory 'column' parameter exists."""
        super()._verify_params()
        if "column" not in self.params:
            raise ValueError("Selector requires 'column' parameter.")
        if not self.params["column"]:
            raise ValueError("Selector 'column' parameter cannot be empty.")
        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that the selected column exists in the dataframe."""
        super()._verify_preconditions(data_frame)
        if self.column not in data_frame.columns:
            raise ValueError(f"Selector: Column '{self.column}' not found in dataframe.")
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Filter the dataframe."""
        return super().__call__(data_frame)
