---
name: shaper-pipeline
description: Guide for creating and using data transformation shapers and pipelines. Use when implementing data transformations, filtering, normalization, or custom data processing logic.
---

## Purpose

Guide for creating custom shapers and building transformation pipelines to prepare gem5 data for visualization.

## Architecture Context

```
┌────────────────────────────────────────┐
│  CSV Data (from parse)                 │
│  - Raw gem5 stats                      │
│  - Multiple columns                    │
└───────────┬────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│  Shaper Pipeline                       │
│  - Sequential transformations          │
│  - Immutable operations                │
└───────────┬────────────────────────────┘
            │
            ▼
┌────────────────────────────────────────┐
│  Transformed Data                      │
│  - Ready for plotting                  │
│  - Clean column names, normalized      │
└────────────────────────────────────────┘
```

## What is a Shaper?

A **shaper** is a data transformation function that:

- Takes a DataFrame as input
- Returns a **new** DataFrame (immutable)
- Performs one specific transformation
- Can be chained with other shapers

## Built-in Shapers

### 1. Rename Shaper

Renames columns for better readability.

```python
config = {
    "type": "rename",
    "column_mapping": {
        "system.cpu.ipc": "IPC",
        "system.cpu.dcache.miss_rate": "Miss Rate"
    }
}
```

### 2. Filter Shaper

Filters rows based on conditions.

```python
config = {
    "type": "filter",
    "column": "benchmark",
    "condition": "equals",  # or "not_equals", "contains", "greater_than", etc.
    "value": "specjbb"
}
```

### 3. Aggregate Shaper

Groups and aggregates data.

```python
config = {
    "type": "aggregate",
    "group_by": ["benchmark", "configuration"],
    "agg_column": "IPC",
    "agg_function": "mean"  # or "sum", "min", "max", "std"
}
```

### 4. Compute Shaper

Creates new columns from computations.

```python
config = {
    "type": "compute",
    "new_column": "speedup",
    "expression": "new_ipc / baseline_ipc"
}
```

### 5. Normalize Shaper

Normalizes values to a baseline.

```python
config = {
    "type": "normalize",
    "value_column": "execution_time",
    "group_by": "benchmark",
    "baseline_filter": {"configuration": "baseline"},
    "operation": "divide"  # result = value / baseline
}
```

## Creating a Custom Shaper

### Step 1: Create Shaper Class

**File**: `src/web/services/shapers/my_custom_shaper.py`

```python
\"\"\"
Custom data shaper for RING-5.
\"\"\"

from typing import Any, Dict

import pandas as pd

from src.web.services.shapers.base_shaper import BaseShaper


class MyCustomShaper(BaseShaper):
    \"\"\"
    Custom shaper that [describe transformation].

    Configuration:
        param1: Type - Description
        param2: Type - Description
    \"\"\"

    def __init__(self, config: Dict[str, Any]):
        \"\"\"
        Initialize shaper with configuration.

        Args:
            config: Configuration dict with required parameters
        \"\"\"
        super().__init__(config)
        self.param1 = config.get("param1")
        self.param2 = config.get("param2", "default_value")

        # Validate configuration
        if not self.param1:
            raise ValueError("param1 is required")

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        \"\"\"
        Apply transformation to data.

        Args:
            data: Input DataFrame

        Returns:
            New DataFrame with transformation applied

        Raises:
            KeyError: If required columns are missing
            ValueError: If transformation cannot be applied
        \"\"\"
        # CRITICAL: Always work on a copy
        result = data.copy()

        # Validate required columns exist
        if "required_column" not in result.columns:
            raise KeyError("Column 'required_column' not found")

        # Perform transformation (example: scale values)
        result["transformed"] = result[self.param1] * self.param2

        return result

    @staticmethod
    def render_config_ui() -> Dict[str, Any]:
        \"\"\"
        Render Streamlit UI for configuration.

        Returns:
            Configuration dict from user input
        \"\"\"
        import streamlit as st

        config = {}

        # Get available columns from current data
        from src.web.state_manager import StateManager
        data = StateManager.get_data()

        if data is not None and not data.empty:
            columns = data.columns.tolist()

            config["param1"] = st.selectbox("Select Column", columns)
            config["param2"] = st.number_input(
                "Scaling Factor",
                value=1.0,
                min_value=0.0
            )

        return config
```

### Step 2: Register in Factory

**File**: `src/web/services/shapers/shaper_factory.py`

```python
from src.web.services.shapers.my_custom_shaper import MyCustomShaper

class ShaperFactory:
    \"\"\"Factory for creating shaper instances.\"\"\"

    _shapers = {
        \"rename\": RenameShaper,
        \"filter\": FilterShaper,
        \"aggregate\": AggregateShaper,
        \"compute\": ComputeShaper,
        \"normalize\": NormalizeShaper,
        \"my_custom\": MyCustomShaper,  # ← Add here
    }

    @staticmethod
    def create_shaper(shaper_type: str, config: Dict[str, Any]) -> BaseShaper:
        \"\"\"Create shaper instance from type and config.\"\"\"
        if shaper_type not in ShaperFactory._shapers:
            raise ValueError(f\"Unknown shaper type: {shaper_type}\")

        shaper_class = ShaperFactory._shapers[shaper_type]
        return shaper_class(config)
```

### Step 3: Add to UI

**File**: `src/web/ui/components/shaper_components.py`

```python
def render_add_shaper_dialog():
    \"\"\"Render dialog for adding new shaper.\"\"\"

    shaper_type = st.selectbox(
        \"Shaper Type\",
        [\"rename\", \"filter\", \"aggregate\", \"compute\",
         \"normalize\", \"my_custom\"],  # ← Add here
        format_func=lambda x: {
            \"rename\": \"Rename Columns\",
            \"filter\": \"Filter Rows\",
            \"aggregate\": \"Aggregate Data\",
            \"compute\": \"Compute New Column\",
            \"normalize\": \"Normalize to Baseline\",
            \"my_custom\": \"My Custom Transform\",  # ← And here
        }[x]
    )
```

## Building Pipelines

### Example 1: Basic Pipeline

```python
# Filter → Rename → Aggregate
pipeline = [
    {
        "type": "filter",
        "column": "benchmark",
        "condition": "equals",
        "value": "specjbb"
    },
    {
        "type": "rename",
        "column_mapping": {
            "system.cpu.ipc": "IPC",
            "config": "Configuration"
        }
    },
    {
        "type": "aggregate",
        "group_by": ["Configuration"],
        "agg_column": "IPC",
        "agg_function": "mean"
    }
]

# Apply pipeline
result = data.copy()
for shaper_config in pipeline:
    shaper = ShaperFactory.create_shaper(
        shaper_config["type"],
        shaper_config
    )
    result = shaper.transform(result)
```

### Example 2: Normalization Pipeline

```python
# Compute speedup normalized to baseline
pipeline = [
    {
        "type": "rename",
        "column_mapping": {"execution_time": "time"}
    },
    {
        "type": "normalize",
        "value_column": "time",
        "group_by": "benchmark",
        "baseline_filter": {"config": "baseline"},
        "operation": "divide"
    },
    {
        "type": "compute",
        "new_column": "speedup",
        "expression": "1 / time_normalized"  # Invert for speedup
    }
]
```

### Example 3: Multi-Stage Aggregation

```python
# Complex aggregation with filtering
pipeline = [
    # First, filter out warmup runs
    {
        "type": "filter",
        "column": "phase",
        "condition": "not_equals",
        "value": "warmup"
    },
    # Then aggregate per benchmark
    {
        "type": "aggregate",
        "group_by": ["benchmark", "config"],
        "agg_column": "ipc",
        "agg_function": "mean"
    },
    # Compute geomean across benchmarks
    {
        "type": "aggregate",
        "group_by": ["config"],
        "agg_column": "ipc",
        "agg_function": "geomean"  # If implemented
    }
]
```

## Using with BackendFacade

```python
from src.web.facade import BackendFacade

facade = BackendFacade()

# Load data
data = facade.load_csv("path/to/data.csv")

# Define pipeline
pipeline = [
    {"type": "filter", "column": "benchmark", "condition": "contains", "value": "spec"},
    {"type": "rename", "column_mapping": {"old_name": "new_name"}},
    {"type": "aggregate", "group_by": ["config"], "agg_column": "ipc", "agg_function": "mean"}
]

# Apply transformations
transformed = facade.apply_shaper_pipeline(data, pipeline)

# Save result
facade.save_transformed_data(transformed, "transformed.csv")
```

## Testing Shapers

### Unit Test Template

**File**: `tests/unit/test_my_custom_shaper.py`

```python
import pandas as pd
import pytest

from src.web.services.shapers.my_custom_shaper import MyCustomShaper


class TestMyCustomShaper:
    \"\"\"Unit tests for MyCustomShaper.\"\"\"

    @pytest.fixture
    def sample_data(self):
        \"\"\"Create sample data for testing.\"\"\"
        return pd.DataFrame({
            \"value\": [10, 20, 30],
            \"other\": [1, 2, 3]
        })

    @pytest.fixture
    def shaper_config(self):
        \"\"\"Create shaper configuration.\"\"\"
        return {
            \"param1\": \"value\",
            \"param2\": 2.0
        }

    def test_initialization(self, shaper_config):
        \"\"\"Test shaper initializes correctly.\"\"\"
        shaper = MyCustomShaper(shaper_config)
        assert shaper.param1 == \"value\"
        assert shaper.param2 == 2.0

    def test_transform_basic(self, sample_data, shaper_config):
        \"\"\"Test basic transformation.\"\"\"
        shaper = MyCustomShaper(shaper_config)
        result = shaper.transform(sample_data)

        # Verify immutability
        assert result is not sample_data
        assert \"transformed\" in result.columns

        # Verify transformation logic
        expected = [20, 40, 60]  # value * 2.0
        assert result[\"transformed\"].tolist() == expected

    def test_missing_column(self, shaper_config):
        \"\"\"Test error when required column missing.\"\"\"
        shaper = MyCustomShaper(shaper_config)
        bad_data = pd.DataFrame({\"wrong\": [1, 2, 3]})

        with pytest.raises(KeyError):
            shaper.transform(bad_data)

    def test_invalid_config(self):
        \"\"\"Test error with invalid configuration.\"\"\"
        with pytest.raises(ValueError, match=\"param1 is required\"):
            MyCustomShaper({})
```

## Best Practices

### ✅ DO

1. **Always copy DataFrames**

   ```python
   result = data.copy()
   # Then modify result
   ```

2. **Chain transformations**

   ```python
   result = data.copy()
   for shaper in shapers:
       result = shaper.transform(result)
   ```

3. **Validate inputs**

   ```python
   if required_col not in data.columns:
       raise KeyError(f"Missing column: {required_col}")
   ```

4. **Keep shapers atomic**
   - One shaper = one transformation
   - Easy to understand, test, and reuse

### ❌ DON'T

1. **Don't use inplace operations**

   ```python
   # BAD
   data.drop(columns=['x'], inplace=True)

   # GOOD
   result = data.drop(columns=['x'])
   ```

2. **Don't modify input DataFrame**

   ```python
   # BAD
   def transform(self, data):
       data['new_col'] = data['old_col'] * 2
       return data

   # GOOD
   def transform(self, data):
       result = data.copy()
       result['new_col'] = result['old_col'] * 2
       return result
   ```

3. **Don't create complex multi-purpose shapers**
   - Split into multiple simple shapers
   - Use pipeline composition

## Common Patterns

### Geomean Calculation

```python
import numpy as np

def geomean(values):
    return np.exp(np.mean(np.log(values)))

result = data.groupby('config')['ipc'].apply(geomean)
```

### Percentage Change

```python
result['pct_change'] = ((result['new'] - result['baseline']) / result['baseline']) * 100
```

### Ranking

```python
result['rank'] = result.groupby('benchmark')['ipc'].rank(ascending=False)
```

## Troubleshooting

| Problem                       | Solution                                        |
| ----------------------------- | ----------------------------------------------- |
| "Column not found"            | Check column names with `data.columns.tolist()` |
| "Cannot modify original data" | Ensure you're using `.copy()`                   |
| "Aggregation fails"           | Verify group_by columns exist and have no NaN   |
| "Shaper not found in factory" | Check registration in `ShaperFactory._shapers`  |

## References

- Base Class: `src/web/services/shapers/base_shaper.py`
- Factory: `src/web/services/shapers/shaper_factory.py`
- Examples: `src/web/services/shapers/` (all built-in shapers)
- Tests: `tests/unit/test_shapers.py`
- Integration: `tests/integration/test_e2e_managers_shapers.py`

