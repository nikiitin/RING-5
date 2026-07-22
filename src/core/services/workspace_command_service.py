"""Bounded deterministic search over the canonical workspace commands."""

from __future__ import annotations

import re
import unicodedata

from src.core.common.security_limits import (
    MAX_WORKSPACE_SEARCH_QUERY_LENGTH,
    MAX_WORKSPACE_SEARCH_RESULTS,
)
from src.core.models.workspace_command_models import (
    WorkspaceCommand,
    WorkspaceCommandSearchResponse,
)
from src.core.services.workspace_command_catalog import WORKSPACE_COMMANDS

_TOKEN = re.compile(r"\w+", re.UNICODE)


class WorkspaceCommandService:
    """Validate, filter, and rank the intentionally small safe command set."""

    @classmethod
    def search_commands(
        cls,
        query: str = "",
        *,
        limit: int = 20,
    ) -> WorkspaceCommandSearchResponse:
        """Return all commands or deterministic AND-matched command results."""
        # [impl->req~ring5.workspace.command-palette~1]
        resolved_query, terms = cls._query(query)
        resolved_limit = cls._limit(limit)
        ranked: list[tuple[int, int, WorkspaceCommand]] = []
        for order, command in enumerate(WORKSPACE_COMMANDS):
            title = cls._normalize(command.title)
            description = cls._normalize(command.description)
            keywords = cls._normalize(" ".join(command.keywords))
            searchable = " ".join(
                (
                    title,
                    description,
                    keywords,
                    cls._normalize(command.category),
                    cls._normalize(command.destination),
                )
            )
            if terms and not all(term in searchable for term in terms):
                continue
            score = cls._score(resolved_query, terms, title, description, keywords)
            ranked.append((-score, order, command))
        ranked.sort(key=lambda match: (match[0], match[1]))
        total = len(ranked)
        commands = tuple(command for _, _, command in ranked[:resolved_limit])
        return WorkspaceCommandSearchResponse(
            query=resolved_query,
            commands=commands,
            total_matches=total,
            returned_matches=len(commands),
            results_truncated=total > resolved_limit,
        )

    @staticmethod
    def _score(
        query: str,
        terms: tuple[str, ...],
        title: str,
        description: str,
        keywords: str,
    ) -> int:
        if not terms:
            return 0
        score = 0
        if title == query:
            score += 10_000
        elif title.startswith(query):
            score += 5_000
        elif query in title:
            score += 3_000
        title_tokens = set(_TOKEN.findall(title))
        for term in terms:
            if term in title_tokens:
                score += 500
            elif any(token.startswith(term) for token in title_tokens):
                score += 300
            elif term in title:
                score += 200
            elif term in keywords:
                score += 75
            elif term in description:
                score += 50
        return score

    @staticmethod
    def _query(query: str) -> tuple[str, tuple[str, ...]]:
        if not isinstance(query, str):
            raise TypeError("Workspace command query must be text.")
        if len(query) > MAX_WORKSPACE_SEARCH_QUERY_LENGTH:
            raise ValueError(
                f"Workspace command query exceeds {MAX_WORKSPACE_SEARCH_QUERY_LENGTH} characters."
            )
        if any(ord(character) < 32 and character not in "\t\n\r" for character in query):
            raise ValueError("Workspace command query contains unsupported control characters.")
        normalized = WorkspaceCommandService._normalize(query)
        return normalized, tuple(dict.fromkeys(_TOKEN.findall(normalized)))

    @staticmethod
    def _limit(limit: int) -> int:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= MAX_WORKSPACE_SEARCH_RESULTS
        ):
            raise ValueError(
                f"Workspace command limit must be from 1 through {MAX_WORKSPACE_SEARCH_RESULTS}."
            )
        return limit

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).casefold()
        return " ".join(normalized.split())
