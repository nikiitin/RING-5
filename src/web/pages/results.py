"""
Results page for displaying and exporting processed data.
"""

import tempfile
import streamlit as st
import pandas as pd

def show_results_page():
    """Results and export page."""
    if st.session_state.processed_data is None:
        st.warning("No processed data available!")
        return
    
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## Step 5: Results & Export")
    st.markdown("</div>", unsafe_allow_html=True)
    
    data = st.session_state.processed_data
    
    # Summary statistics
    st.markdown("### Summary Statistics")
    st.dataframe(data.describe(), width='stretch')
    
    # Full data table
    st.markdown("### Processed Data")
    st.dataframe(data, width='stretch')
    
    # Download options
    st.markdown("### Download Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv_data = data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="processed_data.csv",
            mime="text/csv",
            width='stretch'
        )
    
    with col2:
        json_data = data.to_json(orient='records', indent=2).encode('utf-8')
        st.download_button(
            label="Download JSON",
            data=json_data,
            file_name="processed_data.json",
            mime="application/json",
            width='stretch'
        )
    
    with col3:
        excel_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        data.to_excel(excel_buffer.name, index=False, engine='openpyxl')
        with open(excel_buffer.name, 'rb') as f:
            excel_data = f.read()
        
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name="processed_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width='stretch'
        )
