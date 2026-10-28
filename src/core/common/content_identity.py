"""Typed, deterministic identities for scientific data and application inputs."""

from __future__ import annotations

import hashlib
import json
from typing import Any, overload
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import PurePath

import numpy as np
import pandas as pd


def encode_identity(value: Any) -> Any:
    """Encode supported metadata without conflating Python or pandas types."""
    if value is None or type(value) in (str, bool, int):
        return [type(value).__name__, value]
    if type(value) is float:
        return ["float", value.hex()]
    if type(value) is bytes:
        return ["bytes", value.hex()]
    if type(value) is complex:
        return ["complex", value.real.hex(), value.imag.hex()]
    if value is pd.NA:
        return ["pandas.NA"]
    if value is pd.NaT:
        return ["pandas.NaT"]
    if isinstance(value, pd.Timestamp):
        return ["pandas.Timestamp", value.isoformat(), str(value.tzinfo), value.fold]
    if isinstance(value, pd.Timedelta):
        return ["pandas.Timedelta", value.isoformat()]
    if isinstance(value, pd.Period):
        return ["pandas.Period", value.ordinal, value.freqstr]
    if isinstance(value, pd.Interval):
        return [
            "pandas.Interval",
            encode_identity(value.left),
            encode_identity(value.right),
            value.closed,
        ]
    if type(value) in (date, datetime, time):
        return [
            type(value).__qualname__,
            value.isoformat(),
            getattr(value, "fold", 0),
            str(getattr(value, "tzinfo", None)),
        ]
    if isinstance(value, Decimal):
        return ["Decimal", str(value)]
    if isinstance(value, PurePath):
        return [type(value).__qualname__, str(value)]
    if isinstance(value, np.generic):
        scalar = value.item()
        if isinstance(scalar, np.generic):
            raise TypeError("NumPy scalar has no lossless Python scalar representation.")
        return ["numpy", str(value.dtype), encode_identity(scalar)]
    if type(value) in (list, tuple):
        return [type(value).__name__, [encode_identity(item) for item in value]]
    if type(value) is dict:
        items = [[encode_identity(key), encode_identity(item)] for key, item in value.items()]
        return ["dict", sorted(items, key=lambda item: json.dumps(item[0], sort_keys=True))]
    if isinstance(value, pd.CategoricalDtype):
        return ["categorical", encode_identity(value.categories), value.ordered]
    if isinstance(value, pd.RangeIndex):
        # Range parameters fully identify these values. Expanding every row
        # defeats cache reuse before the transformation can be skipped.
        return [
            type(value).__qualname__,
            value.start,
            value.stop,
            value.step,
            encode_identity(list(value.names)),
        ]
    if isinstance(value, pd.Index):
        dtype = (
            encode_identity(value.dtype)
            if isinstance(value.dtype, pd.CategoricalDtype)
            else repr(value.dtype)
        )
        levels = (
            [encode_identity(level) for level in value.levels]
            if isinstance(value, pd.MultiIndex)
            else None
        )
        return [
            type(value).__qualname__,
            dtype,
            encode_identity(list(value.names)),
            encode_identity(value.tolist()),
            levels,
            getattr(value, "freqstr", None),
        ]
    if isinstance(value, np.ndarray):
        return ["ndarray", str(value.dtype), value.shape, encode_identity(value.tolist())]
    raise TypeError(f"Unsupported cache identity type: {type(value).__qualname__}")


def content_signature(value: Any) -> str:
    """Hash supported typed input without stringifying unsupported objects.

    Raises:
        ValueError: Input contains unsupported or recursive mutable metadata.
    """
    try:
        payload = json.dumps(encode_identity(value), separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("Input contains unsupported or recursive metadata.") from exc
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@overload
def frame_signature(data: pd.DataFrame) -> str:
    """Return the typed identity of a present dataframe."""
    raise NotImplementedError


@overload
def frame_signature(data: None) -> None:
    """Retain the absence of a dataframe without creating a digest."""
    raise NotImplementedError


def frame_signature(data: pd.DataFrame | None) -> str | None:
    """Identify complete dataframe values, axes, dtypes and retained metadata.

    Raises:
        TypeError: Input is neither a dataframe nor ``None``.
        ValueError: Values or metadata have no supported stable identity.
    """
    # [impl->req~ring5.data.dataset-snapshots~1]
    if data is None:
        return None
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Scientific frame identities require a pandas DataFrame or None.")
    metadata = {
        "columns": data.columns,
        "index": data.index,
        "dtypes": [
            dtype if isinstance(dtype, pd.CategoricalDtype) else repr(dtype)
            for dtype in data.dtypes
        ],
        "attrs": data.attrs,
        "object_values": [
            data.iloc[:, position].tolist()
            for position, dtype in enumerate(data.dtypes)
            if pd.api.types.is_object_dtype(dtype)
        ],
    }
    digest = hashlib.sha256(content_signature(metadata).encode("ascii"))
    try:
        numeric_positions = [
            position
            for position, dtype in enumerate(data.dtypes)
            if not pd.api.types.is_object_dtype(dtype)
        ]
        hashes = (
            pd.util.hash_pandas_object(data.iloc[:, numeric_positions], index=True)
            .to_numpy()
            .tobytes()
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Dataframe values have no supported stable identity.") from exc
    digest.update(hashes)
    return "sha256:" + digest.hexdigest()
