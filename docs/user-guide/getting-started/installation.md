# Installation

This page covers how to install and run RING-5 on your local machine.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.12 or later.** Check your version with `python3 --version`.
- **pip.** Included with most Python installations. Verify with `pip --version`.
- **Perl 5.** Required by the gem5 stats parser. Most Linux and macOS systems include Perl by default. Verify with `perl --version`.
- **Git.** Needed to clone the repository.

## Clone the Repository

```bash
git clone https://github.com/your-org/ring5.git
cd ring5
```

## Create a Virtual Environment

Using a virtual environment keeps RING-5 dependencies isolated from your system Python.

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows, activate the environment with `venv\Scripts\activate` instead.

## Install Dependencies

Install the core dependencies defined in `pyproject.toml`:

```bash
pip install -e .
```

This installs the following packages and their transitive dependencies:

- **pandas** -- DataFrame operations for simulation data
- **numpy** and **scipy** -- numerical computation and statistical analysis
- **matplotlib** -- publication-quality static plot rendering
- **plotly** and **kaleido** -- interactive plot rendering and image export
- **streamlit** -- web application framework
- **jsonschema** -- configuration and portfolio validation
- **openpyxl** -- Excel file support

If you plan to run the test suite or use development tools, install the optional dev dependencies as well:

```bash
pip install -e ".[dev]"
```

## Run the Application

Launch RING-5 from the project root directory:

```bash
streamlit run app.py
```

You should see output similar to:

```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

Open `http://localhost:8501` in your browser. You should see the RING-5 Interactive Analyzer with the Data Source page displayed and the sidebar navigation expanded.

## Verify the Installation

To confirm everything is working correctly:

1. Open the application in your browser at `http://localhost:8501`.
2. You should see the sidebar with five navigation buttons: Data Source, Data Managers, Manage Plots, Save/Load Portfolio, and Documentation.
3. On the Data Source page, select "I already have CSV data." The page should display a success message without errors.

If you see the application load without warnings or tracebacks, the installation is complete.

## Troubleshooting

**Port 8501 is already in use.**
Another Streamlit instance or application may be occupying the default port. Either stop the other process or specify a different port:

```bash
streamlit run app.py --server.port 8502
```

**ModuleNotFoundError for a dependency.**
Make sure your virtual environment is activated (`source venv/bin/activate`) and that you ran `pip install -e .` from the project root. You can verify installed packages with `pip list`.

**Perl not found (parser errors).**
The gem5 stats parser relies on Perl scripts. If you see errors related to Perl when parsing stats files, install Perl through your system package manager (for example, `sudo apt install perl` on Debian/Ubuntu).

**Blank page or connection refused.**
Streamlit may take a few seconds to start on first launch. Wait for the "Local URL" message in your terminal before opening the browser. If the problem persists, check that no firewall rules are blocking local connections on the configured port.
