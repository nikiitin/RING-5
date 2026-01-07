from typing import Any

import pandas as pd

from src.web.services.shapers.base_shaper import Shaper


class UniDfShaper(Shaper):
    """
    Abstract class for shapers that work on a single dataframe.
    """

    def __call__(self, data_frame: Any) -> pd.DataFrame:
        # Check the data frame is not none!
        # And if it is a unique dataframe
        if data_frame is None:
            raise ValueError("The data frame is None! Stopping")
        if not isinstance(data_frame, pd.DataFrame):
            raise ValueError("The data frame is not a pandas dataframe! Stopping")
        return super().__call__(data_frame)
