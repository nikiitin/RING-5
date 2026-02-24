"""
Portfolio Management Page

Provides functionality to save and load complete analysis snapshots including
data, plots, and all configurations as portfolio files.
"""

import logging
from typing import Any, cast

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import PortfolioData  # noqa: F401 (re-exported)
from src.web.rendering.config_builder import ConfigSpecBuilder

logger: logging.Logger = logging.getLogger(__name__)


def _build_figure_spec(config: dict[str, Any], plot_type: str) -> dict[str, Any] | None:
    """Build a FigureConfig dict from plot config (injected into core layer)."""
    spec = ConfigSpecBuilder.from_config(config, plot_type)
    return spec.to_dict()


def _portfolio_fragment(api: ApplicationAPI) -> None:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Save Portfolio")
        st.markdown(
            "Save current data, all plots, and their configurations to a single portfolio file."
        )

        portfolio_name = st.text_input(
            "Portfolio Name", value="my_portfolio", key="portfolio_save_name"
        )

        if st.button("Save Portfolio", type="primary", width="stretch"):
            try:
                current_data = api.state_manager.get_data()
                api.data_services.save_portfolio(
                    name=portfolio_name,
                    data=current_data,
                    plots=api.state_manager.get_plots(),
                    config=api.state_manager.get_config(),
                    plot_counter=api.state_manager.get_plot_counter(),
                    csv_path=api.state_manager.get_csv_path(),
                    parse_variables=cast(list[str] | None, api.state_manager.get_parse_variables()),
                    figure_spec_enricher=_build_figure_spec,
                )
                st.toast(f"Portfolio saved: {portfolio_name}", icon="✅")
                st.rerun()
            except Exception as e:
                st.exception(e)
                logger.error(
                    "PORTFOLIO: Failed to save portfolio %r: %s",
                    str(portfolio_name).replace("\n", ""),
                    e,
                    exc_info=True,
                )

    # Fetch portfolio list once for both sections (avoids double disk I/O).
    portfolios = api.data_services.list_portfolios()

    with col2:
        st.markdown("### Load Portfolio")
        st.markdown("Restore a previously saved portfolio with all data and plot configurations.")

        if portfolios:
            selected_portfolio = st.selectbox(
                "Select Portfolio", portfolios, key="portfolio_load_select"
            )

            if st.button("Load Portfolio", type="primary", width="stretch"):
                try:
                    data = api.data_services.load_portfolio(selected_portfolio)
                    api.state_manager.restore_session(data)
                    st.toast(f"Portfolio loaded: {selected_portfolio}", icon="✅")
                    st.rerun(scope="app")
                except Exception as e:
                    st.exception(e)
                    logger.error(
                        "PORTFOLIO: Failed to load portfolio '%s': %s",
                        selected_portfolio,
                        e,
                        exc_info=True,
                    )
        else:
            st.warning("No portfolios found. Save one first!")

    # Manage Saved Portfolios
    st.markdown("---")
    st.markdown("### Manage Saved Portfolios")

    if portfolios:
        for pname in portfolios:
            with st.expander(f"{pname}"):

                def _delete_portfolio(name: str = pname) -> None:
                    api.data_services.delete_portfolio(name)
                    st.toast(f"Deleted {name}", icon="🗑️")

                st.button(
                    "Delete",
                    key=f"del_portfolio_{pname}",
                    on_click=_delete_portfolio,
                    type="tertiary",
                )


def show_portfolio_page(api: ApplicationAPI) -> None:
                        )
            else:
                st.info("No plots available to apply pipeline to.")
        else:
            st.info("No saved pipelines found.")


def show_portfolio_page(api: ApplicationAPI) -> None:
    """
    Display the portfolio management page.

    Allows users to save complete snapshots of their work including data,
    plots, and configurations, and restore previously saved portfolios.
    """
    st.markdown("## Portfolio Management")
    st.markdown(
        "Save and load complete snapshots of your work including data, plots, and all "
        "configurations."
    )
    st.markdown("---")

    st.fragment(_portfolio_fragment)(api)
