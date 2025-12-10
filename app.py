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
import glob

# Add project root to path
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.web.components import UIComponents  # noqa: E402
from src.web.facade import BackendFacade  # noqa: E402
from src.data_plotter.src.shaper.shaperFactory import ShaperFactory  # noqa: E402
from src.data_parser.parser_params import DataParserParams  # noqa: E402

# Page configuration
st.set_page_config(
    page_title="RING-5 Interactive Analyzer",
    page_icon="⚡",
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
if 'csv_path' not in st.session_state:
    st.session_state.csv_path = None
if 'use_parser' not in st.session_state:
    st.session_state.use_parser = False
if 'csv_pool' not in st.session_state:
    st.session_state.csv_pool = []
if 'saved_configs' not in st.session_state:
    st.session_state.saved_configs = []
if 'plots' not in st.session_state:
    st.session_state.plots = []  # List of plot configurations
if 'current_plot_id' not in st.session_state:
    st.session_state.current_plot_id = None
if 'plot_counter' not in st.session_state:
    st.session_state.plot_counter = 0
if 'pipeline_cache' not in st.session_state:
    st.session_state.pipeline_cache = {}  # Cache for incremental pipeline execution

# Create persistent directories
RING5_DATA_DIR = Path.home() / '.ring5'
CSV_POOL_DIR = RING5_DATA_DIR / 'csv_pool'
CONFIG_POOL_DIR = RING5_DATA_DIR / 'saved_configs'
CSV_POOL_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_POOL_DIR.mkdir(parents=True, exist_ok=True)

# Load CSV pool
def load_csv_pool():
    """Load list of CSV files in the pool, checking if they still exist."""
    pool = []
    if CSV_POOL_DIR.exists():
        for csv_file in sorted(CSV_POOL_DIR.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True):
            pool.append({
                'path': str(csv_file),
                'name': csv_file.name,
                'size': csv_file.stat().st_size,
                'modified': csv_file.stat().st_mtime
            })
    return pool

# Load saved configurations
def load_saved_configs():
    """Load list of saved configuration files."""
    configs = []
    if CONFIG_POOL_DIR.exists():
        for config_file in sorted(CONFIG_POOL_DIR.glob('*.json'), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                configs.append({
                    'path': str(config_file),
                    'name': config_file.name,
                    'modified': config_file.stat().st_mtime,
                    'description': config_data.get('description', 'No description')
                })
            except Exception:
                pass
    return configs

st.session_state.csv_pool = load_csv_pool()
st.session_state.saved_configs = load_saved_configs()


def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<h1 class="main-header">RING-5 Interactive Analyzer</h1>', unsafe_allow_html=True)
    st.markdown("### Modern gem5 Data Analysis & Visualization")
    
    # Show current data preview if data is loaded
    if st.session_state.data is not None:
        st.markdown("#### Current Dataset")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", len(st.session_state.data))
        with col2:
            st.metric("Columns", len(st.session_state.data.columns))
        with col3:
            if st.session_state.csv_path:
                st.metric("Source", Path(st.session_state.csv_path).name)
            else:
                st.metric("Source", "Uploaded")
        
        with st.expander("View Current Data", expanded=False):
            st.dataframe(st.session_state.data, width='stretch', height=300)
    
    # Sidebar - Navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/300x100/667eea/ffffff?text=RING-5", width='stretch')
        st.markdown("---")
        
        page = st.radio(
            "Navigation",
            ["Data Source", "Upload Data", "Data Managers", "Manage Plots", "Results", "Save/Load Portfolio"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        if st.button("Clear All Data", width='stretch'):
            st.session_state.data = None
            st.session_state.processed_data = None
            st.session_state.config = {}
            st.session_state.csv_path = None
            st.session_state.use_parser = False
            if st.session_state.temp_dir and Path(st.session_state.temp_dir).exists():
                shutil.rmtree(st.session_state.temp_dir)
            st.session_state.temp_dir = None
            st.rerun()
    
    # Main content
    if page == "Data Source":
        show_data_source_page()
    elif page == "Upload Data":
        show_upload_page()
    elif page == "Data Managers":
        show_data_managers_page()
    elif page == "Manage Plots":
        show_manage_plots_page()
    elif page == "Results":
        show_results_page()
    elif page == "Save/Load Portfolio":
        show_portfolio_page()




def show_data_source_page():
    """Data source selection page - Parser or CSV."""
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## Step 1: Choose Data Source")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("""
    **RING-5 supports two data input methods:**
    - Parse gem5 Stats Files (for raw gem5 output)
    - Upload CSV Directly (if you already have parsed data)
    - Load from Recent (quick access to previously parsed files)
    """)
    
    choice = st.radio(
        "Select your data source:",
        ["Parse gem5 Stats Files", "I already have CSV data", "Load from Recent"],
        key="data_source_choice"
    )
    
    if choice == "Parse gem5 Stats Files":
        st.session_state.use_parser = True
        show_parser_configuration()
    elif choice == "Load from Recent":
        show_csv_pool()
    else:
        st.session_state.use_parser = False
        st.success("CSV mode selected. Proceed to **Upload Data** to upload your CSV file.")


def show_csv_pool():
    """Display and manage the CSV pool."""
    st.markdown("---")
    st.markdown("### Recent CSV Files")
    
    # Reload pool to check for deleted files
    st.session_state.csv_pool = load_csv_pool()
    
    if not st.session_state.csv_pool:
        st.warning("No CSV files in the pool yet. Parse some gem5 stats to populate this list.")
        return
    
    st.info(f"Found {len(st.session_state.csv_pool)} CSV file(s) in the pool")
    
    for idx, csv_info in enumerate(st.session_state.csv_pool):
        csv_path = Path(csv_info['path'])
        
        # Check if file still exists
        if not csv_path.exists():
            st.error(f"File no longer exists: {csv_info['name']}")
            continue
        
        with st.expander(f"{csv_info['name']} ({csv_info['size'] / 1024:.1f} KB)", expanded=(idx==0)):
            import datetime
            modified_time = datetime.datetime.fromtimestamp(csv_info['modified'])
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("Load This File", key=f"load_csv_{idx}"):
                    try:
                        data = pd.read_csv(csv_path, sep=r'\s+')
                        st.session_state.data = data
                        st.session_state.csv_path = str(csv_path)
                        st.session_state.use_parser = False
                        st.success(f"Loaded {len(data)} rows!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error loading file: {e}")
            
            with col2:
                # Preview
                try:
                    preview_data = pd.read_csv(csv_path, sep=r'\s+', nrows=5)
                    if st.button("Preview", key=f"preview_csv_{idx}"):
                        st.dataframe(preview_data)
                except Exception:
                    pass
            
            with col3:
                if st.button("Delete", key=f"delete_csv_{idx}"):
                    csv_path.unlink()
                    st.session_state.csv_pool = load_csv_pool()
                    st.rerun()


def show_parser_configuration():
    """Parser configuration interface."""
    st.markdown("---")
    st.markdown("### gem5 Stats Parser Configuration")
    
    st.markdown("#### File Location")
    
    col1, col2 = st.columns(2)
    
    with col1:
        stats_path = st.text_input(
            "Stats directory path",
            value="/path/to/gem5/stats",
            help="Directory containing gem5 stats files (can include subdirectories)"
        )
    
    with col2:
        stats_pattern = st.text_input(
            "File pattern",
            value="stats.txt",
            help="Filename pattern to search for (e.g., stats.txt, *.txt)"
        )
    
    # Scan for variables
    if st.button("Scan for Variables"):
        with st.spinner("Scanning stats files..."):
            facade = BackendFacade()
            vars_found = facade.scan_stats_variables(stats_path, stats_pattern)
            if vars_found:
                st.session_state.available_variables = vars_found
                st.success(f"Found {len(vars_found)} variables!")
            else:
                st.warning("No variables found. Check path and pattern.")
    
    # Initialize available_variables if not present
    if 'available_variables' not in st.session_state:
        st.session_state.available_variables = None

    # Compression option
    st.markdown("#### Remote Filesystem Optimization")
    
    compress_data = st.checkbox(
        "Enable compression (for remote/SSHFS filesystems)",
        value=False,
        help="Compress and copy stats files locally for faster processing. Use this if your stats are on a remote cluster mounted via SSHFS."
    )
    
    if compress_data:
        st.info("""
        **Compression Mode Enabled:**
        
        Stats files will be copied from the remote filesystem to a local directory and compressed. 
        This significantly speeds up parsing when working with SSHFS-mounted directories.
        """)
    
    # Variables configuration
    st.markdown("#### Variables to Extract")
    
    st.markdown("""
    Define which variables to extract from gem5 stats files. You can add:
    - **Scalar**: Single numeric values (e.g., simTicks, IPC)
    - **Vector**: Arrays of values (e.g., cache miss breakdown)
    - **Distribution**: Statistical distributions
    - **Configuration**: Metadata (benchmark name, config ID, seed)
    """)
    
    # Initialize variables list in session state
    if 'parse_variables' not in st.session_state:
        st.session_state.parse_variables = [
            {"name": "simTicks", "type": "scalar"},
            {"name": "benchmark_name", "type": "configuration"},
            {"name": "config_description", "type": "configuration"}
        ]
    
    # Use UIComponents to manage variables (includes vector support)
    st.session_state.parse_variables = UIComponents.variable_editor(
        st.session_state.parse_variables,
        available_variables=st.session_state.available_variables,
        stats_path=stats_path,
        stats_pattern=stats_pattern
    )
    
    # Preview configuration
    st.markdown("#### Configuration Preview")
    
    # DEBUG: Check variables before creating config
    for v in st.session_state.parse_variables:
        if v.get("type") == "vector":
            st.write(f"DEBUG APP: Variable {v.get('name')} keys: {list(v.keys())}")
            if "vectorEntries" not in v:
                st.error(f"CRITICAL: vectorEntries missing for {v.get('name')} in app.py!")

    parse_config = {
        "parser": "gem5_stats",
        "statsPath": stats_path,
        "statsPattern": stats_pattern,
        "compress": compress_data,
        "variables": st.session_state.parse_variables
    }
    
    st.json(parse_config)
    
    # Parse button
    st.markdown("---")
    
    if st.button("Parse gem5 Stats Files", type="primary", width='stretch'):
        # Validate inputs
        if not stats_path or stats_path == "/path/to/gem5/stats":
            st.error("Please specify a valid stats directory path!")
            return
        
        if not Path(stats_path).exists():
            st.error(f"Directory not found: {stats_path}")
            return
        
        # Check for files
        pattern = f"{stats_path}/**/{stats_pattern}"
        files_found = glob.glob(pattern, recursive=True)
        
        if len(files_found) == 0:
            st.warning(f"No files found matching pattern: {pattern}")
            return
        
        st.info(f"Found {len(files_found)} files to parse")
        
        # Create progress containers
        progress_container = st.container()
        
        with progress_container:
            st.markdown("### Processing Progress")
            
            # Progress bars
            overall_progress = st.progress(0)
            status_text = st.empty()
            
            # File details
            file_details = st.empty()
            
            # Run parser with progress tracking
            try:
                csv_path = run_parser_with_progress(
                    stats_path=stats_path,
                    stats_pattern=stats_pattern,
                    compress=compress_data,
                    variables=st.session_state.parse_variables,
                    files_count=len(files_found),
                    progress_bar=overall_progress,
                    status_text=status_text,
                    file_details=file_details
                )
                
                if csv_path and Path(csv_path).exists():
                    # Copy CSV to pool
                    import datetime
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    csv_pool_path = CSV_POOL_DIR / f"parsed_{timestamp}.csv"
                    shutil.copy(csv_path, csv_pool_path)
                    
                    # Reload pool
                    st.session_state.csv_pool = load_csv_pool()
                    
                    # Load the parsed CSV
                    data = pd.read_csv(csv_path, sep=r'\s+')
                    st.session_state.data = data
                    st.session_state.csv_path = str(csv_path)
                    
                    st.success(f"Successfully parsed {len(data)} rows! CSV saved to pool.")
                    st.markdown("### Parsed Data Preview")
                    st.dataframe(data.head(20), width='stretch')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Rows", len(data))
                    with col2:
                        st.metric("Columns", len(data.columns))
                    
                    st.info("Data ready! Proceed to **Configure Pipeline**")
                else:
                    st.error("Parser did not generate CSV file")
                    
            except Exception as e:
                st.error(f"Error during parsing: {e}")


def run_parser_with_progress(stats_path: str, stats_pattern: str, compress: bool, 
                             variables: list, files_count: int, progress_bar, 
                             status_text, file_details) -> str:
    """Run the gem5 stats parser with progress tracking."""
    # from argumentParser import AnalyzerInfo
    from src.data_parser.src.dataParserFactory import DataParserFactory
    
    # Create temp directory if needed
    if not st.session_state.temp_dir:
        st.session_state.temp_dir = tempfile.mkdtemp()
    
    output_dir = st.session_state.temp_dir
    
    # Update status
    status_text.text("Step 1/3: Initializing parser...")
    progress_bar.progress(0.1)
    
    # Create parse config JSON
    parse_config_data = {
        "outputPath": output_dir,
        "parseConfig": {
            "file": "webapp_parse",
            "config": "webapp_config"
        }
    }
    
    # Create the parse configuration file
    parse_component_dir = Path("config_files/json_components/parse")
    parse_component_dir.mkdir(parents=True, exist_ok=True)
    
    parse_config_file = parse_component_dir / "webapp_parse.json"
    
    # Map variables to parser format
    parser_vars = []
    for var in variables:
        var_config = {
            "id": var["name"],
            "type": var["type"]
        }
        
        # Add type-specific parameters
        if var["type"] == "vector":
            if "vectorEntries" in var:
                var_config["vectorEntries"] = var["vectorEntries"]
        elif var["type"] == "distribution":
            if "minimum" in var:
                var_config["minimum"] = var["minimum"]
            if "maximum" in var:
                var_config["maximum"] = var["maximum"]
        elif var["type"] == "configuration":
            if "onEmpty" in var:
                var_config["onEmpty"] = var["onEmpty"]
            
        parser_vars.append(var_config)
    
    # Create parser configuration
    parser_config = [{
        "id": "webapp_config",
        "impl": "perl",
        "compress": "True" if compress else "False",
        "parsings": [{
            "path": stats_path,
            "files": stats_pattern,
            "vars": parser_vars
        }]
    }]
    
    # Write parser config
    with open(parse_config_file, 'w') as f:
        json.dump(parser_config, f, indent=2)
    
    # Write main config
    config_file = Path(output_dir) / "config.json"
    with open(config_file, 'w') as f:
        json.dump(parse_config_data, f, indent=2)
    
    status_text.text("Step 2/3: Configuring parser...")
    progress_bar.progress(0.2)
    
    # Create DataParserParams
    parser_params = DataParserParams(config_json=parse_config_data)
    
    # Update status for compression phase
    if compress:
        status_text.text(f"Step 3/3: Compressing {files_count} files...")
        file_details.text(f"Processing files... ({files_count} total)")
        progress_bar.progress(0.3)
    
    # Get parser and run
    status_text.text("Step 3/3: Parsing files...")
    file_details.text(f"Parsing {files_count} gem5 stats files...")
    progress_bar.progress(0.5)
    
    parser = DataParserFactory.getDataParser(parser_params, "perl")
    parser()
    
    # Finalize
    status_text.text("Finalizing results...")
    progress_bar.progress(0.9)
    
    # Return path to results.csv
    csv_path = Path(output_dir) / "results.csv"
    
    if csv_path.exists():
        progress_bar.progress(1.0)
        status_text.text("Parsing complete!")
        file_details.text(f"Successfully parsed {files_count} files")
    
    return str(csv_path) if csv_path.exists() else None


def run_parser(stats_path: str, stats_pattern: str, compress: bool, variables: list) -> str:
    """Run the gem5 stats parser and return path to generated CSV."""
    # from argumentParser import AnalyzerInfo
    from src.data_parser.src.dataParserFactory import DataParserFactory
    
    # Create temp directory if needed
    if not st.session_state.temp_dir:
        st.session_state.temp_dir = tempfile.mkdtemp()
    
    output_dir = st.session_state.temp_dir
    
    # Create parse config JSON
    parse_config_data = {
        "outputPath": output_dir,
        "parseConfig": {
            "file": "webapp_parse",
            "config": "webapp_config"
        }
    }
    
    # Create the parse configuration file
    parse_component_dir = Path("config_files/json_components/parse")
    parse_component_dir.mkdir(parents=True, exist_ok=True)
    
    parse_config_file = parse_component_dir / "webapp_parse.json"
    
    # Map variables to parser format
    parser_vars = []
    for var in variables:
        var_config = {
            "id": var["name"],
            "type": var["type"]
        }
        
        # Add type-specific parameters
        if var["type"] == "vector":
            if "vectorEntries" in var:
                var_config["vectorEntries"] = var["vectorEntries"]
        elif var["type"] == "distribution":
            if "minimum" in var:
                var_config["minimum"] = var["minimum"]
            if "maximum" in var:
                var_config["maximum"] = var["maximum"]
        elif var["type"] == "configuration":
            if "onEmpty" in var:
                var_config["onEmpty"] = var["onEmpty"]
            
        parser_vars.append(var_config)
    
    # Create parser configuration
    parser_config = [{
        "id": "webapp_config",
        "impl": "perl",
        "compress": "True" if compress else "False",
        "parsings": [{
            "path": stats_path,
            "files": stats_pattern,
            "vars": parser_vars
        }]
    }]
    
    # Write parser config
    with open(parse_config_file, 'w') as f:
        json.dump(parser_config, f, indent=2)
    
    # Write main config
    config_file = Path(output_dir) / "config.json"
    with open(config_file, 'w') as f:
        json.dump(parse_config_data, f, indent=2)
    
    # Create DataParserParams
    parser_params = DataParserParams(config_json=parse_config_data)
    
    # Get parser and run
    parser = DataParserFactory.getDataParser(parser_params, "perl")
    parser()
    
    # Return path to results.csv
    csv_path = Path(output_dir) / "results.csv"
    return str(csv_path) if csv_path.exists() else None


def show_upload_page():
    """Data upload and preview page."""
    
    # Check if parser mode and data already loaded
    if st.session_state.use_parser:
        if st.session_state.data is not None:
            st.markdown('<div class="step-header">', unsafe_allow_html=True)
            st.markdown("## Step 2: Parsed Data Preview")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.success("Data loaded from parser!")
            
            data = st.session_state.data
            st.dataframe(data.head(20), width='stretch')
            
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
            with st.expander("Column Details"):
                col_info = pd.DataFrame({
                    'Column': data.columns,
                    'Type': data.dtypes.astype(str),
                    'Non-Null': data.count(),
                    'Null': data.isnull().sum(),
                    'Unique': [data[col].nunique() for col in data.columns]
                })
                st.dataframe(col_info, width='stretch')
            
            st.info("Proceed to **Configure Pipeline** to process your data")
            return
        else:
            st.warning("Please parse gem5 stats first in **Data Source** page!")
            return
    
    # CSV upload mode
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## Step 2: Upload Your Data")
    st.markdown("</div>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Upload CSV File", "Paste Data"])
    
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
                except Exception:
                    data = pd.read_csv(csv_path, sep=r'\s+')
                
                st.session_state.data = data
                st.session_state.csv_path = str(csv_path)
                
                st.success(f"Successfully loaded {len(data)} rows × {len(data.columns)} columns!")
                
                # Preview
                st.markdown("### Data Preview")
                st.dataframe(data.head(20), width='stretch')
                
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
                with st.expander("Column Details"):
                    col_info = pd.DataFrame({
                        'Column': data.columns,
                        'Type': data.dtypes.astype(str),
                        'Non-Null': data.count(),
                        'Null': data.isnull().sum(),
                        'Unique': [data[col].nunique() for col in data.columns]
                    })
                    st.dataframe(col_info, width='stretch')
                
            except Exception as e:
                st.error(f"Error loading file: {e}")
    
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
                except Exception:
                    data = pd.read_csv(StringIO(csv_text), sep=r'\s+')
                
                st.session_state.data = data
                st.success(f"Successfully loaded {len(data)} rows × {len(data.columns)} columns!")
                st.dataframe(data.head(10), width='stretch')
                
            except Exception as e:
                st.error(f"Error parsing data: {e}")


def show_manage_plots_page():
    """Import and display the manage plots page."""
    try:
        from src.web.pages.manage_plots import show_manage_plots_page as show_plots
        show_plots()
    except ImportError as e:
        st.error(f"Error loading Manage Plots page: {e}")
        st.info("Make sure src/web/pages/manage_plots.py exists")



def show_configure_page():
    """Pipeline configuration page with dynamic shaper addition."""
    if st.session_state.data is None:
        st.warning("Please upload data first!")
        return
    
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## Step 3: Configure Processing Pipeline")
    st.markdown("</div>", unsafe_allow_html=True)
    
    data = st.session_state.data
    
    # Initialize pipeline in session state
    if 'pipeline' not in st.session_state:
        st.session_state.pipeline = []
    if 'pipeline_counter' not in st.session_state:
        st.session_state.pipeline_counter = 0
    
    st.markdown("### Build Your Processing Pipeline")
    st.info("""
    **Build a custom pipeline** by adding shapers in any order. You can:
    - Add multiple shapers of the same type (e.g., normalize twice with different baselines)
    - Reorder shapers by dragging (use ↑↓ buttons)
    - Remove any shaper from the pipeline
    """)
    
    # Shaper selection
    col1, col2 = st.columns([3, 1])
    with col1:
        shaper_map = {
            'Column Selector': 'columnSelector',
            'Normalize': 'normalize',
            'Mean Calculator': 'mean',
            'Sort': 'sort',
            'Filter': 'conditionSelector'
        }
        shaper_display = st.selectbox(
            "Select shaper to add",
            options=list(shaper_map.keys()),
            key='shaper_selector'
        )
        shaper_type = shaper_map[shaper_display]
    with col2:
        if st.button("➕ Add Shaper", width='stretch'):
            # Add a new shaper configuration to pipeline with unique ID
            st.session_state.pipeline.append({
                'type': shaper_type,
                'config': {},
                'id': st.session_state.pipeline_counter
            })
            st.session_state.pipeline_counter += 1
            st.rerun()
    
    # Display pipeline
    if len(st.session_state.pipeline) == 0:
        st.warning("Pipeline is empty. Add shapers above to build your processing pipeline.")
    else:
        st.markdown("### Current Pipeline")
        
        for idx, shaper in enumerate(st.session_state.pipeline):
            with st.expander(f"**{idx+1}. {shaper['type']}**", expanded=True):
                col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
                
                with col1:
                    # Configure the shaper based on its type (use unique ID for keys)
                    shaper['config'] = configure_shaper(shaper['type'], data, shaper['id'], shaper.get('config', {}))
                
                with col2:
                    if idx > 0:
                        if st.button("↑", key=f"up_{idx}"):
                            st.session_state.pipeline[idx], st.session_state.pipeline[idx-1] = \
                                st.session_state.pipeline[idx-1], st.session_state.pipeline[idx]
                            st.rerun()
                
                with col3:
                    if idx < len(st.session_state.pipeline) - 1:
                        if st.button("↓", key=f"down_{idx}"):
                            st.session_state.pipeline[idx], st.session_state.pipeline[idx+1] = \
                                st.session_state.pipeline[idx+1], st.session_state.pipeline[idx]
                            st.rerun()
                
                with col4:
                    if st.button("🗑️", key=f"delete_{idx}"):
                        st.session_state.pipeline.pop(idx)
                        st.rerun()
                
                # Add preview button for each shaper (except Sort which has its own preview)
                if shaper['config'] and shaper['type'] != 'Sort':
                    if st.button(f"🔍 Preview {shaper['type']}", key=f"preview_{shaper['id']}"):
                        try:
                            preview_data = data.copy()
                            shaper_obj = ShaperFactory.createShaper(shaper['config']['type'], shaper['config'])
                            preview_result = shaper_obj(preview_data)
                            st.markdown(f"**Preview of {shaper['type']} (first 20 rows):**")
                            st.dataframe(preview_result.head(20), width='stretch')
                            st.info(f"Rows: {len(data)} → {len(preview_result)} | Columns: {len(data.columns)} → {len(preview_result.columns)}")
                        except Exception as e:
                            st.error(f"Preview failed: {e}")
    
    # Preview configuration
    if st.session_state.pipeline:
        st.markdown("### Configuration Preview")
        shapers_config = [s['config'] for s in st.session_state.pipeline if s['config']]
        st.json({'shapers': shapers_config})
        st.session_state.config['shapers'] = shapers_config
    
    # Apply and Save buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🗑️ Clear Pipeline", width='stretch'):
            st.session_state.pipeline = []
            st.rerun()
    
    with col2:
        if st.button("Apply Pipeline", type="primary", width='stretch'):
            if not st.session_state.pipeline:
                st.warning("Pipeline is empty!")
            else:
                with st.spinner("Processing data through pipeline..."):
                    try:
                        shapers_config = [s['config'] for s in st.session_state.pipeline if s['config']]
                        processed_data = apply_shapers(data.copy(), shapers_config)
                        st.session_state.processed_data = processed_data
                        
                        st.success("Pipeline applied successfully!")
                        st.markdown("### Processed Data Preview")
                        st.dataframe(processed_data.head(20), width='stretch')
                        
                        col1a, col2a = st.columns(2)
                        with col1a:
                            st.metric("Original Rows", len(data))
                        with col2a:
                            st.metric("Processed Rows", len(processed_data))
                        
                    except Exception as e:
                        st.error(f"Error processing data: {e}")
    
    with col3:
        if st.button("Save Configuration", width='stretch'):
            if st.session_state.pipeline:
                st.session_state.show_save_dialog = True
                st.rerun()
    
    # Show save dialog if flag is set
    if st.session_state.get('show_save_dialog', False):
        shapers_config = [s['config'] for s in st.session_state.pipeline if s['config']]
        show_save_config_dialog(shapers_config)
        if st.button("Cancel Save"):
            st.session_state.show_save_dialog = False
            st.rerun()


def configure_shaper(shaper_type, data, shaper_id, existing_config):
    """Configure a specific shaper and return its config."""
    config = {}
    
    # Handle None existing_config
    if existing_config is None:
        existing_config = {}
    
    if shaper_type == 'columnSelector':
        st.markdown("Select which columns to keep")
        default_cols = existing_config.get('columns', [data.columns[0]] if len(data.columns) > 0 else [])
        selected_columns = st.multiselect(
            "Columns to keep",
            options=data.columns.tolist(),
            default=default_cols,
            key=f"colsel_{shaper_id}"
        )
        config = {
            'type': 'columnSelector',
            'columns': selected_columns if selected_columns else []
        }
    
    elif shaper_type == 'normalize':
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            normalizer_vars = st.multiselect(
                "Normalizer variables (will be summed)",
                options=numeric_cols,
                default=existing_config.get('normalizerVars', []),
                key=f"normalizer_vars_{shaper_id}",
                help="These columns will be summed to create the baseline normalizer value"
            )
            
            normalize_vars = st.multiselect(
                "Variables to normalize",
                options=numeric_cols,
                default=existing_config.get('normalizeVars', []),
                key=f"norm_vars_{shaper_id}",
                help="These columns will be divided by the sum of normalizer variables"
            )
            
            norm_col_default = existing_config.get('normalizerColumn')
            norm_col_index = categorical_cols.index(norm_col_default) if norm_col_default in categorical_cols else 0
            normalizer_column = st.selectbox(
                "Normalizer column (baseline identifier)",
                options=categorical_cols,
                index=norm_col_index,
                key=f"norm_col_{shaper_id}",
                help="The categorical column that identifies the baseline configuration"
            )
        
        with col2:
            normalizer_value = None
            if normalizer_column:
                unique_vals = data[normalizer_column].unique().tolist()
                norm_val_default = existing_config.get('normalizerValue')
                norm_val_index = unique_vals.index(norm_val_default) if norm_val_default in unique_vals else 0
                normalizer_value = st.selectbox(
                    "Baseline value",
                    options=unique_vals,
                    index=norm_val_index,
                    key=f"norm_val_{shaper_id}"
                )
            
            group_by = st.multiselect(
                "Group by",
                options=categorical_cols,
                default=existing_config.get('groupBy', []),
                key=f"norm_group_{shaper_id}"
            )
            
            # Checkbox for auto-normalizing SD columns
            normalize_sd = st.checkbox(
                "Automatically normalize standard deviation columns",
                value=existing_config.get('normalizeSd', True),
                key=f"norm_sd_{shaper_id}",
                help="If enabled, .sd columns will be automatically normalized using the sum of their base normalizer columns"
            )
        
        if normalizer_vars and normalize_vars and normalizer_column and normalizer_value and group_by:
            config = {
                'type': 'normalize',
                'normalizerVars': normalizer_vars,
                'normalizeVars': normalize_vars,
                'normalizerColumn': normalizer_column,
                'normalizerValue': normalizer_value,
                'groupBy': group_by,
                'normalizeSd': normalize_sd
            }
    
    elif shaper_type == 'mean':
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            mean_algos = ['arithmean', 'geomean', 'harmean']
            mean_algo_default = existing_config.get('meanAlgorithm', 'arithmean')
            mean_algo_index = mean_algos.index(mean_algo_default) if mean_algo_default in mean_algos else 0
            mean_algorithm = st.selectbox(
                "Mean type",
                options=mean_algos,
                index=mean_algo_index,
                key=f"mean_algo_{shaper_id}"
            )
        
        with col2:
            mean_vars = st.multiselect(
                "Variables",
                options=numeric_cols,
                default=existing_config.get('meanVars', []),
                key=f"mean_vars_{shaper_id}"
            )
        
        with col3:
            group_col_default = existing_config.get('groupingColumn')
            group_col_index = categorical_cols.index(group_col_default) if group_col_default in categorical_cols else 0
            grouping_column = st.selectbox(
                "Group by",
                options=categorical_cols,
                index=group_col_index,
                key=f"mean_group_{shaper_id}"
            )
        
        if mean_vars and grouping_column:
            replace_col_default = existing_config.get('replacingColumn')
            replace_col_index = categorical_cols.index(replace_col_default) if replace_col_default in categorical_cols else 0
            replacing_column = st.selectbox(
                "Replacing column",
                options=categorical_cols,
                index=replace_col_index,
                key=f"mean_replace_{shaper_id}"
            )
            
            if replacing_column:
                config = {
                    'type': 'mean',
                    'meanAlgorithm': mean_algorithm,
                    'meanVars': mean_vars,
                    'groupingColumn': grouping_column,
                    'replacingColumn': replacing_column
                }
    
    elif shaper_type == 'sort':
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        sort_col_default = None
        if existing_config.get('order_dict'):
            sort_col_default = list(existing_config['order_dict'].keys())[0]
        sort_col_index = categorical_cols.index(sort_col_default) if sort_col_default in categorical_cols else 0
        
        sort_column = st.selectbox(
            "Column to sort",
            options=categorical_cols,
            index=sort_col_index,
            key=f"sort_col_{shaper_id}"
        )
        
        if sort_column:
            unique_values = data[sort_column].unique().tolist()
            st.markdown(f"Define order for `{sort_column}`")
            
            # Use existing order if available, otherwise use unique values
            default_order = existing_config.get('order_dict', {}).get(sort_column, unique_values)
            
            # Initialize order in session state if not exists
            order_key = f"sort_order_list_{shaper_id}"
            if order_key not in st.session_state:
                st.session_state[order_key] = default_order.copy()
            
            order_list = st.session_state[order_key]
            
            # Display sortable list with up/down buttons
            st.markdown("**Drag items to reorder** (use ↑↓ buttons)")
            for i, value in enumerate(order_list):
                col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
                with col1:
                    st.text(value)
                with col2:
                    if i > 0:
                        if st.button("↑", key=f"sort_up_{shaper_id}_{i}"):
                            order_list[i], order_list[i-1] = order_list[i-1], order_list[i]
                            st.session_state[order_key] = order_list
                            st.rerun()
                with col3:
                    if i < len(order_list) - 1:
                        if st.button("↓", key=f"sort_down_{shaper_id}_{i}"):
                            order_list[i], order_list[i+1] = order_list[i+1], order_list[i]
                            st.session_state[order_key] = order_list
                            st.rerun()
                with col4:
                    if st.button("🗑️", key=f"sort_del_{shaper_id}_{i}"):
                        order_list.pop(i)
                        st.session_state[order_key] = order_list
                        st.rerun()
            
            # Add missing values
            missing = [v for v in unique_values if v not in order_list]
            if missing:
                st.warning(f"Missing values (will appear at end): {', '.join(map(str, missing))}")
                if st.button("Add all missing values", key=f"sort_add_missing_{shaper_id}"):
                    order_list.extend(missing)
                    st.session_state[order_key] = order_list
                    st.rerun()
            
            # Preview button
            if st.button("Preview Sort Result", key=f"sort_preview_{shaper_id}"):
                try:
                    preview_data = data.copy()
                    # Apply the sort shaper with correct params structure
                    sort_config = {'order_dict': {sort_column: order_list}}
                    sorter = ShaperFactory.createShaper('sort', sort_config)
                    preview_result = sorter(preview_data)
                    st.markdown("**Preview (first 20 rows):**")
                    st.dataframe(preview_result.head(20), width='stretch')
                except Exception as e:
                    st.error(f"Preview failed: {e}")
            
            if order_list:
                config = {
                    'type': 'sort',
                    'order_dict': {sort_column: order_list}
                }
    
    elif shaper_type == 'conditionSelector':
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        all_cols = categorical_cols + numeric_cols
        
        st.markdown("Filter rows based on column values")
        
        filter_col_default = existing_config.get('column')
        filter_col_index = all_cols.index(filter_col_default) if filter_col_default in all_cols else 0
        
        filter_column = st.selectbox(
            "Column to filter",
            options=all_cols,
            index=filter_col_index,
            key=f"filter_col_{shaper_id}"
        )
        
        if filter_column:
            unique_values = data[filter_column].unique().tolist()
            
            # Check if column is numeric or categorical
            is_numeric = filter_column in numeric_cols
            
            if is_numeric:
                # Numeric filtering
                st.markdown("**Numeric Filter**")
                
                filter_modes = ['range', 'greater_than', 'less_than', 'equals']
                filter_mode_default = existing_config.get('mode', 'range')
                filter_mode_index = filter_modes.index(filter_mode_default) if filter_mode_default in filter_modes else 0
                
                filter_mode = st.selectbox(
                    "Filter mode",
                    options=filter_modes,
                    index=filter_mode_index,
                    key=f"filter_mode_{shaper_id}"
                )
                
                min_val = float(data[filter_column].min())
                max_val = float(data[filter_column].max())
                
                if filter_mode == 'range':
                    default_range = existing_config.get('range', [min_val, max_val])
                    value_range = st.slider(
                        "Value range",
                        min_value=min_val,
                        max_value=max_val,
                        value=(float(default_range[0]), float(default_range[1])),
                        key=f"filter_range_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'range',
                        'range': list(value_range)
                    }
                elif filter_mode == 'greater_than':
                    default_threshold = existing_config.get('threshold', min_val)
                    threshold = st.number_input(
                        "Greater than",
                        value=float(default_threshold),
                        key=f"filter_gt_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'greater_than',
                        'threshold': threshold
                    }
                elif filter_mode == 'less_than':
                    default_threshold = existing_config.get('threshold', max_val)
                    threshold = st.number_input(
                        "Less than",
                        value=float(default_threshold),
                        key=f"filter_lt_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'less_than',
                        'threshold': threshold
                    }
                else:  # equals
                    default_value = existing_config.get('value', min_val)
                    value = st.number_input(
                        "Equals",
                        value=float(default_value),
                        key=f"filter_eq_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'equals',
                        'value': value
                    }
            else:
                # Categorical filtering
                st.markdown("**Categorical Filter**")
                
                default_values = existing_config.get('values', [])
                selected_values = st.multiselect(
                    "Keep rows where value is:",
                    options=unique_values,
                    default=default_values,
                    key=f"filter_values_{shaper_id}"
                )
                
                if selected_values:
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'values': selected_values
                    }
    
    return config


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
        st.warning("Please configure and apply pipeline first!")
        return
    
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## Step 4: Generate Visualizations")
    st.markdown("</div>", unsafe_allow_html=True)
    
    data = st.session_state.processed_data
    
    st.markdown("### Plot Builder")
    
    # Plot type selection
    plot_type = st.selectbox(
        "Plot Type",
        options=['bar', 'line', 'scatter', 'box', 'heatmap'],
        help="Choose visualization type"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Data Configuration")
        
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
        st.markdown("#### Style Configuration")
        
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
    st.markdown("#### Output Configuration")
    col3_1, col3_2 = st.columns(2)
    with col3_1:
        output_format = st.selectbox("Format", options=['png', 'pdf', 'svg'])
    with col3_2:
        filename = st.text_input("Filename", value="plot")
    
    # Generate plot
    if st.button("Generate Plot", type="primary", width='stretch'):
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
                
                st.success(f"Plot generated: {output_file.name}")
                
                # Display plot if PNG
                if output_format == 'png':
                    st.image(str(output_file), width='stretch')
                
                # Download button
                with open(output_file, 'rb') as f:
                    st.download_button(
                        label=f"Download {output_format.upper()}",
                        data=f,
                        file_name=output_file.name,
                        mime=f'image/{output_format}' if output_format != 'pdf' else 'application/pdf',
                        width='stretch'
                    )
                
            except Exception as e:
                st.error(f"Error generating plot: {e}")


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


def show_save_config_dialog():
    """Show dialog to save all plots configuration."""
    st.markdown("---")
    st.markdown("### Save All Plots Configuration")
    
    config_name = st.text_input("Configuration name", value="my_plots_config", key="save_config_name")
    config_description = st.text_area("Description", value="My plots configuration", key="save_config_desc")
    
    if st.button("💾 Save Now", type="primary"):
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        config_filename = f"{config_name}_{timestamp}.json"
        config_path = CONFIG_POOL_DIR / config_filename
        
        # Prepare configuration data with all plots
        plots_data = []
        for plot in st.session_state.plots:
            plots_data.append({
                'name': plot['name'],
                'pipeline': [s['config'] for s in plot['pipeline'] if s['config']],
                'plot_type': plot.get('plot_type', 'bar'),
                'plot_config': plot.get('plot_config', {})
            })
        
        config_data = {
            'name': config_name,
            'description': config_description,
            'timestamp': timestamp,
            'plots': plots_data
        }
        
        # Save to file
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Reload saved configs
        st.session_state.saved_configs = load_saved_configs()
        st.session_state.show_save_dialog = False
        
        st.success(f"Configuration saved: {len(plots_data)} plots in {config_filename}")
        
        if st.button("Close"):
            st.rerun()


def show_load_config_for_plot(current_plot, plot_idx):
    """Show dialog to load configuration into a specific plot."""
    st.markdown("---")
    st.markdown(f"### Load Configuration into '{current_plot['name']}'")
    
    # Reload configurations
    st.session_state.saved_configs = load_saved_configs()
    
    if not st.session_state.saved_configs:
        st.info("No saved configurations yet.")
        return
    
    st.info("Select a configuration to load into this plot:")
    
    for idx, config_info in enumerate(st.session_state.saved_configs):
        config_path = Path(config_info['path'])
        
        if not config_path.exists():
            continue
        
        with st.expander(f"{config_info['name']}", expanded=False):
            import datetime
            modified_time = datetime.datetime.fromtimestamp(config_info['modified'])
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.text(f"Description: {config_info['description']}")
            
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Show preview
                if 'plots' in config_data:
                    st.text(f"Contains {len(config_data['plots'])} plot(s)")
                    plot_names = [p.get('name', f'Plot {i+1}') for i, p in enumerate(config_data['plots'])]
                    
                    selected_plot = st.selectbox(
                        "Select which plot to load:",
                        options=range(len(config_data['plots'])),
                        format_func=lambda i: plot_names[i],
                        key=f"select_plot_{idx}"
                    )
                    
                    if st.button(f"Load '{plot_names[selected_plot]}'", key=f"load_btn_{idx}"):
                        plot_data = config_data['plots'][selected_plot]
                        load_plot_config_into(current_plot, plot_data)
                        st.session_state[f'show_load_for_plot_{current_plot["id"]}'] = False
                        st.success(f"Loaded configuration into {current_plot['name']}!")
                        st.rerun()
                else:
                    # Old single pipeline format
                    if st.button("Load Pipeline", key=f"load_old_{idx}"):
                        pipeline = []
                        pipeline_counter = 0
                        
                        for shaper_cfg in config_data.get('shapers', []):
                            shaper_type_map = {
                                'columnSelector': 'Column Selector',
                                'normalize': 'Normalize',
                                'mean': 'Mean Calculator',
                                'sort': 'Sort'
                            }
                            shaper_type = shaper_type_map.get(shaper_cfg.get('type'), shaper_cfg.get('type'))
                            pipeline.append({
                                'type': shaper_type,
                                'config': shaper_cfg,
                                'id': pipeline_counter
                            })
                            pipeline_counter += 1
                        
                        current_plot['pipeline'] = pipeline
                        current_plot['pipeline_counter'] = pipeline_counter
                        st.session_state[f'show_load_for_plot_{current_plot["id"]}'] = False
                        st.success("Legacy configuration loaded!")
                        st.rerun()
            
            except Exception as e:
                st.error(f"Error loading config: {e}")


def load_plot_config_into(target_plot, plot_data):
    """Load a plot configuration into an existing plot."""
    # Convert shapers config to pipeline format
    pipeline = []
    pipeline_counter = 0
    
    for shaper_cfg in plot_data.get('pipeline', []):
        shaper_type_map = {
            'columnSelector': 'Column Selector',
            'normalize': 'Normalize',
            'mean': 'Mean Calculator',
            'sort': 'Sort'
        }
        shaper_type = shaper_type_map.get(shaper_cfg.get('type'), shaper_cfg.get('type'))
        pipeline.append({
            'type': shaper_type,
            'config': shaper_cfg,
            'id': pipeline_counter
        })
        pipeline_counter += 1
    
    target_plot['pipeline'] = pipeline
    target_plot['pipeline_counter'] = pipeline_counter
    target_plot['plot_type'] = plot_data.get('plot_type', 'bar')
    target_plot['plot_config'] = plot_data.get('plot_config', {})


def show_load_workspace_dialog():
    """Show dialog to load entire workspace (all plots)."""
    st.markdown("---")
    st.markdown("### Load Workspace")
    
    # Reload configurations
    st.session_state.saved_configs = load_saved_configs()
    
    if not st.session_state.saved_configs:
        st.info("No saved workspaces yet.")
        return
    
    st.warning("⚠️ Loading a workspace will replace all current plots!")
    
    for idx, config_info in enumerate(st.session_state.saved_configs):
        config_path = Path(config_info['path'])
        
        if not config_path.exists():
            continue
        
        with st.expander(f"{config_info['name']}", expanded=False):
            import datetime
            modified_time = datetime.datetime.fromtimestamp(config_info['modified'])
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.text(f"Description: {config_info['description']}")
            
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                if 'plots' in config_data:
                    st.info(f"Contains {len(config_data['plots'])} plot(s)")
                    
                    if st.button(f"Load Workspace ({len(config_data['plots'])} plots)", 
                               key=f"load_workspace_{idx}", type="primary"):
                        # Load all plots
                        st.session_state.plots = []
                        st.session_state.plot_counter = 0
                        
                        for plot_data in config_data['plots']:
                            pipeline = []
                            pipeline_counter = 0
                            
                            for shaper_cfg in plot_data.get('pipeline', []):
                                shaper_type_map = {
                                    'columnSelector': 'Column Selector',
                                    'normalize': 'Normalize',
                                    'mean': 'Mean Calculator',
                                    'sort': 'Sort'
                                }
                                shaper_type = shaper_type_map.get(shaper_cfg.get('type'), shaper_cfg.get('type'))
                                pipeline.append({
                                    'type': shaper_type,
                                    'config': shaper_cfg,
                                    'id': pipeline_counter
                                })
                                pipeline_counter += 1
                            
                            st.session_state.plots.append({
                                'id': st.session_state.plot_counter,
                                'name': plot_data.get('name', f'Plot {st.session_state.plot_counter + 1}'),
                                'pipeline': pipeline,
                                'pipeline_counter': pipeline_counter,
                                'plot_type': plot_data.get('plot_type', 'bar'),
                                'plot_config': plot_data.get('plot_config', {}),
                                'processed_data': None
                            })
                            st.session_state.plot_counter += 1
                        
                        st.session_state.show_load_workspace = False
                        st.success(f"Loaded workspace with {len(st.session_state.plots)} plots! Use current data or upload new data separately.")
                        st.rerun()
                else:
                    st.warning("Legacy single-pipeline format. Use 'Load Config to This Plot' instead.")
            
            except Exception as e:
                st.error(f"Error: {e}")


def show_load_config_page():
    """Load a previously saved configuration."""
    st.markdown('<div class="step-header">', unsafe_allow_html=True)
    st.markdown("## Load Saved Configuration")
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Reload configurations
    st.session_state.saved_configs = load_saved_configs()
    
    if not st.session_state.saved_configs:
        st.info("No saved configurations yet. Configure a pipeline and save it to see it here.")
        return
    
    st.info(f"Found {len(st.session_state.saved_configs)} saved configuration(s)")
    
    for idx, config_info in enumerate(st.session_state.saved_configs):
        config_path = Path(config_info['path'])
        
        if not config_path.exists():
            st.error(f"Configuration file no longer exists: {config_info['name']}")
            continue
        
        with st.expander(f"{config_info['name']}", expanded=(idx==0)):
            import datetime
            modified_time = datetime.datetime.fromtimestamp(config_info['modified'])
            st.text(f"Modified: {modified_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.text(f"Description: {config_info['description']}")
            
            # Load and preview config
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                st.json(config_data.get('shapers', []))
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Load This Configuration", key=f"load_config_{idx}"):
                        try:
                            # Check if this is new multi-plot format or old single pipeline format
                            if 'plots' in config_data:
                                # New format: multiple plots
                                st.session_state.plots = []
                                st.session_state.plot_counter = 0
                                
                                for plot_data in config_data['plots']:
                                    # Convert shapers config to pipeline format
                                    pipeline = []
                                    pipeline_counter = 0
                                    
                                    for shaper_cfg in plot_data.get('pipeline', []):
                                        shaper_type_map = {
                                            'Column Selector': 'columnSelector',
                                            'Normalize': 'normalize',
                                            'Mean Calculator': 'mean',
                                            'Sort': 'sort',
                                            'Filter': 'conditionSelector'
                                        }
                                        shaper_type = shaper_type_map.get(shaper_cfg.get('type'), shaper_cfg.get('type'))
                                        pipeline.append({
                                            'type': shaper_type,
                                            'config': shaper_cfg,
                                            'id': pipeline_counter
                                        })
                                        pipeline_counter += 1
                                    
                                    st.session_state.plots.append({
                                        'id': st.session_state.plot_counter,
                                        'name': plot_data.get('name', f'Plot {st.session_state.plot_counter + 1}'),
                                        'pipeline': pipeline,
                                        'pipeline_counter': pipeline_counter,
                                        'plot_type': plot_data.get('plot_type', 'bar'),
                                        'plot_config': plot_data.get('plot_config', {}),
                                        'processed_data': None
                                    })
                                    st.session_state.plot_counter += 1
                                
                                st.success(f"Loaded {len(st.session_state.plots)} plots!")
                            else:
                                # Old format: single pipeline - convert to single plot
                                shapers_config = config_data.get('shapers', [])
                                pipeline = []
                                pipeline_counter = 0
                                
                                for shaper_cfg in shapers_config:
                                    shaper_type_map = {
                                        'Column Selector': 'columnSelector',
                                        'Normalize': 'normalize',
                                        'Mean Calculator': 'mean',
                                        'Sort': 'sort',
                                        'Filter': 'conditionSelector'
                                    }
                                    shaper_type = shaper_type_map.get(shaper_cfg.get('type'), shaper_cfg.get('type'))
                                    pipeline.append({
                                        'type': shaper_type,
                                        'config': shaper_cfg,
                                        'id': pipeline_counter
                                    })
                                    pipeline_counter += 1
                                
                                st.session_state.plots = [{
                                    'id': 0,
                                    'name': 'Imported Plot',
                                    'pipeline': pipeline,
                                    'pipeline_counter': pipeline_counter,
                                    'plot_type': 'bar',
                                    'plot_config': {},
                                    'processed_data': None
                                }]
                                st.session_state.plot_counter = 1
                                st.success("Legacy configuration converted to plot!")
                            
                            # Try to load associated CSV if available
                            if 'csv_path' in config_data and config_data['csv_path']:
                                csv_path = Path(config_data['csv_path'])
                                if csv_path.exists():
                                    data = pd.read_csv(csv_path, sep=r'\s+')
                                    st.session_state.data = data
                                    st.session_state.csv_path = str(csv_path)
                                    st.success("Data loaded!")
                                else:
                                    st.warning("Associated CSV file not found. Please upload data separately.")
                            
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error loading configuration: {e}")
                
                with col2:
                    if st.button("Delete", key=f"delete_config_{idx}"):
                        config_path.unlink()
                        st.session_state.saved_configs = load_saved_configs()
                        st.rerun()
            
            except Exception as e:
                st.error(f"Error reading configuration: {e}")


def show_data_managers_page():
    """Import and display the data managers page from modular implementation."""
    try:
        # Import the modular page
        from src.web.pages.data_managers import show_data_managers_page as show_managers
        show_managers()
    except ImportError as e:
        st.error(f"Error loading Data Managers page: {e}")
        st.info("Make sure src/web/pages/data_managers.py exists")


def show_portfolio_page():
    """Import and display the portfolio page."""
    try:
        from src.web.pages.portfolio import show_portfolio_page as show_port
        show_port()
    except ImportError as e:
        st.error(f"Error loading Portfolio page: {e}")
        st.info("Make sure src/web/pages/portfolio.py exists")


if __name__ == "__main__":
    main()

