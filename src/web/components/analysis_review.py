"""Human-first authored review timeline for portable analysis targets."""

from __future__ import annotations

import hashlib

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import (
    AnalysisReviewStatus,
    AnalysisReviewTarget,
    AnalysisReviewTargetKind,
    AnalysisReviewThread,
)

_STATUS_OPTIONS: tuple[AnalysisReviewStatus, ...] = (
    "not-reviewed",
    "in-review",
    "changes-requested",
    "approved",
)
_STATUS_LABELS = {
    "not-reviewed": "Not reviewed",
    "in-review": "In review",
    "changes-requested": "Changes requested",
    "approved": "Approved",
}


class AnalysisReviewComponent:
    """Let people review exact plots and saved portfolio versions."""

    @classmethod
    def render(cls, api: ApplicationAPI) -> None:
        """Render a portable append-only review conversation in the sidebar."""
        # [impl->req~ring5.workspace.collaborative-review~1]
        with st.expander("Analysis review", expanded=False):
            kind_label = st.selectbox(
                "Review target type",
                ("Plots", "Portfolio versions"),
                key="_analysis_review_target_kind",
            )
            kind: AnalysisReviewTargetKind = (
                "plot" if kind_label == "Plots" else "portfolio_revision"
            )
            try:
                target_response = api.list_analysis_review_targets(kind=kind, limit=100)
                review_response = api.list_analysis_reviews(kind=kind, limit=100)
            except (OSError, TypeError, ValueError) as exc:
                st.error(f"Analysis reviews are unavailable: {exc}")
                return

            cls._render_summary(review_response.status_counts)
            if target_response.index_truncated:
                st.warning(
                    f"Indexed {target_response.indexed_targets:,} of at least "
                    f"{target_response.available_targets:,} review targets."
                )
            elif target_response.truncated:
                st.caption(
                    f"Showing {target_response.returned_targets} of "
                    f"{target_response.total_targets} available review targets."
                )

            available = {target.identity: target for target in target_response.targets}
            threads = {thread.identity: thread for thread in review_response.threads}
            choices: list[AnalysisReviewTarget | AnalysisReviewThread] = []
            for identity, available_target in available.items():
                choices.append(threads.get(identity, available_target))
            choices.extend(
                thread for identity, thread in threads.items() if identity not in available
            )
            if not choices:
                st.info("Create a plot or save a portfolio before starting a review.")
                return
            choices.sort(key=lambda choice: cls._subject_label(choice).casefold())
            selected = st.selectbox(
                "Review subject",
                choices,
                format_func=cls._subject_label,
                key="_analysis_review_subject",
            )
            identity = selected.identity
            thread = threads.get(identity)
            target = available.get(identity)
            cls._render_timeline(thread)
            if target is None:
                st.warning(
                    "This retained review references a target that is not available locally. "
                    "Its history remains portable, but new updates are disabled."
                )
                return

            suffix = hashlib.sha256("\0".join(identity).encode("utf-8")).hexdigest()[:12]
            author_id = st.text_input(
                "Author ID",
                key=f"_analysis_review_author_{suffix}",
                placeholder="name@example.org",
                help="Use a stable identifier so collaborators know who made the update.",
            )
            current_status: AnalysisReviewStatus = (
                thread.status if thread is not None else "not-reviewed"
            )
            status = st.selectbox(
                "Review status",
                _STATUS_OPTIONS,
                index=_STATUS_OPTIONS.index(current_status),
                format_func=lambda value: _STATUS_LABELS[value],
                key=f"_analysis_review_status_{suffix}",
            )
            comment = st.text_area(
                "Review comment",
                key=f"_analysis_review_comment_{suffix}",
                max_chars=4_000,
                placeholder="What should collaborators know or change?",
            )
            if st.button(
                "Add review update",
                key=f"_analysis_review_add_{suffix}",
                use_container_width=True,
                type="primary",
            ):
                try:
                    api.record_analysis_review(
                        target.kind,
                        target.identifier,
                        author_id=author_id,
                        comment=comment,
                        status=status,
                        portfolio_name=target.portfolio_name,
                    )
                except (KeyError, OSError, TypeError, ValueError) as exc:
                    st.error(f"Could not add review update: {exc}")
                else:
                    st.success("Review update added to the portable analysis state.")
                    st.rerun()
            st.caption(
                "Save the workspace as a portfolio to include this review history in "
                "its integrity checks, retained revisions, and portable bundles."
            )

    @staticmethod
    def _render_summary(
        counts: tuple[tuple[AnalysisReviewStatus, int], ...],
    ) -> None:
        total = sum(count for _status, count in counts)
        if total == 0:
            st.caption("No review conversations yet.")
            return
        rendered = " · ".join(
            f"{_STATUS_LABELS[status]}: {count}" for status, count in counts if count
        )
        st.caption(f"{total} review thread(s) · {rendered}")

    @staticmethod
    def _render_timeline(thread: AnalysisReviewThread | None) -> None:
        if thread is None:
            st.info("No review updates for this subject yet.")
            return
        st.markdown(f"**Current status:** {_STATUS_LABELS[thread.status]}")
        for event in reversed(thread.events[-10:]):
            timestamp = event.created_at.replace("T", " ").replace("+00:00", " UTC")[:23]
            with st.container(border=True):
                st.caption(f"{event.author_id} · {timestamp} · {_STATUS_LABELS[event.status]}")
                if event.comment:
                    st.write(event.comment)
        if len(thread.events) > 10:
            st.caption(f"Showing the latest 10 of {len(thread.events)} review updates.")

    @staticmethod
    def _subject_label(subject: AnalysisReviewTarget | AnalysisReviewThread) -> str:
        kind = "Plot" if subject.kind == "plot" else "Portfolio version"
        unavailable = (
            " · unavailable locally" if getattr(subject, "available", True) is False else ""
        )
        status = (
            f" · {_STATUS_LABELS[subject.status]}"
            if isinstance(subject, AnalysisReviewThread)
            else ""
        )
        return f"{kind} · {subject.title}{status}{unavailable}"
