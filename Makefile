# Virtual environment settings
VENV_NAME = python_venv
VENV_BIN = ./$(VENV_NAME)/bin
PYTHON = python3
PIP = $(VENV_BIN)/pip
pytest = $(VENV_BIN)/pytest

# Create virtual environment if it doesn't exist
venv:
	test -d $(VENV_NAME) || $(PYTHON) -m venv $(VENV_NAME)
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install .

dev: venv
	$(PIP) install -e ".[dev]"

test:
	$(pytest)

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
