# Step 17: Configuration, Build & CI Analysis

## 1. Executive Summary

The RING-5 Unified Engine v2 project employs a comprehensive configuration, build, and continuous
integration infrastructure that enforces code quality, security, and architectural integrity at
every stage of development. The project uses `pyproject.toml` as its single source of truth for
package metadata, dependencies, and tool configuration, following modern Python packaging best
practices with setuptools as the build backend. A rich set of GitHub Actions workflows provides
automated quality checks, security scanning, dependency auditing, and documentation deployment.
The pre-commit framework enforces formatting, linting, type-checking, and custom architecture
boundary rules on every commit. JSON Schema validation (Draft-07) governs all pipeline and
portfolio configuration files, with a dedicated `ConfigValidator` service class providing
runtime schema enforcement.

### Key Infrastructure Components

| Component               | Technology                      | Purpose                                     |
|-------------------------|---------------------------------|---------------------------------------------|
| Package metadata        | `pyproject.toml`                | Single source of truth for project config   |
| Build system            | setuptools >= 61.0 + wheel      | Standard Python packaging                   |
| CI/CD                   | GitHub Actions (5 workflows)    | Automated testing, security, deployment     |
| Pre-commit              | 7 third-party + 5 custom hooks  | On-commit quality enforcement               |
| Schema validation       | jsonschema (Draft-07)           | Runtime config validation against 4 schemas |
| Code formatting         | black 26.1.0                    | Deterministic code formatting               |
| Linting                 | flake8 7.3.0                    | Style and error checking                    |
| Type checking           | mypy 1.13.0+                    | Static type analysis                        |
| Security scanning       | bandit + CodeQL + pip-audit     | Vulnerability detection                     |
| Import sorting          | isort 7.0.0                     | Consistent import organization              |
| Test framework          | pytest 9.0.2+ (with xdist)     | Parallel test execution with coverage       |

---

## 2. Package Configuration (pyproject.toml Deep-Dive)

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/pyproject.toml`

The `pyproject.toml` file is the central configuration hub, consolidating project metadata,
dependency declarations, build system settings, and tool configurations for the entire
development toolchain.

### 2.1 Project Metadata

```toml
[project]
name = "ring5"
version = "1.0.0"
description = "Modern gem5 Data Analysis and Visualization Tool"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "GPL-3.0-or-later" }
authors = [{ name = "RING-5 Development Team" }]
keywords = ["gem5", "data-analysis", "visualization", "performance-analysis"]
classifiers = [
  "Development Status :: 4 - Beta",
  "Intended Audience :: Science/Research",
  "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.12",
]
```

Key decisions visible in this metadata:

- **Python 3.12 minimum**: The project targets only Python 3.12+, enabling use of modern
  language features including improved type hints, `match` statements, and performance
  improvements in the interpreter. This is an aggressive minimum version that prioritizes
  developer experience and language features over backward compatibility.

- **GPL-3.0-or-later license**: The project is distributed under the GNU General Public License
  v3, a copyleft license. This is consistent with many academic/research tools.

- **Development Status Beta**: The project self-classifies as Beta (4), indicating it is
  feature-complete for its core use cases but may still undergo significant changes.

- **Science/Research audience**: The classifiers explicitly target the academic research
  community, consistent with gem5 being a computer architecture simulator.

### 2.2 Build System Configuration

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"
```

The project uses **setuptools** as its build backend rather than alternatives like Poetry, Flit,
or Hatch. Setuptools 61.0+ is required because that version introduced native `pyproject.toml`
support, eliminating the need for `setup.py` or `setup.cfg` files. No `setup.py` or `setup.cfg`
files exist in the repository root, confirming the full migration to `pyproject.toml`.

### 2.3 Package Discovery

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["src*", "components_library*"]

[tool.setuptools]
py-modules = ["argumentParser", "ring5"]
```

The package discovery configuration reveals the project structure:

- **`src*`**: The main source tree containing `src/core/`, `src/web/`, and related subpackages.
- **`components_library*`**: A separate top-level package for reusable UI components, sitting
  outside the main `src/` tree.
- **`argumentParser` and `ring5` modules**: Two standalone Python modules at the repository root
  included as top-level importable modules. These are the CLI entry point
  (`argumentParser`) and the main package module (`ring5`).

This layout uses a flat `src/` structure (not `src/ring5/`) combined with `pythonpath = ["."]`
in pytest configuration to ensure imports work correctly both at development time and when
installed as a package.

### 2.4 Project URLs

```toml
[project.urls]
Homepage = "https://github.com/your-org/ring5"
Repository = "https://github.com/your-org/ring5"
```

The URLs use placeholder organization names (`your-org`), indicating the repository has not yet
been published to a final public location or PyPI.

---

## 3. Dependencies Catalog (Runtime vs Dev)

### 3.1 Runtime Dependencies

```toml
dependencies = [
  "pandas>=2.3.3",
  "scipy>=1.17.0",
  "numpy>=2.4.1",
  "matplotlib>=3.10.8",
  "jsonschema>=4.26.0",
  "streamlit>=1.53.1",
  "openpyxl>=3.1.5",
  "plotly>=6.5.2",
  "kaleido>=1.0.0",
]
```

| Package      | Version    | Role in Architecture                                          |
|-------------|------------|---------------------------------------------------------------|
| pandas      | >= 2.3.3   | Core data processing engine; DataFrame is the universal data  |
|             |            | structure across the entire pipeline                          |
| scipy       | >= 1.17.0  | Statistical computations (geometric mean, outlier detection)  |
| numpy       | >= 2.4.1   | Numerical operations underlying pandas and scipy              |
| matplotlib  | >= 3.10.8  | Static plot rendering engine; LaTeX/PDF/PGF export backend    |
| jsonschema  | >= 4.26.0  | JSON Schema Draft-07 validation for pipeline configs          |
| streamlit   | >= 1.53.1  | Web UI framework; the entire web layer depends on this        |
| openpyxl    | >= 3.1.5   | Excel file I/O through pandas `.to_excel()` / `read_excel()` |
| plotly       | >= 6.5.2   | Interactive plot rendering for the web UI (Plotly.js)         |
| kaleido     | >= 1.0.0   | Static image export for Plotly charts (PNG/SVG/PDF)           |

**Dependency Philosophy**: All runtime dependencies use `>=` (minimum version) constraints
without upper bounds. This is a deliberate choice that follows the "library" packaging convention
-- allowing compatibility with future versions of dependencies. It avoids version pinning issues
common in application deployment, favoring flexibility for users who may already have newer
versions installed.

**Notable Observation**: The version numbers are very recent (e.g., pandas >= 2.3.3,
numpy >= 2.4.1, streamlit >= 1.53.1), indicating the project tracks the latest releases
of its dependencies closely. This is consistent with the Python 3.12+ requirement.

### 3.2 Development Dependencies

```toml
[project.optional-dependencies]
dev = [
  "pytest>=9.0.2",
  "pytest-cov>=7.0.0",
  "pytest-xdist>=3.6.1",
  "black>=26.1.0",
  "flake8>=7.3.0",
  "flake8-pyproject>=1.2.0",
  "mypy>=1.13.0",
  "pre-commit>=4.5.0",
  "pytest-randomly>=3.16.0",
  "pandas-stubs>=2.2.3.240909",
  "plotly-stubs>=0.1.2",
  "types-jsonschema>=4.23.0.20240813",
  "scipy-stubs>=1.5.0",
]
```

| Package            | Purpose                                                       |
|-------------------|---------------------------------------------------------------|
| pytest            | Test runner and assertion framework                           |
| pytest-cov        | Coverage measurement and enforcement                          |
| pytest-xdist      | Parallel test execution across multiple CPU cores             |
| black             | Opinionated code formatter (deterministic output)             |
| flake8            | Style and error linter (PEP 8 enforcement)                    |
| flake8-pyproject  | Enables flake8 to read config from `pyproject.toml`           |
| mypy              | Static type checker for Python                                |
| pre-commit        | Git hook framework managing all pre-commit checks             |
| pytest-randomly   | Randomizes test execution order to detect hidden dependencies |
| pandas-stubs      | Type stubs for pandas (mypy support)                          |
| plotly-stubs      | Type stubs for plotly (mypy support)                          |
| types-jsonschema  | Type stubs for jsonschema (mypy support)                      |
| scipy-stubs       | Type stubs for scipy (mypy support)                           |

### 3.3 CI-Only Dependencies

```toml
ci = ["bandit[toml]>=1.7.0", "pytest-timeout>=2.2.0", "pip-audit>=2.7.0"]
```

| Package         | Purpose                                                        |
|----------------|----------------------------------------------------------------|
| bandit[toml]   | Security-focused linter that scans for common vulnerabilities  |
| pytest-timeout | Enforces time limits on tests to prevent CI hangs              |
| pip-audit      | Checks installed packages against known vulnerability databases|

### 3.4 End-to-End Test Dependencies

```toml
e2e = ["pytest-playwright>=0.7.0", "pytest-base-url>=2.1.0"]
```

| Package            | Purpose                                                     |
|-------------------|-------------------------------------------------------------|
| pytest-playwright | Browser automation for E2E testing against the Streamlit UI |
| pytest-base-url   | Configurable base URL for E2E test targets                  |

The separation into four dependency groups (`runtime`, `dev`, `ci`, `e2e`) provides granular
control over installation contexts:
- **Production deployment**: `pip install .` (runtime only)
- **Local development**: `pip install -e ".[dev]"` (runtime + dev tools)
- **CI pipeline**: `pip install -e ".[dev,ci]"` (runtime + dev + CI tools)
- **E2E testing**: `pip install -e ".[dev,e2e]"` (runtime + dev + browser automation)

---

## 4. Build System Configuration

### 4.1 Setuptools Build Backend

The project uses setuptools with the `build_meta` backend, which is the standard PEP 517
build backend. This enables the project to be built using standard tools:

```bash
# Build source distribution and wheel
python -m build

# Install in development mode (editable)
pip install -e ".[dev]"
```

### 4.2 Pytest Configuration

The `pyproject.toml` file contains a comprehensive pytest configuration block:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
norecursedirs = [
  "tests/tests_principle_compliance",
  "tests/manual",
  "tests/data",
  "tests/visual",
]
pythonpath = ["."]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --tb=short --strict-markers -n 3 --dist loadgroup"
xfail_strict = true
markers = [
  "requires_latex: Tests that require LaTeX installation",
  "requires_browser: Tests that require a running browser/server",
  "benchmark: marks tests as performance benchmarks",
  "smoke: Quick smoke tests",
  "data_value: Inject data value into fixtures",
  "slow: Marks tests as slow",
  "xdist_group: Group tests to run on the same xdist worker",
]
```

**Critical settings**:

- **`-n 3 --dist loadgroup`**: Tests run in parallel across 3 worker processes using
  pytest-xdist. The `loadgroup` distribution strategy sends tests with the same
  `xdist_group` marker to the same worker, which is essential when tests share stateful
  resources (like Streamlit session state or temporary files).

- **`xfail_strict = true`**: If a test marked as `xfail` unexpectedly passes, pytest
  will report it as an error. This prevents outdated `xfail` markers from silently
  hiding passing tests.

- **`--strict-markers`**: All markers used in tests must be declared in the `markers` list.
  This prevents typos in marker names from being silently ignored.

- **`norecursedirs`**: Several test directories are excluded from the default test collection:
  - `tests/tests_principle_compliance` -- Architecture principle compliance tests (run separately)
  - `tests/manual` -- Tests requiring manual interaction
  - `tests/data` -- Test data fixtures (not test code)
  - `tests/visual` -- Visual/UI tests requiring a browser (run separately via `make test-visual`)

### 4.3 Coverage Configuration

```toml
[tool.coverage.run]
omit = [
  "src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py",
]
```

The coverage configuration deliberately omits the `dual_axis_bar_dot_plot.py` module, which is
marked as a work-in-progress feature. The comment indicates this module is also excluded from
test execution using `-k "not dual_axis and not dual"`. This is a clean approach to handling
in-progress features: rather than disabling coverage entirely, only the specific WIP module
is excluded.

---

## 5. ConfigManager & Schema Validation

### 5.1 Architecture Overview

Configuration management is split across two layers following the project's strict architecture
boundaries:

1. **Models layer** (`src/core/models/config/config_manager.py`): Pure TypedDict data models
   defining the shape of configuration data. No business logic.
2. **Service layer** (`src/core/services/config_validation_service.py`): Business logic for
   JSON schema validation and configuration template generation.

This separation was performed during "Phase 3.5" of the project's architectural refactoring,
as noted in the source file docstrings.

### 5.2 TypedDict Configuration Models

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/models/config/config_manager.py`

The configuration models use Python `TypedDict` classes rather than dataclasses or Pydantic
models. This is a deliberate design choice: TypedDict provides structural typing for
dictionaries, making them compatible with JSON serialization without any conversion step.

```python
class RingConfig(TypedDict):
    """Type definition for complete RING-5 configuration."""
    outputPath: str
    parseConfig: ParseConfig
    dataManagers: DataManagersConfig
    plots: list[PlotConfig]
```

The complete TypedDict hierarchy:

```
RingConfig
  +-- outputPath: str
  +-- parseConfig: ParseConfig
  |     +-- parser: str
  |     +-- statsPath: str
  |     +-- statsPattern: str
  |     +-- variables: list[VariableConfig]
  |           +-- name: str
  |           +-- type: str          (scalar | vector | distribution | configuration)
  |           +-- rename: str        (optional)
  +-- dataManagers: DataManagersConfig
  |     +-- seedsReducer: bool       (optional)
  |     +-- outlierRemover: dict     (optional)
  |     +-- normalizer: dict         (optional)
  +-- plots: list[PlotConfig]
        +-- type: str
        +-- output: OutputConfig
        |     +-- filename: str
        |     +-- format: str        (png | pdf | svg)
        |     +-- dpi: int
        +-- data: PlotDataConfig
        |     +-- x: str
        |     +-- y: str
        |     +-- hue: str           (optional)
        |     +-- filters: dict      (optional)
        |     +-- aggregate: str     (optional)
        +-- style: PlotStyleConfig
              +-- width: int         (optional)
              +-- height: int        (optional)
              +-- theme: str         (optional)
              +-- title: str         (optional)
              +-- xlabel: str        (optional)
              +-- ylabel: str        (optional)
              +-- ylim: list[float]  (optional)
              +-- grid: bool         (optional)
              +-- legend: dict       (optional)
```

Note that `PlotDataConfig` and `PlotStyleConfig` use `total=False`, making all their
fields optional. `DataManagersConfig` also uses `total=False`. This allows incremental
construction of configuration objects without requiring all fields upfront.

### 5.3 ConfigValidator Service

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/services/config_validation_service.py`

The `ConfigValidator` class wraps `jsonschema.Draft7Validator` to validate configuration
dictionaries and files against the pipeline JSON schema.

```python
class ConfigValidator:
    def __init__(self, schema_path: str | None = None) -> None:
        # Default: loads pipeline_schema.json from schemas directory
        # Uses validate_path_within() for path traversal protection

    def validate(self, config: RingConfig | dict[str, Any]) -> bool:
        # Validates config dict against schema; raises ValidationError on failure

    def validate_file(self, config_path: str) -> bool:
        # Loads JSON file and validates its contents

    def get_errors(self, config: dict[str, Any]) -> list[str]:
        # Returns list of all validation errors (non-throwing)
```

**Security feature**: The constructor uses `validate_path_within()` from
`src/core/common/utils.py` to ensure the schema path cannot escape the `schemas/` directory
through path traversal attacks. This is a defense-in-depth measure since schema paths are
normally not user-controlled, but it protects against misconfiguration or misuse.

### 5.4 ConfigTemplateGenerator Service

The `ConfigTemplateGenerator` class provides a builder-pattern API for programmatically
constructing valid configurations:

```python
class ConfigTemplateGenerator:
    PLOT_TYPES: dict[str, str]       # 8 supported plot types with descriptions
    AGGREGATE_METHODS: dict[str, str] # 4 aggregation methods (mean, median, sum, geomean)
    THEMES: dict[str, str]           # 6 visual themes

    @staticmethod
    def create_minimal_config(output_path, stats_path) -> RingConfig
    @staticmethod
    def create_plot_config(plot_type, x, y, filename, **kwargs) -> PlotConfig
    @staticmethod
    def add_variable(config, name, var_type, rename=None) -> RingConfig
    @staticmethod
    def enable_seeds_reducer(config) -> RingConfig
    @staticmethod
    def enable_outlier_removal(config, column, method, threshold) -> dict
    @staticmethod
    def enable_normalizer(config, baseline, columns, group_by) -> dict
    @staticmethod
    def save_config(config, output_path) -> None
```

All methods are `@staticmethod`, making the class a pure namespace for configuration-building
functions. This pattern works well with TypedDict because the methods modify and return plain
dictionaries rather than class instances.

The class contains rich metadata about supported options:

| Constant            | Count | Values                                                           |
|--------------------|----|------------------------------------------------------------------|
| `PLOT_TYPES`       | 8  | bar, line, heatmap, grouped_bar, stacked_bar, box, violin, scatter |
| `AGGREGATE_METHODS`| 4  | mean, median, sum, geomean                                       |
| `THEMES`           | 6  | default, whitegrid, darkgrid, white, dark, ticks                 |

There is also a convenience function `create_simple_bar_plot_config()` that chains multiple
`ConfigTemplateGenerator` methods to produce a complete bar plot configuration in a single call.

### 5.5 JSON Schema Files

The project maintains four JSON Schema (Draft-07) files for validating different configuration
types:

**Directory**: `src/core/models/config/schemas/`

#### 5.5.1 Pipeline Schema (`pipeline_schema.json`)

The default schema used by `ConfigValidator`. Validates saved pipeline configurations:

```json
{
  "required": ["name", "pipeline"],
  "properties": {
    "name":        { "type": "string" },
    "description": { "type": "string" },
    "timestamp":   { "type": "string", "format": "date-time" },
    "pipeline":    {
      "type": "array",
      "items": {
        "required": ["type"],
        "additionalProperties": true
      }
    }
  }
}
```

Each pipeline item requires a `type` field but allows arbitrary additional properties
(`additionalProperties: true`). This is an intentionally loose schema that permits
shaper-specific properties without requiring the schema to enumerate every possible shaper
configuration.

#### 5.5.2 Parser Config Schema (`parser_config_schema.json`)

Validates gem5 parser configurations. This is the most detailed schema with strict structure:

- **Top-level**: Array of parser objects
- **Parser object**: Requires `id`, `impl` (enum: `"perl"` or `"python"`), and `parsings`
- **Parsing object**: Requires `path`, `files`, and `vars`
- **Variable object**: Requires `id` and `type` (enum: `"scalar"`, `"vector"`,
  `"distribution"`, `"configuration"`); supports optional `vectorEntries`,
  `useSpecialMembers`, `minimum`, `maximum`, `onEmpty`, and `repeat`

This schema is the bridge between the raw gem5 output format and the RING-5 data pipeline.
The `impl` field specifies which parser implementation to use (Perl for legacy compatibility
or Python for the newer native parser).

#### 5.5.3 Portfolio Schema (`portfolio_schema.json`)

Validates complete portfolio snapshots that bundle data and plots together:

- **Required**: `version`, `data_csv`, `plots`
- **Plot objects**: Require `id`, `name`, `plot_type`; may include `config`, `processed_data`
  (serialized CSV), `pipeline` (shaper array), `pipeline_counter`,
  `legend_mappings_by_column`, and `legend_mappings`
- **Optional top-level**: `timestamp`, `csv_path`, `plot_counter`, `config`

The `data_csv` field stores the entire dataset as a CSV string, making portfolios self-contained
and portable.

#### 5.5.4 Saved Config Schema (`saved_config_schema.json`)

Validates saved configurations that preserve shaper pipelines and data source references:

- **Required**: `name`, `shapers`
- **Optional**: `description`, `timestamp`, `csv_path`
- **Shapers**: Array of objects requiring `type` with `additionalProperties: true`

This is structurally similar to the pipeline schema but includes `csv_path` for linking
back to the original data source.

### 5.6 Schema Relationship Map

```
                   +----------------------------+
                   | parser_config_schema.json   |
                   | (gem5 parser input config)  |
                   +----------------------------+
                              |
                        [data parsing]
                              |
                              v
+----------------------------+    +----------------------------+
| pipeline_schema.json       |    | saved_config_schema.json   |
| (shaper pipeline steps)    |    | (shapers + data reference) |
+----------------------------+    +----------------------------+
              |                              |
         [applied to data]            [saved for reuse]
              |                              |
              v                              v
+---------------------------------------------------+
|          portfolio_schema.json                      |
|  (complete snapshot: data + plots + pipelines)     |
+---------------------------------------------------+
```

---

## 6. Code Quality Tools (Linting, Formatting, Type Checking)

### 6.1 Black -- Code Formatting

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/pyproject.toml` (`[tool.black]`)

```toml
[tool.black]
line-length = 100
target-version = ['py312']
```

Black is configured as the project's sole code formatter with two key settings:

- **Line length 100**: Wider than Black's default of 88, giving more horizontal space for
  the data-processing code that often has long method chains (e.g., `df.groupby(...).agg(...)`).
- **Target Python 3.12**: Ensures Black generates syntax compatible with 3.12+ features,
  enabling modern formatting choices like parenthesized context managers.

Black runs in three contexts:
1. **Pre-commit hook**: Automatically formats changed files on commit.
2. **CI quality-checks job**: `black --check --diff src/ tests/` -- fails the build if
   any file is not formatted.
3. **Makefile quality gate**: `black --check --quiet src/` -- part of the `quality-gate` target.

### 6.2 Flake8 -- Linting

```toml
[tool.flake8]
max-line-length = 100
extend-ignore = ["E203", "W503"]
exclude = [
  ".git", "__pycache__", "python_venv",
  ".pytest_cache", "*.egg-info", "build", "dist",
]
```

Configuration details:

- **`max-line-length = 100`**: Matches Black's line length to prevent conflicts.
- **`E203` ignored**: "Whitespace before ':'". This rule conflicts with Black's formatting
  of slice expressions (e.g., `x[1 : 2]`). Ignoring it is standard when using Black.
- **`W503` ignored**: "Line break before binary operator". PEP 8 has changed its recommendation
  on this, and Black always places breaks before operators. Ignoring W503 prevents conflicts.
- **`flake8-pyproject`**: A plugin dependency that enables flake8 to read its configuration
  from `pyproject.toml` (flake8 does not natively support this).

### 6.3 Mypy -- Static Type Checking

```toml
[tool.mypy]
python_version = "3.12"
explicit_package_bases = true
mypy_path = "."
namespace_packages = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = false
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = false
warn_no_return = true
check_untyped_defs = true
strict_equality = true
```

Key mypy settings analysis:

| Setting                    | Value  | Effect                                            |
|---------------------------|--------|---------------------------------------------------|
| `disallow_untyped_defs`    | true   | ALL functions must have type annotations           |
| `no_implicit_optional`     | true   | `x: str = None` is an error; must use `str \| None` |
| `check_untyped_defs`       | true   | Type-check even inside untyped functions           |
| `strict_equality`          | true   | Prevents comparing incompatible types              |
| `warn_return_any`          | true   | Warns when returning `Any` from typed functions    |
| `warn_no_return`           | true   | Warns when functions missing return statements     |
| `warn_unused_ignores`      | false  | Does not warn on unused `# type: ignore` comments |
| `explicit_package_bases`   | true   | Required for the flat `src/` layout                |
| `namespace_packages`       | true   | Supports implicit namespace packages in `src/`     |

**Third-party overrides**: All major dependencies have `ignore_missing_imports = true`:

```toml
[[tool.mypy.overrides]]
module = [
  "pandas.*", "plotly.*", "streamlit.*", "matplotlib.*",
  "scipy.*", "numpy.*", "yaml.*", "jsonschema.*",
]
ignore_missing_imports = true
```

This override works in conjunction with the type stubs in dev dependencies (`pandas-stubs`,
`plotly-stubs`, `types-jsonschema`, `scipy-stubs`) to provide type information where available
while gracefully handling cases where stubs are incomplete.

### 6.4 isort -- Import Sorting

isort is configured via the pre-commit hook arguments rather than `pyproject.toml`:

```yaml
- id: isort
  args: [--profile=black, --line-length=100]
```

- **`--profile=black`**: Uses isort's Black-compatible profile, ensuring import formatting
  does not conflict with Black's output.
- **`--line-length=100`**: Matches the project's global line length standard.

### 6.5 Bandit -- Security Scanning

```toml
[tool.bandit]
# B603: subprocess without shell - we explicitly use shell=False with validated paths
# B404: import subprocess - required for Perl parser execution
skips = ["B603", "B404"]
```

Bandit is configured to skip two rules:
- **B603**: Flags subprocess calls without `shell=True`. Skipped because the project
  deliberately uses `shell=False` with validated paths for running the Perl parser.
- **B404**: Flags `import subprocess`. Skipped because subprocess is required for
  invoking the external Perl parser process.

Both skips include explanatory comments documenting why the exceptions are necessary.

### 6.6 pyupgrade -- Syntax Modernization

Configured in `.pre-commit-config.yaml`:

```yaml
- id: pyupgrade
  args: [--py312-plus]
```

pyupgrade automatically modernizes Python syntax to 3.12+ patterns, including:
- Replacing `Optional[X]` with `X | None`
- Replacing `Union[X, Y]` with `X | Y`
- Replacing `Dict[K, V]` with `dict[K, V]` (lowercase generics)
- Removing redundant `encoding="utf-8"` arguments (default in 3.12)

---

## 7. CI/CD Pipeline (GitHub Actions Workflows)

The project maintains five GitHub Actions workflow files providing a comprehensive CI/CD
pipeline:

**Directory**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.github/workflows/`

### 7.1 Main CI Pipeline (`ci.yml`)

**Trigger**: Push or PR to `main` or `develop` branches; manual dispatch.

```
+-------------------+     +-----------------+     +------------------+
| quality-checks    | --> | tests           | --> | e2e-tests        |
| (Code Quality)    |     | (Python 3.12)   |     | (Playwright)     |
| ubuntu-latest     |     | ubuntu-latest   |     | ubuntu-latest    |
+-------------------+     +-----------------+     +------------------+
```

#### Job 1: quality-checks

Sequential steps:
1. Checkout code
2. Set up Python 3.12 (with pip cache)
3. Install dependencies: `pip install -e ".[dev,ci]"`
4. **Black check**: `black --check --diff src/ tests/`
5. **Flake8 lint**: `flake8 src/ tests/ --count --statistics`
6. **Mypy type check**: `mypy src/ --show-error-codes --pretty`
7. **Bandit security scan**: `bandit -r src/ -c pyproject.toml -ll`

#### Job 2: tests (depends on quality-checks)

Sequential steps:
1. Checkout code (with LFS support for test data)
2. Set up Python 3.12 (with pip cache)
3. Install system dependencies: `perl` (for the Perl-based gem5 parser)
4. Install Python dependencies: `pip install -e ".[dev,ci]"`
5. **Run tests with coverage**: `pytest -v --cov=src --cov-report=xml --cov-report=term-missing --timeout=60`
6. **Upload coverage to Codecov**: Uses `codecov/codecov-action@v4`

#### Job 3: e2e-tests (depends on tests, main branch only)

This job runs **only** on pushes to `main` (not on PRs or feature branches):
1. Checkout code (with LFS)
2. Set up Python 3.12
3. Install dependencies: `pip install -e ".[dev,e2e]"`
4. Install Playwright browsers: `playwright install --with-deps chromium`
5. **Run E2E tests**: `pytest tests/ui/ -v --timeout=120 -m "requires_browser" --tb=short`

### 7.2 Architecture & Security Enforcement (`architecture-check.yml`)

**Trigger**: Push or PR to `main`/`develop` when `src/**/*.py` or `tests/**/*.py` files change.

This workflow enforces architectural boundaries through grep-based pattern detection:

| Check                              | What It Detects                             | Severity |
|-----------------------------------|---------------------------------------------|----------|
| Streamlit imports in core          | `import streamlit` / `from streamlit` in `src/core/` | Error    |
| session_state in core              | `session_state` in `src/core/`              | Error    |
| inplace=True usage                 | `inplace=True` anywhere in `src/`           | Error    |
| Bare except clauses                | `except:` (without exception type) in `src/`| Error    |
| UI libs in parsing/models          | plotly/matplotlib imports in `src/core/parsing/` or `src/core/models/` | Error |

The workflow also includes a **Security Analysis** job that:
1. Checks for dangerous patterns (`eval()`, `exec()`, `pickle.load`, hardcoded secrets)
2. Runs Bandit with JSON report output (uploaded as artifact)
3. Runs pip-audit for known vulnerabilities in dependencies

### 7.3 Dependency Update Check (`dependency-check.yml`)

**Trigger**: Weekly schedule (Monday 9 AM UTC); manual dispatch.

This workflow automates dependency freshness monitoring:
1. Installs the project and runs `pip list --outdated --format=json`
2. Generates a markdown summary table for GitHub's step summary
3. Runs `pip-audit` for security vulnerabilities
4. **Creates a GitHub issue** (with labels `dependencies`, `automated`, `maintenance`) if
   outdated packages are found -- but only if no open issue already exists with those labels

This is a proactive dependency management approach that surfaces outdated packages weekly
without requiring manual checking.

### 7.4 CodeQL Advanced Security (`codeql.yml`)

**Trigger**: Push or PR to `main`/`develop`; weekly schedule (Monday midnight UTC); manual.

GitHub's CodeQL semantic code analysis:
1. Installs the project and dev dependencies for better analysis
2. Initializes CodeQL with `security-and-quality` query suite
3. Uses custom config from `.github/codeql/codeql-config.yml`
4. Runs autobuild (for dependency resolution)
5. Performs CodeQL analysis and uploads results to GitHub Security tab

**CodeQL Configuration** (`.github/codeql/codeql-config.yml`):

Paths excluded from analysis:
- `tests/**`, `scripts/**`, `tests/data/**`, `python_venv/**`
- `**/*.egg-info/**`, `**/__pycache__/**`, `.pytest_cache/**`
- `docs/**`, `*.md`

The config file documents why path-injection and regex-injection queries could produce
false positives (CodeQL's inter-procedural analysis limitation with helper functions),
though these exclusions are currently commented out.

### 7.5 Documentation Deployment (`pages.yml`)

**Trigger**: Push to `main` when `docs/**` or the workflow file itself changes.

A two-job workflow for deploying documentation to GitHub Pages:
1. **Build job**: Uses `actions/jekyll-build-pages@v1` to build the `docs/` directory
2. **Deploy job**: Deploys the built site to GitHub Pages using `actions/deploy-pages@v4`

Uses GitHub Pages concurrency control (`cancel-in-progress: false`) to prevent incomplete
deployments.

### 7.6 CI Pipeline Flow Summary

```
                     Push/PR to main or develop
                              |
                              v
                 +------------------------+
                 |   quality-checks       |
                 |   (format + lint +     |
                 |    types + security)   |
                 +------------------------+
                              |
                         [must pass]
                              |
                              v
                 +------------------------+
                 |   tests                |
                 |   (pytest + coverage   |
                 |    + Codecov upload)   |
                 +------------------------+
                              |
                    [must pass; main only]
                              |
                              v
                 +------------------------+
                 |   e2e-tests            |
                 |   (Playwright browser  |
                 |    automation)         |
                 +------------------------+

  ---- Parallel workflows (on *.py changes) ----

  +------------------------------+
  | architecture-check           |
  | (boundary enforcement +      |
  |  security pattern scanning)  |
  +------------------------------+

  ---- Scheduled workflows ----

  +------------------------------+    +------------------------------+
  | dependency-check             |    | codeql                       |
  | (weekly, Monday 9 AM UTC)   |    | (weekly, Monday midnight)    |
  | Outdated deps + pip-audit    |    | Semantic security analysis   |
  +------------------------------+    +------------------------------+

  ---- Documentation deployment (on docs/** changes to main) ----

  +------------------------------+
  | pages                        |
  | (Jekyll build + GH Pages)   |
  +------------------------------+
```

---

## 8. Pre-commit Hooks

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.pre-commit-config.yaml`

The pre-commit configuration defines 12 third-party hooks across 7 repositories plus 5 custom
local hooks for architecture enforcement.

### 8.1 Global Configuration

```yaml
exclude: ^tests/data/|^python_venv/
```

All hooks skip `tests/data/` (test fixtures) and `python_venv/` (virtual environment).

### 8.2 Third-Party Hooks

| Repository                  | Hook(s)               | Version  | Purpose                    |
|----------------------------|-----------------------|----------|----------------------------|
| `psf/black`                | black                 | 26.1.0   | Code formatting            |
| `pycqa/flake8`             | flake8                | 7.3.0    | Linting                    |
| `pre-commit/mirrors-mypy`  | mypy                  | v1.19.1  | Type checking (src/ only)  |
| `pycqa/isort`              | isort                 | 7.0.0    | Import sorting             |
| `pre-commit/pre-commit-hooks` | (11 checks)        | v6.0.0   | General code hygiene       |
| `PyCQA/bandit`             | bandit                | 1.9.3    | Security scanning          |
| `asottile/pyupgrade`       | pyupgrade             | v3.19.1  | Syntax modernization       |

The **pre-commit-hooks** repository provides 11 individual checks:

| Check                   | Purpose                                         |
|------------------------|-------------------------------------------------|
| trailing-whitespace    | Remove trailing whitespace                       |
| end-of-file-fixer      | Ensure files end with a newline                 |
| check-yaml             | Validate YAML syntax                            |
| check-json             | Validate JSON syntax (excludes `.vscode/`)      |
| check-toml             | Validate TOML syntax                            |
| check-merge-conflict   | Detect unresolved merge conflict markers        |
| check-added-large-files| Block files > 1000 KB from being committed      |
| debug-statements       | Find and flag leftover `pdb`/`breakpoint()` calls|
| mixed-line-ending      | Enforce consistent line endings                 |
| check-ast              | Verify Python files are syntactically valid     |
| check-case-conflict    | Detect filenames that differ only in case       |
| check-docstring-first  | Ensure docstrings are the first statement       |
| detect-private-key     | Flag accidentally committed private keys        |
| no-commit-to-branch    | **Prevent direct commits to `main` branch**     |

The `no-commit-to-branch` hook with `args: [--branch, main]` is particularly important:
it acts as a guardrail preventing developers from accidentally committing directly to `main`,
enforcing the pull request workflow.

### 8.3 Custom Architecture Hooks

Five local hooks enforce project-specific architectural rules:

#### Hook 1: `no-streamlit-in-core`

```bash
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py"
```

Prevents the core layer from depending on Streamlit, maintaining the separation between
business logic and the web framework.

#### Hook 2: `no-session-state-in-core`

```bash
grep -rn "session_state" src/core/ --include="*.py"
```

Prevents the core layer from accessing Streamlit's `session_state`, ensuring state management
is confined to the web layer.

#### Hook 3: `no-inplace-true`

```bash
grep -rn "inplace=True" src/ --include="*.py"
```

Enforces immutable DataFrame operations across the entire `src/` tree. The `inplace=True`
parameter on pandas operations is both deprecated and produces confusing mutation behavior;
this hook mandates the functional style (e.g., `df = df.dropna()` instead of `df.dropna(inplace=True)`).

#### Hook 4: `no-bare-except`

```bash
grep -rn "^[[:space:]]*except:" src/ --include="*.py"
```

Prohibits bare `except:` clauses, requiring all exception handlers to specify an exception type.
This prevents accidentally catching `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit`.

#### Hook 5: `no-eval-exec`

```bash
grep -rn "eval(\|exec(" src/ --include="*.py"
```

Blocks `eval()` and `exec()` in production code as a security measure. These functions
can execute arbitrary code and are common injection vectors.

### 8.4 Pre-commit Hook Execution Order

When a developer runs `git commit`, hooks execute in the order they appear in the YAML file:

```
1. black         (format code)
2. flake8        (lint formatted code)
3. mypy          (type-check src/)
4. isort         (sort imports)
5. pre-commit-hooks (11 basic checks)
6. bandit        (security scan, excludes tests/)
7. pyupgrade     (modernize syntax)
8. no-streamlit-in-core   (architecture)
9. no-session-state-in-core (architecture)
10. no-inplace-true        (immutability)
11. no-bare-except         (error handling)
12. no-eval-exec           (security)
```

---

## 9. Development Scripts & Commands

### 9.1 Makefile Target Catalog

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/Makefile`

| Target             | Command                                              | Purpose                                |
|-------------------|------------------------------------------------------|----------------------------------------|
| `help`            | (echo statements)                                    | Display available targets              |
| `venv`            | `python3 -m venv python_venv`                        | Create virtual environment             |
| `install`         | `pip install .`                                      | Install production dependencies        |
| `dev`             | `pip install -e ".[dev]"`                             | Install dev dependencies (editable)    |
| `install-latex`   | System package installer                              | Install LaTeX for PDF/PGF export       |
| `check-latex`     | Checks latex/xelatex/cm-super                        | Verify LaTeX installation              |
| `test-data`       | Downloads from GitHub Releases                        | Fetch test data if not present         |
| `test`            | `pytest --no-cov`                                    | Run tests (no coverage gate)           |
| `test-ci`         | `pytest --cov=src --cov-fail-under=90`               | Run tests with 90% coverage gate       |
| `test-unit`       | `pytest tests/unit/ -q --no-cov`                     | Run unit tests only (fast)             |
| `test-visual`     | Launches Streamlit + Playwright tests                 | Run visual/browser E2E tests           |
| `run`             | `streamlit run app.py`                                | Start the web application              |
| `pre-commit-install`| `pre-commit install`                                | Set up pre-commit hooks                |
| `pre-commit`      | `pre-commit run --all-files`                          | Run all hooks on entire codebase       |
| `check-outdated`  | `pip list --outdated`                                 | Show outdated packages                 |
| `update-deps`     | Interactive dep update                                | Update packages one-by-one             |
| `security-audit`  | `pip-audit --format columns`                          | Check for known vulnerabilities        |
| `show-deps`       | `pipdeptree`                                          | Show dependency tree                   |
| `check-unused`    | `scripts/analyze_dependencies.py`                     | Find unused dependencies               |
| `clean-deps`      | `pip-autoremove --list`                               | Find removable transitive deps         |
| `clean`           | `rm -rf build/ dist/ *.egg-info __pycache__`          | Remove build artifacts                 |
| `quality-gate`    | 5-gate quality check                                  | Run all quality checks at once         |
| `arch-check`      | Architecture boundary grep                            | Check architecture violations          |

### 9.2 Quality Gate (make quality-gate)

The `quality-gate` target runs five sequential checks and reports a pass/fail summary:

```
+--------------------------------------------------+
|     RING-5 QUALITY GATE                           |
+--------------------------------------------------+
| Gate 1: Architecture (boundary violations)        |
| Gate 2: Type Safety   (mypy error count)          |
| Gate 3: Formatting    (black --check)             |
| Gate 4: Linting       (flake8 error count)        |
| Gate 5: Security      (eval/exec pattern scan)    |
+--------------------------------------------------+
| Results: N passed, M failed                       |
| ALL GATES PASSED / QUALITY GATE FAILED            |
+--------------------------------------------------+
```

This provides a single command that developers can run before pushing to validate their
changes against all CI requirements.

### 9.3 Test Data Management

The Makefile includes a `test-data` target that automatically downloads test data from
GitHub Releases if not already present:

```makefile
TEST_DATA_DIR = tests/data/results-micro26-sens
TEST_DATA_URL = https://github.com/nikiitin/RING-5/releases/download/test-data-v1/test_data.tar.gz
```

The download logic handles three scenarios:
1. **Local tarball present**: Extracts from `test_data.tar.gz` in the repository root
2. **curl available**: Downloads and extracts in a single piped command
3. **wget available**: Falls back to wget if curl is not installed
4. **Neither available**: Fails with an error message

### 9.4 Utility Scripts

#### `scripts/verify_installation.py`

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/scripts/verify_installation.py`

A comprehensive installation verification script that checks:
1. **File structure**: Verifies 8 required files exist (app.py, pyproject.toml, etc.)
2. **Python dependencies**: Imports jsonschema, pandas, numpy, plotly, streamlit
3. **LaTeX dependencies**: Checks for latex, xelatex, and cm-super package
4. **Config validation**: Tests `ConfigValidator` against the template config
5. **Template generation**: Tests `ConfigTemplateGenerator` end-to-end
6. **Schema validation**: Verifies that invalid configs are properly rejected

#### `scripts/analyze_dependencies.py`

**File**: `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/scripts/analyze_dependencies.py`

A static analysis script that:
1. Uses Python's `ast` module to parse all `.py` files under `src/`
2. Extracts all import statements
3. Maps import names to package names (handles aliases like `pd` -> `pandas`)
4. Compares found imports against declared dependencies in `pyproject.toml`
5. Reports potentially unused packages and undeclared dependencies

The script maintains a manual mapping dictionary (`IMPORT_TO_PACKAGE`) for common aliases
and a set of known dev-only packages (`DEV_PACKAGES`) to avoid false positives.

---

## 10. Environment Configuration

### 10.1 Virtual Environment Convention

The project uses `python_venv` as its virtual environment directory name (not the more
common `venv` or `.venv`). This is configured in the Makefile:

```makefile
VENV_NAME = python_venv
VENV_BIN = ./$(VENV_NAME)/bin
PYTHON = python3
PIP = $(VENV_BIN)/pip
pytest = $(VENV_BIN)/pytest
```

All tool invocations use the virtual environment's binary path (`$(VENV_BIN)/...`), ensuring
that the correct versions of tools are used regardless of system Python configuration.

### 10.2 Python Path Configuration

The `pythonpath = ["."]` setting in pytest configuration and the `mypy_path = "."` in mypy
configuration both set the repository root as the Python path. This enables the flat import
style used throughout the project:

```python
from src.core.services.config_validation_service import ConfigValidator
from src.core.models.config.config_manager import RingConfig
```

### 10.3 No requirements.txt Files

The project does not maintain any `requirements.txt` files. All dependency information is
consolidated in `pyproject.toml`. This is a modern best practice that avoids the drift
between `requirements.txt` and `pyproject.toml` that commonly occurs in Python projects.

### 10.4 System Dependencies

The project has one non-Python system dependency:

- **Perl**: Required for the legacy Perl-based gem5 statistics parser. Installed in CI
  via `sudo apt-get install -y perl`.

Optional system dependencies for the LaTeX export feature:
- `texlive-latex-base` -- Core LaTeX engine
- `texlive-fonts-recommended` -- Standard fonts
- `texlive-fonts-extra` -- Additional fonts
- `cm-super` -- Type 1 Computer Modern fonts
- `texlive-xetex` -- XeLaTeX engine (for PGF format)

---

## 11. Summary

### Architecture of the Configuration Infrastructure

The RING-5 project's configuration, build, and CI infrastructure forms a layered defensive
system:

```
Layer 1: Developer Machine
  +-- Pre-commit hooks (12 third-party + 5 custom)
  +-- Makefile targets (quality-gate, arch-check)
  +-- IDE integration (mypy, black on save)

Layer 2: Git Push / Pull Request
  +-- CI quality-checks (black + flake8 + mypy + bandit)
  +-- CI tests (pytest + coverage + Codecov)
  +-- Architecture enforcement (boundary grep checks)
  +-- Security pattern scanning

Layer 3: Main Branch Merge
  +-- E2E browser tests (Playwright)
  +-- 90% coverage gate (test-ci target)

Layer 4: Ongoing Monitoring
  +-- Weekly dependency freshness check
  +-- Weekly CodeQL semantic analysis
  +-- Automated issue creation for outdated deps
```

### Key Design Decisions

| Decision                            | Rationale                                              |
|------------------------------------|--------------------------------------------------------|
| pyproject.toml as single config    | Reduces configuration drift; modern best practice      |
| setuptools (not Poetry/Hatch)      | Broadest compatibility; no lock file needed             |
| TypedDict over Pydantic            | Zero-cost JSON compatibility; no serialization overhead |
| 4 dependency groups                | Granular installation for different contexts            |
| Custom pre-commit architecture hooks| Automated enforcement of layer boundaries             |
| Loose JSON schemas (additionalProperties)| Extensibility for new shaper types without schema changes |
| Weekly dependency checks           | Proactive security without blocking development        |
| CodeQL + Bandit + pip-audit        | Defense in depth: AST analysis + semantic + supply chain|
| No requirements.txt               | Single source of truth for dependencies                 |
| 100-char line length               | Practical balance for data-processing code             |

### Files Referenced in This Analysis

| File Path | Role |
|-----------|------|
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/pyproject.toml` | Package config, deps, tools |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/Makefile` | Build targets & dev commands |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.pre-commit-config.yaml` | Pre-commit hooks config |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.github/workflows/ci.yml` | Main CI pipeline |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.github/workflows/architecture-check.yml` | Architecture enforcement |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.github/workflows/dependency-check.yml` | Weekly dep audit |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.github/workflows/codeql.yml` | CodeQL security scan |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.github/workflows/pages.yml` | Docs deployment |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/.github/codeql/codeql-config.yml` | CodeQL exclusions |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/models/config/__init__.py` | Config module init |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/models/config/config_manager.py` | TypedDict models |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/services/config_validation_service.py` | Validation & templates |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/models/config/schemas/pipeline_schema.json` | Pipeline JSON schema |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/models/config/schemas/parser_config_schema.json` | Parser config schema |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/models/config/schemas/portfolio_schema.json` | Portfolio schema |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/src/core/models/config/schemas/saved_config_schema.json` | Saved config schema |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/scripts/verify_installation.py` | Installation verifier |
| `/home/vnicolas/workspace/repos/RING-5-unified-engine-v2/scripts/analyze_dependencies.py` | Dependency analyzer |
