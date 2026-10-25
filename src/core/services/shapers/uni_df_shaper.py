"""
Single-DataFrame Shaper - Base for Single-Input Transformations.

Abstract base class for shapers that operate on a single DataFrame,
enabling transformations like filtering, sorting, normalization, aggregation,
and selection on individual datasets.
"""

from abc import abstractmethod

import pandas as pd

from src.core.services.shapers.shaper import Shaper


class UniDfShaper(Shaper):
    """
    Abstract class for shapers that operate on a single pandas DataFrame.
    """

    @abstractmethod
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """
        Execute the transformation after validating that input is a DataFrame.

        Args:
            data_frame: The data to transform.

        Returns:
            The transformed DataFrame.

        Raises:
            ValueError: If the input is not a pandas DataFrame.
        """
        return super().__call__(data_frame)
