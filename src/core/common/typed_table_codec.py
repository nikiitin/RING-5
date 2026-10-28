"""One exact typed table contract for portfolios and dataset snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
import sys
from typing import Any, cast
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.core.common.content_identity import content_signature, frame_signature
from src.core.common.distribution_metadata import inspect_distribution_layouts
from src.core.common.source_contributions import inspect_source_contributions
from src.core.common.security_limits import (
    MAX_TYPED_TABLE_BYTES,
    MAX_TYPED_TABLE_CELLS,
    MAX_TYPED_TABLE_COLUMNS,
    MAX_TYPED_TABLE_DEPTH,
    MAX_TYPED_TABLE_ITEMS,
    MAX_TYPED_TABLE_ROWS,
)
from src.core.models.typed_table_models import TypedTablePayload
from src.core.common.semantic_metadata import (
    SEMANTICS_ATTR,
    inspect_semantics,
    semantics_to_payload,
)


def _object(value: Any, keys: set[str]) -> dict[str, Any]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError("Typed table object fields are invalid.")
    return cast(dict[str, Any], value)


def _list(value: Any) -> list[Any]:
    if type(value) is not list:
        raise ValueError("Typed table sequence must be an array.")
    return value


@dataclass
class _TableBudget:
    """Account for emitted nodes and preflight decoded table allocations."""

    items: int = 0
    bytes: int = 0

    def _charge(self, items: int = 0, size: int = 0) -> None:
        self.items += items
        self.bytes += size
        if self.items > MAX_TYPED_TABLE_ITEMS or self.bytes > MAX_TYPED_TABLE_BYTES:
            raise ValueError("Typed table exceeds its allocation item or byte budget.")

    @staticmethod
    def _depth(depth: int) -> None:
        if depth > MAX_TYPED_TABLE_DEPTH:
            raise ValueError("Typed table exceeds its nesting depth budget.")

    def _dtype(self, value: Any, depth: int) -> int:
        self._depth(depth)
        if type(value) is not dict:
            raise ValueError("Typed table dtype must be an object.")
        kind = value.get("kind")
        if kind == "category":
            categories = value.get("categories")
            if isinstance(categories, dict) and categories.get("kind") == "multi":
                raise ValueError("Typed table categorical levels cannot be multi-indexes.")
            self._axis(categories, depth + 1)
            return 8
        if kind == "string":
            self._scalar(value.get("na_value"), depth + 1)
            return 8
        if kind == "sparse":
            self._scalar(value.get("fill"), depth + 1)
            return max(8, self._dtype(value.get("subtype"), depth + 1)) + 8
        if kind not in {"numpy", "pandas"} or type(value.get("name")) is not str:
            raise ValueError("Typed table dtype metadata is invalid.")
        dtype = (
            np.dtype(value["name"]) if kind == "numpy" else pd.api.types.pandas_dtype(value["name"])
        )
        size = max(8, int(getattr(dtype, "itemsize", 8)))
        if size > MAX_TYPED_TABLE_BYTES:
            raise ValueError("Typed table dtype exceeds its decoded byte budget.")
        return size

    def _axis(self, value: Any, depth: int = 0) -> int:
        self._depth(depth)
        if type(value) is not dict:
            raise ValueError("Typed table axis must be an object.")
        kind = value.get("kind")
        if kind == "range":
            start, stop, step = (value.get(key) for key in ("start", "stop", "step"))
            if any(type(v) is not int for v in (start, stop, step)) or step == 0:
                raise ValueError("Typed table range bounds are invalid.")
            start, stop, step = cast(int, start), cast(int, stop), cast(int, step)
            length = (
                max(0, (stop - start + step - 1) // step)
                if step > 0
                else max(0, (start - stop - step - 1) // -step)
            )
            self._scalar(value.get("name"), depth + 1)
            size = 8
        elif kind == "multi":
            levels, codes = _list(value.get("levels")), _list(value.get("codes"))
            if not levels or len(levels) != len(codes):
                raise ValueError("Typed table multi-index level counts differ.")
            length = len(_list(codes[0]))
            for level, code in zip(levels, codes, strict=True):
                if isinstance(level, dict) and level.get("kind") == "multi":
                    raise ValueError("Typed table multi-index levels must be single axes.")
                self._axis(level, depth + 1)
                entries = _list(code)
                if len(entries) != length:
                    raise ValueError("Typed table multi-index code lengths differ.")
                self._charge(len(entries), 8 * len(entries))
            for name in _list(value.get("names")):
                self._scalar(name, depth + 1)
            size = 8 * len(levels)
        else:
            values = _list(value.get("values"))
            length = len(values)
            size = self._dtype(value.get("dtype"), depth + 1)
            self._scalar(value.get("name"), depth + 1)
            for item in values:
                self._scalar(item, depth + 1)
        if length > MAX_TYPED_TABLE_ROWS:
            raise ValueError("Typed table axis exceeds its decoded length budget.")
        self._charge(length, size * length)
        return length

    def _scalar(self, value: Any, depth: int = 0) -> None:
        self._depth(depth)
        self._charge(1, 8)
        if value is None or type(value) in (bool, int):
            return
        if type(value) is str:
            self._charge(size=4 * len(value))
            return
        if type(value) is not dict:
            raise ValueError("Typed table scalar must be primitive or tagged.")
        kind = value.get("type")
        if kind == "array":
            shape, items = _list(value.get("shape")), _list(value.get("items"))
            length = 1
            for dimension in shape:
                if type(dimension) is not int or dimension < 0:
                    raise ValueError("Typed table array shape is invalid.")
                length *= dimension
                if length > MAX_TYPED_TABLE_ITEMS:
                    raise ValueError("Typed table array exceeds its decoded item budget.")
            if length != len(items):
                raise ValueError("Typed table array shape differs from its values.")
            self._charge(length, self._dtype(value.get("dtype"), depth + 1) * length)
            for item in items:
                self._scalar(item, depth + 1)
        elif kind in {"list", "tuple", "dict"}:
            items = _list(value.get("items"))
            self._charge(len(items), 8 * len(items))
            for item in items:
                if kind == "dict":
                    pair = _list(item)
                    if len(pair) != 2:
                        raise ValueError("Typed table mapping entries must have two values.")
                    for entry in pair:
                        self._scalar(entry, depth + 1)
                else:
                    self._scalar(item, depth + 1)
        elif kind == "numpy":
            size = self._dtype({"kind": "numpy", "name": value.get("dtype")}, depth + 1)
            self._charge(size=size)
            self._scalar(value.get("value"), depth + 1)
        else:
            for key, item in value.items():
                if key != "type":
                    self._scalar(item, depth + 1)

    def _frame(self, payload: Mapping[str, Any]) -> None:
        rows = self._axis(payload["index"])
        columns = self._axis(payload["columns"])
        if columns > MAX_TYPED_TABLE_COLUMNS or rows * columns > MAX_TYPED_TABLE_CELLS:
            raise ValueError("Typed table exceeds its decoded shape budget.")
        dtypes, values = _list(payload["dtypes"]), _list(payload["values"])
        if len(dtypes) != columns or len(values) != columns:
            raise ValueError("Typed table column and dtype counts differ.")
        for dtype, column in zip(dtypes, values, strict=True):
            entries = _list(column)
            if len(entries) != rows:
                raise ValueError("Typed table column length differs from its index.")
            self._charge(len(entries), self._dtype(dtype, 0) * rows)
            for item in entries:
                self._scalar(item)
        self._scalar(payload["attrs"])


class TypedTableCodec:
    """Encode and validate the current lossless JSON table payload.

    Unsupported objects, cyclic attributes and inexact reconstructions raise
    ``ValueError`` before a persistence container publishes its contents.
    """

    @classmethod
    def encode(cls, data: pd.DataFrame | None) -> TypedTablePayload | None:
        """Encode a present frame exactly, retaining ``None`` as absence.

        Args:
            data: Scientific dataframe or an absent table.

        Returns:
            The current JSON-compatible typed payload, or ``None``.

        Raises:
            TypeError: Input is neither a dataframe nor ``None``.
            ValueError: Values, axes, dtypes or attributes cannot round-trip exactly.
        """
        if data is None:
            return None
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Typed tables require a pandas DataFrame or None.")
        try:
            rows, columns = len(data), len(data.columns)
        except OverflowError as exc:
            raise ValueError("Typed table exceeds its decoded shape budget.") from exc
        if (
            rows > MAX_TYPED_TABLE_ROWS
            or columns > MAX_TYPED_TABLE_COLUMNS
            or rows * columns > MAX_TYPED_TABLE_CELLS
        ):
            raise ValueError("Typed table exceeds its decoded shape budget.")
        try:
            cls._validate_attrs(data)
            payload = cls._encode_frame(data)
            _TableBudget()._frame(payload)
            expected = frame_signature(data)
            if frame_signature(cls.decode(payload)) != expected:
                raise ValueError("Typed table cannot preserve this dataframe exactly.")
            return payload
        except RecursionError as exc:
            raise ValueError("Typed table contains recursive metadata.") from exc
        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
            InvalidOperation,
            ImportError,
            NotImplementedError,
        ) as exc:
            raise ValueError(f"Cannot encode exact typed table: {exc}") from exc

    @classmethod
    def decode(cls, payload: Any) -> pd.DataFrame | None:
        """Decode a current payload, rejecting malformed or coercing representations.

        Args:
            payload: Current typed JSON table or ``None``.

        Returns:
            A new dataframe with exact retained types and metadata, or ``None``.

        Raises:
            ValueError: The schema is unsupported, malformed or not lossless.
        """
        # [impl->req~ring5.data.semantic-units~1]
        if payload is None:
            return None
        try:
            obj = _object(
                payload,
                {"format", "format_version", "index", "columns", "dtypes", "values", "attrs"},
            )
            if (
                obj["format"] != "ring5.typed-table"
                or type(obj["format_version"]) is not int
                or obj["format_version"] != 1
            ):
                raise ValueError("Unsupported typed table format or version.")
            _TableBudget()._frame(obj)
            index = cls._decode_axis(obj["index"])
            columns = cls._decode_axis(obj["columns"])
            dtypes = _list(obj["dtypes"])
            values = _list(obj["values"])
            if len(dtypes) != len(columns) or len(values) != len(columns):
                raise ValueError("Typed table column and dtype counts differ.")
            series: list[pd.Series[Any]] = []
            for dtype, column in zip(dtypes, values, strict=True):
                items = _list(column)
                if len(items) != len(index):
                    raise ValueError("Typed table column length differs from its index.")
                series.append(
                    pd.Series(
                        [cls._decode_scalar(v) for v in items], dtype=cls._decode_dtype(dtype)
                    )
                )
            frame = pd.concat(series, axis=1) if series else pd.DataFrame(index=range(len(index)))
            frame.index = index
            frame.columns = columns
            attrs = cls._decode_scalar(obj["attrs"])
            if type(attrs) is not dict:
                raise ValueError("Typed table attributes must be a mapping.")
            frame.attrs = attrs
            cls._validate_attrs(frame)
            frame_signature(frame)
            if content_signature(cls._encode_frame(frame)) != content_signature(payload):
                raise ValueError("Typed table payload requires coercion or is not canonical.")
            return frame
        except RecursionError as exc:
            raise ValueError("Typed table contains recursive metadata.") from exc
        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
            InvalidOperation,
            ImportError,
            NotImplementedError,
        ) as exc:
            raise ValueError(f"Invalid typed table payload: {exc}") from exc

    @staticmethod
    def _validate_attrs(data: pd.DataFrame) -> None:
        inspect_distribution_layouts(data)
        inspect_source_contributions(data)
        if SEMANTICS_ATTR in data.attrs:
            normalized = semantics_to_payload(inspect_semantics(data))
            if content_signature(normalized) != content_signature(data.attrs[SEMANTICS_ATTR]):
                raise ValueError("Typed table semantic attributes must be normalized.")

    @classmethod
    def _encode_frame(cls, data: pd.DataFrame) -> TypedTablePayload:
        # [impl->req~ring5.data.semantic-units~1]
        budget = _TableBudget()
        budget._charge(size=512 + 16 * len(data.columns))
        index = cls._encode_axis(data.index, budget)
        columns = cls._encode_axis(data.columns, budget)
        dtypes = [cls._encode_dtype(dtype, budget) for dtype in data.dtypes]
        values = []
        for position in range(len(data.columns)):
            budget._charge(len(data), 64 + 8 * len(data))
            values.append([cls._encode_scalar(value, budget) for value in data.iloc[:, position]])
        return {
            "format": "ring5.typed-table",
            "format_version": 1,
            "index": index,
            "columns": columns,
            "dtypes": dtypes,
            "values": values,
            "attrs": cls._encode_scalar(data.attrs, budget),
        }

    @classmethod
    def _encode_axis(
        cls, axis: pd.Index[Any], budget: _TableBudget, depth: int = 0
    ) -> dict[str, Any]:
        budget._depth(depth)
        budget._charge(1, 256)
        if len(axis) > MAX_TYPED_TABLE_ROWS:
            raise ValueError("Typed table axis exceeds its decoded length budget.")
        name = cls._encode_scalar(axis.name, budget, depth + 1)
        if isinstance(axis, pd.RangeIndex):
            return {
                "kind": "range",
                "name": name,
                "start": axis.start,
                "stop": axis.stop,
                "step": axis.step,
            }
        if isinstance(axis, pd.MultiIndex):
            code_count = sum(len(code) for code in axis.codes)
            budget._charge(code_count, 192 + 36 * code_count)
            return {
                "kind": "multi",
                "names": [cls._encode_scalar(n, budget, depth + 1) for n in axis.names],
                "levels": [cls._encode_axis(v, budget, depth + 1) for v in axis.levels],
                "codes": [v.tolist() for v in axis.codes],
                "sortorder": getattr(axis, "sortorder", None),
            }
        kind = {
            pd.Index: "index",
            pd.CategoricalIndex: "categorical",
            pd.DatetimeIndex: "datetime",
            pd.TimedeltaIndex: "timedelta",
            pd.PeriodIndex: "period",
            pd.IntervalIndex: "interval",
        }.get(type(axis))
        if kind is None:
            raise ValueError(f"Unsupported typed table axis: {type(axis).__qualname__}.")
        budget._charge(len(axis), 64 + 8 * len(axis))
        result = {
            "kind": kind,
            "name": name,
            "dtype": cls._encode_dtype(axis.dtype, budget, depth + 1),
            "values": [cls._encode_scalar(v, budget, depth + 1) for v in axis],
        }
        if kind in {"datetime", "timedelta"}:
            result["freq"] = getattr(axis, "freqstr", None)
        return result

    @classmethod
    def _decode_axis(cls, value: Any) -> pd.Index[Any]:
        if type(value) is not dict:
            raise ValueError("Typed table axis must be an object.")
        kind = value.get("kind")
        if kind == "range":
            obj = _object(value, {"kind", "name", "start", "stop", "step"})
            if any(type(obj[k]) is not int for k in ("start", "stop", "step")) or obj["step"] == 0:
                raise ValueError("Typed table range bounds are invalid.")
            return pd.RangeIndex(
                obj["start"], obj["stop"], obj["step"], name=cls._decode_scalar(obj["name"])
            )
        if kind == "multi":
            obj = _object(value, {"kind", "names", "levels", "codes", "sortorder"})
            names, levels, codes = _list(obj["names"]), _list(obj["levels"]), _list(obj["codes"])
            if len(names) != len(levels) or len(codes) != len(levels) or not levels:
                raise ValueError("Typed table multi-index level counts differ.")
            if any(any(type(code) is not int for code in _list(level)) for level in codes):
                raise ValueError("Typed table multi-index codes must be integers.")
            if obj["sortorder"] is not None and type(obj["sortorder"]) is not int:
                raise ValueError("Typed table multi-index sort order is invalid.")
            return pd.MultiIndex(
                levels=cast(Any, [cls._decode_axis(v) for v in levels]),
                codes=codes,
                names=[cls._decode_scalar(n) for n in names],
                sortorder=obj["sortorder"],
                verify_integrity=True,
            )
        fields = {"kind", "name", "dtype", "values"} | (
            {"freq"} if kind in {"datetime", "timedelta"} else set()
        )
        obj = _object(value, fields)
        name, dtype = cls._decode_scalar(obj["name"]), cls._decode_dtype(obj["dtype"])
        values = [cls._decode_scalar(v) for v in _list(obj["values"])]
        if kind == "datetime":
            return pd.DatetimeIndex(values, dtype=dtype, freq=obj["freq"], name=name)
        if kind == "timedelta":
            return pd.TimedeltaIndex(values, dtype=dtype, freq=obj["freq"], name=name)
        constructors = {
            "index": pd.Index,
            "categorical": pd.CategoricalIndex,
            "period": pd.PeriodIndex,
            "interval": pd.IntervalIndex,
        }
        if kind not in constructors:
            raise ValueError("Typed table axis kind is unsupported.")
        if kind == "index":
            return cast(
                "pd.Index[Any]",
                pd.Index(pd.array(values, dtype=dtype), name=name, tupleize_cols=False),
            )
        return cast("pd.Index[Any]", constructors[kind](values, dtype=dtype, name=name))

    @classmethod
    def _encode_dtype(cls, dtype: Any, budget: _TableBudget, depth: int = 0) -> dict[str, Any]:
        budget._depth(depth)
        budget._charge(1, 256)
        if isinstance(dtype, pd.CategoricalDtype):
            return {
                "kind": "category",
                "categories": cls._encode_axis(dtype.categories, budget, depth + 1),
                "ordered": dtype.ordered,
            }
        if isinstance(dtype, pd.StringDtype):
            return {
                "kind": "string",
                "storage": dtype.storage,
                "na_value": cls._encode_scalar(dtype.na_value, budget, depth + 1),
            }
        if isinstance(dtype, pd.SparseDtype):
            return {
                "kind": "sparse",
                "subtype": cls._encode_dtype(dtype.subtype, budget, depth + 1),
                "fill": cls._encode_scalar(dtype.fill_value, budget, depth + 1),
            }
        if isinstance(dtype, np.dtype):
            if dtype.fields is not None or dtype.subdtype is not None:
                raise ValueError("Structured typed table dtypes are unsupported.")
            return {"kind": "numpy", "name": dtype.str}
        return {"kind": "pandas", "name": str(dtype)}

    @classmethod
    def _decode_dtype(cls, value: Any) -> Any:
        if type(value) is not dict:
            raise ValueError("Typed table dtype must be an object.")
        kind = value.get("kind")
        if kind == "category":
            obj = _object(value, {"kind", "categories", "ordered"})
            if type(obj["ordered"]) is not bool:
                raise ValueError("Typed table categorical order must be boolean.")
            return pd.CategoricalDtype(cls._decode_axis(obj["categories"]), ordered=obj["ordered"])
        if kind == "string":
            obj = _object(value, {"kind", "storage", "na_value"})
            return pd.StringDtype(
                storage=obj["storage"], na_value=cls._decode_scalar(obj["na_value"])
            )
        if kind == "sparse":
            obj = _object(value, {"kind", "subtype", "fill"})
            return pd.SparseDtype(
                cls._decode_dtype(obj["subtype"]), cls._decode_scalar(obj["fill"])
            )
        obj = _object(value, {"kind", "name"})
        if type(obj["name"]) is not str:
            raise ValueError("Typed table dtype name must be text.")
        if kind == "numpy":
            dtype = np.dtype(obj["name"])
            if dtype.fields is not None or dtype.subdtype is not None:
                raise ValueError("Structured typed table dtypes are unsupported.")
            return dtype
        if kind == "pandas":
            return pd.api.types.pandas_dtype(obj["name"])
        raise ValueError("Typed table dtype kind is unsupported.")

    @classmethod
    def _encode_scalar(cls, value: Any, budget: _TableBudget, depth: int = 0) -> Any:
        budget._depth(depth)
        budget._charge(1, 40)
        if value is None or type(value) in (str, bool, int):
            if type(value) is str:
                budget._charge(size=4 * len(value))
            return value
        budget._charge(size=256)
        if type(value) is float:
            return {"type": "float", "value": value.hex()}
        if type(value) is complex:
            return {"type": "complex", "real": value.real.hex(), "imag": value.imag.hex()}
        if type(value) is bytes:
            if len(value) > MAX_TYPED_TABLE_BYTES:
                raise ValueError("Typed table scalar exceeds its decoded byte budget.")
            budget._charge(size=3 * len(value))
            return {"type": "bytes", "value": value.hex()}
        if value is pd.NA or value is pd.NaT:
            return {"type": "NA" if value is pd.NA else "NaT"}
        if isinstance(value, np.generic):
            if value.dtype.hasobject:
                raise ValueError("Object NumPy scalars are unsupported.")
            if value.dtype.itemsize > MAX_TYPED_TABLE_BYTES:
                raise ValueError("Typed table scalar exceeds its decoded byte budget.")
            budget._charge(size=3 * value.dtype.itemsize)
            return {"type": "numpy", "dtype": value.dtype.str, "value": value.tobytes().hex()}
        if isinstance(value, pd.Timestamp):
            return {
                "type": "timestamp",
                "value": value.isoformat(),
                "zone": str(value.tzinfo) if value.tzinfo else None,
                "fold": value.fold,
            }
        if isinstance(value, pd.Timedelta):
            return {"type": "timedelta", "value": value.isoformat()}
        if isinstance(value, pd.Period):
            return {"type": "period", "ordinal": value.ordinal, "freq": value.freqstr}
        if isinstance(value, pd.Interval):
            return {
                "type": "interval",
                "left": cls._encode_scalar(value.left, budget, depth + 1),
                "right": cls._encode_scalar(value.right, budget, depth + 1),
                "closed": value.closed,
            }
        if type(value) in (datetime, date, time):
            return {
                "type": type(value).__name__,
                "value": value.isoformat(),
                "fold": getattr(value, "fold", 0),
                "zone": getattr(getattr(value, "tzinfo", None), "key", None),
            }
        if isinstance(value, Decimal):
            return {"type": "decimal", "value": str(value)}
        if isinstance(value, PurePath):
            return {"type": "path", "kind": type(value).__name__, "value": str(value)}
        if type(value) in (tuple, list):
            budget._charge(len(value), 64 + 8 * len(value))
            return {
                "type": type(value).__name__,
                "items": [cls._encode_scalar(v, budget, depth + 1) for v in value],
            }
        if type(value) is dict:
            budget._charge(len(value), 64 + 80 * len(value))
            return {
                "type": "dict",
                "items": [
                    [
                        cls._encode_scalar(k, budget, depth + 1),
                        cls._encode_scalar(v, budget, depth + 1),
                    ]
                    for k, v in value.items()
                ],
            }
        if isinstance(value, np.ndarray):
            if value.size > MAX_TYPED_TABLE_ITEMS or value.nbytes > MAX_TYPED_TABLE_BYTES:
                raise ValueError("Typed table array exceeds its decoded item or byte budget.")
            budget._charge(value.size, 128 + 8 * value.size + 8 * value.ndim)
            return {
                "type": "array",
                "dtype": cls._encode_dtype(value.dtype, budget, depth + 1),
                "shape": list(value.shape),
                "items": [cls._encode_scalar(v, budget, depth + 1) for v in value.flat],
            }
        raise ValueError(f"Unsupported typed table scalar: {type(value).__qualname__}.")

    @classmethod
    def _decode_scalar(cls, value: Any) -> Any:
        if value is None or type(value) in (str, bool, int):
            return value
        if type(value) is not dict:
            raise ValueError("Typed table scalar must be primitive or tagged.")
        kind = value.get("type")
        fields = {
            "float": {"value"},
            "complex": {"real", "imag"},
            "bytes": {"value"},
            "NA": set(),
            "NaT": set(),
            "numpy": {"dtype", "value"},
            "timestamp": {"value", "zone", "fold"},
            "timedelta": {"value"},
            "period": {"ordinal", "freq"},
            "interval": {"left", "right", "closed"},
            "datetime": {"value", "fold", "zone"},
            "date": {"value", "fold", "zone"},
            "time": {"value", "fold", "zone"},
            "decimal": {"value"},
            "path": {"kind", "value"},
            "tuple": {"items"},
            "list": {"items"},
            "dict": {"items"},
            "array": {"dtype", "shape", "items"},
        }
        if kind not in fields:
            raise ValueError("Typed table scalar tag is unsupported.")
        obj = _object(value, {"type"} | fields[kind])
        if kind == "float":
            return float.fromhex(obj["value"])
        if kind == "complex":
            return complex(float.fromhex(obj["real"]), float.fromhex(obj["imag"]))
        if kind == "bytes":
            return bytes.fromhex(obj["value"])
        if kind in {"NA", "NaT"}:
            return pd.NA if kind == "NA" else pd.NaT
        if kind == "numpy":
            dtype = np.dtype(obj["dtype"])
            raw = bytes.fromhex(obj["value"])
            if dtype.hasobject or dtype.fields is not None or len(raw) != dtype.itemsize:
                raise ValueError("Typed table NumPy scalar representation is invalid.")
            if dtype.kind == "U":
                big_endian = dtype.byteorder == ">" or (
                    dtype.byteorder == "=" and sys.byteorder == "big"
                )
                raw.decode("utf-32-be" if big_endian else "utf-32-le", errors="surrogatepass")
            return np.frombuffer(raw, dtype=dtype, count=1)[0]
        if kind == "timestamp":
            result = pd.Timestamp(obj["value"])
            return result.tz_convert(obj["zone"]) if obj["zone"] is not None else result
        if kind == "timedelta":
            return pd.Timedelta(obj["value"])
        if kind == "period":
            return pd.Period(ordinal=obj["ordinal"], freq=obj["freq"])
        if kind == "interval":
            return pd.Interval(
                cls._decode_scalar(obj["left"]),
                cls._decode_scalar(obj["right"]),
                closed=obj["closed"],
            )
        if kind in {"datetime", "date", "time"}:
            temporal = (
                datetime.fromisoformat(obj["value"])
                if kind == "datetime"
                else (
                    time.fromisoformat(obj["value"])
                    if kind == "time"
                    else date.fromisoformat(obj["value"])
                )
            )
            if kind != "date":
                temporal = cast(Any, temporal).replace(fold=obj["fold"])
                if obj["zone"] is not None:
                    temporal = cast(Any, temporal).replace(tzinfo=ZoneInfo(obj["zone"]))
            return temporal
        if kind == "decimal":
            return Decimal(obj["value"])
        if kind == "path":
            paths = {
                "PurePosixPath": PurePosixPath,
                "PureWindowsPath": PureWindowsPath,
                type(Path()).__name__: Path,
            }
            if obj["kind"] not in paths:
                raise ValueError("Typed table path kind is unsupported on this platform.")
            return paths[obj["kind"]](obj["value"])
        if kind in {"tuple", "list"}:
            items = [cls._decode_scalar(v) for v in _list(obj["items"])]
            return tuple(items) if kind == "tuple" else items
        if kind == "dict":
            result_dict: dict[Any, Any] = {}
            for pair in _list(obj["items"]):
                pair = _list(pair)
                if len(pair) != 2:
                    raise ValueError("Typed table mapping entry must have two items.")
                key, item = cls._decode_scalar(pair[0]), cls._decode_scalar(pair[1])
                if key in result_dict:
                    raise ValueError("Typed table mapping keys must be unique.")
                result_dict[key] = item
            return result_dict
        shape = _list(obj["shape"])
        if any(type(v) is not int or v < 0 for v in shape):
            raise ValueError("Typed table array shape is invalid.")
        items = [cls._decode_scalar(v) for v in _list(obj["items"])]
        array = np.empty(len(items), dtype=cls._decode_dtype(obj["dtype"]))
        for position, item in enumerate(items):
            array[position] = item
        return array.reshape(shape)
