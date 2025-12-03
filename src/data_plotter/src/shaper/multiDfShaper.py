from typing import Any
from src.data_plotter.src.shaper.shaper import Shaper
import pandas as pd

class MultiDfShaper(Shaper):
    """
    Abstract class for shapers that work on multiple dataframes.
    """
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
        return super().__call__(data_frames)