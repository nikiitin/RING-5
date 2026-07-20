"""Safe, versioned persistence for reusable pandas dataset snapshots."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import os
import tempfile
from datetime import date, datetime, time, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import numpy as np
import pandas as pd

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.models import DatasetSnapshotInfo
from src.core.services.data_services.dataset_fingerprint import fingerprint_dataset
from src.core.services.data_services.path_service import PathService

logger = logging.getLogger(__name__)

_FORMAT = "ring5.dataset-snapshot"
_FORMAT_VERSION = 1
_EXTENSION = ".ring5-snapshot"
_MANIFEST_MEMBER = "manifest.json"
_DATA_MEMBER = "data.json"


class DatasetSnapshotService:
    """Save, inspect, reload, and remove local reusable dataset snapshots."""

    @classmethod
    def list_snapshots(cls) -> tuple[DatasetSnapshotInfo, ...]:
        """Return readable snapshot metadata without decoding table payloads."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        snapshots: list[DatasetSnapshotInfo] = []
        for path in PathService.get_dataset_snapshots_dir().glob(f"*{_EXTENSION}"):
            try:
                snapshots.append(cls._read_info(path))
            except (BadZipFile, KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
                logger.warning("Ignoring unreadable dataset snapshot metadata at %s", path)
        return tuple(sorted(snapshots, key=lambda item: (item.created_at, item.name), reverse=True))

    @classmethod
    def save_snapshot(
        cls,
        name: str,
        data: pd.DataFrame,
        *,
        source_dataset: str,
        overwrite: bool = False,
    ) -> DatasetSnapshotInfo:
        """Atomically save an exact, non-executable dataframe snapshot."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        resolved_name = cls._validate_name(name, "Snapshot")
        resolved_source = cls._validate_name(source_dataset, "Source dataset")
        if not isinstance(data, pd.DataFrame):
            raise TypeError("Dataset snapshots require a pandas DataFrame.")

        frame_payload = cls._encode_frame(data)
        payload_bytes = json.dumps(
            frame_payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        expected_fingerprint = fingerprint_dataset(data)
        reconstructed = cls._decode_frame(frame_payload)
        if fingerprint_dataset(reconstructed) != expected_fingerprint:
            raise ValueError(
                "This dataset contains labels, values, or dtypes that cannot be saved exactly "
                "in the reusable snapshot format."
            )

        created_at = datetime.now(timezone.utc).isoformat()
        manifest: dict[str, Any] = {
            "format": _FORMAT,
            "format_version": _FORMAT_VERSION,
            "name": resolved_name,
            "source_dataset": resolved_source,
            "created_at": created_at,
            "row_count": len(data),
            "column_count": len(data.columns),
            "fingerprint": expected_fingerprint,
            "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        }
        manifest_bytes = json.dumps(
            manifest,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        ).encode("utf-8")
        destination = cls._snapshot_path(resolved_name)
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Dataset snapshot {resolved_name!r} already exists.")

        snapshots_dir = PathService.get_dataset_snapshots_dir()
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=snapshots_dir,
                prefix=".ring5-dataset-snapshot-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED, compresslevel=6) as archive:
                archive.writestr(_MANIFEST_MEMBER, manifest_bytes)
                archive.writestr(_DATA_MEMBER, payload_bytes)
            if overwrite:
                os.replace(temporary_path, destination)
            else:
                try:
                    os.link(temporary_path, destination)
                except FileExistsError as exc:
                    raise FileExistsError(
                        f"Dataset snapshot {resolved_name!r} already exists."
                    ) from exc
                temporary_path.unlink()
            temporary_path = None
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        return cls._info_from_manifest(manifest, destination.stat().st_size)

    @classmethod
    def load_snapshot(cls, name: str) -> tuple[DatasetSnapshotInfo, pd.DataFrame]:
        """Load a snapshot only after payload and dataframe fingerprints verify."""
        # [impl->req~ring5.data.dataset-snapshots~1]
        path = cls._snapshot_path(cls._validate_name(name, "Snapshot"))
        if not path.exists():
            raise FileNotFoundError(f"Dataset snapshot {name!r} does not exist.")
        try:
            with ZipFile(path) as archive:
                manifest = cls._parse_manifest(archive.read(_MANIFEST_MEMBER))
                payload_bytes = archive.read(_DATA_MEMBER)
        except (BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"Dataset snapshot {name!r} is unreadable or incomplete.") from exc

        if manifest["name"] != name.strip():
            raise ValueError(f"Dataset snapshot {name!r} has mismatched identity metadata.")

        actual_payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        if actual_payload_hash != manifest["payload_sha256"]:
            raise ValueError(f"Dataset snapshot {name!r} failed its payload checksum.")
        try:
            payload = cast(dict[str, Any], json.loads(payload_bytes))
            data = cls._decode_frame(payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(f"Dataset snapshot {name!r} contains invalid table data.") from exc
        if len(data) != manifest["row_count"] or len(data.columns) != manifest["column_count"]:
            raise ValueError(f"Dataset snapshot {name!r} does not match its recorded dimensions.")
        if fingerprint_dataset(data) != manifest["fingerprint"]:
            raise ValueError(f"Dataset snapshot {name!r} failed fingerprint verification.")
        return cls._info_from_manifest(manifest, path.stat().st_size), data

    @classmethod
    def delete_snapshot(cls, name: str) -> None:
        """Delete one named reusable snapshot, if present."""
        path = cls._snapshot_path(cls._validate_name(name, "Snapshot"))
        if path.exists():
            path.unlink()

    @classmethod
    def _read_info(cls, path: Path) -> DatasetSnapshotInfo:
        with ZipFile(path) as archive:
            manifest = cls._parse_manifest(archive.read(_MANIFEST_MEMBER))
        return cls._info_from_manifest(manifest, path.stat().st_size)

    @staticmethod
    def _parse_manifest(raw: bytes) -> dict[str, Any]:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("Snapshot manifest must be an object.")
        required = {
            "format": str,
            "format_version": int,
            "name": str,
            "source_dataset": str,
            "created_at": str,
            "row_count": int,
            "column_count": int,
            "fingerprint": str,
            "payload_sha256": str,
        }
        for key, expected_type in required.items():
            if key not in parsed or not isinstance(parsed[key], expected_type):
                raise ValueError(f"Snapshot manifest field {key!r} is invalid.")
        if parsed["format"] != _FORMAT:
            raise ValueError("File is not a RING-5 dataset snapshot.")
        if parsed["format_version"] != _FORMAT_VERSION:
            raise ValueError(f"Unsupported dataset snapshot version {parsed['format_version']!r}.")
        if parsed["row_count"] < 0 or parsed["column_count"] < 0:
            raise ValueError("Snapshot dimensions cannot be negative.")
        if not parsed["fingerprint"].startswith("sha256:"):
            raise ValueError("Snapshot fingerprint is invalid.")
        if len(parsed["payload_sha256"]) != 64:
            raise ValueError("Snapshot payload checksum is invalid.")
        return cast(dict[str, Any], parsed)

    @staticmethod
    def _info_from_manifest(manifest: dict[str, Any], size_bytes: int) -> DatasetSnapshotInfo:
        return DatasetSnapshotInfo(
            name=str(manifest["name"]),
            source_dataset=str(manifest["source_dataset"]),
            created_at=str(manifest["created_at"]),
            row_count=int(manifest["row_count"]),
            column_count=int(manifest["column_count"]),
            fingerprint=str(manifest["fingerprint"]),
            size_bytes=size_bytes,
            format_version=int(manifest["format_version"]),
        )

    @classmethod
    def _snapshot_path(cls, name: str) -> Path:
        directory = PathService.get_dataset_snapshots_dir()
        identity = hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        filename = f"{sanitize_filename(name)}-{identity}{_EXTENSION}"
        return validate_path_within(directory / filename, directory)

    @staticmethod
    def _validate_name(name: str, label: str) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{label} name must be a non-empty string.")
        resolved = name.strip()
        if len(resolved) > 100:
            raise ValueError(f"{label} name cannot exceed 100 characters.")
        if any(ord(character) < 32 for character in resolved):
            raise ValueError(f"{label} name cannot contain control characters.")
        return resolved

    @classmethod
    def _encode_frame(cls, data: pd.DataFrame) -> dict[str, Any]:
        columns = [cls._encode_scalar(column) for column in data.columns]
        column_kind = "multi" if isinstance(data.columns, pd.MultiIndex) else "single"
        column_names = [cls._encode_scalar(name) for name in data.columns.names]
        dtypes = [
            cls._encode_dtype(data.iloc[:, index].dtype) for index in range(len(data.columns))
        ]
        rows = [
            [cls._encode_scalar(value) for value in row]
            for row in data.itertuples(index=False, name=None)
        ]
        if isinstance(data.index, pd.MultiIndex):
            index: dict[str, Any] = {
                "kind": "multi",
                "names": [cls._encode_scalar(name) for name in data.index.names],
                "dtypes": [
                    cls._encode_dtype(data.index.get_level_values(level).dtype)
                    for level in range(data.index.nlevels)
                ],
                "values": [cls._encode_scalar(tuple(value)) for value in data.index.tolist()],
            }
        else:
            index = {
                "kind": "single",
                "names": [cls._encode_scalar(data.index.name)],
                "dtypes": [cls._encode_dtype(data.index.dtype)],
                "values": [cls._encode_scalar(value) for value in data.index.tolist()],
            }
        return {
            "columns": columns,
            "column_kind": column_kind,
            "column_names": column_names,
            "dtypes": dtypes,
            "index": index,
            "rows": rows,
        }

    @classmethod
    def _decode_frame(cls, payload: dict[str, Any]) -> pd.DataFrame:
        raw_columns = payload["columns"]
        column_kind = payload["column_kind"]
        raw_column_names = payload["column_names"]
        raw_dtypes = payload["dtypes"]
        raw_rows = payload["rows"]
        if not isinstance(raw_columns, list) or not isinstance(raw_dtypes, list):
            raise ValueError("Snapshot columns and dtypes must be lists.")
        if not isinstance(raw_column_names, list):
            raise ValueError("Snapshot column names must be a list.")
        if len(raw_columns) != len(raw_dtypes):
            raise ValueError("Snapshot column and dtype counts do not match.")
        if not isinstance(raw_rows, list):
            raise ValueError("Snapshot rows must be a list.")
        if any(not isinstance(row, list) or len(row) != len(raw_columns) for row in raw_rows):
            raise ValueError("Snapshot row width does not match its columns.")

        labels = [cls._decode_scalar(column) for column in raw_columns]
        series: list[pd.Series[Any]] = []
        for position, dtype_spec in enumerate(raw_dtypes):
            values = [cls._decode_scalar(row[position]) for row in raw_rows]
            series.append(pd.Series(values, dtype=cls._decode_dtype(dtype_spec)))
        frame = pd.concat(series, axis=1) if series else pd.DataFrame(index=range(len(raw_rows)))
        decoded_column_names = [cls._decode_scalar(name) for name in raw_column_names]
        if column_kind == "single" and len(decoded_column_names) == 1:
            frame.columns = pd.Index(
                labels,
                name=decoded_column_names[0],
                tupleize_cols=False,
            )
        elif column_kind == "multi" and decoded_column_names:
            if any(not isinstance(label, tuple) for label in labels):
                raise ValueError("Snapshot multi-level column labels are invalid.")
            frame.columns = pd.MultiIndex.from_tuples(
                labels,
                names=decoded_column_names,
            )
        else:
            raise ValueError("Snapshot column index kind is invalid.")
        frame.index = cls._decode_index(payload["index"])
        return frame

    @classmethod
    def _decode_index(cls, spec: Any) -> pd.Index[Any]:
        if not isinstance(spec, dict):
            raise ValueError("Snapshot index must be an object.")
        values = spec.get("values")
        names = spec.get("names")
        dtypes = spec.get("dtypes")
        if (
            not isinstance(values, list)
            or not isinstance(names, list)
            or not isinstance(dtypes, list)
        ):
            raise ValueError("Snapshot index metadata is invalid.")
        if spec.get("kind") == "single" and len(names) == 1 and len(dtypes) == 1:
            decoded = [cls._decode_scalar(value) for value in values]
            array = pd.Series(decoded, dtype=cls._decode_dtype(dtypes[0])).array
            return cast("pd.Index[Any]", pd.Index(array, name=cls._decode_scalar(names[0])))
        if spec.get("kind") == "multi" and len(names) == len(dtypes):
            decoded_tuples = [cls._decode_scalar(value) for value in values]
            if any(
                not isinstance(value, tuple) or len(value) != len(names) for value in decoded_tuples
            ):
                raise ValueError("Snapshot multi-index values are invalid.")
            arrays = []
            for level, dtype_spec in enumerate(dtypes):
                level_values = [value[level] for value in decoded_tuples]
                arrays.append(pd.Series(level_values, dtype=cls._decode_dtype(dtype_spec)).array)
            return pd.MultiIndex.from_arrays(
                arrays,
                names=[cls._decode_scalar(name) for name in names],
            )
        raise ValueError("Snapshot index kind is invalid.")

    @classmethod
    def _encode_dtype(cls, dtype: Any) -> dict[str, Any]:
        encoded: dict[str, Any] = {"name": str(dtype)}
        if isinstance(dtype, pd.CategoricalDtype):
            encoded["categories"] = [cls._encode_scalar(value) for value in dtype.categories]
            encoded["ordered"] = dtype.ordered
        return encoded

    @classmethod
    def _decode_dtype(cls, spec: Any) -> Any:
        if not isinstance(spec, dict) or not isinstance(spec.get("name"), str):
            raise ValueError("Snapshot dtype metadata is invalid.")
        if spec["name"] == "category":
            categories = spec.get("categories")
            if not isinstance(categories, list) or not isinstance(spec.get("ordered"), bool):
                raise ValueError("Snapshot category metadata is invalid.")
            return pd.CategoricalDtype(
                categories=[cls._decode_scalar(value) for value in categories],
                ordered=spec["ordered"],
            )
        return spec["name"]

    @classmethod
    def _encode_scalar(cls, value: Any) -> Any:
        if value is None:
            return None
        if value is pd.NA:
            return {"$ring5": "missing"}
        if value is pd.NaT:
            return {"$ring5": "nat"}
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, pd.Timestamp):
            return {"$ring5": "timestamp", "value": value.isoformat()}
        if isinstance(value, pd.Timedelta):
            return {"$ring5": "timedelta", "value": value.isoformat()}
        if isinstance(value, pd.Period):
            return {"$ring5": "period", "value": str(value), "freq": value.freqstr}
        if isinstance(value, pd.Interval):
            return {
                "$ring5": "interval",
                "left": cls._encode_scalar(value.left),
                "right": cls._encode_scalar(value.right),
                "closed": value.closed,
            }
        if isinstance(value, datetime):
            return {"$ring5": "datetime", "value": value.isoformat()}
        if isinstance(value, date):
            return {"$ring5": "date", "value": value.isoformat()}
        if isinstance(value, time):
            return {"$ring5": "time", "value": value.isoformat()}
        if isinstance(value, Decimal):
            return {"$ring5": "decimal", "value": str(value)}
        if isinstance(value, bytes):
            return {"$ring5": "bytes", "value": base64.b64encode(value).decode("ascii")}
        if isinstance(value, complex):
            return {"$ring5": "complex", "real": value.real, "imag": value.imag}
        if isinstance(value, float) and not math.isfinite(value):
            label = "nan" if math.isnan(value) else "infinity" if value > 0 else "-infinity"
            return {"$ring5": label}
        if isinstance(value, tuple):
            return {"$ring5": "tuple", "items": [cls._encode_scalar(item) for item in value]}
        if isinstance(value, list):
            return {"$ring5": "list", "items": [cls._encode_scalar(item) for item in value]}
        if isinstance(value, dict):
            return {
                "$ring5": "mapping",
                "items": [
                    [cls._encode_scalar(key), cls._encode_scalar(item)]
                    for key, item in value.items()
                ],
            }
        if isinstance(value, (bool, int, float, str)):
            return value
        raise TypeError(f"Unsupported snapshot scalar type: {type(value).__name__}.")

    @classmethod
    def _decode_scalar(cls, value: Any) -> Any:
        if not isinstance(value, dict) or "$ring5" not in value:
            return value
        kind = value["$ring5"]
        if kind == "missing":
            return pd.NA
        if kind == "nat":
            return pd.NaT
        if kind == "timestamp":
            return pd.Timestamp(value["value"])
        if kind == "timedelta":
            return pd.Timedelta(value["value"])
        if kind == "period":
            return pd.Period(value["value"], freq=value["freq"])
        if kind == "interval":
            return pd.Interval(
                cls._decode_scalar(value["left"]),
                cls._decode_scalar(value["right"]),
                closed=value["closed"],
            )
        if kind == "datetime":
            return datetime.fromisoformat(value["value"])
        if kind == "date":
            return date.fromisoformat(value["value"])
        if kind == "time":
            return time.fromisoformat(value["value"])
        if kind == "decimal":
            return Decimal(value["value"])
        if kind == "bytes":
            return base64.b64decode(value["value"], validate=True)
        if kind == "complex":
            return complex(value["real"], value["imag"])
        if kind == "nan":
            return float("nan")
        if kind == "infinity":
            return float("inf")
        if kind == "-infinity":
            return float("-inf")
        if kind == "tuple":
            return tuple(cls._decode_scalar(item) for item in value["items"])
        if kind == "list":
            return [cls._decode_scalar(item) for item in value["items"]]
        if kind == "mapping":
            return {
                cls._decode_scalar(key): cls._decode_scalar(item) for key, item in value["items"]
            }
        raise ValueError(f"Unknown snapshot scalar tag {kind!r}.")
