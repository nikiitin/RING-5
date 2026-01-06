"""Portfolio management page - save and load complete analysis snapshots."""

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.plotting import BasePlot
from src.web.state_manager import StateManager


def show_portfolio_page():
    """Save and load complete portfolio snapshots."""
    # Import RING5_DATA_DIR from parent context

    RING5_DATA_DIR = Path(__file__).parent.parent.parent.parent / ".ring5"

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
            if st.session_state.data is None:
                st.error("No data loaded. Please load data first.")
            else:
                try:
                    # Create portfolio directory
                    PORTFOLIO_DIR = RING5_DATA_DIR / "portfolios"
                    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)

                    # Serialize plots
                    serialized_plots = []

                    # Check if we are using the new object-based plots
                    if "plots_objects" in st.session_state and st.session_state.plots_objects:
                        for plot in st.session_state.plots_objects:
                            try:
                                serialized_plots.append(plot.to_dict())
                            except Exception as plot_error:
                                st.error(f"Error serializing plot '{plot.name}': {plot_error}")
                                raise
                    # Fallback to old dictionary-based plots
                    elif "plots" in st.session_state and st.session_state.plots:
                        for i, plot in enumerate(st.session_state.plots):
                            try:
                                plot_copy = plot.copy()
                                # Remove non-serializable Figure objects
                                plot_copy.pop("figure", None)
                                plot_copy.pop("last_generated_fig", None)
                                # Convert processed_data DataFrame to CSV string if it exists
                                if plot_copy.get("processed_data") is not None:
                                    if isinstance(plot_copy["processed_data"], pd.DataFrame):
                                        plot_copy["processed_data"] = plot_copy[
                                            "processed_data"
                                        ].to_csv(index=False)

                                serialized_plots.append(plot_copy)
                            except Exception as plot_error:
                                st.error(f"Error serializing plot {i}: {plot_error}")
                                raise

                    # Create portfolio package
                    portfolio_data = {
                        "version": "2.0",  # Bump version for object support
                        "timestamp": pd.Timestamp.now().isoformat(),
                        "data_csv": st.session_state.data.to_csv(index=False),
                        "csv_path": (
                            str(st.session_state.csv_path) if st.session_state.csv_path else None
                        ),
                        "plots": serialized_plots,
                        "plot_counter": st.session_state.plot_counter,
                        "config": st.session_state.config,
                        "parse_variables": st.session_state.get(StateManager.PARSE_VARIABLES, []),
                    }

                    # Save to file
                    portfolio_path = PORTFOLIO_DIR / f"{portfolio_name}.json"
                    with open(portfolio_path, "w") as f:
                        json.dump(portfolio_data, f, indent=2)

                    st.success(f"Portfolio saved: {portfolio_path}")
                    st.info(
                        f"Saved {len(serialized_plots)} plots and "
                        f"{len(st.session_state.data)} data rows"
                    )
                except Exception as e:
                    st.error(f"Failed to save portfolio: {e}")

    with col2:
        st.markdown("### Load Portfolio")
        st.markdown("Restore a previously saved portfolio with all data and plot configurations.")

        # List available portfolios
        PORTFOLIO_DIR = RING5_DATA_DIR / "portfolios"
        if PORTFOLIO_DIR.exists():
            portfolio_files = list(PORTFOLIO_DIR.glob("*.json"))
            if portfolio_files:
                portfolio_names = [p.stem for p in portfolio_files]
                selected_portfolio = st.selectbox(
                    "Select Portfolio", portfolio_names, key="portfolio_load_select"
                )

                if st.button("Load Portfolio", type="primary", width="stretch"):
                    try:
                        portfolio_path = PORTFOLIO_DIR / f"{selected_portfolio}.json"
                        with open(portfolio_path, "r") as f:
                            portfolio_data = json.load(f)

                        # Restore variables configuration if present (CRITICAL for type enforcement)
                        if "parse_variables" in portfolio_data:
                            st.session_state[StateManager.PARSE_VARIABLES] = portfolio_data["parse_variables"]

                        # Restore data
                        data = pd.read_csv(io.StringIO(portfolio_data["data_csv"]))
                        StateManager.set_data(data)
                        StateManager.set_csv_path(portfolio_data.get("csv_path"))

                        # Clear stale widget states for plots to force re-initialization from config
                        # This ensures advanced options (like order, legend aliases) are reflected correctly
                        keys_to_clear = [
                            k for k in st.session_state.keys()
                            if any(marker in k for marker in [
                                "_order_", "leg_ren_", "leg_orient_", "leg_x_", "leg_y_",
                                "xaxis_angle_", "xaxis_font_", "ydtick_", "automargin_",
                                "margin_b_", "bargap_", "bargroupgap_", "bar_border_",
                                "editable_", "download_fmt_", "show_error_bars", "new_plot_name",
                                "colsel_", "norm_", "mean_", "sort_", "filter_", "trans_"
                            ])
                        ]
                        for k in keys_to_clear:
                            del st.session_state[k]

                        # Restore plots
                        loaded_plots_objects = []
                        loaded_plots_dicts = []  # For backward compatibility if needed

                        for plot_data in portfolio_data.get("plots", []):
                            # Try to load as object first (Version 2.0+)
                            try:
                                if "plot_type" in plot_data:
                                    plot_obj = BasePlot.from_dict(plot_data)
                                    loaded_plots_objects.append(plot_obj)
                            except Exception as e:
                                st.warning(f"Could not load plot as object: {e}")

                            # Also keep as dict for fallback/legacy
                            # Convert processed_data CSV string back to DataFrame if it exists
                            if plot_data.get("processed_data") is not None:
                                if isinstance(plot_data["processed_data"], str):
                                    plot_data["processed_data"] = pd.read_csv(
                                        io.StringIO(plot_data["processed_data"])
                                    )
                            loaded_plots_dicts.append(plot_data)

                        # Update session state
                        st.session_state.plots_objects = loaded_plots_objects
                        st.session_state.plots = loaded_plots_dicts  # Keep for legacy compatibility

                        st.session_state.plot_counter = portfolio_data.get("plot_counter", 0)
                        st.session_state.config = portfolio_data.get("config", {})

                        st.success(f"Portfolio loaded: {selected_portfolio}")
                        st.info(
                            f"Loaded {len(loaded_plots_objects)} plots and "
                            f"{len(st.session_state.data)} data rows"
                        )
                        st.info(f"Timestamp: {portfolio_data.get('timestamp', 'Unknown')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to load portfolio: {e}")
            else:
                st.warning("No portfolios found. Save one first!")
        else:
            st.warning("No portfolios directory found. Save a portfolio first!")

    # Portfolio management
    st.markdown("---")
    st.markdown("### Manage Saved Portfolios")

    PORTFOLIO_DIR = RING5_DATA_DIR / "portfolios"
    if PORTFOLIO_DIR.exists():
        portfolio_files = list(PORTFOLIO_DIR.glob("*.json"))
        if portfolio_files:
            for pf in portfolio_files:
                with st.expander(f"{pf.stem}"):
                    try:
                        with open(pf, "r") as f:
                            pdata = json.load(f)
                        st.text(f"Created: {pdata.get('timestamp', 'Unknown')}")
                        st.text(f"Plots: {len(pdata.get('plots', []))}")
                        st.text(f"Version: {pdata.get('version', 'Unknown')}")

                        if st.button("Delete", key=f"del_portfolio_{pf.stem}"):
                            pf.unlink()
                            st.success(f"Deleted {pf.stem}")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error reading portfolio: {e}")

    # Pipeline Management
    st.markdown("---")
    st.markdown("## Pipeline Templates")
    st.markdown("Save configuration pipelines from existing plots and apply them to others.")

    PIPELINE_DIR = RING5_DATA_DIR / "pipelines"
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Save Pipeline")
        # Select plot to extract pipeline from
        if "plots_objects" in st.session_state and st.session_state.plots_objects:
            plot_names = {p.name: p for p in st.session_state.plots_objects}
            selected_plot_name = st.selectbox(
                "Extract pipeline from:", list(plot_names.keys()), key="pipe_extract_select"
            )

            if selected_plot_name:
                selected_plot = plot_names[selected_plot_name]
                pipeline_name = st.text_input(
                    "Pipeline Name", value=f"{selected_plot_name}_pipeline", key="pipe_save_name"
                )

                if st.button("Save Pipeline", type="primary"):
                    try:
                        pipeline_data = {
                            "name": pipeline_name,
                            "description": f"Extracted from {selected_plot_name}",
                            "pipeline": selected_plot.pipeline,
                            "timestamp": pd.Timestamp.now().isoformat(),
                        }

                        save_path = PIPELINE_DIR / f"{pipeline_name}.json"
                        with open(save_path, "w") as f:
                            json.dump(pipeline_data, f, indent=2)
                        st.success(f"Pipeline saved: {save_path}")
                    except Exception as e:
                        st.error(f"Failed to save pipeline: {e}")
        else:
            st.info("Create some plots first to extract pipelines.")

    with col2:
        st.markdown("### Apply Pipeline")
        # List available pipelines
        pipeline_files = list(PIPELINE_DIR.glob("*.json"))
        if pipeline_files:
            pipeline_names = [p.stem for p in pipeline_files]
            selected_pipeline_name = st.selectbox(
                "Select Pipeline", pipeline_names, key="pipe_load_select"
            )

            # Select target plots
            if "plots_objects" in st.session_state and st.session_state.plots_objects:
                target_plots = st.multiselect(
                    "Apply to plots:",
                    [p.name for p in st.session_state.plots_objects],
                    key="pipe_apply_select",
                )

                if st.button("Apply Pipeline", type="primary"):
                    try:
                        # Load pipeline
                        load_path = PIPELINE_DIR / f"{selected_pipeline_name}.json"
                        with open(load_path, "r") as f:
                            pipeline_data = json.load(f)

                        new_pipeline = pipeline_data.get("pipeline", [])

                        # Apply to targets
                        count = 0
                        for p in st.session_state.plots_objects:
                            if p.name in target_plots:
                                # Deep copy the pipeline to avoid shared references
                                import copy

                                p.pipeline = copy.deepcopy(new_pipeline)
                                # Reset processed data so it gets recomputed
                                p.processed_data = None
                                count += 1

                        st.success(
                            f"Applied pipeline to {count} plots. Go to 'Manage Plots' to re-run "
                            "them."
                        )
                    except Exception as e:
                        st.error(f"Failed to apply pipeline: {e}")
            else:
                st.info("No plots available to apply pipeline to.")
        else:
            st.info("No saved pipelines found.")
