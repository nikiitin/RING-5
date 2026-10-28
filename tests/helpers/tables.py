"""Scientific table cases shared across current persistence containers."""

from datetime import datetime
from decimal import Decimal
from pathlib import PureWindowsPath
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


def scientific_frames() -> list[pd.DataFrame]:
    """Provide dtype, axis and metadata cases shared by persistence regressions."""
    numeric = pd.DataFrame(
        {
            "nullable": pd.Series([1, None], dtype="Int64"),
            "unsigned": pd.Series([2**64 - 1, None], dtype="UInt64"),
            "boolean": pd.Series([True, None], dtype="boolean"),
            "float": pd.Series([1.25, None], dtype="Float64"),
            "text": pd.Series(["α", None], dtype="string"),
            "category": pd.Categorical(["b", "a"], categories=["b", "a", "unused"], ordered=True),
            "timestamp": pd.date_range("2026-01-01", periods=2, tz="Europe/Madrid"),
            "duration": pd.to_timedelta([1, 2], unit="D"),
            "period": pd.period_range("2026-01", periods=2, freq="M"),
        }
    )
    objects = pd.DataFrame(
        {
            "object": pd.Series(
                [
                    None,
                    np.nan,
                    pd.NA,
                    pd.NaT,
                    np.int32(7),
                    np.float32(1.5),
                    np.datetime64("2026-01-01"),
                    b"value",
                    1j,
                    Decimal("1.00"),
                    (1, "x"),
                    [1, None],
                    {1: "x"},
                    datetime(2026, 10, 25, 2, 30, fold=1, tzinfo=ZoneInfo("Europe/Madrid")),
                ],
                dtype=object,
            )
        }
    )
    object_array = np.empty(1, dtype=object)
    object_array[0] = [1, 2]
    objects.attrs = {
        "typed": {
            "value": np.int32(3),
            "path": PureWindowsPath("C:/data"),
            "array": np.array([1, 2]),
            "object_array": object_array,
        }
    }
    multi = pd.DataFrame(
        [[1, 2]],
        index=pd.MultiIndex(
            levels=[["a", "unused"], [1, 2]], codes=[[0], [1]], names=["case", "seed"]
        ),
        columns=pd.MultiIndex(
            levels=[["cpu", "unused"], ["ipc", "cycles"]],
            codes=[[0, 0], [0, 1]],
            names=["component", "metric"],
        ),
    )
    return [
        numeric,
        pd.DataFrame({"sparse": pd.Series([0.0, 1.0], dtype=pd.SparseDtype(float, 0))}),
        pd.DataFrame({"x": [1, 2]}, index=pd.period_range("2026-01", periods=2, freq="M")),
        objects,
        multi,
        pd.DataFrame(
            {"x": [1, 2]},
            index=pd.date_range("2026-01-01", periods=2, freq="h", tz="Europe/Madrid"),
        ),
        pd.DataFrame({"x": [1, 2]}, index=pd.timedelta_range("1h", periods=2, freq="h")),
        pd.DataFrame(
            [[1]],
            columns=pd.CategoricalIndex(
                ["x"], categories=["x", "unused"], ordered=True, name="measurement"
            ),
        ),
        pd.DataFrame({"x": [1, 2]}, index=pd.interval_range(0, 2)),
        pd.DataFrame({"x": pd.Series([], dtype="Int64")}),
        pd.DataFrame(index=pd.RangeIndex(10, 16, 2, name="run")),
        pd.DataFrame([[1, 2]], columns=["duplicate", "duplicate"]),
    ]
