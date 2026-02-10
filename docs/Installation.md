---
title: "Installation"
nav_order: 3
---

# Installation Guide

Complete installation instructions for RING-5 on all platforms.

## System Requirements

### Hardware

- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 500MB for installation, additional space for data
- **CPU**: Multi-core recommended for parallel parsing

### Software

- **Python**: 3.12 or higher
- **Operating System**: Linux, macOS, or Windows
- **Git**: For cloning repository

## Quick Installation

```bash
# Clone repository
git clone https://github.com/vnicolas/RING-5.git
cd RING-5

# Create virtual environment
python3 -m venv python_venv
source python_venv/bin/activate # Linux/macOS
# python_venv\Scripts\activate # Windows

# Install dependencies
make dev

# Verify installation
python scripts/verify_installation.py
```

## Platform-Specific Instructions

### Linux (Ubuntu/Debian)

```bash
# Install Python 3.12
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip git

# Clone and install
git clone https://github.com/vnicolas/RING-5.git
cd RING-5
python3.12 -m venv python_venv
source python_venv/bin/activate
make dev
```

### macOS

```bash
# Install Homebrew if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.12
brew install python@3.12 git

# Clone and install
git clone https://github.com/vnicolas/RING-5.git
cd RING-5
python3.12 -m venv python_venv
source python_venv/bin/activate
make dev
```

### Windows

```powershell
# Install Python 3.12 from python.org
# Install Git from git-scm.com

# Clone repository
git clone https://github.com/vnicolas/RING-5.git
cd RING-5

# Create virtual environment
python -m venv python_venv
python_venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Development Installation

For contributors and developers:

```bash
# Clone repository
git clone https://github.com/vnicolas/RING-5.git
cd RING-5

# Create virtual environment
python3 -m venv python_venv
source python_venv/bin/activate

# Install with development tools
make dev

# Verify installation
python scripts/verify_installation.py

# Run tests
make test

# Check types
mypy src/ --strict

# Format code
black src/ tests/
```

## Dependencies

### Core Dependencies

- **streamlit** - Web interface
- **pandas** - Data manipulation
- **plotly** - Interactive plotting
- **pyyaml** - Configuration files

### Development Dependencies

- **pytest** - Testing framework
- **mypy** - Type checking
- **black** - Code formatting
- **flake8** - Linting

### Full List

See `pyproject.toml` for complete dependency list.

## Troubleshooting

### Python Version Issues

```bash
# Check Python version
python3 --version # Should be 3.12+

# If wrong version, specify explicitly
python3.12 -m venv python_venv
```

### Virtual Environment Not Activating

```bash
# Linux/macOS
source python_venv/bin/activate

# Windows (PowerShell)
python_venv\Scripts\Activate.ps1

# Windows (CMD)
python_venv\Scripts\activate.bat
```

### Permission Errors

```bash
# Linux/macOS: Don't use sudo
# Instead ensure user has write permissions
chmod -R u+w RING-5/
```

### ImportError After Installation

```bash
# Reinstall in development mode
pip install -e .
# Or
make clean
make dev
```

### Missing Perl

Some parsing features require Perl:

```bash
# Linux
sudo apt install perl

# macOS
brew install perl

# Windows
# Download from strawberryperl.com
```

## Verification

After installation, verify everything works:

```bash
# Run verification script
python scripts/verify_installation.py

# Should output:
# Python 3.12+ detected
# All dependencies installed
# Perl available
# RING-5 ready to use

# Run tests
make test

# Launch app (optional)
streamlit run app.py
```

## Updating

To update to the latest version:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
source python_venv/bin/activate
make dev

# Run tests
make test
```

## Uninstallation

```bash
# Delete virtual environment
rm -rf python_venv

# Remove installed package
pip uninstall ring5

# Delete repository (if desired)
cd ..
rm -rf RING-5
```

## Next Steps

- [Quick Start Guide](Quick-Start) - Get started in 5 minutes
- [First Analysis](First-Analysis) - Complete walkthrough
- [Web Interface Guide](Web-Interface) - Master the UI

**Need help?** [Open an issue](https://github.com/vnicolas/RING-5/issues)
