---
title: "Adding a New Shaper"
parent: Development
grand_parent: Engineering Reference
nav_order: 3
---

# Adding a New Shaper

## Overview

- Pattern: Factory + ABC (Template Method)
- Base class: `Shaper` (`src/core/services/shapers/shaper.py`)
- Convenience base: `UniDfShaper` (`src/core/services/shapers/uni_df_shaper.py`)
- Factory: `ShaperFactory` (`src/core/services/shapers/factory.py`)
- Reference implementation: `Sort` (`src/core/services/shapers/impl/sort.py`)

## Abstract Base Class

```python
# src/core/services/shapers/shaper.py

class Shaper(ABC):

    def __init__(self, params: dict[str, Any]) -> None:
        if not isinstance(params, dict):
            raise ValueError("Shaper parameters must be a dictionary.")
        self.params: dict[str, Any] = params
        self._verify_params()

    @abstractmethod
    def _verify_params(self) -> bool:
        """Validate initialization parameters. Called in __init__."""
        if self.params is None:
            raise ValueError("Shaper: parameters cannot be None.")
        return True

    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Validate DataFrame before transformation. Override to add checks."""
        if data_frame is None:
            raise ValueError("Shaper: Input dataframe cannot be None.")
        if data_frame.empty:
            raise ValueError("Shaper: Cannot operate on an empty dataframe.")
        return True

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Execute transformation. Override to implement logic."""
        self._verify_preconditions(data_frame)
        return data_frame
```

| Method | Abstract | Purpose |
|--------|----------|---------|
| `_verify_params()` | Yes | Validate config dict at construction time |
| `_verify_preconditions(df)` | No | Validate input DataFrame before transform |
| `__call__(df)` | No | Execute transformation, return new DataFrame |

## UniDfShaper Convenience Base

```python
# src/core/services/shapers/uni_df_shaper.py

class UniDfShaper(Shaper):
    """Adds DataFrame type checking on top of Shaper."""

    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        if data_frame is None:
            raise ValueError("UniDfShaper: Data frame cannot be None.")
        if not isinstance(data_frame, pd.DataFrame):
            raise ValueError(
                f"UniDfShaper: Expected pandas DataFrame, got {type(data_frame).__name__}."
            )
        return super().__call__(data_frame)
```

- Use `UniDfShaper` for single-DataFrame operations (most cases).
- Use `Shaper` directly for multi-DataFrame or non-standard operations.

## Steps

### 1. Create the shaper implementation

```python
# src/core/services/shapers/impl/threshold_filter.py

from typing import Any, cast, override

import pandas as pd

from src.core.services.shapers.uni_df_shaper import UniDfShaper


class ThresholdFilter(UniDfShaper):
    """Filter rows where a column exceeds a threshold value."""

    def __init__(self, params: dict[str, Any]) -> None:
        self.column: str = params.get("column", "")
        self.threshold: float = params.get("threshold", 0.0)
        self.keep: str = params.get("keep", "above")  # "above" or "below"
        super().__init__(params)

    @override
    def _verify_params(self) -> bool:
        super()._verify_params()
        if "column" not in self.params:
            raise ValueError("ThresholdFilter requires 'column' parameter.")
        if "threshold" not in self.params:
            raise ValueError("ThresholdFilter requires 'threshold' parameter.")
        if not isinstance(self.params["threshold"], (int, float)):
            raise TypeError("ThresholdFilter 'threshold' must be numeric.")
        if self.params.get("keep", "above") not in ("above", "below"):
            raise ValueError("ThresholdFilter 'keep' must be 'above' or 'below'.")
        return True

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        super()._verify_preconditions(data_frame)
        if self.column not in data_frame.columns:
            raise ValueError(
                f"ThresholdFilter: Column '{self.column}' not found in dataframe."
            )
        return True

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        self._verify_preconditions(data_frame)
        result = data_frame.copy()
        if self.keep == "above":
            return result[result[self.column] > self.threshold].reset_index(drop=True)
        return result[result[self.column] <= self.threshold].reset_index(drop=True)
```

### 2. (Optional) Define a TypedDict for typed config access

```python
# src/core/models/shaper_models.py  (add to existing file)

class ThresholdFilterConfig(TypedDict):
    column: str
    threshold: float
    keep: str  # "above" or "below"
```

### 3. Register with ShaperFactory

```python
# src/core/services/shapers/factory.py

# Add import:
from src.core.services.shapers.impl.threshold_filter import ThresholdFilter

# Add to _registry dict:
"thresholdFilter": ThresholdFilter,

# Add to _display_names dict:
"thresholdFilter": "Threshold Filter",
```

Or register at runtime:

```python
from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.impl.threshold_filter import ThresholdFilter

ShaperFactory.register("thresholdFilter", ThresholdFilter)
ShaperFactory._display_names["thresholdFilter"] = "Threshold Filter"
```

### 4. Verify registration

```python
from src.core.services.shapers.factory import ShaperFactory

assert "thresholdFilter" in ShaperFactory.get_available_types()
shaper = ShaperFactory.create_shaper(
    "thresholdFilter",
    {"column": "ipc", "threshold": 1.0, "keep": "above"},
)
```

### 5. Add a UI configuration widget (web layer)

- The shaper pipeline UI calls `configure_shaper` per shaper type.
- Add a branch for the new type to render Streamlit widgets.
- Widgets produce a dict matching the shaper's expected params.

```python
# In the shaper configuration UI component:

if shaper_type == "thresholdFilter":
    column = st.selectbox("Column", options=numeric_cols)
    threshold = st.number_input("Threshold", value=0.0)
    keep = st.selectbox("Keep", options=["above", "below"])
    return {"column": column, "threshold": threshold, "keep": keep}
```

## ShaperFactory API Reference

| Method | Returns |
|--------|---------|
| `ShaperFactory.register(type_id, class)` | None |
| `ShaperFactory.create_shaper(type_id, params)` | `Shaper` instance |
| `ShaperFactory.get_available_types()` | `list[str]` |
| `ShaperFactory.get_display_name_map()` | `dict[str, str]` (display name -> type id) |
| `ShaperFactory.get_display_name(type_id)` | `str` |

## Existing Shaper Types

| Type ID | Class | Purpose |
|---------|-------|---------|
| `mean` | `Mean` | Compute group-wise averages |
| `columnSelector` | `ColumnSelector` | Select/filter columns |
| `conditionSelector` | `ConditionSelector` | Filter rows by conditions |
| `itemSelector` | `ItemSelector` | Select specific categorical items |
| `normalize` | `Normalize` | Normalize values (ratio-to-baseline) |
| `pivotLonger` | `PivotLonger` | Melt wide format to long format |
| `pivotWider` | `PivotWider` | Pivot long format to wide format |
| `sort` | `Sort` | Custom categorical sort ordering |
| `splitApply` | `SplitApply` | Group-wise transformations (per-axis) |
| `transformer` | `Transformer` | General expression-based transforms |

## Implementation Checklist

1. Extract instance fields before `super().__init__()` (constructor calls `_verify_params`)
2. Call `super()._verify_params()` first in `_verify_params`
3. Call `super()._verify_preconditions(data_frame)` first in `_verify_preconditions`
4. Call `self._verify_preconditions(data_frame)` first in `__call__`
5. Return a new DataFrame (never mutate input)
6. Use `@override` decorator on all overridden methods
7. Use `cast()` with TypedDict for typed config access

## Conventions

1. Type IDs: `camelCase` (`conditionSelector`, `thresholdFilter`)
2. Display names: Title Case with spaces (`"Threshold Filter"`)
3. Shapers are stateful (params set at construction), not cached by factory
4. Layer rule: shapers live in `src/core/`, must NOT import from `src/web/`
5. All shapers are callable: `result_df = shaper(input_df)`
