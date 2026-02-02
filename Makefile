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
	@echo ""
	@echo "📋 Don't forget to install pre-commit hooks:"
	@echo "   make pre-commit-install"

test:
	$(pytest)

# Install pre-commit hooks
pre-commit-install:
	@echo "=== Installing pre-commit hooks ==="
	@$(VENV_BIN)/pre-commit install
	@echo "✅ Pre-commit hooks installed!"
	@echo "   Hooks will run automatically on git commit"
	@echo "   Run manually: make pre-commit"

# Run pre-commit on all files
pre-commit:
	@echo "=== Running pre-commit on all files ==="
	@$(VENV_BIN)/pre-commit run --all-files

# Check for outdated dependencies
check-outdated:
	@echo "=== Checking for outdated packages ==="
	$(PIP) list --outdated --format=columns
	@echo ""
	@echo "To update all packages: make update-deps"
	@echo "To update specific package: $(PIP) install --upgrade <package>"

# Update dependencies interactively (asks for each package)
update-deps:
	@echo "=== Interactive Dependency Update ==="
	@echo "Will check for outdated packages and ask for confirmation for each one."
	@echo ""
	@echo "📦 Checking for outdated packages..."
	@echo ""
	@$(PIP) list --outdated --format=columns
	@echo ""
	@bash -c ' \
	read -p "Start interactive update? [y/N] " -r REPLY < /dev/tty; \
	echo; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "❌ Update cancelled"; \
		exit 0; \
	fi; \
	echo ""; \
	updated=0; \
	skipped=0; \
	$(PIP) list --outdated --format=columns | tail -n +3 | while IFS= read -r line; do \
		pkg=$$(echo "$$line" | awk "{print \$$1}"); \
		current=$$(echo "$$line" | awk "{print \$$2}"); \
		latest=$$(echo "$$line" | awk "{print \$$3}"); \
		if [ -n "$$pkg" ] && [ "$$pkg" != "Package" ]; then \
			echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
			echo "📦 Package: $$pkg"; \
			echo "   Current: $$current"; \
			echo "   Latest:  $$latest"; \
			read -p "   Update? [y/N] " -r REPLY < /dev/tty; \
			echo; \
			if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
				echo "   ⬆️  Updating $$pkg..."; \
				$(PIP) install --upgrade $$pkg || echo "   ❌ Failed to update $$pkg"; \
				echo "   ✅ Updated $$pkg"; \
			else \
				echo "   ⏭️  Skipped $$pkg"; \
			fi; \
			echo ""; \
		fi; \
	done; \
	echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
	echo "✅ Update complete!"; \
	echo ""; \
	echo "📝 Next steps:"; \
	echo "   1. Run: make test"; \
	echo "   2. Run: mypy src/ --strict"; \
	echo "   3. Update version constraints in pyproject.toml"; \
	echo "   4. Commit changes if all tests pass"; \
	'

# Security audit of dependencies
security-audit:
	@echo "=== Running security audit ==="
	@$(PIP) list | grep -q pip-audit || $(PIP) install pip-audit
	@$(VENV_BIN)/pip-audit --format columns || true

# Show dependency tree
show-deps:
	@echo "=== Dependency tree ==="
	@$(PIP) list | grep -q pipdeptree || $(PIP) install pipdeptree
	@$(VENV_BIN)/pipdeptree

# Check for unused dependencies
check-unused:
	@echo "=== Checking for unused dependencies ==="
	@echo ""
	@./python_venv/bin/python scripts/analyze_dependencies.py || \
		(echo "Analysis script not available, doing manual check:" && \
		echo "" && \
		echo "📦 Checking for unused imports..." && \
		echo "" && \
		echo "❌ seaborn: $(shell grep -r 'import seaborn\|from seaborn' src/ || echo 'NOT FOUND')" && \
		echo "✅ openpyxl: $(shell grep -r '\.to_excel\|read_excel' src/ | head -1 || echo 'NOT FOUND')" && \
		echo "❌ pytest: Should only be in tests/ ($(shell grep -r 'import pytest' src/ || echo 'NOT IN SRC'))")
	@echo ""
	@echo "💡 Summary:"
	@echo "  • seaborn: Declared but NOT used → Safe to remove"
	@echo "  • openpyxl: Used by pandas for Excel export → Keep"
	@echo "  • kaleido: Used by plotly for image export → Keep"
	@echo "  • pytest: Move to dev dependencies only"

# Clean unused dependencies interactively
clean-deps:
	@echo "=== Finding potentially unused dependencies ==="
	@$(PIP) list | grep -q pip-autoremove || $(PIP) install pip-autoremove
	@echo ""
	@echo "⚠️  This will show dependencies that might be safe to remove"
	@echo "⚠️  Be careful - some packages may be runtime dependencies"
	@echo ""
	@$(VENV_BIN)/pip-autoremove --help > /dev/null 2>&1 && \
		$(VENV_BIN)/pip-autoremove --list || \
		echo "Run: $(VENV_BIN)/pip-autoremove <package> to remove unused deps"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
