"""Immutable portfolio revisions and bounded field-level comparison."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from src.core.common.security_limits import MAX_PORTFOLIO_DIFF_ENTRIES
from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.models.portfolio_models import PortfolioData
from src.core.models.portfolio_revision_models import (
    PortfolioChangeKind,
    PortfolioDiff,
    PortfolioDiffEntry,
    PortfolioDiffSection,
    PortfolioRevisionInfo,
)
from src.core.services.data_services.path_service import PathService
from src.core.services.portfolio_migrator import PortfolioMigrator
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService

_REVISION_ID = re.compile(r"^[0-9a-f]{64}$")
_SECTIONS: tuple[PortfolioDiffSection, ...] = (
    "data_sources",
    "pipelines",
    "plots",
    "figure_settings",
)
_DATA_BINDING_KEYS = {
    "color",
    "facet_col",
    "group",
    "group_by",
    "histogram_variable",
    "metric_columns",
    "parallel_color",
    "parallel_dimensions",
    "sankey_label",
    "sankey_source",
    "sankey_target",
    "sankey_value",
    "x",
    "y",
    "y_bar",
    "y_columns",
    "y_columns_right",
    "y_dot",
}
_MISSING = object()

logger = logging.getLogger(__name__)


class PortfolioRevisionService:
    """Retain exact portfolio bytes and compare reviewable configuration fields."""

    @classmethod
    def retain_and_replace(
        cls,
        name: str,
        payload: bytes,
        current_path: Path,
        *,
        overwrite: bool,
    ) -> str:
        """Retain *payload* as a revision and atomically make it current."""
        # [impl->req~ring5.portfolio.history-diff~1]
        cls._validate_name(name)
        if current_path.exists() and not overwrite:
            raise FileExistsError(f"Portfolio {name!r} already exists at {current_path}")
        if current_path.exists():
            cls._record(name, current_path.read_bytes())

        revision_id, revision_path, created = cls._record(name, payload)
        try:
            cls._write_current(current_path, payload, overwrite=overwrite)
        except OSError:
            if created:
                revision_path.unlink(missing_ok=True)
            raise
        return revision_id

    @classmethod
    def list_revisions(
        cls,
        name: str,
        current_path: Path,
    ) -> tuple[PortfolioRevisionInfo, ...]:
        """Return saved versions in capture order, including a legacy baseline."""
        # [impl->req~ring5.portfolio.history-diff~1]
        cls._validate_name(name)
        active_revision: str | None = None
        if current_path.exists():
            current = current_path.read_bytes()
            active_revision, _path, _created = cls._record(name, current)

        directory = cls._history_dir(name, create=False)
        if not directory.exists():
            return ()
        drafts: list[tuple[int, str, str, int, str, int]] = []
        for path in directory.glob("*.json"):
            try:
                raw = cls._verified_bytes(path)
                data = cls._load_document(raw)
                stat = path.stat()
                plots = data.get("plots", [])
                drafts.append(
                    (
                        stat.st_mtime_ns,
                        path.stem,
                        cls._created_at(data, stat.st_mtime),
                        len(raw),
                        cls._source_label(data),
                        len(plots) if isinstance(plots, list) else 0,
                    )
                )
            except (OSError, TypeError, ValueError) as exc:
                logger.warning("Ignoring unreadable portfolio revision %s: %s", path, exc)
        drafts.sort(key=lambda item: (item[0], item[1]))
        return tuple(
            PortfolioRevisionInfo(
                portfolio_name=name,
                revision_id=revision_id,
                sequence=index,
                created_at=created_at,
                active=revision_id == active_revision,
                size_bytes=size_bytes,
                source=source,
                plot_count=plot_count,
            )
            for index, (
                _modified,
                revision_id,
                created_at,
                size_bytes,
                source,
                plot_count,
            ) in enumerate(drafts, start=1)
        )

    @classmethod
    def load_revision(cls, name: str, revision_id: str) -> PortfolioData:
        """Load and migrate one checksum-verified immutable revision."""
        cls._validate_name(name)
        path = cls._revision_path(name, revision_id)
        if not path.exists():
            raise FileNotFoundError(
                f"Portfolio revision {revision_id!r} for {name!r} was not found."
            )
        return cls._load_document(cls._verified_bytes(path))

    @classmethod
    def compare(cls, name: str, before_revision: str, after_revision: str) -> PortfolioDiff:
        """Compare tracked portfolio fields without inspecting embedded data rows."""
        # [impl->req~ring5.portfolio.history-diff~1]
        before = cls.load_revision(name, before_revision)
        after = cls.load_revision(name, after_revision)
        before_sections = cls._sections(before)
        after_sections = cls._sections(after)
        entries: list[PortfolioDiffEntry] = []
        truncated = False
        for section in _SECTIONS:
            if cls._walk(
                section,
                before_sections[section],
                after_sections[section],
                "",
                entries,
            ):
                truncated = True
                break
        counts = tuple(
            (section, sum(entry.section == section for entry in entries)) for section in _SECTIONS
        )
        return PortfolioDiff(
            portfolio_name=name,
            before_revision=before_revision,
            after_revision=after_revision,
            entries=tuple(entries),
            section_counts=counts,
            truncated=truncated,
        )

    @classmethod
    def delete_history(cls, name: str) -> None:
        """Delete only the immutable revisions belonging to *name*."""
        directory = cls._history_dir(name, create=False)
        if not directory.exists():
            return
        for path in directory.iterdir():
            if not path.is_file() or path.suffix != ".json":
                raise OSError(f"Unexpected entry in portfolio revision directory: {path}")
            path.unlink()
        directory.rmdir()

    @classmethod
    def _record(cls, name: str, payload: bytes) -> tuple[str, Path, bool]:
        revision_id = hashlib.sha256(payload).hexdigest()
        path = cls._revision_path(name, revision_id, create_directory=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise ValueError(f"Portfolio revision {revision_id!r} failed identity validation.")
            return revision_id, path, False

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=path.parent,
                prefix=".ring5-portfolio-revision-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(payload)
            try:
                os.link(temporary_path, path)
            except FileExistsError:
                if path.read_bytes() != payload:
                    raise ValueError(
                        f"Portfolio revision {revision_id!r} failed identity validation."
                    )
                return revision_id, path, False
            return revision_id, path, True
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _write_current(path: Path, payload: bytes, *, overwrite: bool) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=path.parent,
                prefix=".ring5-portfolio-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(payload)
            if overwrite:
                os.replace(temporary_path, path)
            else:
                try:
                    os.link(temporary_path, path)
                except FileExistsError as exc:
                    raise FileExistsError(f"Portfolio already exists at {path}") from exc
                temporary_path.unlink()
            temporary_path = None
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    @classmethod
    def _revision_path(
        cls,
        name: str,
        revision_id: str,
        *,
        create_directory: bool = False,
    ) -> Path:
        if not isinstance(revision_id, str) or not _REVISION_ID.fullmatch(revision_id):
            raise ValueError("Portfolio revision IDs must be 64 lowercase hexadecimal characters.")
        directory = cls._history_dir(name, create=create_directory)
        return validate_path_within(directory / f"{revision_id}.json", directory)

    @classmethod
    def _history_dir(cls, name: str, *, create: bool) -> Path:
        validated = cls._validate_name(name)
        root = PathService.get_portfolio_revisions_dir()
        identity = hashlib.sha256(validated.encode("utf-8")).hexdigest()[:12]
        directory = validate_path_within(
            root / f"{sanitize_filename(validated)}-{identity}",
            root,
        )
        if create:
            directory.mkdir(parents=True, exist_ok=True)
        return directory

    @staticmethod
    def _validate_name(name: object) -> str:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Portfolio name must be non-empty text.")
        if len(name) > 120:
            raise ValueError("Portfolio name cannot exceed 120 characters.")
        if any(ord(character) < 32 for character in name):
            raise ValueError("Portfolio name cannot contain control characters.")
        return name

    @staticmethod
    def _verified_bytes(path: Path) -> bytes:
        if not _REVISION_ID.fullmatch(path.stem):
            raise ValueError("Portfolio revision filename is invalid.")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != path.stem:
            raise ValueError("Portfolio revision checksum does not match its filename.")
        return raw

    @staticmethod
    def _load_document(raw: bytes) -> PortfolioData:
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Portfolio revision must contain a JSON object.")
        integrity = PortfolioIntegrityService.verify(value)
        PortfolioIntegrityService.require_restorable(integrity)
        return cast(PortfolioData, PortfolioMigrator.migrate(value))

    @staticmethod
    def _created_at(data: PortfolioData, modified: float) -> str:
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str) and timestamp.strip():
            return timestamp
        return datetime.fromtimestamp(modified, tz=timezone.utc).isoformat()

    @staticmethod
    def _source_label(data: PortfolioData) -> str:
        if data.get("use_parser"):
            return "Simulator parser"
        if data.get("csv_path"):
            return "CSV"
        return "Configuration only"

    @classmethod
    def _sections(cls, data: PortfolioData) -> dict[PortfolioDiffSection, Any]:
        plots = data.get("plots", [])
        if not isinstance(plots, list):
            raise TypeError("Portfolio plots must be a list before comparison.")
        sources: dict[str, Any] = {
            "mode": "parser" if data.get("use_parser") else "csv",
            "csv_path": data.get("csv_path"),
            "stats_path": data.get("stats_path"),
            "stats_pattern": data.get("stats_pattern"),
            "parse_variables": copy.deepcopy(data.get("parse_variables", [])),
            "scanned_variables": copy.deepcopy(data.get("scanned_variables", [])),
            "semantics": copy.deepcopy(data.get("data_semantics", {})),
        }
        pipelines: list[dict[str, Any]] = []
        plot_fields: list[dict[str, Any]] = []
        figure_settings: list[dict[str, Any]] = []
        for index, raw_plot in enumerate(plots):
            if not isinstance(raw_plot, dict):
                raise TypeError(f"Portfolio plot {index} must be an object before comparison.")
            config = raw_plot.get("config", {})
            if not isinstance(config, Mapping):
                raise TypeError(f"Portfolio plot {index} config must be an object.")
            bindings = {
                str(key): copy.deepcopy(value)
                for key, value in config.items()
                if cls._is_data_binding(str(key))
            }
            appearance = {
                str(key): copy.deepcopy(value)
                for key, value in config.items()
                if not cls._is_data_binding(str(key))
            }
            plot_id = raw_plot.get("id", index)
            pipelines.append(
                {
                    "plot_id": plot_id,
                    "steps": copy.deepcopy(raw_plot.get("pipeline", [])),
                }
            )
            plot_fields.append(
                {
                    "id": plot_id,
                    "name": raw_plot.get("name"),
                    "plot_type": raw_plot.get("plot_type"),
                    "data_bindings": bindings,
                    "legend_mappings": copy.deepcopy(raw_plot.get("legend_mappings", {})),
                    "legend_mappings_by_column": copy.deepcopy(
                        raw_plot.get("legend_mappings_by_column", {})
                    ),
                    "semantics": copy.deepcopy(raw_plot.get("processed_semantics", {})),
                }
            )
            figure_settings.append(
                {
                    "plot_id": plot_id,
                    "resolved": copy.deepcopy(raw_plot.get("figure_spec")),
                    "raw": appearance,
                }
            )
        return {
            "data_sources": sources,
            "pipelines": pipelines,
            "plots": plot_fields,
            "figure_settings": figure_settings,
        }

    @staticmethod
    def _is_data_binding(key: str) -> bool:
        return key in _DATA_BINDING_KEYS or key.endswith(
            ("_column", "_columns", "_filter", "_variable")
        )

    @classmethod
    def _walk(
        cls,
        section: PortfolioDiffSection,
        before: object,
        after: object,
        path: str,
        entries: list[PortfolioDiffEntry],
    ) -> bool:
        if len(entries) >= MAX_PORTFOLIO_DIFF_ENTRIES:
            return not cls._equal(before, after)
        if isinstance(before, Mapping) and isinstance(after, Mapping):
            keys = sorted(set(before) | set(after), key=str)
            for key in keys:
                child = f"{path}.{key}" if path else str(key)
                if cls._walk(
                    section,
                    before.get(key, _MISSING),
                    after.get(key, _MISSING),
                    child,
                    entries,
                ):
                    return True
            return False
        if cls._sequence(before) and cls._sequence(after):
            before_values = cast(Sequence[object], before)
            after_values = cast(Sequence[object], after)
            for index in range(max(len(before_values), len(after_values))):
                child = f"{path}[{index}]" if path else f"[{index}]"
                if cls._walk(
                    section,
                    before_values[index] if index < len(before_values) else _MISSING,
                    after_values[index] if index < len(after_values) else _MISSING,
                    child,
                    entries,
                ):
                    return True
            return False
        if before is _MISSING:
            return cls._walk_added(section, after, path, entries)
        if after is _MISSING:
            return cls._walk_removed(section, before, path, entries)
        if cls._equal(before, after):
            return False
        return cls._append(section, path or "value", "changed", before, after, entries)

    @classmethod
    def _walk_added(
        cls,
        section: PortfolioDiffSection,
        value: object,
        path: str,
        entries: list[PortfolioDiffEntry],
    ) -> bool:
        if isinstance(value, Mapping) and value:
            for key in sorted(value, key=str):
                child = f"{path}.{key}" if path else str(key)
                if cls._walk_added(section, value[key], child, entries):
                    return True
            return False
        if cls._sequence(value) and len(cast(Sequence[object], value)) > 0:
            for index, item in enumerate(cast(Sequence[object], value)):
                child = f"{path}[{index}]" if path else f"[{index}]"
                if cls._walk_added(section, item, child, entries):
                    return True
            return False
        return cls._append(section, path or "value", "added", None, value, entries)

    @classmethod
    def _walk_removed(
        cls,
        section: PortfolioDiffSection,
        value: object,
        path: str,
        entries: list[PortfolioDiffEntry],
    ) -> bool:
        if isinstance(value, Mapping) and value:
            for key in sorted(value, key=str):
                child = f"{path}.{key}" if path else str(key)
                if cls._walk_removed(section, value[key], child, entries):
                    return True
            return False
        if cls._sequence(value) and len(cast(Sequence[object], value)) > 0:
            for index, item in enumerate(cast(Sequence[object], value)):
                child = f"{path}[{index}]" if path else f"[{index}]"
                if cls._walk_removed(section, item, child, entries):
                    return True
            return False
        return cls._append(section, path or "value", "removed", value, None, entries)

    @staticmethod
    def _sequence(value: object) -> bool:
        return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))

    @staticmethod
    def _equal(before: object, after: object) -> bool:
        if isinstance(before, float) and isinstance(after, float):
            if math.isnan(before) and math.isnan(after):
                return True
        return before == after

    @staticmethod
    def _append(
        section: PortfolioDiffSection,
        path: str,
        change: PortfolioChangeKind,
        before: object,
        after: object,
        entries: list[PortfolioDiffEntry],
    ) -> bool:
        if len(entries) >= MAX_PORTFOLIO_DIFF_ENTRIES:
            return True
        entries.append(PortfolioDiffEntry(section, path, change, before, after))
        return False
