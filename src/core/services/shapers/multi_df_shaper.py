"""
Multi-DataFrame Shaper - Base for Multi-Input Transformations.

Abstract base class for shapers that operate on multiple input dataframes,
enabling complex transformations that combine or aggregate data from different
sources (e.g., merging, blending, synthesis operations).
"""

from typing import Any

import pandas as pd

from src.core.services.shapers.shaper import Shaper


class MultiDfShaper(Shaper):
    """
    Abstract class for shapers that work on multiple dataframes.
    """

    def _verify_params(self) -> bool:
        """Verify parameters for MultiDfShaper."""
        return super()._verify_params()

    def __call__(self, data_frames: Any) -> pd.DataFrame:
        # Check the data frame is not none!
        # And if it is a unique dataframe
        if data_frames is None:
            raise ValueError("The data frame is None! Stopping")
        if not isinstance(data_frames, list):
            raise ValueError("The data frame is not a list of pandas dataframes! Stopping")
        for df in data_frames:
            if not isinstance(df, pd.DataFrame):
                raise ValueError("The data frame is not a pandas dataframe! Stopping")
        return super().__call__(data_frames)  # type: ignore[arg-type]
