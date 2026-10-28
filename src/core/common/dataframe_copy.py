"""Defensive dataframe ownership, including mutable Python object cells."""

from copy import deepcopy

import numpy as np
import pandas as pd

from src.core.common.distribution_metadata import inspect_distribution_layouts


def copy_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Copy values, axes, attributes and nested object cells without changing dtypes.

    Args:
        data: Source frame whose reserved declarations are validated before copying.

    Returns:
        An owned frame retaining exact dtypes and independently owned nested cells.

    Raises:
        TypeError: Reserved Distribution metadata has an unsupported exact type.
        ValueError: Reserved declarations, numeric bindings or resource bounds are invalid.
    """
    inspect_distribution_layouts(data)
    result = data.copy(deep=True)
    for position, dtype in enumerate(data.dtypes):
        if pd.api.types.is_object_dtype(dtype):
            values = np.empty(len(data), dtype=object)
            for index, value in enumerate(data.iloc[:, position]):
                values[index] = deepcopy(value)
            result.isetitem(position, pd.Series(values, index=result.index, dtype=dtype))
    return result
