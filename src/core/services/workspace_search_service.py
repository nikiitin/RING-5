"""Bounded inverted index over the complete interactive workspace."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from src.core.common.security_limits import (
    MAX_WORKSPACE_SEARCH_ENTRIES_PER_KIND,
    MAX_WORKSPACE_SEARCH_FIELD_LENGTH,
    MAX_WORKSPACE_SEARCH_QUERY_LENGTH,
    MAX_WORKSPACE_SEARCH_RESULTS,
)
from src.core.models.workspace_search_models import (
    WorkspaceSearchEntry,
    WorkspaceSearchKind,
    WorkspaceSearchResponse,
    WorkspaceSearchResult,
)
from src.core.services.workspace_search_catalog import (
    WORKSPACE_COMMANDS,
    WORKSPACE_DOCUMENTATION,
)
from src.core.state.state_manager import StateManager

_TOKEN = re.compile(r"\w+", re.UNICODE)
_KIND_ORDER: dict[WorkspaceSearchKind, int] = {
    "command": 0,
    "variable": 1,
    "dataset": 2,
    "plot": 3,
    "pipeline": 4,
    "portfolio": 5,
    "documentation": 6,
}


@dataclass(frozen=True, slots=True)
class _IndexedEntry:
    entry: WorkspaceSearchEntry
    title: str
    description: str
    keywords: str
    combined: str
    tokens: frozenset[str]


class WorkspaceSearchService:
    """Collect and rank stable workspace documents without mutating state."""

    @classmethod
    def search_workspace(
        cls,
        state_manager: StateManager,
        portfolio_names: Sequence[str],
        query: str,
        *,
        limit: int = 20,
    ) -> WorkspaceSearchResponse:
        """Search every supported workspace source through one bounded index."""
        # [impl->req~ring5.workspace.global-search~1]
        entries = cls._workspace_entries(state_manager, portfolio_names)
        return cls.search(entries, query, limit=limit)

    @classmethod
    def search(
        cls,
        entries: Sequence[WorkspaceSearchEntry],
        query: str,
        *,
        limit: int = 20,
    ) -> WorkspaceSearchResponse:
        """Build a bounded inverted index and return deterministic ranked matches."""
        resolved_query, terms = cls._query(query)
        resolved_limit = cls._limit(limit)
        indexed, postings, index_truncated = cls._index(entries)
        if not terms:
            return WorkspaceSearchResponse(
                query=resolved_query,
                results=(),
                total_matches=0,
                returned_matches=0,
                results_truncated=False,
                available_entries=len(entries),
                indexed_entries=len(indexed),
                index_truncated=index_truncated,
            )

        candidates: set[int] | None = None
        for term in terms:
            matching = set().union(
                *(identifiers for token, identifiers in postings.items() if term in token)
            )
            candidates = matching if candidates is None else candidates & matching
            if not candidates:
                break

        ranked: list[WorkspaceSearchResult] = []
        for index in candidates or ():
            document = indexed[index]
            if not all(term in document.combined for term in terms):
                continue
            ranked.append(cls._result(document, resolved_query, terms))
        ranked.sort(
            key=lambda result: (
                -result.score,
                _KIND_ORDER[result.kind],
                cls._normalize(result.title),
                result.location,
                result.identifier,
            )
        )
        total = len(ranked)
        results = tuple(ranked[:resolved_limit])
        return WorkspaceSearchResponse(
            query=resolved_query,
            results=results,
            total_matches=total,
            returned_matches=len(results),
            results_truncated=total > resolved_limit,
            available_entries=len(entries),
            indexed_entries=len(indexed),
            index_truncated=index_truncated,
        )

    @classmethod
    def _workspace_entries(
        cls,
        state_manager: StateManager,
        portfolio_names: Sequence[str],
    ) -> tuple[WorkspaceSearchEntry, ...]:
        entries: list[WorkspaceSearchEntry] = [*WORKSPACE_COMMANDS, *WORKSPACE_DOCUMENTATION]
        entries.extend(cls._variable_entries(state_manager))
        entries.extend(cls._dataset_entries(state_manager))
        entries.extend(cls._plot_entries(state_manager))
        entries.extend(cls._portfolio_entries(portfolio_names))
        return tuple(entries)

    @classmethod
    def _variable_entries(cls, state_manager: StateManager) -> tuple[WorkspaceSearchEntry, ...]:
        variables: dict[str, dict[str, Any]] = {}
        for configured_variable in state_manager.get_parse_variables():
            name = configured_variable.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            record = variables.setdefault(name.strip(), {"configured": False, "keywords": []})
            record["configured"] = True
            record["keywords"].extend(
                (configured_variable.get("type", ""), configured_variable.get("alias", ""))
            )
        for scanned_variable in state_manager.get_scanned_variables():
            name = scanned_variable.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            record = variables.setdefault(name.strip(), {"configured": False, "keywords": []})
            record["scanned"] = True
            record["keywords"].append(scanned_variable.get("type", ""))
            entries = scanned_variable.get("entries", [])
            if isinstance(entries, list):
                record["keywords"].extend(entries[:32])
        return tuple(
            WorkspaceSearchEntry(
                kind="variable",
                title=name,
                description=(
                    "Configured and scanned variable"
                    if record.get("configured") and record.get("scanned")
                    else (
                        "Configured parser variable"
                        if record.get("configured")
                        else "Scanned variable"
                    )
                ),
                location="Data Source",
                identifier=name,
                keywords=tuple(str(value) for value in record["keywords"] if value),
            )
            for name, record in variables.items()
        )

    @staticmethod
    def _dataset_entries(state_manager: StateManager) -> tuple[WorkspaceSearchEntry, ...]:
        return tuple(
            WorkspaceSearchEntry(
                kind="dataset",
                title=info.name,
                description=(
                    f"{info.row_count:,} rows × {info.column_count:,} columns"
                    + (" · active" if info.selected else "")
                ),
                location="Data Managers",
                identifier=info.name,
                keywords=("active",) if info.selected else (),
            )
            for info in state_manager.list_datasets()
        )

    @classmethod
    def _plot_entries(cls, state_manager: StateManager) -> tuple[WorkspaceSearchEntry, ...]:
        entries: list[WorkspaceSearchEntry] = []
        for plot in state_manager.get_plots():
            plot_id = str(plot.plot_id)
            entries.append(
                WorkspaceSearchEntry(
                    kind="plot",
                    title=plot.name,
                    description=f"{plot.plot_type.replace('_', ' ').title()} plot",
                    location="Manage Plots",
                    identifier=plot_id,
                    keywords=(plot.plot_type, *cls._flatten_keywords(plot.config)),
                )
            )
            for index, step in enumerate(plot.pipeline):
                step_type = str(step.get("type", "Transformation"))
                step_title = step_type.replace("_", " ").title()
                step_id = step.get("id", index)
                entries.append(
                    WorkspaceSearchEntry(
                        kind="pipeline",
                        title=f"{plot.name} · step {index + 1}: {step_title}",
                        description=f"Pipeline step on {plot.name}",
                        location="Manage Plots",
                        identifier=f"{plot_id}:{step_id}",
                        keywords=(step_type, *cls._flatten_keywords(step.get("config", {}))),
                    )
                )
        return tuple(entries)

    @staticmethod
    def _portfolio_entries(portfolio_names: Sequence[str]) -> tuple[WorkspaceSearchEntry, ...]:
        return tuple(
            WorkspaceSearchEntry(
                kind="portfolio",
                title=name,
                description="Saved workspace portfolio",
                location="Save/Load Portfolio",
                identifier=name,
                keywords=("saved", "workspace", "restore"),
            )
            for name in portfolio_names
            if isinstance(name, str) and name.strip()
        )

    @classmethod
    def _index(
        cls,
        entries: Sequence[WorkspaceSearchEntry],
    ) -> tuple[tuple[_IndexedEntry, ...], dict[str, set[int]], bool]:
        indexed: list[_IndexedEntry] = []
        postings: dict[str, set[int]] = defaultdict(set)
        per_kind: dict[WorkspaceSearchKind, int] = defaultdict(int)
        truncated = False
        seen: set[tuple[WorkspaceSearchKind, str, str]] = set()
        for entry in entries:
            sanitized = cls._sanitize_entry(entry)
            identity = (sanitized.kind, sanitized.location, sanitized.identifier or sanitized.title)
            if identity in seen:
                continue
            seen.add(identity)
            if per_kind[sanitized.kind] >= MAX_WORKSPACE_SEARCH_ENTRIES_PER_KIND:
                truncated = True
                continue
            per_kind[sanitized.kind] += 1
            title = cls._normalize(sanitized.title)
            description = cls._normalize(sanitized.description)
            keywords = cls._normalize(" ".join(sanitized.keywords))
            combined = " ".join(
                (
                    title,
                    description,
                    keywords,
                    cls._normalize(sanitized.kind),
                    cls._normalize(sanitized.identifier),
                )
            )
            document = _IndexedEntry(
                sanitized,
                title,
                description,
                keywords,
                combined,
                frozenset(_TOKEN.findall(combined)),
            )
            identifier = len(indexed)
            indexed.append(document)
            for token in document.tokens:
                postings[token].add(identifier)
        return tuple(indexed), postings, truncated

    @classmethod
    def _result(
        cls,
        document: _IndexedEntry,
        query: str,
        terms: tuple[str, ...],
    ) -> WorkspaceSearchResult:
        score = 0
        if document.title == query:
            score += 10_000
        elif document.title.startswith(query):
            score += 5_000
        elif query in document.title:
            score += 3_000
        title_tokens = set(_TOKEN.findall(document.title))
        for term in terms:
            if term in title_tokens:
                score += 500
            elif any(token.startswith(term) for token in title_tokens):
                score += 300
            elif term in document.title:
                score += 200
            elif term in document.keywords:
                score += 75
            elif term in document.description:
                score += 50
            else:
                score += 20
        return WorkspaceSearchResult(
            kind=document.entry.kind,
            title=document.entry.title,
            description=document.entry.description,
            location=document.entry.location,
            identifier=document.entry.identifier,
            score=score,
            matched_terms=terms,
        )

    @classmethod
    def _sanitize_entry(cls, entry: WorkspaceSearchEntry) -> WorkspaceSearchEntry:
        if not isinstance(entry, WorkspaceSearchEntry):
            raise TypeError("Workspace search entries must be WorkspaceSearchEntry instances.")
        if entry.kind not in _KIND_ORDER:
            raise ValueError(f"Unsupported workspace search kind {entry.kind!r}.")
        title = cls._bounded_text(entry.title, "title", required=True)
        description = cls._bounded_text(entry.description, "description")
        location = cls._bounded_text(entry.location, "location", required=True)
        identifier = cls._bounded_text(entry.identifier, "identifier")
        keywords = tuple(
            cls._bounded_text(keyword, "keyword")
            for keyword in entry.keywords[:64]
            if isinstance(keyword, str) and keyword.strip()
        )
        return replace(
            entry,
            title=title,
            description=description,
            location=location,
            identifier=identifier,
            keywords=keywords,
        )

    @staticmethod
    def _query(query: str) -> tuple[str, tuple[str, ...]]:
        if not isinstance(query, str):
            raise TypeError("Workspace search query must be text.")
        if len(query) > MAX_WORKSPACE_SEARCH_QUERY_LENGTH:
            raise ValueError(
                f"Workspace search query exceeds {MAX_WORKSPACE_SEARCH_QUERY_LENGTH} characters."
            )
        if any(ord(character) < 32 and character not in "\t\n\r" for character in query):
            raise ValueError("Workspace search query contains unsupported control characters.")
        normalized = WorkspaceSearchService._normalize(query)
        terms = tuple(dict.fromkeys(_TOKEN.findall(normalized)))
        return normalized, terms

    @staticmethod
    def _limit(limit: int) -> int:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_WORKSPACE_SEARCH_RESULTS
        ):
            raise ValueError(
                f"Workspace search limit must be from 1 through {MAX_WORKSPACE_SEARCH_RESULTS}."
            )
        return limit

    @staticmethod
    def _bounded_text(value: str, field: str, *, required: bool = False) -> str:
        if not isinstance(value, str):
            raise TypeError(f"Workspace search {field} must be text.")
        stripped = value.strip()
        if required and not stripped:
            raise ValueError(f"Workspace search {field} must not be empty.")
        return stripped[:MAX_WORKSPACE_SEARCH_FIELD_LENGTH]

    @classmethod
    def _flatten_keywords(cls, value: Any, *, depth: int = 0) -> tuple[str, ...]:
        if depth >= 3:
            return ()
        if isinstance(value, Mapping):
            flattened: list[str] = []
            for key in sorted(value, key=str)[:32]:
                flattened.append(str(key))
                flattened.extend(cls._flatten_keywords(value[key], depth=depth + 1))
                if len(flattened) >= 64:
                    break
            return tuple(flattened[:64])
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            flattened = []
            for item in value[:32]:
                flattened.extend(cls._flatten_keywords(item, depth=depth + 1))
                if len(flattened) >= 64:
                    break
            return tuple(flattened[:64])
        if value is None:
            return ()
        return (str(value)[:MAX_WORKSPACE_SEARCH_FIELD_LENGTH],)

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).casefold()
        return " ".join(normalized.split())
