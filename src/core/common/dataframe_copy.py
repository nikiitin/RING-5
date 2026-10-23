"""Defensive dataframe ownership, including mutable Python object cells."""

from copy import deepcopy

import numpy as np
import pandas as pd


def copy_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Copy values, axes, attributes and nested object cells without changing dtypes."""
    result = data.copy(deep=True)
    for position, dtype in enumerate(data.dtypes):
        if pd.api.types.is_object_dtype(dtype):
            values = np.empty(len(data), dtype=object)
            for index, value in enumerate(data.iloc[:, position]):
                values[index] = deepcopy(value)
            result.isetitem(position, pd.Series(values, index=result.index, dtype=dtype))
    return result
