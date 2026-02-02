# Shaper API

Complete API reference for RING-5's data transformation system.

## Overview

Shapers transform DataFrames in the analysis pipeline. All shapers:
- Follow the Strategy Pattern
- Are immutable (return new DataFrames)
- Are chainable in pipelines
- Use callable interface (`__call__`)

## ShaperFactory

### Class: `ShaperFactory`

Factory for creating shaper instances.

**Location**: `src/web/services/shapers/shaper_factory.py`

#### Methods

##### `create_shaper(shaper_type, config)`

Create shaper instance by type.

**Parameters**:
- `shaper_type` (str): Shaper type identifier
- `config` (Dict[str, Any]): Configuration dictionary

**Returns**: Shaper instance (callable)

**Raises**: `ValueError` - If shaper type unknown

**Supported Shaper Types**:
- `"column_selector"` - Select/rename columns
- `"sort"` - Sort rows
- `"mean_calculator"` - Calculate means by group
- `"normalize"` - Normalize values
- `"filter"` - Filter rows
- `"transformer"` - Apply custom transformations

**Example**:
```python
from src.web.services.shapers.shaper_factory import ShaperFactory
import pandas as pd

# Create shaper
config = {"columns": ["benchmark", "ipc"], "rename": {"ipc": "Instructions Per Cycle"}}
shaper = ShaperFactory.create_shaper("column_selector", config)

# Apply to data
data = pd.read_csv("data.csv")
result = shaper(data)  # Callable interface
```

## Built-in Shapers

### ColumnSelector

Select and optionally rename columns.

**Configuration**:
```python
{
    "columns": List[str],              # Columns to keep
    "rename": Dict[str, str],          # Optional: old_name → new_name
}
```

**Example**:
```python
config = {
    "columns": ["benchmark", "ipc", "cache_misses"],
    "rename": {"ipc": "IPC", "cache_misses": "Cache Misses"}
}
shaper = ShaperFactory.create_shaper("column_selector", config)
result = shaper(data)
```

**Location**: `src/web/services/shapers/column_selector.py`

### SortShaper

Sort DataFrame by column(s).

**Configuration**:
```python
{
    "column": str | List[str],         # Column(s) to sort by
    "ascending": bool | List[bool],    # Sort direction
}
```

**Example**:
```python
# Single column
config = {"column": "ipc", "ascending": False}
shaper = ShaperFactory.create_shaper("sort", config)

# Multiple columns
config = {
    "column": ["benchmark", "ipc"],
    "ascending": [True, False]
}
```

**Location**: `src/web/services/shapers/sort_shaper.py`

### MeanCalculator

Calculate mean values grouped by dimension(s).

**Configuration**:
```python
{
    "group_by": str | List[str],       # Grouping column(s)
    "value_columns": List[str],        # Columns to average
}
```

**Example**:
```python
config = {
    "group_by": "benchmark",
    "value_columns": ["ipc", "cache_hit_rate"]
}
shaper = ShaperFactory.create_shaper("mean_calculator", config)
result = shaper(data)  # Aggregated data
```

**Location**: `src/web/services/shapers/mean_calculator.py`

### NormalizeShaper

Normalize values to baseline or range.

**Configuration**:
```python
{
    "method": str,                     # "baseline" | "minmax" | "zscore"
    "column": str,                     # Column to normalize
    "baseline_value": float,           # For baseline method
    "baseline_column": str,            # Or baseline from column
}
```

**Methods**:
- `"baseline"`: Divide by baseline value
- `"minmax"`: Scale to [0, 1] range
- `"zscore"`: Standardize to mean=0, std=1

**Example (Baseline)**:
```python
config = {
    "method": "baseline",
    "column": "ipc",
    "baseline_value": 1.0  # Normalize to 1.0
}
shaper = ShaperFactory.create_shaper("normalize", config)
result = shaper(data)
```

**Example (Min-Max)**:
```python
config = {
    "method": "minmax",
    "column": "ipc"
}
shaper = ShaperFactory.create_shaper("normalize", config)
```

**Location**: `src/web/services/shapers/normalize_shaper.py`

### FilterShaper

Filter rows based on conditions.

**Configuration**:
```python
{
    "column": str,                     # Column to filter
    "operator": str,                   # Comparison operator
    "value": Any,                      # Value to compare
}
```

**Supported Operators**:
- `">"`, `">="` - Greater than
- `"<"`, `"<="` - Less than
- `"=="`, `"!="` - Equality
- `"contains"` - String contains (case-insensitive)
- `"in"` - Value in list

**Example (Numeric)**:
```python
config = {
    "column": "ipc",
    "operator": ">",
    "value": 1.5
}
shaper = ShaperFactory.create_shaper("filter", config)
result = shaper(data)  # Only rows where ipc > 1.5
```

**Example (String)**:
```python
config = {
    "column": "benchmark",
    "operator": "in",
    "value": ["mcf", "omnetpp", "xalancbmk"]
}
shaper = ShaperFactory.create_shaper("filter", config)
```

**Location**: `src/web/services/shapers/filter_shaper.py`

### TransformerShaper

Apply custom transformation functions.

**Configuration**:
```python
{
    "transformations": List[Dict],     # List of transformations
}
```

**Transformation Dict**:
```python
{
    "type": str,                       # Transformation type
    "column": str,                     # Target column
    "new_column": str,                 # Output column (optional)
    "params": Dict,                    # Transformation parameters
}
```

**Supported Transformations**:
- `"multiply"`: Multiply by constant
- `"add"`: Add constant
- `"log"`: Logarithm
- `"sqrt"`: Square root
- `"inverse"`: 1/x

**Example**:
```python
config = {
    "transformations": [
        {
            "type": "multiply",
            "column": "cycles",
            "new_column": "cycles_billions",
            "params": {"factor": 1e-9}
        },
        {
            "type": "log",
            "column": "ipc",
            "new_column": "log_ipc",
            "params": {"base": 10}
        }
    ]
}
shaper = ShaperFactory.create_shaper("transformer", config)
```

**Location**: `src/web/services/shapers/transformer_shaper.py`

## Pipeline Execution

### Function: `apply_shaper_pipeline(data, pipeline)`

Apply multiple shapers sequentially.

**Location**: `src/web/services/shapers/pipeline.py`

**Parameters**:
- `data` (pd.DataFrame): Input data
- `pipeline` (List[Dict]): List of shaper configurations

**Returns**: `pd.DataFrame` - Transformed data

**Example**:
```python
from src.web.services.shapers.pipeline import apply_shaper_pipeline

pipeline = [
    {
        "type": "filter",
        "column": "benchmark",
        "operator": "in",
        "value": ["mcf", "omnetpp"]
    },
    {
        "type": "column_selector",
        "columns": ["benchmark", "ipc"],
        "rename": {"ipc": "IPC"}
    },
    {
        "type": "sort",
        "column": "IPC",
        "ascending": False
    }
]

result = apply_shaper_pipeline(data, pipeline)
```

## Creating Custom Shapers

### Template

```python
from typing import Dict, Any
import pandas as pd


class MyCustomShaper:
    """
    Description of transformation.

    Configuration:
        param1 (type): Description
        param2 (type): Description
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self.config = config
        self.param1 = config["param1"]
        self.param2 = config.get("param2", default_value)

    def __call__(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply transformation.

        Args:
            data: Input DataFrame

        Returns:
            Transformed DataFrame (new instance)
        """
        # Validate
        if "required_column" not in data.columns:
            raise KeyError("required_column missing")

        # Transform (immutable)
        result = data.copy()
        # ... apply transformation ...
        return result
```

### Registration

Add to `ShaperFactory._shapers`:

```python
class ShaperFactory:
    _shapers = {
        "column_selector": ColumnSelector,
        "my_custom_shaper": MyCustomShaper,  # Add here
        # ...
    }
```

## Best Practices

1. **Immutability**: Always return new DataFrame, never modify input
2. **Validation**: Check required columns/config before transformation
3. **Type Hints**: Full type annotations on all methods
4. **Error Handling**: Clear, actionable error messages
5. **Documentation**: Docstrings with examples
6. **Testing**: Test basic operation, immutability, errors, edge cases

## Error Handling

### Common Exceptions

**KeyError** (missing column):
```python
try:
    result = shaper(data)
except KeyError as e:
    st.error(f"Required column missing: {e}")
```

**ValueError** (invalid config):
```python
try:
    shaper = ShaperFactory.create_shaper("sort", {})
except ValueError as e:
    st.error(f"Invalid configuration: {e}")
```

## Type Definitions

### ShaperConfig (TypedDict)

```python
from typing import TypedDict, Any, List, Dict

class ShaperConfig(TypedDict, total=False):
    type: str
    # Type-specific fields
    columns: List[str]
    rename: Dict[str, str]
    column: str
    ascending: bool
    group_by: str | List[str]
    value_columns: List[str]
    method: str
    operator: str
    value: Any
```

## Performance

**Memory Usage**:
- Each shaper creates new DataFrame (copy)
- Pipeline of N shapers creates N DataFrames
- Use efficient pandas operations (vectorized)

**Optimization Tips**:
- Filter early in pipeline (reduce data size)
- Select columns before expensive operations
- Use vectorized pandas operations, avoid loops

## Next Steps

- Data Transformations: [../Data-Transformations.md](../Data-Transformations.md)
- Adding Shapers: [../Adding-Shapers.md](../Adding-Shapers.md)
- Pandas Reference: https://pandas.pydata.org/docs/
