"""Safe, versioned persistence for reusable pandas dataset snapshots."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, cast
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

import pandas as pd

from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.common.content_identity import frame_signature
from src.core.common.security_limits import MAX_PORTFOLIO_BUNDLE_BYTES
from src.core.models import DatasetSnapshotInfo
from src.core.services.data_services.path_service import PathService
from src.core.common.typed_table_codec import TypedTableCodec

logger = logging.getLogger(__name__)

_FORMAT = "ring5.dataset-snapshot"
_FORMAT_VERSION = 3
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

        frame_payload = TypedTableCodec.encode(data)
        expected_fingerprint = frame_signature(data)
        payload_bytes = json.dumps(
            frame_payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
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
        return cls._load_payload(path.read_bytes(), expected_name=name.strip())

    @classmethod
    def export_snapshot(cls, name: str) -> bytes:
        """Return exact verified snapshot bytes for a portable bundle.

        Args:
            name: Saved snapshot name.

        Returns:
            Complete ``.ring5-snapshot`` archive bytes.
        """
        path = cls._snapshot_path(cls._validate_name(name, "Snapshot"))
        if not path.exists():
            raise FileNotFoundError(f"Dataset snapshot {name!r} does not exist.")
        payload = path.read_bytes()
        cls._load_payload(payload, expected_name=name.strip())
        return payload

    @classmethod
    def inspect_snapshot(cls, payload: bytes) -> DatasetSnapshotInfo:
        """Validate in-memory snapshot bytes and return their metadata.

        Args:
            payload: Complete ``.ring5-snapshot`` archive bytes.

        Returns:
            Verified snapshot metadata without persisting the archive.
        """
        info, _data = cls._load_payload(payload)
        return info

    @classmethod
    def _load_payload(
        cls,
        payload: bytes,
        *,
        expected_name: str | None = None,
    ) -> tuple[DatasetSnapshotInfo, pd.DataFrame]:
        """Decode one bounded snapshot archive from memory."""
        if not isinstance(payload, bytes) or not payload:
            raise ValueError("Dataset snapshot payload must be non-empty bytes.")
        if len(payload) > MAX_PORTFOLIO_BUNDLE_BYTES:
            raise ValueError("Dataset snapshot exceeds the portable bundle size limit.")
        try:
            with ZipFile(BytesIO(payload)) as archive:
                infos = archive.infolist()
                if len(infos) != 2 or {info.filename for info in infos} != {
                    _MANIFEST_MEMBER,
                    _DATA_MEMBER,
                }:
                    raise ValueError("Dataset snapshot has unexpected archive members.")
                if any(
                    info.file_size > MAX_PORTFOLIO_BUNDLE_BYTES
                    or info.flag_bits & 0x1
                    or info.is_dir()
                    for info in infos
                ):
                    raise ValueError("Dataset snapshot contains an unsafe archive member.")
                if sum(info.file_size for info in infos) > MAX_PORTFOLIO_BUNDLE_BYTES:
                    raise ValueError("Dataset snapshot expands beyond the portable size limit.")
                manifest = cls._parse_manifest(archive.read(_MANIFEST_MEMBER))
                payload_bytes = archive.read(_DATA_MEMBER)
        except (BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Dataset snapshot is unreadable or incomplete.") from exc

        if expected_name is not None and manifest["name"] != expected_name:
            raise ValueError(
                f"Dataset snapshot {expected_name!r} has mismatched identity metadata."
            )

        actual_payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        if actual_payload_hash != manifest["payload_sha256"]:
            raise ValueError("Dataset snapshot failed its payload checksum.")
        try:
            frame_payload = cast(dict[str, Any], json.loads(payload_bytes))
            data = TypedTableCodec.decode(frame_payload)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Dataset snapshot contains invalid table data.") from exc
        if data is None:
            raise ValueError("Dataset snapshot must contain a present table.")
        if len(data) != manifest["row_count"] or len(data.columns) != manifest["column_count"]:
            raise ValueError("Dataset snapshot does not match its recorded dimensions.")
        if frame_signature(data) != manifest["fingerprint"]:
            raise ValueError("Dataset snapshot failed fingerprint verification.")
        return cls._info_from_manifest(manifest, len(payload)), data

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
        if set(parsed) != set(required):
            raise ValueError("Snapshot manifest fields are invalid.")
        for key, expected_type in required.items():
            if type(parsed[key]) is not expected_type:
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
