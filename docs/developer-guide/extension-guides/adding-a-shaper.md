# Adding a New Shaper

## Overview

Shapers are the atomic data-transformation units in RING-5's pipeline system.
Each shaper accepts a pandas `DataFrame`, applies a single well-defined
transformation (filtering, sorting, aggregation, normalization, ...), and returns
a new `DataFrame`. Users chain shapers together in the UI to build reusable
analysis pipelines.

Add a new shaper when you need a reusable DataFrame transformation that does not
already exist among the ten built-in types (`mean`, `normalize`, `sort`,
`columnSelector`, `conditionSelector`, `itemSelector`, `pivotLonger`,
`pivotWider`, `splitApply`, `transformer`).

The process touches four layers of the codebase:

| Layer | What you add | Key file |
|-------|-------------|----------|
| Core models | TypedDict config | `src/core/models/shaper_models.py` |
| Core services | Shaper implementation | `src/core/services/shapers/impl/<name>.py` |
| Core services | Factory + validation registration | `src/core/services/shapers/factory.py`, `validation.py` |
| Web | UI config component | `src/web/components/shapers/<name>_config.py` |
| Web | Orchestrator dispatch | `src/web/pages/ui/shaper_config.py` |

---

## Step 1: Define the Shaper Config Model

Every shaper has a dedicated `TypedDict` in `src/core/models/shaper_models.py`
that declares exactly the fields it requires. This replaces the old flat
mega-union and gives type checkers precise knowledge of each shaper's shape.

Create a new TypedDict that extends `BaseShaperConfig`:

```python
# src/core/models/shaper_models.py

class CumulativeSumShaperConfig(BaseShaperConfig, total=False):
    """Configuration for the Cumulative Sum shaper.

    Attributes:
        columns: Numeric columns to accumulate.
        groupBy: Columns defining independent groups.
        resetOnGroup: Whether to reset the running total at group boundaries.
    """

    columns: Required[list[str]]
    groupBy: Required[list[str]]
    resetOnGroup: bool
```

Then add the new config to the `ShaperStepConfig` union at the bottom of the
file:

```python
ShaperStepConfig = Union[
    MeanShaperConfig,
    # ... existing entries ...
    CumulativeSumShaperConfig,
]
```

**Convention**: field names use `camelCase` to stay consistent with the existing
shaper configs and the JSON pipeline format.

---

## Step 2: Create the Shaper Class

Create a new module under `src/core/services/shapers/impl/`. The class must
extend either `Shaper` (for advanced multi-input transforms) or `UniDfShaper`
(the common case for single-DataFrame transforms).

```python
# src/core/services/shapers/impl/cumulative_sum.py
"""
Cumulative Sum shaper -- running totals within groups.
"""

from typing import Any, cast, override

import pandas as pd

from src.core.models.shaper_models import CumulativeSumShaperConfig
from src.core.services.shapers.uni_df_shaper import UniDfShaper


class CumulativeSum(UniDfShaper):
    """Computes a running total for numeric columns, optionally grouped."""

    def __init__(self, params: dict[str, Any]) -> None:
        config = cast(CumulativeSumShaperConfig, params)
        self.columns: list[str] = config.get("columns", [])
        self.group_by: list[str] = config.get("groupBy", [])
        self.reset_on_group: bool = config.get("resetOnGroup", True)
        super().__init__(params)
```

Extract instance attributes **before** calling `super().__init__()` because the
parent constructor immediately invokes `_verify_params()`, and that method may
need the parsed values.

---

## Step 3: Implement `__call__` and `_verify_params`

Override the three lifecycle hooks defined by the `Shaper` ABC:

```python
    @override
    def _verify_params(self) -> bool:
        """Validate that required configuration fields are present and typed correctly."""
        super()._verify_params()
        config = cast(CumulativeSumShaperConfig, self.params)

        if "columns" not in config or not config["columns"]:
            raise ValueError("CumulativeSum requires a non-empty 'columns' list.")
        if "groupBy" not in config:
            raise ValueError("CumulativeSum requires 'groupBy' parameter.")
        if not all(isinstance(c, str) for c in config["columns"]):
            raise TypeError("CumulativeSum 'columns' entries must be strings.")
        return True

    @override
    def _verify_preconditions(self, data_frame: pd.DataFrame) -> bool:
        """Verify that referenced columns exist in the DataFrame."""
        super()._verify_preconditions(data_frame)
        missing = [c for c in self.columns if c not in data_frame.columns]
        if missing:
            raise ValueError(f"CumulativeSum: columns not found: {missing}")
        missing_groups = [c for c in self.group_by if c not in data_frame.columns]
        if missing_groups:
            raise ValueError(f"CumulativeSum: groupBy columns not found: {missing_groups}")
        return True

    @override
    def __call__(self, data_frame: pd.DataFrame) -> pd.DataFrame:
        """Apply cumulative sum to the specified columns."""
        self._verify_preconditions(data_frame)
        result = data_frame.copy()

        if self.group_by and self.reset_on_group:
            for col in self.columns:
                result[col] = result.groupby(self.group_by)[col].cumsum()
        else:
            for col in self.columns:
                result[col] = result[col].cumsum()

        return result
```

Key rules to follow:

- Always call `self._verify_preconditions(data_frame)` at the start of
  `__call__`.
- Always call `super()._verify_params()` at the start of `_verify_params`.
- Never mutate the input DataFrame; work on `data_frame.copy()`.
- Use the `@override` decorator on every overridden method.

---

## Step 4: Register with ShaperFactory

Three files need a registration entry.

### 4a. Factory registry and display name

In `src/core/services/shapers/factory.py`, add an import and entries in both
dictionaries:

```python
from src.core.services.shapers.impl.cumulative_sum import CumulativeSum

class ShaperFactory:
    _registry: dict[str, type[Shaper]] = {
        # ... existing entries ...
        "cumulativeSum": CumulativeSum,
    }

    _display_names: dict[str, str] = {
        # ... existing entries ...
        "cumulativeSum": "Cumulative Sum",
    }
```

The type identifier (`"cumulativeSum"`) must use `camelCase` -- this is the
project convention for shaper type IDs.

### 4b. Validation required-params

In `src/core/services/shapers/validation.py`, add the required fields for
pre-flight validation:

```python
_REQUIRED_PARAMS: dict[str, list[str]] = {
    # ... existing entries ...
    "cumulativeSum": ["columns", "groupBy"],
}
```

This enables the pipeline executor to show a user-friendly warning when the
configuration is incomplete, instead of raising an exception.

---

## Step 5: Create the UI Config Component

Create a Streamlit component that renders the configuration form for the new
shaper. Follow the pattern established by `SortConfig`:

```python
# src/web/components/shapers/cumulative_sum_config.py
"""UI Configuration for the Cumulative Sum shaper."""

from typing import cast

import pandas as pd
import streamlit as st

from src.core.models.data_models import ShaperStepConfig


class CumulativeSumConfig:
    """UI Component for configuring the CumulativeSum shaper."""

    @staticmethod
    def render(
        data: pd.DataFrame,
        existing_config: ShaperStepConfig,
        key_prefix: str,
        shaper_id: int,
    ) -> ShaperStepConfig:
        numeric_cols = data.select_dtypes(include="number").columns.tolist()
        all_cols = data.columns.tolist()

        prev_columns = cast(list, existing_config.get("columns", []))
        prev_group = cast(list, existing_config.get("groupBy", []))

        columns = st.multiselect(
            "Columns to accumulate",
            options=numeric_cols,
            default=[c for c in prev_columns if c in numeric_cols],
            key=f"{key_prefix}cumsum_cols_{shaper_id}",
        )
        group_by = st.multiselect(
            "Group by",
            options=[c for c in all_cols if c not in columns],
            default=[c for c in prev_group if c in all_cols],
            key=f"{key_prefix}cumsum_group_{shaper_id}",
        )
        reset = st.checkbox(
            "Reset on group boundary",
            value=existing_config.get("resetOnGroup", True),
            key=f"{key_prefix}cumsum_reset_{shaper_id}",
        )

        return {
            "type": "cumulativeSum",
            "columns": columns,
            "groupBy": group_by,
            "resetOnGroup": reset,
        }
```

Then wire it into the orchestrator in `src/web/pages/ui/shaper_config.py`:

1. Import the component at the top of the file.
2. Add a key to `config_dispatch` inside `configure_shaper`:

```python
from src.web.components.shapers.cumulative_sum_config import CumulativeSumConfig

config_dispatch = {
    # ... existing entries ...
    "cumulativeSum": CumulativeSumConfig.render,
}
```

---

## Step 6: Add Tests

### Unit tests for the shaper implementation

Place tests under `tests/unit/`. Cover at minimum: valid execution, parameter
validation errors, precondition errors, and edge cases.

```python
# tests/unit/test_cumulative_sum.py
import pandas as pd
import pytest

from src.core.services.shapers.impl.cumulative_sum import CumulativeSum


class TestCumulativeSum:
    def test_basic_cumsum(self) -> None:
        df = pd.DataFrame({"val": [1, 2, 3], "group": ["a", "a", "a"]})
        shaper = CumulativeSum({"columns": ["val"], "groupBy": ["group"]})
        result = shaper(df)
        assert list(result["val"]) == [1, 3, 6]

    def test_grouped_reset(self) -> None:
        df = pd.DataFrame({
            "val": [1, 2, 10, 20],
            "group": ["a", "a", "b", "b"],
        })
        shaper = CumulativeSum({
            "columns": ["val"],
            "groupBy": ["group"],
            "resetOnGroup": True,
        })
        result = shaper(df)
        assert list(result["val"]) == [1, 3, 10, 30]

    def test_missing_columns_param(self) -> None:
        with pytest.raises(ValueError, match="non-empty 'columns'"):
            CumulativeSum({"columns": [], "groupBy": []})

    def test_missing_column_in_dataframe(self) -> None:
        df = pd.DataFrame({"other": [1, 2]})
        shaper = CumulativeSum({"columns": ["val"], "groupBy": []})
        with pytest.raises(ValueError, match="columns not found"):
            shaper(df)

    def test_does_not_mutate_input(self) -> None:
        df = pd.DataFrame({"val": [1, 2, 3], "group": ["a", "a", "a"]})
        original = df.copy()
        shaper = CumulativeSum({"columns": ["val"], "groupBy": ["group"]})
        shaper(df)
        pd.testing.assert_frame_equal(df, original)
```

### Unit tests for the UI config component

Follow the pattern in `tests/unit/test_sort_config_coverage.py` -- patch
`streamlit` and verify the returned configuration dict:

```python
# tests/unit/test_cumulative_sum_config.py
from unittest.mock import MagicMock, patch
import pandas as pd
from src.web.components.shapers.cumulative_sum_config import CumulativeSumConfig


class TestCumulativeSumConfig:
    @patch("src.web.components.shapers.cumulative_sum_config.st")
    def test_render_returns_expected_keys(self, mock_st: MagicMock) -> None:
        mock_st.multiselect.side_effect = [["val"], ["group"]]
        mock_st.checkbox.return_value = True
        data = pd.DataFrame({"val": [1, 2], "group": ["a", "b"]})

        result = CumulativeSumConfig.render(data, {}, "pfx_", 1)

        assert result["type"] == "cumulativeSum"
        assert result["columns"] == ["val"]
        assert result["groupBy"] == ["group"]
        assert result["resetOnGroup"] is True
```

---

## Complete Example

Below is a consolidated view of every file touched when adding the hypothetical
`cumulativeSum` shaper.

**`src/core/models/shaper_models.py`** -- add the TypedDict and union entry.

**`src/core/services/shapers/impl/cumulative_sum.py`** -- full implementation
(see Steps 2-3 above for the complete class).

**`src/core/services/shapers/factory.py`** -- add import, `_registry` entry,
`_display_names` entry.

**`src/core/services/shapers/validation.py`** -- add `_REQUIRED_PARAMS` entry.

**`src/web/components/shapers/cumulative_sum_config.py`** -- Streamlit config
component (see Step 5).

**`src/web/pages/ui/shaper_config.py`** -- add import and `config_dispatch`
entry.

**`tests/unit/test_cumulative_sum.py`** -- implementation tests.

**`tests/unit/test_cumulative_sum_config.py`** -- UI component tests.

---

## Checklist

Before opening a pull request, verify every item:

- [ ] TypedDict config added to `src/core/models/shaper_models.py` with `Required[]` annotations
- [ ] Config added to the `ShaperStepConfig` union
- [ ] Shaper class extends `UniDfShaper` (or `Shaper` for multi-input)
- [ ] `_verify_params` validates all required fields with clear error messages
- [ ] `_verify_preconditions` checks that referenced columns exist in the DataFrame
- [ ] `__call__` copies the input DataFrame before mutating and returns the copy
- [ ] All overridden methods use the `@override` decorator
- [ ] Factory `_registry` entry uses `camelCase` type ID
- [ ] Factory `_display_names` entry provides a human-readable label
- [ ] `validation.py` `_REQUIRED_PARAMS` entry lists all mandatory fields
- [ ] UI config component follows the `render(data, existing_config, key_prefix, shaper_id)` signature
- [ ] UI config component restores previous values from `existing_config`
- [ ] `shaper_config.py` `config_dispatch` routes to the new component
- [ ] Unit tests cover: happy path, parameter validation errors, precondition errors, immutability
- [ ] UI tests mock Streamlit and verify the returned config dict
- [ ] `mypy` passes with no new errors
- [ ] No Streamlit imports in any `src/core/` file (layer boundary rule)

---

## See Also

- [Shaper ABC source](../../../src/core/services/shapers/shaper.py) -- base class and lifecycle hooks
- [UniDfShaper source](../../../src/core/services/shapers/uni_df_shaper.py) -- single-DataFrame convenience base
- [ShaperFactory source](../../../src/core/services/shapers/factory.py) -- factory registry and creation
- [Shaper models source](../../../src/core/models/shaper_models.py) -- TypedDict configs and union type
- [Validation source](../../../src/core/services/shapers/validation.py) -- pre-flight config validation
- [Sort shaper source](../../../src/core/services/shapers/impl/sort.py) -- reference implementation
- [Sort UI config source](../../../src/web/components/shapers/sort_config.py) -- reference UI component
- [Shaper config orchestrator](../../../src/web/pages/ui/shaper_config.py) -- dispatch and pipeline execution
