"""Offer the bundled tutorial without replacing existing analysis work."""

import logging

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.web.state.ui_state_manager import UIStateManager

logger = logging.getLogger(__name__)


def render_example_portfolio(api: ApplicationAPI) -> None:
    """Offer an explicit tutorial load only before analysis work begins."""
    # [impl->req~ring5.portfolio.bundled-example~1]
    if not api.can_load_example_portfolio():
        return

    with st.container(border=True):
        st.markdown("### Explore an example")
        st.write(
            "Try every plot type with synthetic tutorial data. "
            "No simulator files or network access are needed."
        )
        if not st.button(
            "Load example portfolio",
            key="example_portfolio.load",
            type="primary",
        ):
            return
        try:
            report = api.load_example_portfolio()
        except (OSError, KeyError, TypeError, ValueError) as error:
            logger.error("Example portfolio could not be loaded: %s", error)
            st.error(f"The example portfolio could not be loaded: {error}")
            return
        ui_state = UIStateManager()
        ui_state.cleanup_all()
        if not report.complete:
            issues = list(report.plots_skipped)
            if report.data_error:
                issues.insert(0, f"data: {report.data_error}")
            if report.parse_variables_skipped:
                issues.append(f"{report.parse_variables_skipped} parser variables were skipped")
            details = "; ".join(issue[:300] for issue in issues[:3])
            st.error(f"Example restoration is incomplete: {details}")
            st.caption(
                f"Restored {report.plots_restored} plots. "
                "Open Manage Plots to inspect the restored content."
            )
            return
        ui_state.nav.set_current_page("Manage Plots")
        st.toast("Example portfolio loaded. All values are synthetic tutorial data.")
        st.rerun(scope="app")
