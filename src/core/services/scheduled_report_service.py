"""Durable stable-input decisions for watched and scheduled reports."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NoReturn, cast

from src.core.common.security_limits import (
    MAX_SCHEDULED_REPORT_SOURCE_BYTES,
    MAX_SCHEDULED_REPORT_SOURCE_FILES,
    MAX_SCHEDULED_REPORT_STABLE_SECONDS,
    MAX_SCHEDULED_REPORT_STATE_BYTES,
)
from src.core.models.recipe_models import RecipeSource
from src.core.models.scheduled_report_models import ScheduledReportOutcome, ScheduledReportResult

_STATE_FORMAT = "ring5.scheduled-report-state"
_STATE_VERSION = 1
_CHUNK_BYTES = 1024 * 1024


class ScheduledReportError(ValueError):
    """A scheduled-report source or durable state is invalid."""


class ScheduledReportPublishError(OSError):
    """A generated report or its durable state could not be published."""


class _UnstableSource(RuntimeError):
    def __init__(self, files: tuple[str, ...] = ()) -> None:
        self.files = files
        super().__init__("Scheduled report source changed while it was inspected.")


@dataclass(frozen=True)
class _SourceSnapshot:
    fingerprint: str
    files: tuple[str, ...]


@dataclass(frozen=True)
class _Decision:
    outcome: Literal["ready", "unchanged", "waiting_for_stability"]
    snapshot: _SourceSnapshot | None


class ScheduledReportService:
    """Publish reports only after a changed source remains stable."""

    @staticmethod
    def source_files(
        source: RecipeSource,
        find_stats_files: Callable[[str, str], Sequence[str]],
    ) -> tuple[str, ...]:
        """Resolve the concrete files that determine one recipe source."""
        if source.kind == "csv":
            return (source.path,)
        files = tuple(find_stats_files(source.path, source.pattern))
        if not files:
            raise ScheduledReportError(
                f"No files matching {source.pattern!r} found under {source.path!r}."
            )
        if source.strategy == "config_aware":
            companions = tuple(str(Path(path).parent / "config.ini") for path in files)
            return tuple(dict.fromkeys(files + companions))
        return files

    @classmethod
    def run(
        cls,
        *,
        recipe_name: str,
        configuration_fingerprint: str,
        resolve_source_files: Callable[[], Sequence[str]],
        report_path: str,
        state_path: str,
        stable_for_seconds: float,
        generate: Callable[[], bytes],
        now: float | None = None,
    ) -> ScheduledReportResult:
        """Check, generate, recheck, and atomically publish one report tick."""
        # [impl->req~ring5.automation.scheduled-reporting~1]
        configuration = cls._validate_fingerprint(
            configuration_fingerprint,
            "configuration_fingerprint",
        )
        stable_for = cls._validate_stable_for(stable_for_seconds)
        timestamp = cls._timestamp(now)
        decision = cls._check(
            resolve_source_files,
            report_path,
            state_path,
            configuration,
            stable_for,
            timestamp,
        )
        if decision.outcome != "ready":
            return cls._result(
                recipe_name,
                cast(ScheduledReportOutcome, decision.outcome),
                decision.snapshot,
                configuration,
                report_path,
                state_path,
                stable_for,
            )

        assert decision.snapshot is not None
        cls._validate_destinations(decision.snapshot.files, report_path, state_path)
        payload = generate()
        if not isinstance(payload, bytes) or not payload:
            raise ScheduledReportPublishError("Scheduled report generation produced no bytes.")

        try:
            confirmation = cls._snapshot(resolve_source_files)
        except _UnstableSource as exc:
            return cls._result(
                recipe_name,
                "waiting_for_stability",
                None,
                configuration,
                report_path,
                state_path,
                stable_for,
                source_files=exc.files,
            )
        if confirmation.fingerprint != decision.snapshot.fingerprint:
            cls._observe(confirmation, state_path, cls._timestamp(now))
            return cls._result(
                recipe_name,
                "waiting_for_stability",
                confirmation,
                configuration,
                report_path,
                state_path,
                stable_for,
            )

        state = cls._load_state(Path(state_path))
        if (
            state["generated_fingerprint"] == confirmation.fingerprint
            and state["generated_configuration_fingerprint"] == configuration
            and Path(report_path).is_file()
        ):
            return cls._result(
                recipe_name,
                "unchanged",
                confirmation,
                configuration,
                report_path,
                state_path,
                stable_for,
            )
        if state["observed_fingerprint"] != confirmation.fingerprint:
            cls._observe(confirmation, state_path, cls._timestamp(now))
            return cls._result(
                recipe_name,
                "waiting_for_stability",
                confirmation,
                configuration,
                report_path,
                state_path,
                stable_for,
            )

        cls._atomic_write(Path(report_path), payload, "report")
        state["generated_fingerprint"] = confirmation.fingerprint
        state["generated_configuration_fingerprint"] = configuration
        state["generated_at"] = cls._timestamp(now)
        cls._write_state(Path(state_path), state)
        return cls._result(
            recipe_name,
            "generated",
            confirmation,
            configuration,
            report_path,
            state_path,
            stable_for,
        )

    @classmethod
    def _check(
        cls,
        resolve_source_files: Callable[[], Sequence[str]],
        report_path: str,
        state_path: str,
        configuration_fingerprint: str,
        stable_for: float,
        timestamp: float,
    ) -> _Decision:
        # [impl->req~ring5.automation.scheduled-reporting~1]
        try:
            snapshot = cls._snapshot(resolve_source_files)
        except _UnstableSource as exc:
            unstable = _SourceSnapshot("", exc.files) if exc.files else None
            return _Decision("waiting_for_stability", unstable)

        cls._validate_destinations(snapshot.files, report_path, state_path)
        state_file = Path(state_path)
        state = cls._load_state(state_file)
        if (
            state["generated_fingerprint"] == snapshot.fingerprint
            and state["generated_configuration_fingerprint"] == configuration_fingerprint
            and Path(report_path).is_file()
        ):
            return _Decision("unchanged", snapshot)
        observed_at = state["observed_at"]
        if state["observed_fingerprint"] != snapshot.fingerprint or (
            isinstance(observed_at, float) and timestamp < observed_at
        ):
            state["observed_fingerprint"] = snapshot.fingerprint
            state["observed_at"] = timestamp
            cls._write_state(state_file, state)
            return _Decision(
                "ready" if stable_for == 0 else "waiting_for_stability",
                snapshot,
            )
        assert isinstance(observed_at, float)
        if timestamp - observed_at < stable_for:
            return _Decision("waiting_for_stability", snapshot)
        return _Decision("ready", snapshot)

    @classmethod
    def _snapshot(
        cls,
        resolve_source_files: Callable[[], Sequence[str]],
    ) -> _SourceSnapshot:
        files = cls._normalize_files(resolve_source_files())
        digest = hashlib.sha256()
        total_bytes = 0
        for file_path in files:
            path = Path(file_path)
            try:
                before = path.stat()
                signature = (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                )
                total_bytes += before.st_size
                if total_bytes > MAX_SCHEDULED_REPORT_SOURCE_BYTES:
                    raise ScheduledReportError("Scheduled report sources exceed the 4 GiB limit.")
                encoded_path = file_path.encode("utf-8")
                digest.update(len(encoded_path).to_bytes(8, "big"))
                digest.update(encoded_path)
                with path.open("rb") as source:
                    while chunk := source.read(_CHUNK_BYTES):
                        digest.update(chunk)
                after = path.stat()
            except FileNotFoundError as exc:
                raise _UnstableSource(files) from exc
            except OSError as exc:
                raise ScheduledReportError(
                    f"Scheduled report source could not be read: {file_path}"
                ) from exc
            if signature != (
                after.st_dev,
                after.st_ino,
                after.st_size,
                after.st_mtime_ns,
            ):
                raise _UnstableSource(files)
        try:
            confirmed_files = cls._normalize_files(resolve_source_files())
        except (OSError, ScheduledReportError) as exc:
            raise _UnstableSource(files) from exc
        if files != confirmed_files:
            raise _UnstableSource(files)
        return _SourceSnapshot(f"sha256:{digest.hexdigest()}", files)

    @staticmethod
    def _normalize_files(files: Sequence[str]) -> tuple[str, ...]:
        if not files:
            raise ScheduledReportError("Scheduled report source contains no files.")
        if len(files) > MAX_SCHEDULED_REPORT_SOURCE_FILES:
            raise ScheduledReportError(
                f"Scheduled report source exceeds {MAX_SCHEDULED_REPORT_SOURCE_FILES:,} files."
            )
        normalized: list[str] = []
        for value in files:
            if not isinstance(value, str) or not value:
                raise ScheduledReportError("Scheduled report source paths must be non-empty text.")
            path = Path(value)
            if path.is_symlink():
                raise ScheduledReportError(f"Scheduled report source cannot be a symlink: {value}")
            try:
                resolved = path.resolve(strict=True)
            except OSError as exc:
                raise ScheduledReportError(
                    f"Scheduled report source is unavailable: {value}"
                ) from exc
            if not resolved.is_file():
                raise ScheduledReportError(f"Scheduled report source is not a file: {value}")
            normalized.append(str(resolved))
        return tuple(sorted(dict.fromkeys(normalized)))

    @classmethod
    def _observe(cls, snapshot: _SourceSnapshot, state_path: str, timestamp: float) -> None:
        state_file = Path(state_path)
        state = cls._load_state(state_file)
        state["observed_fingerprint"] = snapshot.fingerprint
        state["observed_at"] = timestamp
        cls._write_state(state_file, state)

    @staticmethod
    def _validate_destinations(
        source_files: tuple[str, ...],
        report_path: str,
        state_path: str,
    ) -> None:
        report = Path(report_path).resolve()
        state = Path(state_path).resolve()
        sources = {Path(path).resolve() for path in source_files}
        if report == state:
            raise ScheduledReportError("Scheduled report and state paths must be different.")
        if report in sources or state in sources:
            raise ScheduledReportError("Scheduled report destinations cannot replace source files.")

    @classmethod
    def _load_state(cls, path: Path) -> dict[str, Any]:
        if not path.exists():
            return cls._empty_state()
        try:
            if path.stat().st_size > MAX_SCHEDULED_REPORT_STATE_BYTES:
                raise ScheduledReportError("Scheduled report state exceeds the 64 KiB limit.")
            raw = path.read_bytes()
            value = json.loads(raw.decode("utf-8"), parse_constant=cls._reject_constant)
        except ScheduledReportError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ScheduledReportError(f"Scheduled report state is invalid: {path}") from exc
        if not isinstance(value, dict) or value.get("format") != _STATE_FORMAT:
            raise ScheduledReportError(f"Scheduled report state is invalid: {path}")
        if value.get("schema_version") != _STATE_VERSION:
            raise ScheduledReportError("Scheduled report state uses an unsupported schema version.")
        if set(value) != set(cls._empty_state()):
            raise ScheduledReportError("Scheduled report state has missing or unsupported fields.")
        for field in (
            "observed_fingerprint",
            "generated_fingerprint",
            "generated_configuration_fingerprint",
        ):
            fingerprint = value.get(field)
            if fingerprint is not None:
                cls._validate_fingerprint(fingerprint, field)
        for field in ("observed_at", "generated_at"):
            timestamp = value.get(field)
            if timestamp is not None and (
                isinstance(timestamp, bool)
                or not isinstance(timestamp, (int, float))
                or not math.isfinite(float(timestamp))
                or timestamp < 0
            ):
                raise ScheduledReportError(f"Scheduled report state has an invalid {field}.")
            if isinstance(timestamp, int):
                value[field] = float(timestamp)
        if (value["observed_fingerprint"] is None) != (value["observed_at"] is None):
            raise ScheduledReportError("Scheduled report state has inconsistent observed fields.")
        generated_fields = (
            value["generated_fingerprint"],
            value["generated_configuration_fingerprint"],
            value["generated_at"],
        )
        if any(field is None for field in generated_fields) != all(
            field is None for field in generated_fields
        ):
            raise ScheduledReportError("Scheduled report state has inconsistent generated fields.")
        if value["generated_fingerprint"] is not None and value["observed_fingerprint"] is None:
            raise ScheduledReportError("Scheduled report state has no observation for its report.")
        return value

    @staticmethod
    def _empty_state() -> dict[str, Any]:
        return {
            "format": _STATE_FORMAT,
            "schema_version": _STATE_VERSION,
            "observed_fingerprint": None,
            "observed_at": None,
            "generated_fingerprint": None,
            "generated_configuration_fingerprint": None,
            "generated_at": None,
        }

    @staticmethod
    def report_configuration_fingerprint(
        recipe_payload: bytes,
        *,
        report_path: str,
        title: str,
        format: str,
    ) -> str:
        """Identify every non-source input that changes the generated report."""
        digest = hashlib.sha256()
        values = (
            recipe_payload,
            str(Path(report_path).resolve()).encode(),
            title.encode(),
            format.encode(),
        )
        for value in values:
            digest.update(len(value).to_bytes(8, "big"))
            digest.update(value)
        return f"sha256:{digest.hexdigest()}"

    @staticmethod
    def _validate_fingerprint(value: str, field: str) -> str:
        if (
            not isinstance(value, str)
            or len(value) != 71
            or not value.startswith("sha256:")
            or any(character not in "0123456789abcdef" for character in value[7:])
        ):
            raise ScheduledReportError(f"Scheduled report has an invalid {field}.")
        return value

    @classmethod
    def _write_state(cls, path: Path, state: dict[str, Any]) -> None:
        payload = (json.dumps(state, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode(
            "utf-8"
        )
        if len(payload) > MAX_SCHEDULED_REPORT_STATE_BYTES:
            raise ScheduledReportPublishError("Scheduled report state exceeds the 64 KiB limit.")
        cls._atomic_write(path, payload, "state")

    @staticmethod
    def _atomic_write(path: Path, payload: bytes, label: str) -> None:
        temporary_path: Path | None = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=path.parent,
                prefix=f".ring5-scheduled-{label}-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(payload)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        except OSError as exc:
            raise ScheduledReportPublishError(
                f"Could not write scheduled report {label} {str(path)!r}: {exc}"
            ) from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _validate_stable_for(value: float) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or not 0 <= value <= MAX_SCHEDULED_REPORT_STABLE_SECONDS
        ):
            raise ScheduledReportError("stable_for_seconds must be from 0 through 604800.")
        return float(value)

    @staticmethod
    def _timestamp(value: float | None) -> float:
        timestamp = time.time() if value is None else value
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, (int, float))
            or not math.isfinite(float(timestamp))
            or timestamp < 0
        ):
            raise ScheduledReportError(
                "Scheduled report timestamp must be finite and non-negative."
            )
        return float(timestamp)

    @staticmethod
    def _result(
        recipe_name: str,
        outcome: ScheduledReportOutcome,
        snapshot: _SourceSnapshot | None,
        configuration_fingerprint: str,
        report_path: str,
        state_path: str,
        stable_for: float,
        *,
        source_files: tuple[str, ...] = (),
    ) -> ScheduledReportResult:
        fingerprint = snapshot.fingerprint if snapshot and snapshot.fingerprint else None
        files = snapshot.files if snapshot else source_files
        return ScheduledReportResult(
            recipe_name=recipe_name,
            outcome=outcome,
            source_fingerprint=fingerprint,
            configuration_fingerprint=configuration_fingerprint,
            source_files=files,
            report_path=report_path,
            state_path=state_path,
            stable_for_seconds=stable_for,
        )

    @staticmethod
    def _reject_constant(value: str) -> NoReturn:
        raise ValueError(f"Invalid JSON constant {value!r}.")
