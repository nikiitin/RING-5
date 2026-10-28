RING5_NATIVE_THREADS ?= 2
E2E_WORKERS ?= 2
export OPENBLAS_NUM_THREADS := $(RING5_NATIVE_THREADS)
export OMP_NUM_THREADS := $(RING5_NATIVE_THREADS)
export MKL_NUM_THREADS := $(RING5_NATIVE_THREADS)
export NUMEXPR_NUM_THREADS := $(RING5_NATIVE_THREADS)
export VECLIB_MAXIMUM_THREADS := $(RING5_NATIVE_THREADS)

VENV_NAME := python_venv
UV_VERSION := 0.13.5
UV ?= uvx --isolated --from uv==$(UV_VERSION) uv
VENV_BIN := $(VENV_NAME)/bin
PYTHON := $(VENV_BIN)/python
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
OFT_VERSION := 4.11.0
OFT_SHA256 := f094cd314f0fc4236f513f66fb39260a16f72e2320beb6b4fdeb7940b9b8cf87
OFT_CACHE_DIR := .cache/openfasttrace
OFT_JAR := $(OFT_CACHE_DIR)/openfasttrace-$(OFT_VERSION).jar
OFT_URL := https://repo1.maven.org/maven2/org/itsallcode/openfasttrace/openfasttrace/$(OFT_VERSION)/openfasttrace-$(OFT_VERSION).jar
OFT_NATIVE_REPORT := $(OFT_CACHE_DIR)/ring5-openfasttrace.html
OFT_REPORT := spec/oft/generated/report.html
OFT_EXECUTION_RESULTS_ARG = $(if $(EXECUTION_RESULTS),--execution-results "$(EXECUTION_RESULTS)",)

.PHONY: help venv install sync-dev dev lock run example-portfolio playwright-install chrome-install install-latex check-latex \
	test-data mock-data test test-unit test-nonbrowser test-api test-ci test-export test-latex \
	test-e2e test-visual \
	format format-check lint type-check arch-check comments-check docs-check dependency-check \
	docs-build docs-audit docs-security security-audit quality-gate package-check check-outdated pre-commit-install \
	pre-commit oft-generate oft-check oft-download oft-trace oft-trace-all oft-report oft-diff clean

help:
	@echo "RING-5 development targets"
	@echo ""
	@echo "  dev                 Install editable development and browser dependencies"
	@echo "  sync-dev            Reproduce development dependencies from uv.lock"
	@echo "  lock                Refresh the dependency lock after editing pyproject.toml"
	@echo "  chrome-install      Install the Chrome used by Kaleido static exports"
	@echo "  run                 Start the Streamlit application"
	@echo "  example-portfolio   Generate the example plot portfolio"
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
	@$(UV) --version >/dev/null || { echo "Install uv (including uvx) before running this target."; exit 1; }
	test -d $(VENV_NAME) || $(UV) venv --python python3 $(VENV_NAME)

install: venv
	UV_PROJECT_ENVIRONMENT="$(abspath $(VENV_NAME))" $(UV) sync --locked --no-default-groups

sync-dev: venv
	UV_PROJECT_ENVIRONMENT="$(abspath $(VENV_NAME))" $(UV) sync --locked --all-extras

lock:
	$(UV) lock

dev: sync-dev
	$(MAKE) playwright-install chrome-install mock-data

run:
	$(VENV_BIN)/streamlit run app.py

example-portfolio:
	$(PYTHON) -m scripts.generate_example_portfolio

playwright-install: venv
	$(VENV_BIN)/playwright install chromium

chrome-install:
	$(PYTHON) -m ring5.cli install-chrome

install-latex:
	@if command -v apt-get >/dev/null 2>&1; then \
		sudo apt-get update; \
		sudo apt-get install -y texlive-latex-base texlive-fonts-recommended \
			texlive-fonts-extra texlive-latex-extra texlive-xetex cm-super; \
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
		$(PYTHON) -m scripts.generate_mock_fixtures; \
	fi

test-unit:
	$(PYTEST) tests/unit tests/ui_unit -m "not serial and not requires_latex" -q --no-cov

test-nonbrowser:
	$(PYTEST) $(NON_BROWSER_TESTS) -m "not serial and not requires_latex" \
		--timeout=60 --no-cov

test-export:
	$(PYTEST) tests/unit/test_plotly_download.py tests/unit/test_duplicate_bar_geometry.py \
		-m "serial" -n 0 --timeout=120 --no-cov

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
		-n $(E2E_WORKERS) --dist loadgroup --order-scope=class \
		--timeout=240 --timeout-method=thread --no-cov
	$(PYTEST) tests/e2e -m "requires_browser and serial" -n 0 --order-scope=class \
		--timeout=240 --timeout-method=thread --no-cov

test-visual:
	$(PYTEST) tests/visual -n 0 --order-scope=class --timeout=120 --no-cov

format:
	$(VENV_BIN)/black --workers $(RING5_NATIVE_THREADS) $(PYTHON_SOURCES)

format-check:
	$(VENV_BIN)/black --check --diff --workers $(RING5_NATIVE_THREADS) $(PYTHON_SOURCES)

lint:
	$(VENV_BIN)/flake8 --jobs=1 $(PYTHON_SOURCES) --count --statistics

type-check:
	$(VENV_BIN)/mypy src ring5 --show-error-codes --pretty

arch-check:
	$(PYTHON) -m scripts.check_architecture

comments-check:
	$(PYTHON) -m scripts.check_comments

docs-check:
	$(PYTHON) -m scripts.check_public_docstrings
	$(PYTHON) -m scripts.check_doc_structure

docs-build:
	rm -rf _site
	JEKYLL_ENV=production BUNDLE_GEMFILE=$(CURDIR)/Gemfile bundle exec jekyll build \
		--source docs --destination _site

docs-audit:
	$(PYTHON) -m scripts.check_built_site

docs-security:
	BUNDLE_GEMFILE=$(CURDIR)/Gemfile bundle exec bundler-audit check --update

dependency-check:
	$(UV) lock --check
	$(PYTHON) -m scripts.analyze_dependencies
	$(UV) pip check --python $(PYTHON)

security-audit:
	$(VENV_BIN)/bandit -r ring5 src -c pyproject.toml -ll
	@set -eu; requirements=$$(mktemp); trap 'rm -f "$$requirements"' EXIT INT TERM; \
		$(UV) export --locked --all-extras --no-emit-project --output-file "$$requirements" >/dev/null; \
		$(VENV_BIN)/pip-audit --strict --progress-spinner off --disable-pip --require-hashes --requirement "$$requirements"

oft-generate:
	$(PYTHON) -m scripts.generate_oft_inventory

oft-check:
	$(PYTHON) -m scripts.generate_oft_inventory --check

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
		set -eu; \
		tmp_file=$$(mktemp "$(OFT_CACHE_DIR)/openfasttrace.XXXXXX"); \
		trap 'rm -f "$$tmp_file"' EXIT INT TERM; \
		curl --fail --location --silent --show-error "$(OFT_URL)" --output "$$tmp_file"; \
		echo "$(OFT_SHA256)  $$tmp_file" | sha256sum --check --status; \
		mv "$$tmp_file" "$(OFT_JAR)"; \
		trap - EXIT INT TERM; \
	fi

oft-trace: oft-check oft-download
	$(PYTHON) -m scripts.trace_oft_inventory --jar "$(OFT_JAR)" --mode approved

oft-trace-all: oft-check oft-download
	$(PYTHON) -m scripts.trace_oft_inventory --jar "$(OFT_JAR)" --mode all

oft-report: oft-generate oft-download
	$(RM) "$(OFT_NATIVE_REPORT)"
	-$(PYTHON) -m scripts.trace_oft_inventory --jar "$(OFT_JAR)" --mode html \
		--output-file "$(OFT_NATIVE_REPORT)"
	@test -s "$(OFT_NATIVE_REPORT)"
	$(PYTHON) -m scripts.generate_oft_html_report \
		--oft-html "$(OFT_NATIVE_REPORT)" --output "$(OFT_REPORT)" $(OFT_EXECUTION_RESULTS_ARG)
	$(PYTHON) -m scripts.generate_oft_inventory --check
	@echo "Open $(OFT_REPORT) in a browser."

oft-diff:
	@test -n "$(BASE)" || { echo "Use: make oft-diff BASE=<git-revision>"; exit 2; }
	$(PYTHON) -m scripts.diff_oft_inventory "$(BASE)"

quality-gate: arch-check comments-check docs-check dependency-check oft-check format-check lint type-check security-audit
	@echo "Quality gate passed."

package-check:
	rm -rf build dist ring5.egg-info
	$(PYTHON) -m build
	$(VENV_BIN)/twine check dist/*
	$(PYTHON) -m scripts.check_package_contents

check-outdated:
	$(UV) pip list --python $(PYTHON) --outdated

pre-commit-install:
	$(VENV_BIN)/pre-commit install

pre-commit:
	$(VENV_BIN)/pre-commit run --all-files

clean:
	rm -rf build dist _site .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
