VENV_NAME := python_venv
VENV_BIN := ./$(VENV_NAME)/bin
PYTHON := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
PYTEST := $(VENV_BIN)/pytest

PYTHON_SOURCES := app.py ring5 src scripts tests
PRODUCTION_SOURCES := ring5 src
TEST_DATA_DIR := tests/data/results-micro26-sens
TEST_DATA_URL := https://github.com/nikiitin/RING-5/releases/download/test-data-v1/test_data.tar.gz
TEST_DATA_TARBALL := test_data.tar.gz
MOCK_CSV := tests/data/mock/inputs/csv/configurer/configurer_test_case01.csv
COVERAGE_MIN := 84
NON_BROWSER_TESTS := tests/unit tests/integration tests/ui tests/ui_logic tests/ui_unit \
	tests/performance tests/tests_principle_compliance
OFT_VERSION := 4.6.0
OFT_SHA256 := 4c6194fdd59d5098edb7abd184a8c53002a139794d8a66f10997b27a140bb40a
OFT_CACHE_DIR := .cache/openfasttrace
OFT_JAR := $(OFT_CACHE_DIR)/openfasttrace-$(OFT_VERSION).jar
OFT_URL := https://repo1.maven.org/maven2/org/itsallcode/openfasttrace/openfasttrace/$(OFT_VERSION)/openfasttrace-$(OFT_VERSION).jar
OFT_SPEC_SOURCES := spec/oft/generated/features.md spec/oft/generated/requirements.md
OFT_CODE_SOURCES := app.py ring5 src scripts tests
OFT_DOCUMENTATION_SOURCES := docs spec/oft/README.md spec/oft/discovery-audit.md
OFT_SOURCES := $(OFT_SPEC_SOURCES) $(OFT_CODE_SOURCES) $(OFT_DOCUMENTATION_SOURCES)
OFT_NATIVE_REPORT := $(OFT_CACHE_DIR)/ring5-openfasttrace.html
OFT_REPORT := spec/oft/generated/report.html
OFT_EXECUTION_RESULTS_ARG = $(if $(EXECUTION_RESULTS),--execution-results "$(EXECUTION_RESULTS)",)

.PHONY: help venv install dev run playwright-install install-latex check-latex \
	test-data mock-data test test-unit test-nonbrowser test-api test-ci test-export test-latex \
	test-e2e test-visual \
	format format-check lint type-check arch-check comments-check docs-check dependency-check \
	docs-build docs-audit security-audit quality-gate package-check check-outdated pre-commit-install \
	pre-commit oft-generate oft-check oft-download oft-trace oft-trace-all oft-report oft-diff clean

help:
	@echo "RING-5 development targets"
	@echo ""
	@echo "  dev                 Install editable development and browser dependencies"
	@echo "  run                 Start the Streamlit application"
	@echo "  test-unit           Run fast unit tests"
	@echo "  test                Run non-browser tests, including serial exports"
	@echo "  test-latex          Run tests that require a local XeLaTeX installation"
	@echo "  test-api            Run the exact 100% line/branch public API gate"
	@echo "  test-ci             Run tests with the coverage gate"
	@echo "  test-e2e            Run Playwright browser tests"
	@echo "  quality-gate        Run architecture, docs, format, lint, types, and security"
	@echo "  oft-generate        Generate the OpenFastTrace feature catalog"
	@echo "  oft-check           Check catalog evidence, live registries, and generated files"
	@echo "  oft-trace           Trace the approved/current feature baseline"
	@echo "  oft-trace-all       Trace current and proposed features, exposing future gaps"
	@echo "  oft-report          Build the HTML traceability report from native OFT output"
	@echo "  oft-diff            Compare catalog and native coverage with BASE=<git-revision>"
	@echo "  docs-build          Build the documentation site with Bundler"
	@echo "  docs-audit          Audit generated routes and local site references"
	@echo "  package-check       Build and validate wheel and source distributions"
	@echo "  pre-commit          Run all pre-commit hooks"

venv:
	test -d $(VENV_NAME) || python3 -m venv $(VENV_NAME)
	$(PIP) install --upgrade pip

install: venv
	$(PIP) install .

dev: venv
	$(PIP) install -e ".[dev,ci,e2e]"
	$(VENV_BIN)/playwright install chromium
	$(MAKE) mock-data

run:
	$(VENV_BIN)/streamlit run app.py

playwright-install: venv
	$(VENV_BIN)/playwright install chromium

install-latex:
	@if command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update; \
		sudo apt-get install -y texlive-latex-base texlive-fonts-recommended \
			texlive-fonts-extra texlive-latex-extra texlive-xetex cm-super; \
	elif command -v brew >/dev/null 2>&1; then \
		brew install --cask mactex; \
	else \
		echo "Install TeX Live with XeLaTeX using your system package manager."; \
		exit 1; \
	fi

check-latex:
	@command -v latex >/dev/null || { echo "latex not found"; exit 1; }
	@command -v xelatex >/dev/null || { echo "xelatex not found"; exit 1; }
	@kpsewhich type1ec.sty >/dev/null || { echo "cm-super not found"; exit 1; }
	@echo "LaTeX export dependencies are available."

test-data:
	@if [ ! -d "$(TEST_DATA_DIR)" ]; then \
		mkdir -p tests/data; \
		if [ -f "$(TEST_DATA_TARBALL)" ]; then \
			tar xzf "$(TEST_DATA_TARBALL)" -C tests/data; \
		elif command -v curl >/dev/null 2>&1; then \
			curl --fail --location "$(TEST_DATA_URL)" | tar xz -C tests/data; \
		elif command -v wget >/dev/null 2>&1; then \
			wget --quiet --output-document=- "$(TEST_DATA_URL)" | tar xz -C tests/data; \
		else \
			echo "Install curl or wget, or provide $(TEST_DATA_TARBALL)."; \
			exit 1; \
		fi; \
	fi

mock-data: test-data
	@if [ ! -f "$(MOCK_CSV)" ]; then \
		$(PYTHON) scripts/generate_mock_fixtures.py; \
	fi

test-unit:
	$(PYTEST) tests/unit tests/ui_unit -m "not serial and not requires_latex" -q --no-cov

test-nonbrowser:
	$(PYTEST) $(NON_BROWSER_TESTS) -m "not serial and not requires_latex" \
		--timeout=60 --no-cov

test-export:
	$(PYTEST) tests/unit/test_plotly_download.py -m "serial" -n 0 --timeout=120 --no-cov

test-api: test-data mock-data
	$(PYTEST) -m "public_api" -n 0 --cov=ring5 --cov-branch \
		--cov-report=term-missing --cov-fail-under=100 --timeout=120

test-latex:
	$(PYTEST) tests/unit/test_matplotlib_download.py::TestMatplotlibPGF \
		-m "requires_latex" -n 0 --timeout=120 --no-cov

test: test-data mock-data
	$(MAKE) test-nonbrowser
	$(MAKE) test-export

test-ci: test-data mock-data test-api
	$(PYTEST) $(NON_BROWSER_TESTS) -m "not serial and not requires_latex" \
		--cov=src --cov=ring5 --cov-branch --cov-report=term-missing \
		--cov-report=xml --cov-fail-under=$(COVERAGE_MIN) --timeout=60

test-e2e:
	$(PYTEST) tests/e2e -m "requires_browser and not serial" \
		-n 2 --dist loadgroup --timeout=240 --timeout-method=thread --no-cov
	$(PYTEST) tests/e2e -m "requires_browser and serial" \
		-n 0 --timeout=240 --timeout-method=thread --no-cov

test-visual:
	@set -eu; \
		$(VENV_BIN)/streamlit run app.py --server.port 8502 --server.headless true & \
		server_pid=$$!; \
		trap 'kill $$server_pid 2>/dev/null || true' EXIT INT TERM; \
		sleep 5; \
		$(PYTEST) tests/visual -n 0 --timeout=120 --no-cov

format:
	find $(PYTHON_SOURCES) -name '*.py' -print0 | xargs -0 -n 1 $(VENV_BIN)/black --quiet

format-check:
	find $(PYTHON_SOURCES) -name '*.py' -print0 | xargs -0 -n 1 $(VENV_BIN)/black --check --diff --quiet

lint:
	$(VENV_BIN)/flake8 --jobs=1 $(PYTHON_SOURCES) --count --statistics

type-check:
	$(VENV_BIN)/mypy src ring5 --show-error-codes --pretty

arch-check:
	$(PYTHON) scripts/check_architecture.py

comments-check:
	$(PYTHON) scripts/check_comments.py

docs-check:
	$(PYTHON) scripts/check_public_docstrings.py
	$(PYTHON) scripts/check_doc_structure.py

docs-build:
	rm -rf _site
	JEKYLL_ENV=production BUNDLE_GEMFILE=$(CURDIR)/Gemfile bundle exec jekyll build \
		--source docs --destination _site

docs-audit:
	$(PYTHON) scripts/check_built_site.py

dependency-check:
	$(PYTHON) scripts/analyze_dependencies.py
	$(PIP) check

security-audit:
	$(VENV_BIN)/bandit -r ring5 src -c pyproject.toml -ll
	$(VENV_BIN)/pip-audit --progress-spinner off

oft-generate:
	$(PYTHON) scripts/generate_oft_inventory.py

oft-check:
	$(PYTHON) scripts/generate_oft_inventory.py --check

oft-download:
	@command -v java >/dev/null 2>&1 || { echo "Java 17 or newer is required."; exit 1; }
	@command -v curl >/dev/null 2>&1 || { echo "curl is required to download OFT."; exit 1; }
	@command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required."; exit 1; }
	@mkdir -p "$(OFT_CACHE_DIR)"
	@if [ -f "$(OFT_JAR)" ] && ! echo "$(OFT_SHA256)  $(OFT_JAR)" | sha256sum --check --status; then \
		echo "Discarding cached OFT JAR with an invalid checksum."; \
		rm -f "$(OFT_JAR)"; \
	fi
	@if [ ! -f "$(OFT_JAR)" ]; then \
		tmp_file=$$(mktemp "$(OFT_CACHE_DIR)/openfasttrace.XXXXXX"); \
		trap 'rm -f "$$tmp_file"' EXIT INT TERM; \
		curl --fail --location --silent --show-error "$(OFT_URL)" --output "$$tmp_file"; \
		echo "$(OFT_SHA256)  $$tmp_file" | sha256sum --check --status; \
		mv "$$tmp_file" "$(OFT_JAR)"; \
		trap - EXIT INT TERM; \
	fi

oft-trace: oft-check oft-download
	java -jar "$(OFT_JAR)" trace -w approved --v summary $(OFT_SOURCES)

oft-trace-all: oft-check oft-download
	java -jar "$(OFT_JAR)" trace --v summary $(OFT_SOURCES)

oft-report: oft-generate oft-download
	$(RM) "$(OFT_NATIVE_REPORT)"
	-java -jar "$(OFT_JAR)" trace --output-format html --report-verbosity all \
		--details-section-display collapse --output-file "$(OFT_NATIVE_REPORT)" $(OFT_SOURCES)
	@test -s "$(OFT_NATIVE_REPORT)"
	$(PYTHON) scripts/generate_oft_html_report.py \
		--oft-html "$(OFT_NATIVE_REPORT)" --output "$(OFT_REPORT)" $(OFT_EXECUTION_RESULTS_ARG)
	$(PYTHON) scripts/generate_oft_inventory.py --check
	@echo "Open $(OFT_REPORT) in a browser."

oft-diff:
	@test -n "$(BASE)" || { echo "Use: make oft-diff BASE=<git-revision>"; exit 2; }
	$(PYTHON) scripts/diff_oft_inventory.py "$(BASE)"

quality-gate: arch-check comments-check docs-check dependency-check oft-check format-check lint type-check security-audit
	@echo "Quality gate passed."

package-check:
	rm -rf build dist ring5.egg-info
	$(PYTHON) -m build
	$(VENV_BIN)/twine check dist/*
	$(PYTHON) scripts/check_package_contents.py

check-outdated:
	$(PIP) list --outdated --format=columns

pre-commit-install:
	$(VENV_BIN)/pre-commit install

pre-commit:
	$(VENV_BIN)/pre-commit run --all-files

clean:
	rm -rf build dist _site .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
