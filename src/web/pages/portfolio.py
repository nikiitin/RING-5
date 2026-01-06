"""Portfolio management page - save and load complete analysis snapshots."""

import pandas as pd
import streamlit as st
import copy
from src.web.state_manager import StateManager
from src.web.services.portfolio_service import PortfolioService
from src.web.services.pipeline_service import PipelineService

def show_portfolio_page():
    """Save and load complete portfolio snapshots."""
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
            if not StateManager.has_data():
                st.error("No data loaded. Please load data first.")
            else:
                try:
                    PortfolioService.save_portfolio(
                        name=portfolio_name,
                        data=StateManager.get_data(),
                        plots=StateManager.get_plots(),
                        config=StateManager.get_config(),
                        plot_counter=StateManager.get_plot_counter(),
                        csv_path=StateManager.get_csv_path(),
                        parse_variables=StateManager.get_parse_variables()
                    )
                    st.success(f"Portfolio saved: {portfolio_name}")
                except Exception as e:
                    st.error(f"Failed to save portfolio: {e}")

    with col2:
        st.markdown("### Load Portfolio")
        st.markdown("Restore a previously saved portfolio with all data and plot configurations.")

        portfolios = PortfolioService.list_portfolios()
        if portfolios:
            selected_portfolio = st.selectbox(
                "Select Portfolio", portfolios, key="portfolio_load_select"
            )

            if st.button("Load Portfolio", type="primary", width="stretch"):
                try:
                    data = PortfolioService.load_portfolio(selected_portfolio)
                    StateManager.restore_session_state(data)
                    st.success(f"Portfolio loaded: {selected_portfolio}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to load portfolio: {e}")
        else:
            st.warning("No portfolios found. Save one first!")

    # Manage Saved Portfolios
    st.markdown("---")
    st.markdown("### Manage Saved Portfolios")
    
    portfolios = PortfolioService.list_portfolios()
    if portfolios:
        for pname in portfolios:
            with st.expander(f"{pname}"):
                if st.button("Delete", key=f"del_portfolio_{pname}"):
                    PortfolioService.delete_portfolio(pname)
                    st.success(f"Deleted {pname}")
                    st.rerun()

    # Pipeline Management
    st.markdown("---")
    st.markdown("## Pipeline Templates")
    st.markdown("Save configuration pipelines from existing plots and apply them to others.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Save Pipeline")
        plots = StateManager.get_plots()
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
                        PipelineService.save_pipeline(
                            pipeline_name, 
                            selected_plot.pipeline, 
                            description=f"Extracted from {selected_plot_name}"
                        )
                        st.success(f"Pipeline saved: {pipeline_name}")
                    except Exception as e:
                        st.error(f"Failed to save pipeline: {e}")
        else:
            st.info("Create some plots first to extract pipelines.")

    with col2:
        st.markdown("### Apply Pipeline")
        pipelines = PipelineService.list_pipelines()
        if pipelines:
            selected_pipeline_name = st.selectbox(
                "Select Pipeline", pipelines, key="pipe_load_select"
            )

            plots = StateManager.get_plots()
            if plots:
                target_plots = st.multiselect(
                    "Apply to plots:",
                    [p.name for p in plots],
                    key="pipe_apply_select",
                )

                if st.button("Apply Pipeline", type="primary"):
                    try:
                        pipeline_data = PipelineService.load_pipeline(selected_pipeline_name)
                        new_pipeline = pipeline_data.get("pipeline", [])

                        count = 0
                        for p in plots:
                            if p.name in target_plots:
                                p.pipeline = copy.deepcopy(new_pipeline)
                                p.processed_data = None
                                count += 1
                        
                        # Update state
                        StateManager.set_plots(plots)
                        
                        st.success(f"Applied pipeline to {count} plots.")
                    except Exception as e:
                        st.error(f"Failed to apply pipeline: {e}")
            else:
                st.info("No plots available to apply pipeline to.")
        else:
            st.info("No saved pipelines found.")
