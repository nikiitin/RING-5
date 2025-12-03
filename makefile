# Makefile for RING-5 Pure Python Edition
# Manages Python dependencies and project setup

.PHONY: build install test clean help

# Default target
all: build

# Help target
help:
	@echo "RING-5 Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  build     - Check dependencies and install everything"
	@echo "  install   - Install Python dependencies"
	@echo "  test      - Run all tests"
	@echo "  clean     - Remove virtual environment"
	@echo "  help      - Show this help message"

# Build: check dependencies and install
build: check_python_dependencies
	@echo "Build finished successfully"

# Install dependencies
install: check_pip_dependencies
	@echo "Dependencies installed successfully"

#### PYTHON DEPENDENCIES ####

check_python_dependencies: check_python check_pip
	@echo "All python dependencies are solved"

check_python: check_python_version create_virtualenv
	@echo "Python is correctly installed and configured"

# Check if python is installed and version is greater than 3.8
check_python_version:
	@which python3 > /dev/null || (echo "Python3 is not installed. Please install python >= 3.8 before proceeding."; exit 1)
	@python3 -c "import sys; assert sys.version_info >= (3,8), 'Python version should be greater than 3.8'"

# Create a virtual environment for the project
create_virtualenv:
	@python3 -m venv --help > /dev/null || (echo "Virtualenv is not installed. Please install python >= 3.8 before proceeding."; exit 1)
	@if [ ! -d python_venv ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv python_venv; \
		echo "Virtual environment created successfully"; \
	else \
		echo "Virtual environment already exists"; \
	fi

check_pip: install_pip check_pip_dependencies
	@python3 -m pip > /dev/null || (echo "Could not manage to execute pip... aborting."; exit 1)

# Install pip
install_pip:
	@echo "Checking if pip is installed..."
	@. python_venv/bin/activate && python3 -m pip --version 2>/dev/null 1>/dev/null || \
	( \
		echo "pip is not installed. Installing..."; \
		curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py; \
		python3 get-pip.py; \
		rm get-pip.py; \
		echo "pip installed successfully"; \
	)

# Check if pip dependencies are solved
check_pip_dependencies: requirements.txt
	@echo "Checking if requirements.txt exists..."
	@if [ ! -f requirements.txt ]; then \
		echo "requirements.txt not found. Please create it before proceeding."; \
		exit 1; \
	fi
	@echo "Installing python dependencies from requirements.txt in python_venv..."
	@( \
		. python_venv/bin/activate && \
		python3 -m pip install --upgrade pip && \
		pip install -r requirements.txt && \
		echo "Python dependencies installed successfully" \
	)

#### TEST OBJECTIVES ####

# Main test objective
test:
	@echo "Running tests..."
	@. python_venv/bin/activate && python3 -m pytest tests/ -v

# Clean up
clean:
	@echo "Cleaning up..."
	@rm -rf python_venv
	@rm -rf __pycache__
	@rm -rf src/__pycache__
	@rm -rf src/*/__pycache__
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "Cleanup complete"