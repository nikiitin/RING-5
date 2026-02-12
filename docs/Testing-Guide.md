---
title: "Testing Guide"
nav_order: 18
---

# Testing Guide

Comprehensive guide to testing in RING-5.

## Overview

RING-5 uses pytest for all testing with four test levels:

- **Unit Tests** (`tests/unit/`): Individual functions, classes, and modules in isolation
- **UI Unit Tests** (`tests/ui_unit/`): Streamlit UI components tested with mocked `st` module
- **Integration Tests** (`tests/integration/`): Component interactions and end-to-end workflows
- **Performance Tests** (`tests/performance/`): Benchmark and regression tests

**Current Baseline**: 1344 tests passing, 17 skipped

## Test Structure

```text
tests/
├── conftest.py              # Root conftest — shared helpers & fixtures
├── __init__.py
├── unit/                    # Pure unit tests (~65+ files)
│   ├── conftest.py
│   ├── __init__.py
│   ├── export/              # LaTeX export tests
│   │   ├── conftest.py      # requires_xelatex marker
│   │   ├── __init__.py
│   │   └── converters/
│   │       └── __init__.py
│   ├── test_base_plot.py
│   ├── test_shapers_extended.py
│   └── ...
├── ui_unit/                 # Streamlit UI unit tests (mocked st)
│   ├── conftest.py
│   ├── __init__.py
│   ├── test_plot_manager_logic.py
│   ├── test_data_source_extras.py
│   └── ...
├── integration/             # Integration tests
│   ├── conftest.py
│   ├── __init__.py
│   ├── test_transformation_pipeline.py
│   ├── test_e2e_managers_shapers.py
│   └── ...
├── performance/             # Performance benchmarks
│   ├── conftest.py
│   ├── __init__.py
│   └── test_worker_pool_performance.py
├── ui/                      # Streamlit AppTest E2E tests
│   ├── __init__.py
│   ├── test_pages.py
│   └── test_ui_sanity.py
├── helpers/                 # Reusable test helper functions
│   └── sample_figures.py    # Plotly figure factories for export tests
├── data/                    # Test data files (excluded from collection)
│   └── mock/                # Mock gem5 data for integration tests
│       ├── inputs/
│       ├── expects/
│       └── config_files/
└── manual/                  # Manual visual tests (excluded from collection)
    └── test_histogram_visual.py
```

## Running Tests

### All Tests

```bash
make test
# or
pytest
```

### Specific Test Directory

```bash
pytest tests/unit/ -v
pytest tests/ui_unit/ -v
pytest tests/integration/ -v
```

### Specific Test File or Function

```bash
pytest tests/unit/test_shapers_extended.py -v
pytest tests/unit/test_shapers_extended.py::test_rename_basic -v
```

### With Coverage

```bash
pytest --cov=src --cov-report=html tests/
# Open htmlcov/index.html
```

### Excluding Slow Tests

```bash
pytest -m "not slow" tests/
pytest -m "not benchmark" tests/
```

## Shared Fixtures (conftest.py)

### Root Conftest (`tests/conftest.py`)

Provides utilities shared across **all** test directories:

```python
from tests.conftest import columns_side_effect

# columns_side_effect — Mocks st.columns() behavior
# Returns a list of MagicMock objects matching the spec (int or list/tuple)

# mock_api — Basic ApplicationAPI mock with state_manager
# Automatically available to all tests via pytest fixture injection
```

### Usage in Test Files

**Using `columns_side_effect`** (import the helper function):

```python
from tests.conftest import columns_side_effect

@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.components.my_module.st") as mock_st:
        mock_st.columns.side_effect = columns_side_effect
        yield mock_st
```

**Using `mock_api`** (auto-discovered by pytest):

```python
def test_something(mock_api):
    # mock_api has: api.state_manager = MagicMock()
    mock_api.state_manager.get_data.return_value = some_data
    ...
```

**Overriding `mock_api`** for extended wiring:

```python
@pytest.fixture
def mock_api():
    """Extended mock with backend and portfolio."""
    api = MagicMock()
    api.state_manager = MagicMock()
    api.backend = MagicMock()
    api.portfolio = MagicMock()
    return api
```

## Writing Tests

### Unit Test Template

```python
import pytest
import pandas as pd

from src.module.my_class import MyClass


@pytest.fixture
def sample_data():
    """Fixture providing sample data specific to this test file."""
    return pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"]
    })


class TestMyClass:
    """Test suite for MyClass."""

    def test_initialization(self):
        obj = MyClass(param=123)
        assert obj.param == 123

    def test_basic_operation(self, sample_data):
        obj = MyClass()
        result = obj.process(sample_data)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_error_handling(self):
        obj = MyClass()
        with pytest.raises(ValueError):
            obj.process(None)
```

### UI Unit Test Template

```python
from unittest.mock import MagicMock, patch

import pytest

from src.web.pages.ui.components.my_component import MyComponent
from tests.conftest import columns_side_effect


@pytest.fixture
def mock_streamlit():
    with patch("src.web.pages.ui.components.my_component.st") as mock_st:
        mock_st.session_state = {}
        mock_st.columns.side_effect = columns_side_effect
        yield mock_st


def test_render_component(mock_streamlit, mock_api):
    MyComponent.render(mock_api)
    mock_streamlit.markdown.assert_called()
```

### Integration Test Template

```python
import pytest
import pandas as pd

from src.core.application_api import ApplicationAPI


@pytest.fixture
def facade():
    return ApplicationAPI()


class TestDataPipeline:
    def test_parse_and_load_workflow(self, facade, tmp_path):
        stats_file = tmp_path / "stats.txt"
        stats_file.write_text("simTicks 1000\\nsystem.cpu.ipc 1.5\\n")

        # Execute parse workflow
        futures = facade.submit_parse_async(
            str(tmp_path), "stats.txt", ["system.cpu.ipc"], str(tmp_path)
        )
        results = [f.result() for f in futures]
        csv_path = facade.finalize_parsing(str(tmp_path), results)

        data = facade.load_csv_file(csv_path)
        assert "system.cpu.ipc" in data.columns
```

## Best Practices

### DO

- **Use fixtures** for test data — avoid inline DataFrame creation
- **One concern per test** — focused assertions
- **Test edge cases** — empty data, nulls, extremes
- **Use `autospec=True`** for mocks — catches API mismatches
- **Use `@pytest.mark.parametrize`** for input variations
- **Use `tmp_path`** for file operations — auto-cleaned by pytest
- **Import `columns_side_effect`** from conftest — don't redefine it

### DON'T

- **No `print()` in tests** — use assertions and `pytest -s` for debugging
- **No `if __name__ == "__main__"`** — pytest discovers tests automatically
- **No `inplace=True`** — always return new DataFrames
- **No bare `except:`** — catch specific exceptions
- **No synchronous wrappers** around async APIs

## Parameterized Tests

```python
@pytest.mark.parametrize("input_val,expected", [
    (1, 2),
    (2, 4),
    (0, 0),
    (-1, -2),
])
def test_double(input_val, expected):
    assert double(input_val) == expected
```

## Testing DataFrame Operations

```python
def test_dataframe_transform():
    input_df = pd.DataFrame({"col": [1, 2, 3]})
    result_df = transform(input_df)

    expected = pd.DataFrame({"col": [2, 4, 6]})
    pd.testing.assert_frame_equal(result_df, expected)

    # Verify immutability
    assert result_df is not input_df
```

## Debugging Tests

```bash
# Show stdout during tests
pytest -s tests/unit/test_file.py

# Drop into debugger on failure
pytest --pdb tests/unit/test_file.py

# Verbose with full tracebacks
pytest -vv --tb=long tests/unit/test_file.py
```

## Markers

Available markers (registered in `pyproject.toml`):

| Marker | Purpose |
|--------|---------|
| `@pytest.mark.slow` | Long-running tests |
| `@pytest.mark.benchmark` | Performance benchmarks |
| `@pytest.mark.smoke` | Quick smoke tests |
| `@pytest.mark.requires_latex` | Tests needing LaTeX |
| `@pytest.mark.requires_browser` | Tests needing a browser |

## Next Steps

- Development Setup: [Development-Setup.md](Development-Setup.md)
- Adding Plot Types: [Adding-Plot-Types.md](Adding-Plot-Types.md)
- Architecture: [Architecture.md](Architecture.md)
