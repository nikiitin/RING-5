# 🚀 RING-5 Interactive Web Application

**Modern, interactive dashboard for gem5 data analysis and visualization**

![RING-5 Dashboard](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production-success?style=for-the-badge)

---

## ✨ Features

### ⚙️ **Data Source Selection** (NEW!)
Choose between two input methods:
- **🔍 Parse gem5 Stats**: Direct parsing of raw gem5 output files
  - Interactive variable selection
  - Support for scalar, vector, distribution, and configuration variables
  - Optional compression for remote filesystems (SSHFS)
  - Automatic CSV generation
- **📄 Upload CSV**: Pre-parsed CSV data
  - Drag-and-drop or paste data
  - Auto-detect separators

### 📤 **Interactive Data Upload**
- **File Upload**: Drag-and-drop CSV files
- **Paste Data**: Direct CSV data input
- **Auto-Detection**: Automatically detects separators (comma, whitespace)
- **Live Preview**: Real-time data preview with statistics
- **Column Analysis**: Type detection, null values, unique counts

### 🔧 **Visual Pipeline Configuration**
No JSON editing required! Configure your data pipeline through an intuitive UI:

- **📌 Column Selector**: Multi-select dropdown for column filtering
- **📊 Normalizer**: Interactive baseline selection with grouping options
- **📈 Mean Calculator**: Choose arithmetic/geometric/harmonic means
- **🔢 Sort**: Custom ordering with drag-and-drop interface
- **⚙️ Real-time Preview**: See configuration JSON live

### 📊 **Interactive Plot Builder**
Create professional visualizations without code:

- **Plot Types**: Bar, Line, Scatter, Box, Heatmap
- **Data Mapping**: Dropdown selection for X, Y, Hue
- **Style Controls**: Title, labels, dimensions, rotations
- **Live Generation**: Instant plot rendering
- **Multiple Formats**: PNG, PDF, SVG export
- **In-Browser Preview**: View plots immediately

### 📈 **Results Dashboard**
Comprehensive data analysis and export:

- **Summary Statistics**: Automatic descriptive statistics
- **Interactive Tables**: Sortable, filterable data views
- **Multiple Export Formats**:
  - 📄 CSV (comma-separated)
  - 📋 JSON (records format)
  - 📊 Excel (XLSX with formatting)
- **One-Click Downloads**: Direct browser downloads

---

## 🏃 Quick Start

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Launch Application**
```bash
streamlit run app.py
```

### 3. **Open Browser**
The app automatically opens at:
- **Local**: http://localhost:8501
- **Network**: http://YOUR_IP:8501

---

## 📖 User Guide

### Step 1: Choose Data Source (NEW!)
1. Navigate to **⚙️ Data Source** page
2. Select input method:

   **Option A: Parse gem5 Stats Files**
   - Choose "🔍 Parse gem5 Stats Files"
   - Configure parser settings:
     - **Stats Directory**: Path to gem5 output (e.g., `/path/to/gem5/runs`)
     - **File Pattern**: Filename to search (e.g., `stats.txt`)
     - **Compression**: Enable for remote/SSHFS filesystems
   
   - Define variables to extract:
     - **Scalar**: Single values (simTicks, IPC, cache misses)
     - **Vector**: Arrays (per-core stats, cache breakdown)
     - **Distribution**: Statistical distributions
     - **Configuration**: Metadata (benchmark, config, seed)
   
   - Click **▶️ Parse gem5 Stats Files**
   - Wait for parsing to complete
   - Review parsed data preview
   
   **Option B: Upload CSV**
   - Choose "📄 I already have CSV data"
   - Proceed to Upload Data page

### Step 2: Upload Data (CSV Mode)
### Step 2: Upload Data (CSV Mode)
1. Navigate to **📤 Upload Data** page
2. Choose upload method:
   - **Upload CSV File**: Click or drag-and-drop
   - **Paste Data**: Copy-paste CSV text
3. Review data preview and statistics

*(Skip this step if using parser - data is already loaded)*

### Step 3: Configure Pipeline
1. Navigate to **🔧 Configure Pipeline** page
2. Enable and configure shapers:
   
   **Column Selector**
   - Select columns to keep
   - Reduces data dimensions
   
   **Normalizer** (Optional)
   - Choose variables to normalize
   - Select baseline configuration
   - Define grouping columns
   - Values normalized to baseline = 1.0
   
   **Mean Calculator** (Optional)
   - Select mean type: arithmean, geomean, harmean
   - Choose variables to aggregate
   - Define grouping column
   - Specify replacing column for mean label
   
   **Sort** (Optional)
   - Select column to sort
   - Define custom order
   - Drag-and-drop interface

3. Click **▶️ Apply Configuration**
4. Review processed data preview

### Step 4: Generate Plots
1. Navigate to **📊 Generate Plots** page
2. Configure plot:
   
   **Data Configuration**
   - Select plot type (bar, line, scatter, box, heatmap)
   - Choose X-axis column
   - Choose Y-axis column (numeric)
   - Optional: Select hue column for grouping
   
   **Style Configuration**
   - Set plot title
   - Customize axis labels
   - Adjust dimensions (width, height)
   - Configure label rotation
   
   **Output Configuration**
   - Choose format: PNG, PDF, SVG
   - Set filename

3. Click **🎨 Generate Plot**
4. Preview in browser
5. Download generated file

### Step 5: Export Results
1. Navigate to **📈 Results** page
2. Review summary statistics
3. Browse processed data table
4. Download in preferred format:
   - **CSV**: For spreadsheets
   - **JSON**: For programmatic use
   - **Excel**: For reports

---

## 🔍 gem5 Stats Parser

### Overview
RING-5 includes a high-performance parser for gem5 statistics files. The parser:
- Extracts variables from raw gem5 output (stats.txt)
- Supports multiple variable types (scalar, vector, distribution, configuration)
- Handles recursive directory searches
- Optional compression for remote filesystems
- Generates CSV output for analysis

### When to Use Parser vs CSV Upload

**Use Parser (🔍) when:**
- You have raw gem5 stats.txt files
- Stats files are on remote cluster (via SSHFS)
- You want to extract specific variables
- You need automatic CSV generation

**Use CSV Upload (📄) when:**
- You already have parsed CSV data
- Data is from previous RING-5 runs
- Data is from other tools
- You want quick iteration on analysis

### Compression Feature

**What is it?**
The compression feature copies stats files from remote filesystems (e.g., SSHFS-mounted cluster) to local storage before parsing.

**Why use it?**
- **Performance**: Remote filesystem access is slow (especially SSHFS)
- **Reliability**: Reduces network-related parsing failures
- **Speed**: 10-100x faster parsing on local files

**When to enable:**
- ✅ Stats files on SSHFS-mounted remote cluster
- ✅ Network filesystem (NFS, SMB)
- ✅ Slow I/O performance
- ❌ Files already local
- ❌ SSD/NVMe local storage

**How it works:**
1. Scanner finds all matching stats files
2. Files copied to local temp directory
3. Parser processes local copies
4. CSV generated from local data

### Variable Types

| Type | Description | Example | Use Case |
|------|-------------|---------|----------|
| **scalar** | Single numeric value | `simTicks`, `system.cpu.ipc` | Performance metrics |
| **vector** | Array of values | Per-core stats, cache breakdown | Multi-dimensional data |
| **distribution** | Statistical distribution | Latency histograms | Distribution analysis |
| **configuration** | Metadata string | `benchmark_name`, `config_id`, `seed` | Grouping, filtering |

### Example Parser Configuration

```python
# Parsing gem5 stats from remote cluster
Stats Path: /mnt/cluster/gem5_runs
File Pattern: stats.txt
Compression: ✅ Enabled (SSHFS filesystem)

Variables:
- simTicks (scalar)           # Execution time
- system.cpu.ipc (scalar)     # IPC
- benchmark_name (configuration)  # Benchmark
- config_description (configuration)  # Config
- random_seed (configuration)  # Seed
```

**Result**: Parsed CSV with columns:
```
simTicks  system.cpu.ipc  benchmark_name  config_description  random_seed
1234567   1.85           bzip2           baseline            1
2345678   1.92           gcc             opt_l1              1
...
```

---

## 🎨 UI Components

### Navigation Sidebar
- **Page Selection**: Radio button navigation
- **About Section**: Quick reference
- **Clear Data**: Reset application state

### Main Content Area
- **Step Headers**: Clear workflow progression
- **Expandable Sections**: Organized controls
- **Metrics Display**: Key statistics
- **Interactive Tables**: Sortable data views
- **Live Previews**: Real-time feedback

### Visual Design
- **Modern Gradient Header**: Professional branding
- **Color-Coded Alerts**: Success (green), info (blue), warning (orange)
- **Responsive Layout**: Works on different screen sizes
- **Consistent Spacing**: Clean, organized interface

---

## 🔧 Advanced Configuration

### Streamlit Configuration
Create `~/.streamlit/config.toml`:

```toml
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### Custom Port
```bash
streamlit run app.py --server.port 8080
```

### Network Access
```bash
streamlit run app.py --server.address 0.0.0.0
```

### Production Deployment
```bash
streamlit run app.py --server.headless true --server.enableCORS false
```

---

## 🏗️ Architecture

### Technology Stack
- **Frontend**: Streamlit (Python-based reactive UI)
- **Data Processing**: pandas, scipy, numpy
- **Visualization**: matplotlib, seaborn (via RING-5 plotting module)
- **Export**: openpyxl (Excel), built-in CSV/JSON

### Integration with RING-5
The web app integrates seamlessly with RING-5 architecture:

```
app.py
├── Data Upload → pandas.DataFrame
├── Pipeline Config → ShaperFactory
│   ├── ColumnSelector
│   ├── Normalizer
│   ├── Mean Calculator
│   └── Sort
├── Plot Generation → PlotFactory + PlotRenderer
│   ├── BarPlot
│   ├── LinePlot
│   ├── ScatterPlot
│   ├── BoxPlot
│   └── HeatmapPlot
└── Export → CSV/JSON/Excel
```

### Session State Management
```python
st.session_state.data           # Original uploaded data
st.session_state.processed_data # After shapers applied
st.session_state.config         # Pipeline configuration
st.session_state.temp_dir       # Temporary file storage
```

---

## 🚀 Deployment Options

### Local Development
```bash
streamlit run app.py
```

### Docker Container
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t ring5-app .
docker run -p 8501:8501 ring5-app
```

### Cloud Deployment
- **Streamlit Cloud**: One-click deployment from GitHub
- **Heroku**: Add `Procfile` with Streamlit command
- **AWS/GCP**: Deploy as containerized service

---

## 📊 Example Workflow

### Complete Analysis Pipeline

1. **Upload gem5 Statistics**
   - Upload `stats.csv` with benchmark results
   - Contains columns: benchmark, config, metric1, metric2, seeds

2. **Configure Data Pipeline**
   ```
   ColumnSelector: [benchmark, config, metric1, metric2]
   Normalizer: baseline=config_A, groupBy=[benchmark]
   Mean: geomean, groupBy=config, replacingColumn=seeds
   Sort: config order=[A, B, C, D]
   ```

3. **Generate Visualizations**
   ```
   Type: bar
   X: config
   Y: metric1
   Hue: benchmark
   Title: "Normalized Performance by Configuration"
   ```

4. **Export Results**
   - Download processed CSV for reports
   - Download plot PDFs for presentations
   - Export Excel for stakeholders

---

## 🛠️ Troubleshooting

### App Won't Start
```bash
# Check Python version
python --version  # Should be 3.12+

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Clear Streamlit cache
rm -rf ~/.streamlit/cache
```

### Data Upload Fails
- Check CSV format (valid separators)
- Ensure file encoding is UTF-8
- Try "Paste Data" method for troubleshooting

### Plots Not Generating
- Verify processed data exists (run pipeline first)
- Check column selections (X/Y must exist in data)
- Review browser console for errors

### Performance Issues
- Reduce data size with Column Selector
- Use multiprocessing for batch plots (via original CLI)
- Clear old session data with "🗑️ Clear All Data"

---

## 🎯 Tips & Best Practices

### Data Preparation
✅ **DO**: Use consistent column naming
✅ **DO**: Clean data before upload (remove nulls)
✅ **DO**: Use meaningful column names
❌ **DON'T**: Upload extremely large files (>100MB)

### Pipeline Configuration
✅ **DO**: Apply Column Selector first (reduce dimensions)
✅ **DO**: Normalize before calculating means
✅ **DO**: Sort as final step
❌ **DON'T**: Apply contradictory transformations

### Visualization
✅ **DO**: Use appropriate plot types (bar for comparisons, line for trends)
✅ **DO**: Set clear titles and labels
✅ **DO**: Choose contrasting colors for hue
❌ **DON'T**: Overcrowd plots with too many categories

---

## 📝 Future Enhancements

- [ ] **Multi-file Upload**: Batch processing of multiple CSVs
- [ ] **Template Management**: Save/load pipeline configurations
- [ ] **Advanced Filtering**: SQL-like data filtering
- [ ] **Custom Themes**: User-defined color schemes
- [ ] **Collaboration**: Share sessions via URLs
- [ ] **API Mode**: RESTful API for programmatic access
- [ ] **Real-time Updates**: Live data streaming
- [ ] **Export Templates**: Customizable report generation

---

## 📄 License

See LICENSE file in repository root.

---

## 🤝 Contributing

RING-5 is a complete Python rewrite of gem5 data analysis tools. Contributions welcome!

### Development Setup
```bash
# Clone repository
git clone <repo-url>
cd RING-5

# Create virtual environment
python -m venv python_venv
source python_venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Launch app
streamlit run app.py
```

---

## 📞 Support

For issues, questions, or feature requests:
1. Check this README
2. Review example configurations in `examples/`
3. Run verification: `python verify_installation.py`
4. Check test suite: `pytest tests/ -v`

---

**Built with ❤️ using Python, Streamlit, and the power of RING-5**

*Transform gem5 data into insights with zero code!*
