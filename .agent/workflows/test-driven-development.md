# Workflow: Test-Driven Development

**Workflow ID**: `tdd-workflow`  
**Complexity**: Fundamental  
**Applies to**: All code changes

## Overview

RING-5 follows strict TDD principles: **NO code is committed until it passes unit AND integration tests.**

## The Golden Rule

```
Write Test → See it Fail → Write Code → See it Pass → Refactor → Repeat
```

## Step-by-Step Process

### 1. Write the Test First

Before implementing ANY new feature or fixing a bug, write the test that defines expected behavior.

**Example: Adding new shaper**

```python
# tests/unit/test_percentage_shaper.py

def test_percentage_shaper_basic():
    """Test percentage calculation between two columns."""
    data = pd.DataFrame({
        "numerator": [50, 75, 100],
        "denominator": [100, 100, 100]
    })

    config = {
        "numerator_col": "numerator",
        "denominator_col": "denominator",
        "output_col": "percentage"
    }

    shaper = PercentageShaper(config)
    result = shaper.transform(data)

    expected = [50.0, 75.0, 100.0]
    assert result["percentage"].tolist() == expected
```

### 2. Run Test (Should Fail)

```bash
pytest tests/unit/test_percentage_shaper.py -v
```

Expected output:

```
FAILED - ModuleNotFoundError: No module named 'percentage_shaper'
```

✅ **Good**: Test fails for the right reason (missing implementation)

### 3. Implement Minimal Code

Write just enough code to make the test pass.

```python
# src/web/services/shapers/percentage_shaper.py

from src.web.services.shapers.base_shaper import BaseShaper

class PercentageShaper(BaseShaper):
    def __init__(self, config):
        super().__init__(config)
        self.numerator_col = config["numerator_col"]
        self.denominator_col = config["denominator_col"]
        self.output_col = config["output_col"]

    def transform(self, data):
        result = data.copy()
        result[self.output_col] = (
            result[self.numerator_col] / result[self.denominator_col] * 100
        )
        return result
```

### 4. Run Test Again (Should Pass)

```bash
pytest tests/unit/test_percentage_shaper.py -v
```

Expected output:

```
PASSED
```

✅ **Good**: Test passes

### 5. Add Edge Cases

Now add tests for edge cases:

```python
def test_percentage_shaper_division_by_zero():
    """Test handling of division by zero."""
    data = pd.DataFrame({
        "numerator": [50],
        "denominator": [0]
    })

    config = {...}
    shaper = PercentageShaper(config)

    with pytest.raises(ZeroDivisionError):
        shaper.transform(data)

def test_percentage_shaper_missing_column():
    """Test error when column doesn't exist."""
    data = pd.DataFrame({"other": [1, 2, 3]})

    config = {
        "numerator_col": "missing",
        "denominator_col": "denominator",
        "output_col": "percentage"
    }

    shaper = PercentageShaper(config)

    with pytest.raises(KeyError):
        shaper.transform(data)
```

### 6. Refine Implementation

Update implementation to handle edge cases:

```python
def transform(self, data):
    # Validate columns exist
    for col in [self.numerator_col, self.denominator_col]:
        if col not in data.columns:
            raise KeyError(f"Column '{col}' not found")

    result = data.copy()

    # Check for division by zero
    if (result[self.denominator_col] == 0).any():
        raise ZeroDivisionError("Cannot divide by zero")

    result[self.output_col] = (
        result[self.numerator_col] / result[self.denominator_col] * 100
    )

    return result
```

### 7. Run All Tests

```bash
pytest tests/unit/test_percentage_shaper.py -v
```

All tests should pass.

### 8. Write Integration Test

Test the shaper in context:

```python
# tests/integration/test_shaper_integration.py

def test_percentage_shaper_in_pipeline():
    """Test percentage shaper within a full pipeline."""
    data = pd.DataFrame({
        "baseline_time": [100, 200, 300],
        "optimized_time": [80, 160, 240],
        "benchmark": ["A", "B", "C"]
    })

    pipeline = [
        {
            "type": "percentage",
            "numerator_col": "optimized_time",
            "denominator_col": "baseline_time",
            "output_col": "percentage_of_baseline"
        }
    ]

    result = data.copy()
    for shaper_config in pipeline:
        shaper = ShaperFactory.create_shaper(
            shaper_config["type"],
            shaper_config
        )
        result = shaper.transform(result)

    expected = [80.0, 80.0, 80.0]
    assert result["percentage_of_baseline"].tolist() == expected
```

### 9. Run Full Test Suite

```bash
make test
```

Expected output:

```
===== 458 passed, 2 warnings in X.XXs =====
```

## Test Organization

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual functions/classes in isolation

**Characteristics**:

- Fast (milliseconds)
- Use mocks for external dependencies
- Test one thing at a time
- No file I/O, no network calls

**Example structure**:

```
tests/unit/
├── test_shapers.py              # All shaper unit tests
├── test_plot_classes.py         # Plot type unit tests
├── test_scanner_service.py      # Scanner logic tests
└── test_parse_service.py        # Parser logic tests
```

### Integration Tests (`tests/integration/`)

**Purpose**: Test component interactions

**Characteristics**:

- Slower (seconds)
- Use real files (test data)
- Test data flow through layers
- Verify contracts between components

**Example structure**:

```
tests/integration/
├── test_gem5_parsing.py         # End-to-end parsing
├── test_data_pipeline.py        # Full data pipeline
├── test_plot_lifecycle.py       # Plot creation to rendering
└── test_e2e_managers_shapers.py # Manager + shaper integration
```

### E2E Tests (`tests/e2e/`)

**Purpose**: Test complete user workflows

**Characteristics**:

- Slowest (seconds to minutes)
- Simulate user actions
- Use real Streamlit interactions (if possible)
- Test full system behavior

## Running Tests

### Run Specific Test File

```bash
pytest tests/unit/test_shapers.py -v
```

### Run Specific Test Function

```bash
pytest tests/unit/test_shapers.py::test_rename_shaper_basic -v
```

### Run Tests Matching Pattern

```bash
pytest -k "shaper" -v
```

### Run with Coverage

```bash
pytest --cov=src tests/unit/ --cov-report=term-missing
```

### Run in Parallel

```bash
pytest -n auto
```

### Run All Tests (Make Target)

```bash
make test
```

## Test Fixtures

Use fixtures for reusable test data:

```python
@pytest.fixture
def sample_gem5_data():
    """Create realistic gem5 stats data."""
    return pd.DataFrame({
        "system.cpu.ipc": [1.5, 2.0, 1.8],
        "system.cpu.cycles": [1000, 2000, 1500],
        "benchmark": ["specjbb", "specjbb", "specjbb"],
        "config": ["baseline", "optimized", "aggressive"]
    })

@pytest.fixture
def facade():
    """Create BackendFacade instance."""
    return BackendFacade()

def test_load_csv(facade, tmp_path):
    """Test CSV loading via facade."""
    csv_path = tmp_path / "test.csv"
    sample_gem5_data().to_csv(csv_path, index=False)

    data = facade.load_csv(str(csv_path))
    assert len(data) == 3
```

## Mocking Patterns

### Mock Streamlit

```python
from unittest.mock import MagicMock, patch

@patch("src.web.ui.components.st")
def test_ui_component(mock_st):
    """Test UI component without Streamlit."""
    mock_st.selectbox.return_value = "option1"
    mock_st.button.return_value = True

    # Test component logic
    result = render_component()

    # Verify interactions
    mock_st.selectbox.assert_called_once()
    assert result == "expected_value"
```

### Mock File I/O

```python
from unittest.mock import mock_open, patch

@patch("builtins.open", mock_open(read_data="test content"))
def test_file_reading():
    """Test file reading without actual files."""
    content = read_file("fake_path.txt")
    assert content == "test content"
```

### Mock Async Operations

```python
from unittest.mock import MagicMock
from concurrent.futures import Future

def test_async_parsing():
    """Test async parsing with mocked futures."""
    mock_future = Future()
    mock_future.set_result({"variable": "data"})

    facade = BackendFacade()
    with patch.object(facade, 'submit_parse_async', return_value=[mock_future]):
        futures = facade.submit_parse_async("path", "pattern", [], "output")
        results = [f.result() for f in futures]

        assert len(results) == 1
        assert results[0]["variable"] == "data"
```

## Coverage Goals

- **Unit tests**: 80%+ coverage
- **Integration tests**: Cover all major workflows
- **E2E tests**: Cover all user journeys

## When Tests Fail

### 1. Read the Error Message

```
FAILED tests/unit/test_shapers.py::test_rename - KeyError: 'old_col'
```

→ Missing column in test data

### 2. Run with Verbose Output

```bash
pytest tests/unit/test_shapers.py::test_rename -vv
```

### 3. Use Debugger

```bash
pytest tests/unit/test_shapers.py::test_rename --pdb
```

### 4. Check Test Data

```python
# Add print statement in test
def test_rename():
    print(f"Data columns: {data.columns.tolist()}")
    # ... rest of test
```

### 5. Verify Assumptions

- Is the fixture providing correct data?
- Are mocks configured correctly?
- Is the test logic correct?

## Checklist

Before committing:

- [ ] All new functions have unit tests
- [ ] All new classes have unit tests
- [ ] Integration tests cover new workflows
- [ ] All tests pass (`make test`)
- [ ] Coverage hasn't decreased
- [ ] Edge cases are tested
- [ ] Error handling is tested
- [ ] Documentation is updated

## References

- pytest documentation: https://docs.pytest.org/
- Test examples: `tests/unit/`, `tests/integration/`
- Makefile targets: `make test`, `make test-unit`, `make test-integration`
- Coverage reports: Generated in `htmlcov/` directory
