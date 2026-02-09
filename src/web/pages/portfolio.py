"""
Portfolio Management Page

Provides functionality to save and load complete analysis snapshots including
data, plots, and all configurations as portfolio files.
"""

import copy
import logging
from typing import List, Optional, cast

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import PortfolioData

logger: logging.Logger = logging.getLogger(__name__)


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
            if not api.state_manager.has_data():
                st.error("No data loaded. Please load data first.")
                logger.warning("PORTFOLIO: Attempted to save portfolio without data.")
            else:
                try:
                    current_data = api.state_manager.get_data()
                    if current_data is None:
                        st.error("No data available to save")
                        return
                    api.portfolio_service.save_portfolio(
                        name=portfolio_name,
                        data=current_data,
                        plots=api.state_manager.get_plots(),
                        config=api.state_manager.get_config(),
                        plot_counter=api.state_manager.get_plot_counter(),
                        csv_path=api.state_manager.get_csv_path(),
                        parse_variables=cast(
                            Optional[List[str]], api.state_manager.get_parse_variables()
                        ),
                    )
                    st.success(f"Portfolio saved: {portfolio_name}")
                except Exception as e:
                    st.error(f"Failed to save portfolio: {e}")
                    logger.error(
                        "PORTFOLIO: Failed to save portfolio %r: %s",
                        str(portfolio_name).replace("\n", ""),
                        e,
                        exc_info=True,
                    )

    with col2:
        st.markdown("### Load Portfolio")
        st.markdown("Restore a previously saved portfolio with all data and plot configurations.")

        portfolios = api.portfolio_service.list_portfolios()
        if portfolios:
            selected_portfolio = st.selectbox(
                "Select Portfolio", portfolios, key="portfolio_load_select"
            )

            if st.button("Load Portfolio", type="primary", width="stretch"):
                try:
                    data = api.portfolio_service.load_portfolio(selected_portfolio)
                    api.state_manager.restore_session(cast(PortfolioData, data))
                    st.success(f"Portfolio loaded: {selected_portfolio}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load portfolio: {e}")
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

    portfolios = api.portfolio_service.list_portfolios()
    if portfolios:
        for pname in portfolios:
            with st.expander(f"{pname}"):
                if st.button("Delete", key=f"del_portfolio_{pname}"):
                    api.portfolio_service.delete_portfolio(pname)
                    st.success(f"Deleted {pname}")
                    st.rerun()

    # Pipeline Management
    st.markdown("---")
    st.markdown("## Pipeline Templates")
    st.markdown("Save configuration pipelines from existing plots and apply them to others.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Save Pipeline")
        plots = api.state_manager.get_plots()
        if plots:
            plot_map = {p.name: p for p in plots}
            selected_plot_name = st.selectbox(
                "Extract pipeline from:", list(plot_map.keys()), key="pipe_extract_select"
            )

            if selected_plot_name:
                selected_plot = plot_map[selected_plot_name]
                pipeline_name = st.text_input(
                    "Pipeline Name", value=f"{selected_plot_name}_pipeline", key="pipe_save_name"
                )

                if st.button("Save Pipeline", type="primary"):
                    try:
                        api.pipeline.save_pipeline(
                            pipeline_name,
                            selected_plot.pipeline,
                            description=f"Extracted from {selected_plot_name}",
                        )
                        st.success(f"Pipeline saved: {pipeline_name}")
                    except Exception as e:
                        st.error(f"Failed to save pipeline: {e}")
                        logger.error(
                            "PIPELINE: Failed to save pipeline %r: %s",
                            str(pipeline_name).replace("\n", ""),
                            e,
                            exc_info=True,
                        )
        else:
            st.info("Create some plots first to extract pipelines.")

    with col2:
        st.markdown("### Apply Pipeline")
        pipelines = api.pipeline.list_pipelines()
        if pipelines:
            selected_pipeline_name = st.selectbox(
                "Select Pipeline", pipelines, key="pipe_load_select"
            )

            plots = api.state_manager.get_plots()
            if plots:
                target_plots = st.multiselect(
                    "Apply to plots:",
                    [p.name for p in plots],
                    key="pipe_apply_select",
                )

                if st.button("Apply Pipeline", type="primary"):
                    try:
                        pipeline_data = api.pipeline.load_pipeline(selected_pipeline_name)
                        new_pipeline = pipeline_data.get("pipeline", [])

                        count = 0
                        for p in plots:
                            if p.name in target_plots:
                                p.pipeline = copy.deepcopy(new_pipeline)
                                p.processed_data = None
                                count += 1

                        # Update state
                        api.state_manager.set_plots(plots)

                        st.success(f"Applied pipeline to {count} plots.")
                    except Exception as e:
                        st.error(f"Failed to apply pipeline: {e}")
                        logger.error(
                            "PIPELINE: Failed to apply pipeline '%s': %s",
                            selected_pipeline_name,
                            e,
                            exc_info=True,
                        )
            else:
                st.info("No plots available to apply pipeline to.")
        else:
            st.info("No saved pipelines found.")
