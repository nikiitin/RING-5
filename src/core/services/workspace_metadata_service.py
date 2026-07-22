"""Validated favorites and tags for live artifacts and saved portfolios."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from src.core.common.security_limits import (
    MAX_WORKSPACE_METADATA_ENTRIES,
    MAX_WORKSPACE_METADATA_FILE_BYTES,
    MAX_WORKSPACE_SEARCH_ENTRIES_PER_KIND,
    MAX_WORKSPACE_SEARCH_FIELD_LENGTH,
    MAX_WORKSPACE_SEARCH_RESULTS,
    MAX_WORKSPACE_TAG_LENGTH,
    MAX_WORKSPACE_TAGS_PER_ARTIFACT,
)
from src.core.models.workspace_metadata_models import (
    WorkspaceArtifact,
    WorkspaceArtifactKind,
    WorkspaceArtifactResponse,
)
from src.core.services.data_services.path_service import PathService
from src.core.state.state_manager import StateManager

_CONFIG_KEY = "_workspace_artifact_metadata"
_PORTFOLIO_METADATA_FILE = ".workspace-metadata"
_PORTFOLIO_METADATA_VERSION = 1
_TAG_SEPARATORS = frozenset({" ", "-"})
_KINDS: tuple[WorkspaceArtifactKind, ...] = (
    "variable",
    "dataset",
    "plot",
    "pipeline",
    "portfolio",
)
_KIND_ORDER = {kind: index for index, kind in enumerate(_KINDS)}


class WorkspaceMetadataService:
    """Discover current targets and retain only bounded canonical metadata."""

    _portfolio_lock = threading.RLock()

    @classmethod
    def list_artifacts(
        cls,
        state_manager: StateManager,
        portfolio_names: Sequence[str],
        *,
        kind: WorkspaceArtifactKind | None = None,
        tags: Sequence[str] = (),
        favorites_only: bool = False,
        limit: int = 100,
    ) -> WorkspaceArtifactResponse:
        """Return artifacts matching a kind, all tags, and optional favorite filter."""
        # [impl->req~ring5.workspace.favorites-tags~1]
        resolved_kind = cls._kind(kind, optional=True)
        resolved_tags = cls._tags(tags)
        if not isinstance(favorites_only, bool):
            raise TypeError("Workspace favorites-only filter must be a boolean.")
        resolved_limit = cls._limit(limit)
        artifacts, available, index_truncated = cls._discover(
            state_manager,
            portfolio_names,
        )
        metadata = cls._metadata(state_manager)
        metadata.update(cls._portfolio_metadata())
        enriched = tuple(
            cls._enrich(artifact, metadata.get((artifact.kind, artifact.identifier)))
            for artifact in artifacts
        )
        available_tags = tuple(sorted({tag for artifact in enriched for tag in artifact.tags}))
        matches = tuple(
            artifact
            for artifact in enriched
            if (resolved_kind is None or artifact.kind == resolved_kind)
            and all(tag in artifact.tags for tag in resolved_tags)
            and (not favorites_only or artifact.favorite)
        )
        return WorkspaceArtifactResponse(
            kind=resolved_kind,
            tags=resolved_tags,
            favorites_only=favorites_only,
            artifacts=matches[:resolved_limit],
            available_tags=available_tags,
            total_matches=len(matches),
            returned_matches=min(len(matches), resolved_limit),
            results_truncated=len(matches) > resolved_limit,
            available_artifacts=available,
            indexed_artifacts=len(artifacts),
            index_truncated=index_truncated,
        )

    @classmethod
    def set_metadata(
        cls,
        state_manager: StateManager,
        portfolio_names: Sequence[str],
        kind: WorkspaceArtifactKind,
        identifier: str,
        *,
        tags: Sequence[str] = (),
        favorite: bool = False,
    ) -> WorkspaceArtifact:
        """Validate a live target and replace its complete metadata record."""
        # [impl->req~ring5.workspace.favorites-tags~1]
        resolved_kind = cast(WorkspaceArtifactKind, cls._kind(kind))
        resolved_identifier = cls._text(identifier, "identifier", required=True)
        resolved_tags = cls._tags(tags)
        if not isinstance(favorite, bool):
            raise TypeError("Workspace favorite flag must be a boolean.")
        artifacts, _, _ = cls._discover(state_manager, portfolio_names)
        targets = {(artifact.kind, artifact.identifier): artifact for artifact in artifacts}
        identity = (resolved_kind, resolved_identifier)
        if identity not in targets:
            raise KeyError(
                f"Workspace {resolved_kind} {resolved_identifier!r} is not currently available."
            )
        record = {"tags": list(resolved_tags), "favorite": favorite}
        if resolved_kind == "portfolio":
            with cls._portfolio_lock:
                metadata = cls._portfolio_metadata()
                cls._replace_record(metadata, identity, record)
                existing_portfolios = {
                    artifact.identifier for artifact in artifacts if artifact.kind == "portfolio"
                }
                metadata = {
                    key: value
                    for key, value in metadata.items()
                    if key[0] != "portfolio" or key[1] in existing_portfolios
                }
                cls._write_portfolio_metadata(metadata)
        else:
            metadata = cls._metadata(state_manager)
            cls._replace_record(metadata, identity, record)
            cls._write_workspace_metadata(state_manager, metadata)
        return cls._enrich(targets[identity], record)

    @staticmethod
    def _replace_record(
        metadata: dict[tuple[WorkspaceArtifactKind, str], dict[str, Any]],
        identity: tuple[WorkspaceArtifactKind, str],
        record: dict[str, Any],
    ) -> None:
        if record["tags"] or record["favorite"]:
            if identity not in metadata and len(metadata) >= MAX_WORKSPACE_METADATA_ENTRIES:
                raise ValueError(
                    f"Workspace metadata is limited to {MAX_WORKSPACE_METADATA_ENTRIES:,} entries."
                )
            metadata[identity] = record
        else:
            metadata.pop(identity, None)

    @classmethod
    def _discover(
        cls,
        state_manager: StateManager,
        portfolio_names: Sequence[str],
    ) -> tuple[tuple[WorkspaceArtifact, ...], int, bool]:
        candidates: list[WorkspaceArtifact] = []
        variable_names: dict[str, None] = {}
        for variable in (
            *state_manager.get_parse_variables(),
            *state_manager.get_scanned_variables(),
        ):
            name = variable.get("name")
            if isinstance(name, str) and name.strip():
                variable_names.setdefault(name.strip(), None)
        candidates.extend(WorkspaceArtifact("variable", name, name) for name in variable_names)
        candidates.extend(
            WorkspaceArtifact("dataset", info.name, info.name)
            for info in state_manager.list_datasets()
        )
        for plot in state_manager.get_plots():
            plot_id = str(plot.plot_id)
            candidates.append(WorkspaceArtifact("plot", plot_id, plot.name))
            for index, step in enumerate(plot.pipeline):
                step_id = step.get("id", index)
                step_type = str(step.get("type", "Transformation")).replace("_", " ").title()
                candidates.append(
                    WorkspaceArtifact(
                        "pipeline",
                        f"{plot_id}:{step_id}",
                        f"{plot.name} · step {index + 1}: {step_type}",
                    )
                )
        candidates.extend(
            WorkspaceArtifact("portfolio", name.strip(), name.strip())
            for name in portfolio_names
            if isinstance(name, str) and name.strip()
        )

        indexed: list[WorkspaceArtifact] = []
        per_kind = {kind: 0 for kind in _KINDS}
        seen: set[tuple[WorkspaceArtifactKind, str]] = set()
        truncated = False
        for artifact in candidates:
            sanitized = WorkspaceArtifact(
                artifact.kind,
                cls._text(artifact.identifier, "identifier", required=True),
                cls._text(artifact.title, "title", required=True),
            )
            identity = (sanitized.kind, sanitized.identifier)
            if identity in seen:
                continue
            seen.add(identity)
            if per_kind[sanitized.kind] >= MAX_WORKSPACE_SEARCH_ENTRIES_PER_KIND:
                truncated = True
                continue
            per_kind[sanitized.kind] += 1
            indexed.append(sanitized)
        indexed.sort(
            key=lambda artifact: (
                _KIND_ORDER[artifact.kind],
                artifact.title.casefold(),
                artifact.identifier,
            )
        )
        return tuple(indexed), len(seen), truncated

    @classmethod
    def _metadata(
        cls,
        state_manager: StateManager,
    ) -> dict[tuple[WorkspaceArtifactKind, str], dict[str, Any]]:
        return cls._records(state_manager.get_config().get(_CONFIG_KEY))

    @classmethod
    def _write_workspace_metadata(
        cls,
        state_manager: StateManager,
        metadata: Mapping[tuple[WorkspaceArtifactKind, str], Mapping[str, Any]],
    ) -> None:
        state_manager.update_config(_CONFIG_KEY, cls._records_payload(metadata))

    @classmethod
    def _portfolio_metadata(
        cls,
    ) -> dict[tuple[WorkspaceArtifactKind, str], dict[str, Any]]:
        with cls._portfolio_lock:
            path = cls._portfolio_metadata_path()
            if not path.exists():
                return {}
            if path.is_symlink():
                raise ValueError("Workspace portfolio metadata must not be a symbolic link.")
            if path.stat().st_size > MAX_WORKSPACE_METADATA_FILE_BYTES:
                raise ValueError(
                    "Workspace portfolio metadata exceeds the safe local file-size limit."
                )
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError(f"Workspace portfolio metadata is unreadable: {exc}") from exc
            if not isinstance(payload, dict) or payload.get("schema_version") != 1:
                raise ValueError("Workspace portfolio metadata has an unsupported format.")
            return {
                identity: record
                for identity, record in cls._records(payload.get("entries")).items()
                if identity[0] == "portfolio"
            }

    @classmethod
    def _write_portfolio_metadata(
        cls,
        metadata: Mapping[tuple[WorkspaceArtifactKind, str], Mapping[str, Any]],
    ) -> None:
        with cls._portfolio_lock:
            path = cls._portfolio_metadata_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(
                {
                    "schema_version": _PORTFOLIO_METADATA_VERSION,
                    "entries": cls._records_payload(metadata),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            if len(payload) > MAX_WORKSPACE_METADATA_FILE_BYTES:
                raise ValueError(
                    "Workspace portfolio metadata exceeds the safe local file-size limit."
                )
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".workspace-metadata-",
                dir=path.parent,
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _portfolio_metadata_path() -> Path:
        return PathService.get_portfolios_dir() / _PORTFOLIO_METADATA_FILE

    @classmethod
    def _records(
        cls,
        payload: object,
    ) -> dict[tuple[WorkspaceArtifactKind, str], dict[str, Any]]:
        if not isinstance(payload, list):
            return {}
        records: dict[tuple[WorkspaceArtifactKind, str], dict[str, Any]] = {}
        for item in payload[:MAX_WORKSPACE_METADATA_ENTRIES]:
            if not isinstance(item, dict):
                continue
            try:
                kind = cast(WorkspaceArtifactKind, cls._kind(item.get("kind")))
                identifier = cls._text(item.get("identifier"), "identifier", required=True)
                tags = cls._tags(item.get("tags", ()))
                favorite = item.get("favorite", False)
                if not isinstance(favorite, bool):
                    continue
            except (TypeError, ValueError):
                continue
            if tags or favorite:
                records[(kind, identifier)] = {
                    "tags": list(tags),
                    "favorite": favorite,
                }
        return records

    @staticmethod
    def _records_payload(
        metadata: Mapping[tuple[WorkspaceArtifactKind, str], Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "kind": kind,
                "identifier": identifier,
                "tags": list(record.get("tags", ())),
                "favorite": bool(record.get("favorite", False)),
            }
            for (kind, identifier), record in sorted(
                metadata.items(), key=lambda item: (_KIND_ORDER[item[0][0]], item[0][1])
            )
        ]

    @staticmethod
    def _enrich(
        artifact: WorkspaceArtifact,
        record: Mapping[str, Any] | None,
    ) -> WorkspaceArtifact:
        if record is None:
            return artifact
        return WorkspaceArtifact(
            kind=artifact.kind,
            identifier=artifact.identifier,
            title=artifact.title,
            tags=tuple(record.get("tags", ())),
            favorite=bool(record.get("favorite", False)),
        )

    @staticmethod
    def _kind(value: object, *, optional: bool = False) -> WorkspaceArtifactKind | None:
        if optional and value is None:
            return None
        if not isinstance(value, str) or value not in _KINDS:
            choices = ", ".join(_KINDS)
            raise ValueError(f"Workspace artifact kind must be one of: {choices}.")
        return value

    @classmethod
    def _tags(cls, tags: object) -> tuple[str, ...]:
        if isinstance(tags, (str, bytes, bytearray)) or not isinstance(tags, Sequence):
            raise TypeError("Workspace tags must be a sequence of tag strings.")
        if len(tags) > MAX_WORKSPACE_TAGS_PER_ARTIFACT:
            raise ValueError(f"An artifact accepts at most {MAX_WORKSPACE_TAGS_PER_ARTIFACT} tags.")
        canonical: list[str] = []
        for tag in tags:
            normalized = cls._normalize_tag(tag)
            if normalized not in canonical:
                canonical.append(normalized)
        return tuple(canonical)

    @staticmethod
    def _normalize_tag(tag: object) -> str:
        if not isinstance(tag, str):
            raise TypeError("Every workspace tag must be text.")
        normalized = " ".join(unicodedata.normalize("NFKC", tag).casefold().split())
        if not normalized:
            raise ValueError("Workspace tags must not be empty.")
        if len(normalized) > MAX_WORKSPACE_TAG_LENGTH:
            raise ValueError(
                f"Workspace tags are limited to {MAX_WORKSPACE_TAG_LENGTH} characters."
            )
        if (
            normalized[0] in _TAG_SEPARATORS
            or normalized[-1] in _TAG_SEPARATORS
            or any(
                character != "_" and not character.isalnum() and character not in _TAG_SEPARATORS
                for character in normalized
            )
            or any(
                left in _TAG_SEPARATORS and right in _TAG_SEPARATORS
                for left, right in zip(normalized, normalized[1:], strict=False)
            )
        ):
            raise ValueError(
                "Workspace tags may contain letters, numbers, spaces, underscores, and hyphens."
            )
        return normalized

    @staticmethod
    def _text(value: object, field: str, *, required: bool = False) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Workspace artifact {field} must be text.")
        stripped = value.strip()
        if required and not stripped:
            raise ValueError(f"Workspace artifact {field} must not be empty.")
        if len(stripped) > MAX_WORKSPACE_SEARCH_FIELD_LENGTH:
            raise ValueError(
                f"Workspace artifact {field} exceeds "
                f"{MAX_WORKSPACE_SEARCH_FIELD_LENGTH} characters."
            )
        if any(ord(character) < 32 for character in stripped):
            raise ValueError(f"Workspace artifact {field} contains control characters.")
        return stripped

    @staticmethod
    def _limit(limit: int) -> int:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_WORKSPACE_SEARCH_RESULTS
        ):
            raise ValueError(
                f"Workspace artifact limit must be from 1 through {MAX_WORKSPACE_SEARCH_RESULTS}."
            )
        return limit
