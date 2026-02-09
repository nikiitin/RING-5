"""
Single-DataFrame Shaper - Base for Single-Input Transformations.

Abstract base class for shapers that operate on a single DataFrame,
enabling transformations like filtering, sorting, normalization, aggregation,
and selection on individual datasets.
"""

from typing import Any

import pandas as pd

from src.core.services.shapers.shaper import Shaper


class UniDfShaper(Shaper):
    """
    Abstract class for shapers that operate on a single pandas DataFrame.
    """

    def __call__(self, data_frame: Any) -> pd.DataFrame:
        """
        Execute the transformation after validating that input is a DataFrame.

        Args:
            data_frame: The data to transform.

        Returns:
            The transformed DataFrame.

        Raises:
            ValueError: If the input is not a pandas DataFrame.
        """
        if data_frame is None:
            raise ValueError("UniDfShaper: Data frame cannot be None.")

        if not isinstance(data_frame, pd.DataFrame):
            raise ValueError(
                f"UniDfShaper: Expected pandas DataFrame, got {type(data_frame).__name__}."
            )

        return super().__call__(data_frame)
