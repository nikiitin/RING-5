"""Human-first saved-version review for portfolios."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import PortfolioDiff, PortfolioRevisionInfo

_SECTION_LABELS = {
    "data_sources": "Data sources",
    "pipelines": "Pipelines",
    "plots": "Plots",
    "figure_settings": "Figure settings",
}


class PortfolioHistoryComponent:
    """Render retained portfolio versions and field-level differences."""

    @staticmethod
    def render(api: ApplicationAPI, portfolio_name: str) -> None:
        """Render history and comparison controls for one saved portfolio."""
        # [impl->req~ring5.portfolio.history-diff~1]
        st.markdown("#### Saved versions")
        st.caption(
            "Each successful save is retained. Compare setup changes without exposing "
            "the portfolio's embedded data rows."
        )
        try:
            revisions = api.data_services.list_portfolio_revisions(portfolio_name)
        except (OSError, TypeError, ValueError) as exc:
            st.error(f"Saved versions could not be read: {exc}")
            return
        if not revisions:
            st.info("No saved versions are available yet.")
            return

        st.dataframe(
            [PortfolioHistoryComponent._revision_row(revision) for revision in revisions],
            hide_index=True,
            width="stretch",
        )
        if len(revisions) < 2:
            st.info("Save this portfolio again to compare what changed.")
            return

        earlier_column, later_column = st.columns(2)
        with earlier_column:
            before = st.selectbox(
                "Earlier saved version",
                revisions,
                index=len(revisions) - 2,
                format_func=PortfolioHistoryComponent._revision_label,
                key=f"portfolio_history_before_{portfolio_name}",
            )
        with later_column:
            after = st.selectbox(
                "Later saved version",
                revisions,
                index=len(revisions) - 1,
                format_func=PortfolioHistoryComponent._revision_label,
                key=f"portfolio_history_after_{portfolio_name}",
            )
        if not st.button(
            "Compare saved versions",
            key=f"portfolio_history_compare_{portfolio_name}",
        ):
            return
        if before is None or after is None:
            st.error("Choose two saved versions to compare.")
            return
        try:
            difference = api.data_services.compare_portfolio_revisions(
                portfolio_name,
                before.revision_id,
                after.revision_id,
            )
        except (OSError, TypeError, ValueError) as exc:
            st.error(f"Saved versions could not be compared: {exc}")
            return
        PortfolioHistoryComponent._render_difference(difference)

    @staticmethod
    def _revision_row(revision: PortfolioRevisionInfo) -> dict[str, Any]:
        return {
            "Version": revision.sequence,
            "Saved": PortfolioHistoryComponent._display_date(revision.created_at),
            "Source": revision.source,
            "Plots": revision.plot_count,
            "Status": "Current" if revision.active else "Retained",
            "ID": revision.revision_id[:12],
        }

    @staticmethod
    def _revision_label(revision: PortfolioRevisionInfo) -> str:
        status = " · current" if revision.active else ""
        return (
            f"Version {revision.sequence} · "
            f"{PortfolioHistoryComponent._display_date(revision.created_at)}{status}"
        )

    @staticmethod
    def _display_date(value: str) -> str:
        return value.replace("T", " ").replace("Z", " UTC")[:19]

    @staticmethod
    def _render_difference(difference: PortfolioDiff) -> None:
        if difference.change_count == 0:
            st.success("These saved versions have the same tracked setup.")
            return
        counts = ", ".join(
            f"{_SECTION_LABELS[section]}: {count}"
            for section, count in difference.section_counts
            if count
        )
        st.success(f"Found {difference.change_count} setup change(s). {counts}.")
        st.dataframe(
            [
                {
                    "Area": _SECTION_LABELS[entry.section],
                    "Field": entry.path,
                    "Change": entry.change.title(),
                    "Earlier": PortfolioHistoryComponent._display_value(entry.before),
                    "Later": PortfolioHistoryComponent._display_value(entry.after),
                }
                for entry in difference.entries
            ],
            hide_index=True,
            width="stretch",
        )
        if difference.truncated:
            st.warning(
                "This comparison reached the safety limit. Narrow the changes or inspect "
                "the saved JSON for the remaining fields."
            )

    @staticmethod
    def _display_value(value: object) -> str:
        if value is None:
            return "—"
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, str):
            rendered = value
        else:
            try:
                rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
            except (TypeError, ValueError):
                rendered = str(value)
        return rendered if len(rendered) <= 200 else f"{rendered[:197]}…"
