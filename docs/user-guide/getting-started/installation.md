---
title: "Installation"
parent: Getting Started
grand_parent: User Guide
nav_order: 1
---

# Installation

This page covers how to install and run RING-5 on your local machine.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.12, 3.13, or 3.14.** Check your version with `python3 --version`.
- **pip.** Included with most Python installations. Verify with `pip --version`.
- **Perl 5.** Required by the gem5 stats parser. Most Linux and macOS systems include Perl by default. Verify with `perl --version`.
- **Git.** Needed to clone the repository.

## Clone the Repository

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
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
- **openpyxl** -- Excel file support

For the complete contributor environment, install the development, CI, and browser-test groups:

```bash
pip install -e ".[dev,ci,e2e]"
playwright install chromium
```

## Platform-Specific Instructions

The steps above work on any platform once Python 3.12, Perl, and Git are available. The sections below show how to obtain those prerequisites on each operating system.

### Linux (Ubuntu/Debian)

```bash
# Install Python 3.12, the venv module, pip, and Git
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip git perl

# Clone and install
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev,ci,e2e]"
```

### macOS

RING-5 installs cleanly on macOS using [Homebrew](https://brew.sh) to provide Python and Git.

```bash
# Install Homebrew if you do not already have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.12 and Git (Perl ships with macOS)
brew install python@3.12 git

# Clone and install
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev,ci,e2e]"
```

### Windows

On Windows, install Python 3.12 from [python.org](https://www.python.org/downloads/) and Git from [git-scm.com](https://git-scm.com/download/win). Because the gem5 stats parser relies on Perl, also install [Strawberry Perl](https://strawberryperl.com/), which provides a Perl 5 distribution for Windows.

```powershell
# After installing Python 3.12, Git, and Strawberry Perl:

# Clone the repository
git clone https://github.com/nikiitin/RING-5.git
cd RING-5

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -e ".[dev,ci,e2e]"
```

## Dependencies

RING-5 organizes its requirements into core and optional development, CI, and browser-test groups
declared in `pyproject.toml`.

### Core Dependencies

Installed by `pip install -e .` and required to run the application:

- **streamlit** -- web application framework
- **pandas** -- DataFrame operations for simulation data
- **numpy** and **scipy** -- numerical computation and statistical analysis
- **matplotlib** -- publication-quality static plot rendering
- **plotly** and **kaleido** -- interactive plot rendering and image export
- **openpyxl** -- Excel file support

### Development Dependencies

Installed by `pip install -e ".[dev,ci,e2e]"` and used for testing, type checking, formatting,
security checks, and browser automation:

- **pytest** -- testing framework
- **pytest-order**, **pytest-randomly**, and **pytest-xdist** -- deterministic ordering,
  order-dependence detection, and parallel execution
- **mypy** -- static type checking
- **black** -- code formatting
- **flake8** -- linting

### Full List

See `pyproject.toml` for the complete, authoritative dependency list, including transitive and optional packages.

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

You can also run the test suite to confirm the development environment is healthy:

```bash
make test
```

## Updating

To update an existing installation to the latest version:

```bash
# Pull the latest changes
git pull origin main

# Update dependencies inside your virtual environment
source venv/bin/activate
pip install -e ".[dev,ci,e2e]"

# Confirm everything still works
make test
```

## Uninstallation

To remove RING-5 from your machine:

```bash
# Delete the virtual environment
rm -rf venv

# Remove the installed package
pip uninstall ring5

# Delete the repository (if desired)
cd ..
rm -rf ring5
```

## Troubleshooting

**Port 8501 is already in use.**
Another Streamlit instance or application may be occupying the default port. Either stop the other process or specify a different port:

```bash
streamlit run app.py --server.port 8502
```

**ModuleNotFoundError for a dependency.**
Make sure your virtual environment is activated (`source venv/bin/activate`) and that you ran
`pip install -e .` from the project root. Contributors should install
`pip install -e ".[dev,ci,e2e]"`. You can verify installed packages with `pip list`.

**Perl not found (parser errors).**
The gem5 stats parser relies on Perl scripts. If you see errors related to Perl when parsing stats files, install Perl through your system package manager:

```bash
# Linux (Debian/Ubuntu)
sudo apt install perl

# macOS
brew install perl

# Windows: install Strawberry Perl from https://strawberryperl.com/
```

**Wrong Python version.**
Check your version with `python3 --version`; supported releases are 3.12, 3.13, and 3.14. If
your default `python3` points elsewhere, create the virtual environment with an explicit supported
interpreter, for example `python3.12 -m venv venv`.

**Virtual environment not activating.**
The activation command differs by platform:

```bash
# Linux/macOS
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate.bat
```

**Permission errors on Linux/macOS.**
Do not use `sudo` to install RING-5. Instead, ensure your user has write permissions to the project directory (for example, `chmod -R u+w ring5/`).

**ImportError after installation.**
Reinstall in editable mode from the project root:

```bash
pip install -e ".[dev,ci,e2e]"
```

**Blank page or connection refused.**
Streamlit may take a few seconds to start on first launch. Wait for the "Local URL" message in your terminal before opening the browser. If the problem persists, check that no firewall rules are blocking local connections on the configured port.
