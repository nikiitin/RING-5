"""Portfolio management page - save and load complete analysis snapshots."""
import streamlit as st
import pandas as pd
import json
from pathlib import Path


def show_portfolio_page():
    """Save and load complete portfolio snapshots."""
    # Import RING5_DATA_DIR from parent context
    from pathlib import Path
    RING5_DATA_DIR = Path.home() / '.ring5'
    
    st.markdown("## Portfolio Management")
    st.markdown("Save and load complete snapshots of your work including data, plots, and all configurations.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Save Portfolio")
        st.markdown("Save current data, all plots, and their configurations to a single portfolio file.")
        
        portfolio_name = st.text_input("Portfolio Name", value="my_portfolio", key="portfolio_save_name")
        
        if st.button("Save Portfolio", type="primary", width="stretch"):
            if st.session_state.data is None:
                st.error("No data loaded. Please load data first.")
            else:
                try:
                    # Create portfolio directory
                    PORTFOLIO_DIR = RING5_DATA_DIR / 'portfolios'
                    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
                    
                    # Serialize plots (convert DataFrames to CSV strings, remove Figure objects)
                    serialized_plots = []
                    for i, plot in enumerate(st.session_state.plots):
                        try:
                            plot_copy = plot.copy()
                            # Remove non-serializable Figure objects
                            plot_copy.pop('figure', None)
                            plot_copy.pop('last_generated_fig', None)
                            # Convert processed_data DataFrame to CSV string if it exists
                            if plot_copy.get('processed_data') is not None:
                                if isinstance(plot_copy['processed_data'], pd.DataFrame):
                                    plot_copy['processed_data'] = plot_copy['processed_data'].to_csv(index=False)
                            
                            # Test serialize this individual plot to catch issues early
                            json.dumps(plot_copy)
                            serialized_plots.append(plot_copy)
                        except Exception as plot_error:
                            st.error(f"Error serializing plot {i} ('{plot.get('name', 'unknown')}'): {plot_error}")
                            # Try to identify the problematic key
                            for key, value in plot.items():
                                try:
                                    json.dumps({key: value})
                                except:
                                    st.error(f"  → Non-serializable key: '{key}' = {type(value)}")
                            raise
                    
                    # Create portfolio package
                    portfolio_data = {
                        'version': '1.0',
                        'timestamp': pd.Timestamp.now().isoformat(),
                        'data_csv': st.session_state.data.to_csv(index=False),
                        'csv_path': str(st.session_state.csv_path) if st.session_state.csv_path else None,
                        'plots': serialized_plots,
                        'plot_counter': st.session_state.plot_counter,
                        'config': st.session_state.config
                    }
                    
                    # Save to file
                    portfolio_path = PORTFOLIO_DIR / f"{portfolio_name}.json"
                    with open(portfolio_path, 'w') as f:
                        json.dump(portfolio_data, f, indent=2)
                    
                    st.success(f"Portfolio saved: {portfolio_path}")
                    st.info(f"Saved {len(st.session_state.plots)} plots and {len(st.session_state.data)} data rows")
                except Exception as e:
                    st.error(f"Failed to save portfolio: {e}")
    
    with col2:
        st.markdown("### Load Portfolio")
        st.markdown("Restore a previously saved portfolio with all data and plot configurations.")
        
        # List available portfolios
        PORTFOLIO_DIR = RING5_DATA_DIR / 'portfolios'
        if PORTFOLIO_DIR.exists():
            portfolio_files = list(PORTFOLIO_DIR.glob("*.json"))
            if portfolio_files:
                portfolio_names = [p.stem for p in portfolio_files]
                selected_portfolio = st.selectbox("Select Portfolio", portfolio_names, key="portfolio_load_select")
                
                if st.button("Load Portfolio", type="primary", width="stretch"):
                    try:
                        portfolio_path = PORTFOLIO_DIR / f"{selected_portfolio}.json"
                        with open(portfolio_path, 'r') as f:
                            portfolio_data = json.load(f)
                        
                        # Restore data
                        st.session_state.data = pd.read_csv(pd.io.common.StringIO(portfolio_data['data_csv']))
                        st.session_state.csv_path = portfolio_data.get('csv_path')
                        
                        # Deserialize plots (convert CSV strings back to DataFrames)
                        loaded_plots = []
                        for plot in portfolio_data.get('plots', []):
                            # Convert processed_data CSV string back to DataFrame if it exists
                            if plot.get('processed_data') is not None:
                                if isinstance(plot['processed_data'], str):
                                    plot['processed_data'] = pd.read_csv(pd.io.common.StringIO(plot['processed_data']))
                            loaded_plots.append(plot)
                        
                        st.session_state.plots = loaded_plots
                        st.session_state.plot_counter = portfolio_data.get('plot_counter', 0)
                        st.session_state.config = portfolio_data.get('config', {})
                        
                        st.success(f"Portfolio loaded: {selected_portfolio}")
                        st.info(f"Loaded {len(st.session_state.plots)} plots and {len(st.session_state.data)} data rows")
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
    
    PORTFOLIO_DIR = RING5_DATA_DIR / 'portfolios'
    if PORTFOLIO_DIR.exists():
        portfolio_files = list(PORTFOLIO_DIR.glob("*.json"))
        if portfolio_files:
            for pf in portfolio_files:
                with st.expander(f"{pf.stem}"):
                    try:
                        with open(pf, 'r') as f:
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
