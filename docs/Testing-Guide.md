---
title: "Testing Guide"
nav_order: 18
---

# Testing Guide

Comprehensive guide to testing in RING-5.

## Overview

RING-5 uses pytest for all testing with three test levels:

- **Unit Tests**: Individual functions and classes
- **Integration Tests**: Component interactions
- **E2E Tests**: Full application workflows

**Current Coverage**: 77% (target: 80%+)

## Test Structure

```text
tests/
├── unit/                   # Unit tests
│   ├── test_shapers.py
│   ├── test_parsers.py
│   └── test_plot_types.py
├── integration/            # Integration tests
│   ├── test_data_pipeline.py
│   ├── test_parser_workflow.py
│   └── test_transformation_pipeline.py
└── e2e/                    # End-to-end tests
    └── test_user_journeys.py
```

## Running Tests

### All Tests

```bash
make test
# or
pytest
```

### Specific Test File

```bash
pytest tests/unit/test_shapers.py -v
```

### Specific Test Function

```bash
pytest tests/unit/test_shapers.py::test_rename_basic -v
```

### With Coverage

```bash
pytest --cov=src --cov-report=html tests/
# Open htmlcov/index.html
```

### Watch Mode

```bash
pytest-watch
# Re-runs tests on file changes
```

## Writing Unit Tests

### Test Template

```python
import pytest
import pandas as pd
from src.module.my_class import MyClass


@pytest.fixture
def sample_data():
    """Fixture providing sample data."""
    return pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"]
    })


class TestMyClass:
    """Test suite for MyClass."""

    def test_initialization(self):
        """Test class initialization."""
        obj = MyClass(param=123)
        assert obj.param == 123

    def test_basic_operation(self, sample_data):
        """Test basic operation."""
        obj = MyClass()
        result = obj.process(sample_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3

    def test_error_handling(self):
        """Test error conditions."""
        obj = MyClass()

        with pytest.raises(ValueError):
            obj.process(None)
```

### Best Practices

1. **One Assertion Per Test**: Focus tests narrowly
2. **Use Fixtures**: Avoid code duplication
3. **Test Edge Cases**: Empty data, nulls, extremes
4. **Test Errors**: Verify exceptions raised
5. **Descriptive Names**: `test_normalize_to_baseline_success`

## Writing Integration Tests

### Integration Test Template

```python
import pytest
from pathlib import Path
from src.web.facade import BackendFacade


@pytest.fixture
def facade():
    return BackendFacade()


class TestDataPipeline:
    """Integration tests for data pipeline."""

    def test_parse_and_load_workflow(self, facade, tmp_path):
        """Test complete parse → load workflow."""
        # Setup: Create test data
        stats_file = tmp_path / "stats.txt"
        stats_file.write_text("simTicks 1000\nsystem.cpu.ipc 1.5\n")

        # Execute: Parse
        futures = facade.submit_parse_async(
            str(tmp_path), "stats.txt", ["system.cpu.ipc"], str(tmp_path)
        )
        results = [f.result() for f in futures]
        csv_path = facade.finalize_parsing(str(tmp_path), results)

        # Verify: Data loaded correctly
        data = facade.load_csv_file(csv_path)
        assert "system.cpu.ipc" in data.columns
        assert len(data) > 0
```

## Testing Shapers

### Shaper Test Pattern

```python
class TestRenameShaper:
    def test_rename_columns(self):
        data = pd.DataFrame({"old_name": [1, 2, 3]})
        config = {"column_mapping": {"old_name": "new_name"}}

        shaper = RenameShaper(config)
        result = shaper.transform(data)

        assert "new_name" in result.columns
        assert "old_name" not in result.columns

    def test_immutability(self):
        data = pd.DataFrame({"col": [1, 2, 3]})
        config = {"column_mapping": {"col": "new"}}

        shaper = RenameShaper(config)
        result = shaper.transform(data)

        # Original unchanged
        assert "col" in data.columns
        assert result is not data
```

## Testing Plot Types

### Plot Test Pattern

```python
class TestBarPlot:
    def test_create_figure(self):
        data = pd.DataFrame({
            "x": ["A", "B", "C"],
            "y": [1, 2, 3]
        })

        plot = BarPlot(plot_id=1, name="Test")
        plot.config = {"x_column": "x", "y_column": "y"}

        fig = plot.create_figure(data)

        assert fig is not None
        assert len(fig.data) > 0

    def test_missing_column(self):
        data = pd.DataFrame({"wrong": [1, 2, 3]})

        plot = BarPlot(plot_id=1, name="Test")
        plot.config = {"x_column": "x", "y_column": "y"}

        with pytest.raises(KeyError):
            plot.create_figure(data)
```

## Fixtures

### Common Fixtures

```python
@pytest.fixture
def sample_benchmark_data():
    """Sample gem5 benchmark data."""
    return pd.DataFrame({
        "benchmark": ["mcf", "omnetpp"] * 2,
        "config": ["baseline", "baseline", "tx", "tx"],
        "ipc": [1.5, 2.0, 1.8, 2.4]
    })


@pytest.fixture
def temp_directory(tmp_path):
    """Temporary directory for file operations."""
    return tmp_path


@pytest.fixture
def mock_streamlit(monkeypatch):
    """Mock Streamlit session_state."""
    import streamlit as st
    mock_state = {}
    monkeypatch.setattr(st, "session_state", mock_state)
    return mock_state
```

## Mocking

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch


def test_with_mock():
    with patch("src.module.external_call") as mock:
        mock.return_value = "mocked_result"

        result = my_function()

        assert result == "mocked_result"
        mock.assert_called_once()
```

## Test Coverage

### Generating Reports

```bash
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

### Coverage Goals

- **Overall**: 80%+
- **Critical Paths**: 90%+
- **UI Components**: 60%+ (harder to test)

### Improving Coverage

1. Identify untested code in report
2. Add tests for uncovered lines
3. Focus on critical business logic first

## Continuous Integration

Tests run automatically on:

- Every commit (pre-commit hook)
- Every pull request (GitHub Actions)
- Before deployment

**Requirements**: All tests must pass before merge.

## Debugging Tests

### Print Debugging

```python
def test_something(sample_data):
    print(f"Data shape: {sample_data.shape}")
    result = process(sample_data)
    print(f"Result: {result}")
    assert result == expected
```

Run with `-s` flag: `pytest -s tests/unit/test_file.py`

### PDB Debugger

```python
def test_something():
    import pdb; pdb.set_trace()
    result = process(data)
    assert result == expected
```

Run with `--pdb` flag: `pytest --pdb`

## Common Patterns

### Testing Async Code

```python
def test_async_operation():
    futures = submit_async_work()
    results = [f.result() for f in futures]
    assert len(results) > 0
```

### Testing DataFrame Operations

```python
def test_dataframe_operation():
    input_df = pd.DataFrame({"col": [1, 2, 3]})
    result_df = transform(input_df)

    # Use pandas testing utilities
    expected = pd.DataFrame({"col": [2, 4, 6]})
    pd.testing.assert_frame_equal(result_df, expected)
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6)
])
def test_double(input, expected):
    assert double(input) == expected
```

## Next Steps

- Development Setup: [Development-Setup.md](Development-Setup.md)
- Adding Features: [Adding-Plot-Types.md](Adding-Plot-Types.md)
- Contributing: [../CONTRIBUTING.md](../CONTRIBUTING.md)
