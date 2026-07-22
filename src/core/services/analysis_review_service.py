"""Validated append-only review conversations stored in portable state."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, cast

from src.core.common.security_limits import (
    MAX_ANALYSIS_REVIEW_AUTHOR_LENGTH,
    MAX_ANALYSIS_REVIEW_COMMENT_LENGTH,
    MAX_ANALYSIS_REVIEW_DOCUMENT_BYTES,
    MAX_ANALYSIS_REVIEW_EVENTS,
    MAX_ANALYSIS_REVIEW_EVENTS_PER_THREAD,
    MAX_ANALYSIS_REVIEW_THREADS,
    MAX_WORKSPACE_SEARCH_FIELD_LENGTH,
    MAX_WORKSPACE_SEARCH_RESULTS,
)
from src.core.models.analysis_review_models import (
    AnalysisReviewEvent,
    AnalysisReviewResponse,
    AnalysisReviewStatus,
    AnalysisReviewTarget,
    AnalysisReviewTargetKind,
    AnalysisReviewTargetResponse,
    AnalysisReviewThread,
)
from src.core.state.state_manager import StateManager

ANALYSIS_REVIEWS_CONFIG_KEY = "_analysis_review_threads"
_STATUSES: tuple[AnalysisReviewStatus, ...] = (
    "not-reviewed",
    "in-review",
    "changes-requested",
    "approved",
)
_KINDS: tuple[AnalysisReviewTargetKind, ...] = ("plot", "portfolio_revision")
_REVISION_ID = re.compile(r"^[0-9a-f]{64}$")


class AnalysisReviewService:
    """Validate, retain, filter, and append portable analysis review events."""

    @classmethod
    def list_targets(
        cls,
        targets: Sequence[AnalysisReviewTarget],
        *,
        kind: AnalysisReviewTargetKind | None = None,
        limit: int = 100,
        available_targets: int | None = None,
        index_truncated: bool = False,
    ) -> AnalysisReviewTargetResponse:
        """Return unique available targets through bounded optional filtering."""
        resolved_kind = cls._kind(kind, optional=True)
        resolved_limit = cls._limit(limit)
        unique: dict[tuple[AnalysisReviewTargetKind, str, str], AnalysisReviewTarget] = {}
        for target in targets:
            validated = cls._target(target)
            unique.setdefault(validated.identity, validated)
        matching = tuple(
            sorted(
                (
                    target
                    for target in unique.values()
                    if resolved_kind is None or target.kind == resolved_kind
                ),
                key=lambda target: (
                    0 if target.kind == "plot" else 1,
                    target.title.casefold(),
                    target.identity,
                ),
            )
        )
        return AnalysisReviewTargetResponse(
            targets=matching[:resolved_limit],
            total_targets=len(matching),
            returned_targets=min(len(matching), resolved_limit),
            truncated=len(matching) > resolved_limit,
            available_targets=(len(unique) if available_targets is None else available_targets),
            indexed_targets=len(unique),
            index_truncated=index_truncated,
        )

    @classmethod
    def list_reviews(
        cls,
        state_manager: StateManager,
        targets: Sequence[AnalysisReviewTarget],
        *,
        kind: AnalysisReviewTargetKind | None = None,
        status: AnalysisReviewStatus | None = None,
        limit: int = 100,
    ) -> AnalysisReviewResponse:
        """Return portable threads, retaining unavailable imported references."""
        # [impl->req~ring5.workspace.collaborative-review~1]
        resolved_kind = cls._kind(kind, optional=True)
        resolved_status = cls._status(status, optional=True)
        resolved_limit = cls._limit(limit)
        available = {cls._target(target).identity for target in targets}
        threads = tuple(
            cls._availability(thread, thread.identity in available)
            for thread in cls._threads(state_manager)
            if (resolved_kind is None or thread.kind == resolved_kind)
            and (resolved_status is None or thread.status == resolved_status)
        )
        ordered = tuple(
            sorted(
                threads,
                key=lambda thread: (
                    thread.events[-1].created_at,
                    thread.identity,
                ),
                reverse=True,
            )
        )
        return AnalysisReviewResponse(
            threads=ordered[:resolved_limit],
            total_threads=len(ordered),
            returned_threads=min(len(ordered), resolved_limit),
            truncated=len(ordered) > resolved_limit,
            status_counts=tuple(
                (candidate, sum(thread.status == candidate for thread in threads))
                for candidate in _STATUSES
            ),
        )

    @classmethod
    def record(
        cls,
        state_manager: StateManager,
        targets: Sequence[AnalysisReviewTarget],
        kind: AnalysisReviewTargetKind,
        identifier: str,
        *,
        author_id: str,
        comment: str = "",
        status: AnalysisReviewStatus | None = None,
        portfolio_name: str | None = None,
    ) -> AnalysisReviewThread:
        """Append one authored review event to an available exact target."""
        # [impl->req~ring5.workspace.collaborative-review~1]
        identity = (
            cast(AnalysisReviewTargetKind, cls._kind(kind)),
            cls._portfolio_name(kind, portfolio_name),
            cls._identifier(kind, identifier),
        )
        discovered: dict[tuple[AnalysisReviewTargetKind, str, str], AnalysisReviewTarget] = {}
        for candidate in targets:
            validated = cls._target(candidate)
            discovered[validated.identity] = validated
        target = discovered.get(identity)
        if target is None:
            raise KeyError("The selected analysis review target is not currently available.")
        author = cls._author(author_id)
        body = cls._comment(comment)
        threads = list(cls._threads(state_manager))
        existing_index = next(
            (index for index, thread in enumerate(threads) if thread.identity == identity),
            None,
        )
        previous = threads[existing_index] if existing_index is not None else None
        resolved_status: AnalysisReviewStatus = cls._status(status, optional=True) or (
            previous.status if previous is not None else "not-reviewed"
        )
        if not body and previous is not None and resolved_status == previous.status:
            raise ValueError("Add a comment or choose a different review status.")
        if not body and previous is None and resolved_status == "not-reviewed":
            raise ValueError("Add a comment or choose a review status.")
        if previous is None and len(threads) >= MAX_ANALYSIS_REVIEW_THREADS:
            raise ValueError(
                f"Portable analysis reviews are limited to {MAX_ANALYSIS_REVIEW_THREADS:,} threads."
            )
        previous_events = previous.events if previous is not None else ()
        if len(previous_events) >= MAX_ANALYSIS_REVIEW_EVENTS_PER_THREAD:
            raise ValueError(
                "This analysis review thread reached its portable event limit of "
                f"{MAX_ANALYSIS_REVIEW_EVENTS_PER_THREAD:,}."
            )
        if sum(len(thread.events) for thread in threads) >= MAX_ANALYSIS_REVIEW_EVENTS:
            raise ValueError(
                f"Portable analysis reviews are limited to {MAX_ANALYSIS_REVIEW_EVENTS:,} events."
            )
        created_at = datetime.now(timezone.utc).isoformat()
        event_id = hashlib.sha256(
            json.dumps(
                [*identity, author, created_at, len(previous_events), body, resolved_status],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        event = AnalysisReviewEvent(
            event_id=event_id,
            author_id=author,
            created_at=created_at,
            status=resolved_status,
            comment=body,
        )
        updated = AnalysisReviewThread(
            kind=target.kind,
            identifier=target.identifier,
            title=target.title,
            portfolio_name=target.portfolio_name,
            status=resolved_status,
            events=(*previous_events, event),
        )
        if existing_index is None:
            threads.append(updated)
        else:
            threads[existing_index] = updated
        cls._write(state_manager, tuple(threads))
        return updated

    @classmethod
    def _threads(cls, state_manager: StateManager) -> tuple[AnalysisReviewThread, ...]:
        payload = state_manager.get_config().get(ANALYSIS_REVIEWS_CONFIG_KEY, [])
        if not isinstance(payload, list):
            raise ValueError("Portable analysis reviews must be stored as a list.")
        try:
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Portable analysis reviews must contain JSON-compatible data."
            ) from exc
        if len(encoded) > MAX_ANALYSIS_REVIEW_DOCUMENT_BYTES:
            raise ValueError("Portable analysis review document size limit was exceeded.")
        if len(payload) > MAX_ANALYSIS_REVIEW_THREADS:
            raise ValueError("Portable analysis review thread limit was exceeded.")
        threads: list[AnalysisReviewThread] = []
        identities: set[tuple[AnalysisReviewTargetKind, str, str]] = set()
        event_count = 0
        for raw in payload:
            thread = cls._parse_thread(raw)
            if thread.identity in identities:
                raise ValueError("Portable analysis reviews contain a duplicate target thread.")
            identities.add(thread.identity)
            event_count += len(thread.events)
            if event_count > MAX_ANALYSIS_REVIEW_EVENTS:
                raise ValueError("Portable analysis review event limit was exceeded.")
            threads.append(thread)
        return tuple(threads)

    @classmethod
    def _parse_thread(cls, raw: object) -> AnalysisReviewThread:
        if not isinstance(raw, Mapping):
            raise ValueError("Every portable analysis review thread must be an object.")
        kind = cast(AnalysisReviewTargetKind, cls._kind(raw.get("kind")))
        identifier = cls._identifier(kind, raw.get("identifier"))
        title = cls._text(raw.get("title"), "target title")
        portfolio_name = cls._portfolio_name(kind, raw.get("portfolio_name")) or None
        events_raw = raw.get("events")
        if not isinstance(events_raw, list) or not events_raw:
            raise ValueError("Every portable analysis review thread needs at least one event.")
        if len(events_raw) > MAX_ANALYSIS_REVIEW_EVENTS_PER_THREAD:
            raise ValueError("Portable analysis review thread event limit was exceeded.")
        events = tuple(cls._parse_event(event) for event in events_raw)
        if len({event.event_id for event in events}) != len(events):
            raise ValueError("Portable analysis review event IDs must be unique within a thread.")
        for index, event in enumerate(events):
            previous_status = events[index - 1].status if index else "not-reviewed"
            if not event.comment and event.status == previous_status:
                raise ValueError(
                    "Portable analysis review events must add a comment or change status."
                )
        status = cast(AnalysisReviewStatus, cls._status(raw.get("status")))
        if events[-1].status != status:
            raise ValueError("Portable analysis review status must match its latest event.")
        return AnalysisReviewThread(
            kind=kind,
            identifier=identifier,
            title=title,
            portfolio_name=portfolio_name,
            status=status,
            events=events,
        )

    @classmethod
    def _parse_event(cls, raw: object) -> AnalysisReviewEvent:
        if not isinstance(raw, Mapping):
            raise ValueError("Every portable analysis review event must be an object.")
        event_id = raw.get("event_id")
        if (
            not isinstance(event_id, str)
            or len(event_id) != 64
            or any(character not in "0123456789abcdef" for character in event_id)
        ):
            raise ValueError("Portable analysis review event IDs must be SHA-256 values.")
        created_at = cls._timestamp(raw.get("created_at"))
        return AnalysisReviewEvent(
            event_id=event_id,
            author_id=cls._author(raw.get("author_id")),
            created_at=created_at,
            status=cast(AnalysisReviewStatus, cls._status(raw.get("status"))),
            comment=cls._comment(raw.get("comment", "")),
        )

    @classmethod
    def _write(
        cls,
        state_manager: StateManager,
        threads: Sequence[AnalysisReviewThread],
    ) -> None:
        payload = [cls._thread_payload(thread) for thread in threads]
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_ANALYSIS_REVIEW_DOCUMENT_BYTES:
            raise ValueError(
                "Portable analysis reviews exceed the "
                f"{MAX_ANALYSIS_REVIEW_DOCUMENT_BYTES:,}-byte safety limit."
            )
        state_manager.update_config(ANALYSIS_REVIEWS_CONFIG_KEY, payload)

    @staticmethod
    def _thread_payload(thread: AnalysisReviewThread) -> dict[str, Any]:
        return {
            "kind": thread.kind,
            "identifier": thread.identifier,
            "title": thread.title,
            "portfolio_name": thread.portfolio_name,
            "status": thread.status,
            "events": [
                {
                    "event_id": event.event_id,
                    "author_id": event.author_id,
                    "created_at": event.created_at,
                    "status": event.status,
                    "comment": event.comment,
                }
                for event in thread.events
            ],
        }

    @staticmethod
    def _availability(thread: AnalysisReviewThread, available: bool) -> AnalysisReviewThread:
        return AnalysisReviewThread(
            kind=thread.kind,
            identifier=thread.identifier,
            title=thread.title,
            portfolio_name=thread.portfolio_name,
            status=thread.status,
            events=thread.events,
            available=available,
        )

    @classmethod
    def _target(cls, target: object) -> AnalysisReviewTarget:
        if not isinstance(target, AnalysisReviewTarget):
            raise TypeError("Analysis review targets must be AnalysisReviewTarget instances.")
        kind = cast(AnalysisReviewTargetKind, cls._kind(target.kind))
        return AnalysisReviewTarget(
            kind=kind,
            identifier=cls._identifier(kind, target.identifier),
            title=cls._text(target.title, "target title"),
            portfolio_name=cls._portfolio_name(kind, target.portfolio_name) or None,
        )

    @staticmethod
    def _kind(value: object, *, optional: bool = False) -> AnalysisReviewTargetKind | None:
        if optional and value is None:
            return None
        if not isinstance(value, str) or value not in _KINDS:
            raise ValueError("Analysis review target kind must be plot or portfolio_revision.")
        return value

    @staticmethod
    def _status(value: object, *, optional: bool = False) -> AnalysisReviewStatus | None:
        if optional and value is None:
            return None
        if not isinstance(value, str) or value not in _STATUSES:
            raise ValueError("Analysis review status is not supported.")
        return value

    @classmethod
    def _portfolio_name(cls, kind: object, value: object) -> str:
        if kind == "plot":
            if value not in (None, ""):
                raise ValueError("Plot review targets must not specify a portfolio name.")
            return ""
        name = cls._text(value, "portfolio name")
        if len(name) > 120:
            raise ValueError("Analysis review portfolio names cannot exceed 120 characters.")
        return name

    @classmethod
    def _identifier(cls, kind: object, value: object) -> str:
        identifier = cls._text(value, "target identifier")
        if kind == "plot":
            if not identifier.isdigit():
                raise ValueError("Analysis review plot identifiers must be non-negative integers.")
        elif not _REVISION_ID.fullmatch(identifier):
            raise ValueError(
                "Analysis review portfolio revision IDs must be 64 lowercase "
                "hexadecimal characters."
            )
        return identifier

    @staticmethod
    def _text(value: object, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Analysis review {field} must be non-empty text.")
        text = value.strip()
        if len(text) > MAX_WORKSPACE_SEARCH_FIELD_LENGTH:
            raise ValueError(f"Analysis review {field} is too long.")
        if any(ord(character) < 32 for character in text):
            raise ValueError(f"Analysis review {field} contains control characters.")
        return text

    @staticmethod
    def _author(value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Analysis review author ID must be non-empty text.")
        author = value.strip()
        if len(author) > MAX_ANALYSIS_REVIEW_AUTHOR_LENGTH:
            raise ValueError(
                f"Analysis review author IDs are limited to "
                f"{MAX_ANALYSIS_REVIEW_AUTHOR_LENGTH} characters."
            )
        if any(ord(character) < 32 for character in author):
            raise ValueError("Analysis review author ID contains control characters.")
        return author

    @staticmethod
    def _comment(value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("Analysis review comments must be text.")
        comment = value.strip()
        if len(comment) > MAX_ANALYSIS_REVIEW_COMMENT_LENGTH:
            raise ValueError(
                f"Analysis review comments are limited to "
                f"{MAX_ANALYSIS_REVIEW_COMMENT_LENGTH:,} characters."
            )
        if any(ord(character) == 0 for character in comment):
            raise ValueError("Analysis review comments must not contain null characters.")
        return comment

    @staticmethod
    def _timestamp(value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Analysis review timestamps must be ISO 8601 text.")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Analysis review timestamps must be valid ISO 8601 values.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Analysis review timestamps must include a timezone.")
        return parsed.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _limit(limit: int) -> int:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_WORKSPACE_SEARCH_RESULTS
        ):
            raise ValueError(
                f"Analysis review limit must be from 1 through {MAX_WORKSPACE_SEARCH_RESULTS}."
            )
        return limit
