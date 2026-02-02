# Adding Shapers

Guide to creating custom data transformation shapers.

## Overview

Shapers transform DataFrames in the analysis pipeline. They follow the **Strategy Pattern** and are composable (pipelines).

**Key Concepts**:
- All shapers inherit from base interface
- Immutable transformations (return new DataFrame)
- Registered in `ShaperFactory`
- Chainable in pipelines

## Step 1: Create Shaper Class

### File Location

Create in `src/web/services/shapers/`:

```
src/web/services/shapers/
├── my_shaper.py       # Your new shaper
├── column_selector.py
├── sort_shaper.py
└── ...
```

### Class Template

```python
from typing import Dict, Any
import pandas as pd


class MyShaper:
    """
    Custom shaper that [describe transformation].

    Configuration:
        param1 (type): Description
        param2 (type): Description

    Example:
        config = {"param1": "value", "param2": 123}
        shaper = MyShaper(config)
        result = shaper(data)
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize shaper with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.param1 = config.get("param1")
        self.param2 = config.get("param2", default_value)

    def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformation to data.

        Args:
            data: Input DataFrame

        Returns:
            Transformed DataFrame (new instance)

        Raises:
            ValueError: If configuration invalid
            KeyError: If required columns missing
        """
        # Validate
        self._validate(data)

        # Transform (immutable)
        result = data.copy()

        # Apply your transformation
        result = self._transform(result)

        return result

    def _validate(self, data: pd.DataFrame) -> None:
        """Validate data and configuration."""
        if self.param1 not in data.columns:
            raise KeyError(f"Column {self.param1} not found")

        if not isinstance(self.param2, int):
            raise ValueError("param2 must be integer")

    def _transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Core transformation logic."""
        # Your transformation here
        return data
```

## Step 2: Register in Factory

Edit `src/web/services/shapers/shaper_factory.py`:

```python
from src.web.services.shapers.my_shaper import MyShaper


class ShaperFactory:
    @staticmethod
    def create_shaper(shaper_type: str, config: Dict[str, Any]):
        shapers = {
            "column_selector": ColumnSelector,
            "sort": SortShaper,
            "my_shaper": MyShaper,  # Add here
            # ...
        }

        if shaper_type not in shapers:
            raise ValueError(f"Unknown shaper: {shaper_type}")

        return shapers[shaper_type](config)
```

## Step 3: Write Tests

Create `tests/unit/test_my_shaper.py`:

```python
import pytest
import pandas as pd
from src.web.services.shapers.my_shaper import MyShaper


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return pd.DataFrame({
        "col1": [1, 2, 3, 4, 5],
        "col2": ["a", "b", "c", "d", "e"]
    })


class TestMyShaper:
    """Test suite for MyShaper."""

    def test_basic_transformation(self, sample_data):
        """Test basic shaper operation."""
        config = {"param1": "col1", "param2": 10}
        shaper = MyShaper(config)

        result = shaper(sample_data)

        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        # Add specific assertions

    def test_immutability(self, sample_data):
        """Test data immutability."""
        original = sample_data.copy()
        config = {"param1": "col1", "param2": 10}
        shaper = MyShaper(config)

        result = shaper(sample_data)

        # Original unchanged
        pd.testing.assert_frame_equal(sample_data, original)
        # Result is different object
        assert result is not sample_data

    def test_missing_column(self, sample_data):
        """Test error on missing column."""
        config = {"param1": "missing", "param2": 10}
        shaper = MyShaper(config)

        with pytest.raises(KeyError):
            shaper(sample_data)

    def test_invalid_config(self, sample_data):
        """Test error on invalid config."""
        config = {"param1": "col1", "param2": "invalid"}
        shaper = MyShaper(config)

        with pytest.raises(ValueError):
            shaper(sample_data)
```

Run tests:

```bash
pytest tests/unit/test_my_shaper.py -v
```

## Step 4: Add UI Component

Create `src/web/ui/components/shapers/my_shaper_ui.py`:

```python
import streamlit as st
from typing import Dict, Any


def render_my_shaper_config() -> Dict[str, Any]:
    """
    Render UI for MyShaper configuration.

    Returns:
        Configuration dictionary
    """
    st.subheader("My Shaper")

    # Get available columns
    from src.web.state_manager import StateManager
    columns = StateManager.get_columns()

    # Configuration inputs
    param1 = st.selectbox(
        "Parameter 1",
        options=columns,
        help="Select column for param1"
    )

    param2 = st.number_input(
        "Parameter 2",
        min_value=0,
        value=10,
        help="Integer parameter"
    )

    # Return config
    return {
        "type": "my_shaper",
        "param1": param1,
        "param2": param2
    }
```

Register in `src/web/ui/components/shaper_configurator.py`:

```python
from src.web.ui.components.shapers.my_shaper_ui import render_my_shaper_config


def render_shaper_selector():
    shaper_type = st.selectbox(
        "Shaper Type",
        options=["column_selector", "sort", "my_shaper", ...]
    )

    if shaper_type == "my_shaper":
        return render_my_shaper_config()
    # ... other shapers
```

## Example: Filter Shaper

Complete example of a filtering shaper:

```python
class FilterShaper:
    """
    Filter rows based on column values.

    Configuration:
        column (str): Column to filter
        operator (str): Comparison operator ('>', '<', '==', '!=')
        value (float|str): Value to compare against

    Example:
        config = {"column": "ipc", "operator": ">", "value": 1.5}
        shaper = FilterShaper(config)
        filtered = shaper(data)  # Keep only rows where ipc > 1.5
    """

    OPERATORS = {
        ">": lambda x, v: x > v,
        "<": lambda x, v: x < v,
        "==": lambda x, v: x == v,
        "!=": lambda x, v: x != v,
        ">=": lambda x, v: x >= v,
        "<=": lambda x, v: x <= v
    }

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.column = config["column"]
        self.operator = config["operator"]
        self.value = config["value"]

        if self.operator not in self.OPERATORS:
            raise ValueError(f"Invalid operator: {self.operator}")

    def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
        if self.column not in data.columns:
            raise KeyError(f"Column {self.column} not found")

        # Apply filter
        op_func = self.OPERATORS[self.operator]
        mask = op_func(data[self.column], self.value)

        return data[mask].copy()
```

## Best Practices

1. **Immutability**: Always return new DataFrame, never modify input
2. **Validation**: Check config and data before transformation
3. **Type Hints**: Full annotations on all methods
4. **Error Handling**: Clear error messages with context
5. **Documentation**: Docstrings with examples
6. **Testing**: Test basic operation, immutability, errors, edge cases

## Common Patterns

### Column Operations

```python
def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["new_col"] = result["col1"] + result["col2"]
    return result
```

### Conditional Transformation

```python
def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    mask = result["col"] > threshold
    result.loc[mask, "col"] = new_value
    return result
```

### Aggregation

```python
def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
    return data.groupby("category").agg({"value": "mean"}).reset_index()
```

## Integration Testing

Test shaper in pipeline:

```python
def test_shaper_in_pipeline():
    data = pd.DataFrame({"col": [1, 2, 3, 4, 5]})

    pipeline = [
        {"type": "my_shaper", "param1": "col", "param2": 10},
        {"type": "sort", "column": "col", "ascending": False}
    ]

    result = data.copy()
    for shaper_config in pipeline:
        shaper = ShaperFactory.create_shaper(
            shaper_config["type"],
            shaper_config
        )
        result = shaper(result)

    assert len(result) > 0
```

## Next Steps

- Pipeline Building: [Data-Transformations.md](Data-Transformations.md)
- Testing: [Testing-Guide.md](Testing-Guide.md)
- Pandas Reference: https://pandas.pydata.org/docs/
