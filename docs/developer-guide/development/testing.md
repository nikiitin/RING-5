---
title: "Testing"
parent: Development
grand_parent: Developer Guide
nav_order: 2
---

# Testing

This guide covers the testing architecture, patterns, and conventions used in
RING-5. The test suite is organized across eight directories, each targeting a
specific testing concern. Run `make test` for the current suite.

## Overview

The project uses **pytest** (>= 9.0.2) as its test framework, with parallel
execution via **pytest-xdist** (`-n 3 --dist loadgroup`) enabled by default.

| Category | Directory | Purpose |
|---|---|---|
| Unit | `tests/unit/` | Pure logic tests with mocked dependencies |
| Integration | `tests/integration/` | Multi-component tests with real services |
| UI E2E | `tests/ui/` | Streamlit `AppTest`-based end-to-end tests |
| UI Unit | `tests/ui_unit/` | UI component tests with mocked Streamlit |
| UI Logic | `tests/ui_logic/` | Controller and orchestration tests |
| E2E (browser) | `tests/e2e/` | Playwright browser tests (marker `requires_browser`) |
| Visual | `tests/visual/` | Playwright screenshot tests (excluded from default runs) |
| Performance | `tests/performance/` | Timing threshold regression tests |
| Compliance | `tests/tests_principle_compliance/` | TDD principle demos (excluded from default runs) |

## Directory Structure

```
tests/
    conftest.py                     # Root: shared fixtures, pytest_plugins
    helpers/                        # Shared utilities (gem5 fixtures, benchmarks, sample figures)
    data/                           # Test data: synthetic gem5 stats, mock configs (excluded)
    unit/                           # core, visualization, export, parsers, shapers
    integration/                    # real API, pipelines, parsing, portfolios
    ui/                             # AppTest E2E with helpers.py bootstrap
    ui_unit/                        # mocked st module component tests
    ui_logic/                       # controller tests with StubPlotHandle
    e2e/                            # Playwright browser tests (marker requires_browser)
    visual/                         # Playwright Page Object Model (excluded from default)
    performance/                    # timing threshold regression
    tests_principle_compliance/     # TDD demos (excluded from default)
```

## Pytest Configuration

All settings are defined in `pyproject.toml` under `[tool.pytest.ini_options]`.

### Default Options

```toml
addopts = "-v --tb=short --strict-markers -n 3 --dist loadgroup"
```

- `-n 3` -- 3 parallel xdist workers.
- `--dist loadgroup` -- Tests sharing an `xdist_group` marker run on the same worker.
- `--strict-markers` -- Undefined marker names cause an error.
- `xfail_strict = true` -- Tests marked `xfail` that unexpectedly pass will fail.

### Custom Markers

| Marker | Purpose |
|---|---|
| `requires_latex` | Skip when XeLaTeX is not installed |
| `requires_browser` | Skip when no browser/server is available |
| `benchmark` | Performance benchmark tests |
| `smoke` | Quick smoke tests |
| `slow` | Slow tests (deselect with `-m "not slow"`) |
| `xdist_group` | Force grouped tests onto one xdist worker |

### Excluded Directories

These directories are excluded from default discovery via `norecursedirs`:
`tests/tests_principle_compliance`, `tests/manual`, `tests/data`, `tests/visual`.

### Plugins

| Plugin | Version | Purpose |
|---|---|---|
| `pytest-xdist` | >= 3.6.1 | Parallel execution |
| `pytest-cov` | >= 7.0.0 | Coverage reporting |
| `pytest-randomly` | >= 3.16.0 | Random ordering to detect order dependencies |
| `pytest-timeout` | >= 2.2.0 | CI timeout protection (optional `ci` extra) |
| `pytest-playwright` | >= 0.7.0 | Browser integration (optional `e2e` extra) |

## Fixture Architecture

The project uses a layered conftest hierarchy. The root `conftest.py` provides
fixtures available everywhere; sub-directory conftest files add specialized fixtures.

### Root Fixtures (`tests/conftest.py`)

```python
@pytest.fixture
def mock_api() -> MagicMock:
    """MagicMock ApplicationAPI -- used by most UI tests."""
    api = MagicMock()
    api.state_manager = MagicMock()
    return api
```

- **`sample_data`** -- 6-row DataFrame with `benchmark_name`, `config_description`,
  `simTicks`, `system.cpu.ipc`. The universal test data fixture.
- **`sample_data_extended`** -- Adds `numCycles` and `committedInsts` columns.
- **`mock_state_manager`** -- `MagicMock` of `RepositoryStateManager` with all
  getters returning empty/None defaults.
- **`e2e_sample_data`** -- 18-row, 8-column DataFrame from `tests.ui.helpers`.
- **`_cleanup_perl_worker_pool`** -- Session autouse fixture that shuts down the
  global `PerlWorkerPool` after all tests complete.

Synthetic gem5 path fixtures are registered globally via:

```python
pytest_plugins = ["tests.helpers.gem5_fixtures"]
```

### Integration Fixtures (`tests/integration/conftest.py`)

Uses **real** (not mocked) instances:

- **`_reset_service_caches`** (autouse) -- Resets `PathService`, `CsvPoolService`,
  and `ConfigService` class-level caches before and after each test.
- **`facade`** -- Fresh `ApplicationAPI()`.
- **`loaded_facade`** -- `ApplicationAPI` with data pre-loaded.
- **`bar_config`**, **`grouped_bar_config`**, etc. -- Minimal plot config dicts.

### UI Logic Fixtures (`tests/ui_logic/conftest.py`)

- **`StubPlotHandle`** -- Lightweight class satisfying the `PlotHandle` protocol
  with no-op or MagicMock-returning methods.
- **`mock_lifecycle`** -- Mock `PlotLifecycleService`.
- **`mock_registry`** -- Mock `PlotTypeRegistry` returning 8 available types.

## Unit Test Patterns

### Arrange-Act-Assert

All unit tests follow the AAA pattern:

```python
def test_load_data_success(self, application_api: Any) -> None:
    # Arrange
    path = "/test/data.csv"
    df = pd.DataFrame({"col": [1, 2]})
    mock_data = cast(Any, application_api)._mock_services.data_services
    mock_data.load_csv_file.return_value = df

    # Act
    application_api.load_data(path)

    # Assert
    mock_data.load_csv_file.assert_called_once_with(path)
    application_api.state_manager.set_data.assert_called_once_with(df)
```

### Test Class Grouping and Naming

Related tests are grouped into `Test*` classes. Naming conventions:

- Files: `test_<module>.py`, `test_<module>_coverage.py`, `test_<module>_branches.py`
- Classes: `Test<ComponentOrFeature>`
- Methods: `test_<behavior_under_test>`

### xdist Grouping

Tests involving shared resources (e.g., `PerlWorkerPool`) use `xdist_group`:

```python
pytestmark = pytest.mark.xdist_group("perl_pool")
```

## Integration Test Patterns

Integration tests use real `ApplicationAPI` and `RepositoryStateManager` instances.

### Service Cache Isolation

An autouse fixture resets class-level caches, which is critical because
`PathService`, `CsvPoolService`, and `ConfigService` use class-level caches:

```python
@pytest.fixture(autouse=True)
def _reset_service_caches() -> Any:
    PathService.reset_caches()
    CsvPoolService.clear_caches()
    ConfigService.reset_caches()
    yield
    PathService.reset_caches()
    CsvPoolService.clear_caches()
    ConfigService.reset_caches()
```

### Coverage Areas

- **Data pipeline** -- Seeds reduction, outlier removal, shaper operations.
- **gem5 parsing** -- Full scan/parse/CSV workflow with synthetic and real data.
- **Render pipeline** -- Data-to-figure rendering for all plot types.
- **Portfolio lifecycle** -- Save/load round-trip serialization.
- **State management** -- Multi-repository coordination.

## UI Test Patterns

The project tests Streamlit code at three tiers with increasing fidelity.

### Tier 1: Mocked `st` Module (`tests/ui_unit/`)

Patches the `st` module at the import location of the component under test:

```python
with patch("src.web.components.data_managers.seeds_reducer.st") as mock_st:
    mock_st.session_state = {}
    mock_st.columns.side_effect = columns_side_effect
```

### Tier 2: Controller-Level Patch (`tests/ui_logic/`)

Patches `st` and `Component.render()` at the controller level, using
`StubPlotHandle` for protocol compliance:

```python
@patch("src.web.controllers.plot.creation_controller.st")
@patch("src.web.controllers.plot.creation_controller.PlotCreationComponent.render")
def test_create_delegates_to_lifecycle(self, mock_render, mock_st):
    mock_render.return_value = {"name": "Plot", "plot_type": "bar", "create_clicked": True}
    ctrl = _make_controller(api=api, lifecycle=lifecycle)
    ctrl.render_create_section()
    lifecycle.create_plot.assert_called_once()
```

### Tier 3: Real Streamlit Runtime (`tests/ui/`)

Uses Streamlit's `AppTest` framework running the actual `app.py` headlessly:

```python
from tests.ui.helpers import create_app_with_data, get_api

def test_bar_plot_full_chain(self) -> None:
    at = create_app_with_data()
    api = get_api(at)
    # ... create plot, apply shapers, render figure
    assert isinstance(fig, go.Figure)
```

Helpers in `tests/ui/helpers.py`: `create_app()`, `create_app_with_data(df)`,
`navigate_to(at, page)`, `get_api(at)`.

## Mock and Patch Strategies

### ApplicationAPI Mocking

Three levels depending on the test category:

- **Full mock** (root `mock_api` fixture) -- `MagicMock` with no wiring.
- **Partially-mocked** (unit tests) -- Patches `RepositoryStateManager` and
  `DefaultServicesAPI` while keeping `ApplicationAPI` itself real.
- **Real instances** (integration tests) -- `ApplicationAPI()` with no patches.

### Widget Interaction Mocking

Widget interactions are simulated using `side_effect` keyed on widget keys:

```python
apply_key = WidgetKeyBuilder.manager_key("seeds_reducer", "apply")
mock_st.button.side_effect = lambda label, key=None, **kwargs: key == apply_key
```

### DataFrame Assertions

```python
pd.testing.assert_frame_equal(result1, result2)   # Exact equality
assert "value.sd" in reduced.columns               # Column existence
assert np.isclose(result["col"].iloc[0], expected)  # Float comparison
```

## Running Tests

```bash
# Full suite (3 parallel workers, excludes visual/manual/compliance)
pytest

# Single directory or file
pytest tests/unit/
pytest tests/unit/test_application_api.py::TestApplicationAPI::test_load_data_success

# By marker
pytest -m smoke
pytest -m "not slow"
pytest -m requires_browser

# Keyword filtering
pytest -k "not dual_axis and not dual"

# Disable parallel execution
pytest -n 0

# Visual/Playwright tests (excluded from default runs)
pytest tests/visual/ -m requires_browser
HEADED=1 SLOW_MO=500 pytest tests/visual/   # Headed debugging mode

# Verbose/debug output
pytest --tb=long -v
pytest -s               # Show print/logging output
```

## Coverage

Coverage is managed via `pytest-cov` across both `src` and the supported
`ring5` package.

```bash
pytest --cov=src --cov=ring5 --cov-branch --cov-report=term-missing
pytest --cov=src --cov=ring5 --cov-branch --cov-report=html
```

The project includes coverage-targeted test files
(`test_*_coverage.py` and `test_*_branches.py`) that systematically fill
coverage gaps for specific modules.

```toml
[tool.coverage.run]
omit = [
    "src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py",
]
```

## See Also

- [pyproject.toml](https://github.com/nikiitin/RING-5/blob/main/pyproject.toml) -- Full pytest, coverage, and tool configuration.
- `tests/conftest.py` -- Root fixtures and plugin registration.
- `tests/helpers/` -- Shared test utilities (benchmarks, fixtures, sample figures).
- `tests/ui/helpers.py` -- AppTest bootstrapping and navigation helpers.
