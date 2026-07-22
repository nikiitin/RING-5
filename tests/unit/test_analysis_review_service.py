"""Unit coverage for portable append-only analysis review conversations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.models import AnalysisReviewTarget
from src.core.services import analysis_review_service as review_module
from src.core.services.analysis_review_service import AnalysisReviewService


def _state() -> MagicMock:
    config: dict[str, object] = {}
    state = MagicMock()
    state.get_config.side_effect = lambda: dict(config)
    state.update_config.side_effect = lambda key, value: config.__setitem__(key, value)
    state._review_config = config
    return state


def _targets() -> tuple[AnalysisReviewTarget, ...]:
    return (
        AnalysisReviewTarget("plot", "7", "IPC plot"),
        AnalysisReviewTarget(
            "portfolio_revision",
            "a" * 64,
            "paper · version 1",
            portfolio_name="paper",
        ),
    )


def test_comments_authors_timestamps_and_status_changes_are_append_only() -> None:
    # [test->req~ring5.workspace.collaborative-review~1]
    state = _state()
    first = AnalysisReviewService.record(
        state,
        _targets(),
        "plot",
        "7",
        author_id="alice@example.org",
        comment="Check the confidence interval.",
        status="in-review",
    )
    updated = AnalysisReviewService.record(
        state,
        _targets(),
        "plot",
        "7",
        author_id="bob@example.org",
        status="approved",
    )

    assert first.status == "in-review"
    assert updated.status == "approved"
    assert [event.author_id for event in updated.events] == [
        "alice@example.org",
        "bob@example.org",
    ]
    assert updated.events[0].comment == "Check the confidence interval."
    assert updated.events[1].comment == ""
    assert all(event.created_at.endswith("+00:00") for event in updated.events)
    assert len({event.event_id for event in updated.events}) == 2


def test_review_targets_threads_filters_and_unavailable_references_are_honest() -> None:
    state = _state()
    AnalysisReviewService.record(
        state,
        _targets(),
        "portfolio_revision",
        "a" * 64,
        portfolio_name="paper",
        author_id="reviewer-1",
        comment="Re-run the parser.",
        status="changes-requested",
    )

    targets = AnalysisReviewService.list_targets(
        _targets(),
        kind="portfolio_revision",
        limit=1,
        available_targets=12,
        index_truncated=True,
    )
    filtered = AnalysisReviewService.list_reviews(
        state,
        (),
        kind="portfolio_revision",
        status="changes-requested",
    )

    assert targets.returned_targets == targets.total_targets == 1
    assert targets.available_targets == 12
    assert targets.index_truncated is True
    assert filtered.total_threads == 1
    assert filtered.threads[0].available is False
    assert dict(filtered.status_counts)["changes-requested"] == 1


@pytest.mark.parametrize(
    ("kind", "identifier", "portfolio_name", "author", "comment", "status", "message"),
    [
        ("plot", "99", None, "alice", "note", "in-review", "not currently available"),
        ("plot", "7", None, "", "note", "in-review", "author ID"),
        ("plot", "7", "paper", "alice", "note", "in-review", "must not specify"),
        ("plot", "7", None, "alice", "", None, "Add a comment"),
        ("plot", "7", None, "alice", "x" * 4_001, None, "4,000 characters"),
        ("plot", "7", None, "alice", "note", "done", "status is not supported"),
        (
            "portfolio_revision",
            "a" * 64,
            None,
            "alice",
            "note",
            "approved",
            "portfolio name",
        ),
    ],
)
def test_invalid_review_updates_are_rejected(
    kind: object,
    identifier: str,
    portfolio_name: object,
    author: str,
    comment: str,
    status: object,
    message: str,
) -> None:
    with pytest.raises((KeyError, TypeError, ValueError), match=message):
        AnalysisReviewService.record(
            _state(),
            _targets(),
            kind,  # type: ignore[arg-type]
            identifier,
            portfolio_name=portfolio_name,  # type: ignore[arg-type]
            author_id=author,
            comment=comment,
            status=status,  # type: ignore[arg-type]
        )


def test_corrupt_portable_documents_and_event_limits_are_rejected(monkeypatch) -> None:
    state = _state()
    AnalysisReviewService.record(
        state,
        _targets(),
        "plot",
        "7",
        author_id="alice",
        comment="first",
    )
    monkeypatch.setattr(review_module, "MAX_ANALYSIS_REVIEW_EVENTS_PER_THREAD", 1)

    with pytest.raises(ValueError, match="event limit"):
        AnalysisReviewService.record(
            state,
            _targets(),
            "plot",
            "7",
            author_id="alice",
            comment="second",
        )

    state._review_config["_analysis_review_threads"][0]["status"] = "approved"
    with pytest.raises(ValueError, match="latest event"):
        AnalysisReviewService.list_reviews(state, _targets())
