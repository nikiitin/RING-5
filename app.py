"""
RING-5 Interactive Web Application
Modern, interactive dashboard for gem5 data analysis and visualization.
"""
import streamlit as st
import pandas as pd
import json
import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.data_management.dataManager import DataManager
from src.data_management.dataManagerFactory import DataManagerFactory
from src.data_plotter.src.shaper.shaperFactory import ShaperFactory
from src.plotting import PlotManager, PlotFactory
from src.config.config_manager import ConfigValidator

# Page configuration
st.set_page_config(
    page_title="RING-5 Interactive Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .step-header {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'config' not in st.session_state:
    st.session_state.config = {}
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = None


def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<h1 class="main-header">RING-5 Interactive Analyzer</h1>', unsafe_allow_html=True)
    st.markdown("### 🚀 Modern gem5 Data Analysis & Visualization")
    
    # Sidebar - Navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=RING-5", use_column_width=True)
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["📤 Upload Data", "🔧 Configure Pipeline", "📊 Generate Plots", "📈 Results"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.markdown("### About RING-5")
        st.info("""
        **Pure Python** implementation for gem5 data analysis.
        
        ✅ No R dependencies  
        ✅ Interactive configuration  
        ✅ Real-time visualization  
        ✅ Professional plots
        """)
        
        if st.button("🗑️ Clear All Data", use_container_width=True):
            st.session_state.data = None
            st.session_state.processed_data = None
            st.session_state.config = {}
            if st.session_state.temp_dir and Path(st.session_state.temp_dir).exists():
                shutil.rmtree(st.session_state.temp_dir)
            st.session_state.temp_dir = None
            st.rerun()
    
    # Main content
    if page == "📤 Upload Data":
        show_upload_page()
    elif page == "🔧 Configure Pipeline":
        show_configure_page()
    elif page == "📊 Generate Plots":
        show_plots_page()
    elif page == "📈 Results":
        show_results_page()


def show_upload_page():
    """Data upload and preview page."""
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## 📤 Step 1: Upload Your Data")
    st.markdown("</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📁 Upload CSV File", "✍️ Paste Data"])
    
    with tab1:
        st.markdown("### Upload gem5 Statistics CSV")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=['csv', 'txt'],
            help="Upload your gem5 statistics file (CSV format, whitespace or comma separated)"
        )
        
        if uploaded_file:
            try:
                # Create temp directory if needed
                if not st.session_state.temp_dir:
                    st.session_state.temp_dir = tempfile.mkdtemp()
                
                # Save uploaded file
                csv_path = Path(st.session_state.temp_dir) / uploaded_file.name
                with open(csv_path, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
                
                # Try to read with different separators
                try:
                    data = pd.read_csv(csv_path)
                except:
                    data = pd.read_csv(csv_path, sep=r'\s+')
                
                st.session_state.data = data
                st.session_state.csv_path = str(csv_path)
                
                st.success(f"✅ Successfully loaded {len(data)} rows × {len(data.columns)} columns!")
                
                # Preview
                st.markdown("### 👀 Data Preview")
                st.dataframe(data.head(20), use_container_width=True)
                
                # Statistics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Rows", len(data))
                with col2:
                    st.metric("Columns", len(data.columns))
                with col3:
                    numeric_cols = data.select_dtypes(include=['number']).columns
                    st.metric("Numeric Columns", len(numeric_cols))
                with col4:
                    categorical_cols = data.select_dtypes(include=['object']).columns
                    st.metric("Categorical Columns", len(categorical_cols))
                
                # Column information
                with st.expander("📋 Column Details"):
                    col_info = pd.DataFrame({
                        'Column': data.columns,
                        'Type': data.dtypes.astype(str),
                        'Non-Null': data.count(),
                        'Null': data.isnull().sum(),
                        'Unique': [data[col].nunique() for col in data.columns]
                    })
                    st.dataframe(col_info, use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ Error loading file: {e}")
    
    with tab2:
        st.markdown("### Paste CSV Data")
        csv_text = st.text_area(
            "Paste your CSV data here",
            height=200,
            help="Paste CSV data (comma or whitespace separated)"
        )
        
        if csv_text and st.button("Load Data"):
            try:
                from io import StringIO
                try:
                    data = pd.read_csv(StringIO(csv_text))
                except:
                    data = pd.read_csv(StringIO(csv_text), sep=r'\s+')
                
                st.session_state.data = data
                st.success(f"✅ Successfully loaded {len(data)} rows × {len(data.columns)} columns!")
                st.dataframe(data.head(10), use_container_width=True)
                
            except Exception as e:
                st.error(f"❌ Error parsing data: {e}")


def show_configure_page():
    """Pipeline configuration page."""
    if st.session_state.data is None:
        st.warning("⚠️ Please upload data first!")
        return
    
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## 🔧 Step 2: Configure Processing Pipeline")
    st.markdown("</div>", unsafe_allow_html=True)
    
    data = st.session_state.data
    
    # Shaper Configuration
    st.markdown("### 🎯 Data Shapers")
    st.info("Shapers transform your data: select columns, normalize, calculate means, sort, etc.")
    
    shapers_config = []
    
    # Column Selector
    with st.expander("📌 Column Selector", expanded=True):
        st.markdown("Select which columns to keep in your analysis")
        selected_columns = st.multiselect(
            "Columns to keep",
            options=data.columns.tolist(),
            default=[data.columns[0]] if len(data.columns) > 0 else [],
            help="Choose the columns you want to work with"
        )
        
        if selected_columns:
            shapers_config.append({
                'type': 'columnSelector',
                'columns': selected_columns
            })
    
    # Normalizer
    with st.expander("📊 Normalizer"):
        st.markdown("Normalize numeric columns relative to a baseline")
        use_normalizer = st.checkbox("Enable Normalizer")
        
        if use_normalizer:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
            
            col1, col2 = st.columns(2)
            with col1:
                normalize_vars = st.multiselect(
                    "Variables to normalize",
                    options=numeric_cols,
                    help="Select numeric columns to normalize"
                )
            
            with col2:
                normalizer_column = st.selectbox(
                    "Normalizer column",
                    options=categorical_cols,
                    help="Column containing baseline configuration"
                )
            
            if normalizer_column:
                normalizer_value = st.selectbox(
                    "Baseline value",
                    options=data[normalizer_column].unique().tolist(),
                    help="Value to use as baseline (will be normalized to 1.0)"
                )
                
                group_by = st.multiselect(
                    "Group by",
                    options=categorical_cols,
                    help="Columns to group by for normalization"
                )
                
                if normalize_vars and normalizer_value and group_by:
                    shapers_config.append({
                        'type': 'normalize',
                        'normalizeVars': normalize_vars,
                        'normalizerColumn': normalizer_column,
                        'normalizerValue': normalizer_value,
                        'groupBy': group_by
                    })
    
    # Mean Calculator
    with st.expander("📈 Mean Calculator"):
        st.markdown("Calculate arithmetic, geometric, or harmonic means")
        use_mean = st.checkbox("Enable Mean Calculator")
        
        if use_mean:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                mean_algorithm = st.selectbox(
                    "Mean type",
                    options=['arithmean', 'geomean', 'harmean'],
                    help="Type of mean to calculate"
                )
            
            with col2:
                mean_vars = st.multiselect(
                    "Variables",
                    options=numeric_cols,
                    help="Columns to calculate mean for"
                )
            
            with col3:
                grouping_column = st.selectbox(
                    "Group by",
                    options=categorical_cols,
                    help="Column to group by"
                )
            
            if mean_vars and grouping_column:
                replacing_column = st.selectbox(
                    "Replacing column",
                    options=categorical_cols,
                    help="Column where mean label will be added"
                )
                
                if replacing_column:
                    shapers_config.append({
                        'type': 'mean',
                        'meanAlgorithm': mean_algorithm,
                        'meanVars': mean_vars,
                        'groupingColumn': grouping_column,
                        'replacingColumn': replacing_column
                    })
    
    # Sort
    with st.expander("🔢 Sort"):
        st.markdown("Sort data by custom order")
        use_sort = st.checkbox("Enable Sort")
        
        if use_sort:
            categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
            
            sort_column = st.selectbox(
                "Column to sort",
                options=categorical_cols,
                help="Column to apply custom sorting"
            )
            
            if sort_column:
                unique_values = data[sort_column].unique().tolist()
                st.markdown(f"Define order for `{sort_column}` (drag to reorder)")
                
                sort_order = st.text_area(
                    "Custom order (one value per line)",
                    value='\n'.join(unique_values),
                    height=150,
                    help="Enter values in desired order, one per line"
                )
                
                order_list = [line.strip() for line in sort_order.split('\n') if line.strip()]
                
                if order_list:
                    shapers_config.append({
                        'type': 'sort',
                        'order_dict': {sort_column: order_list}
                    })
    
    # Preview configuration
    st.markdown("### ⚙️ Configuration Preview")
    st.json({'shapers': shapers_config})
    
    st.session_state.config['shapers'] = shapers_config
    
    # Apply button
    if st.button("▶️ Apply Configuration", type="primary", use_container_width=True):
        with st.spinner("Processing data..."):
            try:
                processed_data = apply_shapers(data.copy(), shapers_config)
                st.session_state.processed_data = processed_data
                
                st.success("✅ Configuration applied successfully!")
                st.markdown("### 📊 Processed Data Preview")
                st.dataframe(processed_data.head(20), use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Original Rows", len(data))
                with col2:
                    st.metric("Processed Rows", len(processed_data))
                
            except Exception as e:
                st.error(f"❌ Error processing data: {e}")
                import traceback
                st.code(traceback.format_exc())


def apply_shapers(data, shapers_config):
    """Apply shapers to data."""
    result = data.copy()
    
    for shaper_config in shapers_config:
        shaper_type = shaper_config['type']
        shaper = ShaperFactory.createShaper(shaper_type, shaper_config)
        result = shaper(result)
    
    return result


def show_plots_page():
    """Plot generation page."""
    if st.session_state.processed_data is None:
        st.warning("⚠️ Please configure and apply pipeline first!")
        return
    
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## 📊 Step 3: Generate Visualizations")
    st.markdown("</div>", unsafe_allow_html=True)
    
    data = st.session_state.processed_data
    
    st.markdown("### 🎨 Plot Builder")
    
    # Plot type selection
    plot_type = st.selectbox(
        "Plot Type",
        options=['bar', 'line', 'scatter', 'box', 'heatmap'],
        help="Choose visualization type"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Data Configuration")
        
        x_column = st.selectbox(
            "X-axis",
            options=data.columns.tolist(),
            help="Column for X-axis"
        )
        
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        y_column = st.selectbox(
            "Y-axis",
            options=numeric_cols,
            help="Column for Y-axis"
        )
        
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        hue_column = st.selectbox(
            "Hue (optional)",
            options=[None] + categorical_cols,
            help="Column for color grouping"
        )
    
    with col2:
        st.markdown("#### 🎨 Style Configuration")
        
        title = st.text_input("Plot Title", value=f"{y_column} by {x_column}")
        xlabel = st.text_input("X-axis Label", value=x_column)
        ylabel = st.text_input("Y-axis Label", value=y_column)
        
        col2_1, col2_2 = st.columns(2)
        with col2_1:
            width = st.number_input("Width (inches)", value=12, min_value=4, max_value=20)
        with col2_2:
            height = st.number_input("Height (inches)", value=6, min_value=4, max_value=20)
        
        rotation = st.slider("X-label Rotation", min_value=0, max_value=90, value=45, step=15)
    
    # Output configuration
    st.markdown("#### 💾 Output Configuration")
    col3_1, col3_2 = st.columns(2)
    with col3_1:
        output_format = st.selectbox("Format", options=['png', 'pdf', 'svg'])
    with col3_2:
        filename = st.text_input("Filename", value="plot")
    
    # Generate plot
    if st.button("🎨 Generate Plot", type="primary", use_container_width=True):
        with st.spinner("Generating plot..."):
            try:
                # Create temp dir if needed
                if not st.session_state.temp_dir:
                    st.session_state.temp_dir = tempfile.mkdtemp()
                
                output_path = Path(st.session_state.temp_dir) / filename
                
                plot_config = {
                    'type': plot_type,
                    'data': {
                        'x': x_column,
                        'y': y_column,
                    },
                    'style': {
                        'title': title,
                        'xlabel': xlabel,
                        'ylabel': ylabel,
                        'width': width,
                        'height': height,
                        'rotation': rotation
                    },
                    'output': {
                        'filename': str(output_path),
                        'format': output_format
                    }
                }
                
                if hue_column:
                    plot_config['data']['hue'] = hue_column
                
                # Generate plot
                from src.plotting import PlotFactory, PlotRenderer
                plot = PlotFactory.create_plot(data, plot_config)
                renderer = PlotRenderer()
                renderer.render(plot)
                
                output_file = Path(str(output_path) + f'.{output_format}')
                
                st.success(f"✅ Plot generated: {output_file.name}")
                
                # Display plot if PNG
                if output_format == 'png':
                    st.image(str(output_file), use_column_width=True)
                
                # Download button
                with open(output_file, 'rb') as f:
                    st.download_button(
                        label=f"⬇️ Download {output_format.upper()}",
                        data=f,
                        file_name=output_file.name,
                        mime=f'image/{output_format}' if output_format != 'pdf' else 'application/pdf',
                        use_container_width=True
                    )
                
            except Exception as e:
                st.error(f"❌ Error generating plot: {e}")
                import traceback
                st.code(traceback.format_exc())


def show_results_page():
    """Results and export page."""
    if st.session_state.processed_data is None:
        st.warning("⚠️ No processed data available!")
        return
    
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## 📈 Step 4: Results & Export")
    st.markdown("</div>", unsafe_allow_html=True)
    
    data = st.session_state.processed_data
    
    # Summary statistics
    st.markdown("### 📊 Summary Statistics")
    st.dataframe(data.describe(), use_container_width=True)
    
    # Full data table
    st.markdown("### 📋 Processed Data")
    st.dataframe(data, use_container_width=True)
    
    # Download options
    st.markdown("### ⬇️ Download Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv_data = data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Download CSV",
            data=csv_data,
            file_name="processed_data.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        json_data = data.to_json(orient='records', indent=2).encode('utf-8')
        st.download_button(
            label="📋 Download JSON",
            data=json_data,
            file_name="processed_data.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        excel_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        data.to_excel(excel_buffer.name, index=False, engine='openpyxl')
        with open(excel_buffer.name, 'rb') as f:
            excel_data = f.read()
        
        st.download_button(
            label="📊 Download Excel",
            data=excel_data,
            file_name="processed_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
