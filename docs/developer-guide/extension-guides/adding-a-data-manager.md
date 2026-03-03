# Adding a New Data Manager

## Overview

Data managers are UI components that let users transform loaded DataFrames
(reduce seeds, remove outliers, create derived columns, mix datasets, etc.).
Every manager extends the `DataManager` abstract base class defined in
`src/web/components/data_managers/data_manager.py` and follows a three-phase
template method:

1. **Configure** -- the user selects columns, parameters, and options.
2. **Preview** -- a tentative result is computed and shown; the DataFrame is
   stored via `api.set_preview()` but the application state is *not* mutated.
3. **Confirm** -- the user accepts the preview; the application DataFrame is
   replaced via `self.set_data()` and an `OperationRecord` is appended to
   the history.

The base class provides two convenience helpers -- `get_data()` and
`set_data()` -- that delegate to `ApplicationAPI.state_manager`.

---

## Step 1 -- Create the Manager Class

Create a new file under `src/web/components/data_managers/`.
For example, `interpolator.py`:

```python
"""Interpolator Manager"""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.components.common.history_components import HistoryComponents
from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import UIStateManager, WidgetKeyBuilder


class InterpolatorManager(DataManager):
    """Manager for interpolating missing values in numeric columns."""

    @property
    def name(self) -> str:
        return "Interpolator"

    def render(self) -> None:
        ...  # see Step 2
```

The only contract is:

* Extend `DataManager` (which requires `ApplicationAPI` in the constructor).
* Implement the `name` property (used as the tab label).
* Implement the `render()` method (the full UI and logic).

---

## Step 2 -- Implement `name` and `render`

`render()` is where the configure / preview / confirm flow lives.
Use `WidgetKeyBuilder.manager_key(<slug>, <field>)` for every Streamlit
widget key to avoid session-state collisions with other managers.

Key conventions:

* Retrieve the current DataFrame with `self.get_data()`.
* Guard early if there is no data or no suitable columns.
* Store preview results with `self.api.set_preview("<slug>", df)`.
* Show the **Confirm** button only when `self.api.has_preview("<slug>")`.
* On confirmation, call `self.set_data(df)`, clear the preview, record
  history, and call `st.rerun()`.
* Optionally restore form values from history via
  `UIStateManager().manager.consume_load_trigger("<slug>")`.

---

## Step 3 -- Create the Backend Service (if needed)

If your manager requires non-trivial computation, add the logic to a core
service reachable through `ApplicationAPI` rather than putting it directly
inside `render()`.  This keeps the web layer free of domain logic and makes
the computation independently testable.

Typical integration points:

| Need | Where to add |
|---|---|
| Stateless transform (e.g., interpolation) | `src/core/services/managers/managers_api.py` |
| Validation helper | Same service, returning `list[str]` of errors |
| New model / typed dict | `src/core/models/` |

Call the service from `render()` via `self.api.managers.<method>(...)`.

---

## Step 4 -- Register in the Data Managers Page

Open `src/web/pages/data_managers.py` and wire the new manager:

1. **Import** the class at the top of the file:

```python
from src.web.components.data_managers.interpolator import InterpolatorManager
```

2. **Add a tab** to the `st.tabs(...)` call -- append the display name to
   the list and destructure an extra variable:

```python
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
    [
        "Summary",
        "Data Visualization",
        "Seeds Reducer",
        "Outlier Remover",
        "Preprocessor",
        "Mixer",
        "Interpolator",        # <-- new
        "Operations History",
    ]
)
```

3. **Render inside a fragment** (isolates reruns to the tab):

```python
with tab7:
    @st.fragment
    def _interpolator_fragment() -> None:
        InterpolatorManager(api).render()

    _interpolator_fragment()
```

4. Move the history tab to the new last position (`tab8`).

---

## Step 5 -- Add Tests

### Unit test (mock Streamlit)

Create `tests/ui_unit/test_interpolator_logic.py`.  The project convention
is to patch `st` at the module path, supply a `mock_api` fixture from
`tests/conftest.py`, and assert service calls and state transitions:

```python
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.web.components.data_managers.interpolator import InterpolatorManager
from src.web.state.ui_state_manager import WidgetKeyBuilder


@pytest.fixture
def mock_st():
    with patch("src.web.components.data_managers.interpolator.st") as m:
        m.session_state = {}
        yield m


def test_preview_stores_result(mock_st, mock_api):
    data = pd.DataFrame({"x": [1.0, None, 3.0]})
    mock_api.managers.interpolate.return_value = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    manager = InterpolatorManager(mock_api)
    manager.get_data = MagicMock(return_value=data)

    preview_key = WidgetKeyBuilder.manager_key("interpolator", "preview")
    mock_st.button.side_effect = lambda label, key=None, **kw: key == preview_key

    manager.render()

    mock_api.set_preview.assert_called_once()


def test_confirm_updates_data(mock_st, mock_api):
    result = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    mock_api.has_preview.return_value = True
    mock_api.get_preview.return_value = result

    manager = InterpolatorManager(mock_api)
    manager.get_data = MagicMock(return_value=result)

    confirm_key = WidgetKeyBuilder.manager_key("interpolator", "confirm")
    mock_st.button.side_effect = lambda label, key=None, **kw: key == confirm_key

    manager.render()

    mock_api.state_manager.set_data.assert_called_with(result)
    mock_api.clear_preview.assert_called_once_with("interpolation")
```

### Page-level test

In `tests/unit/test_data_managers_page.py`, update the tab count from 7 to
8 and add an assertion that the new manager class is instantiated and
rendered.

---

## Complete Example -- InterpolatorManager Skeleton

```python
"""Interpolator Manager -- fills missing values via interpolation."""

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from src.core.models.history_models import OperationRecord
from src.web.components.common.history_components import HistoryComponents
from src.web.components.data_managers.data_manager import DataManager
from src.web.state.ui_state_manager import UIStateManager, WidgetKeyBuilder

SLUG = "interpolator"


class InterpolatorManager(DataManager):
    @property
    def name(self) -> str:
        return "Interpolator"

    def render(self) -> None:
        st.markdown("### Interpolator")
        data = self.get_data()
        if data is None:
            st.error("No data available. Please load data first.")
            return

        numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
        if not numeric_cols:
            st.warning("No numeric columns available.")
            return

        # -- Configure ---------------------------------------------------
        target: str = str(
            st.selectbox(
                "Column to interpolate",
                options=numeric_cols,
                key=WidgetKeyBuilder.manager_key(SLUG, "col"),
            ) or ""
        )
        method: str = str(
            st.selectbox(
                "Method",
                options=["linear", "nearest", "zero", "quadratic", "cubic"],
                key=WidgetKeyBuilder.manager_key(SLUG, "method"),
            ) or "linear"
        )

        # -- Preview -----------------------------------------------------
        if st.button("Preview", key=WidgetKeyBuilder.manager_key(SLUG, "preview")):
            preview = data.copy()
            preview[target] = preview[target].interpolate(method=method)
            st.dataframe(preview[[target]].head(10))
            self.api.set_preview("interpolation", preview)

        # -- Confirm -----------------------------------------------------
        if self.api.has_preview("interpolation"):
            if st.button(
                "Confirm Interpolation",
                key=WidgetKeyBuilder.manager_key(SLUG, "confirm"),
                type="primary",
            ):
                confirmed = self.api.get_preview("interpolation")
                if confirmed is not None:
                    self.set_data(confirmed)
                    self.api.clear_preview("interpolation")
                    record: OperationRecord = {
                        "source_columns": [target],
                        "dest_columns": [target],
                        "operation": f"Interpolator: {method}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    self.api.add_manager_history_record(record)
                    st.rerun()

        HistoryComponents.render_manager_history(
            self.api.get_manager_history(),
            "Interpolator",
            WidgetKeyBuilder.manager_key(SLUG, "load_trigger"),
            self.api.remove_manager_history_record,
        )
```

---

## Checklist

- [ ] New file created under `src/web/components/data_managers/`.
- [ ] Class extends `DataManager` and implements `name` and `render()`.
- [ ] All widget keys use `WidgetKeyBuilder.manager_key(SLUG, ...)`.
- [ ] Preview stored via `api.set_preview()`, not by mutating app state.
- [ ] Confirm flow calls `self.set_data()`, clears preview, records history, reruns.
- [ ] Backend logic (if any) lives in a core service, not in `render()`.
- [ ] Manager imported and registered in `src/web/pages/data_managers.py`.
- [ ] Tab count in `st.tabs()` updated; history tab repositioned.
- [ ] Unit tests cover preview and confirm paths.
- [ ] Page-level test updated for the new tab count.

---

## See Also

- `src/web/components/data_managers/data_manager.py` -- base class.
- `src/web/components/data_managers/preprocessor.py` -- canonical example.
- `src/web/pages/data_managers.py` -- page registration.
- `src/web/state/ui_state_manager.py` -- `WidgetKeyBuilder` and `UIStateManager`.
- `src/core/models/history_models.py` -- `OperationRecord` TypedDict.
- `src/core/application_api.py` -- preview and history API surface.
- `tests/ui_unit/test_data_manager_logic.py` -- test patterns.
