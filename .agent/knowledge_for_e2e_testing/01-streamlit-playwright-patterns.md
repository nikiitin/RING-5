# Streamlit × Playwright Testing Patterns

> **Purpose**: Battle-tested patterns for testing Streamlit apps with Playwright.
> Derived from real debugging experience on RING-5.

---

## 1. Streamlit DOM Architecture

### 1.1 Key `data-testid` Selectors

| Widget | Selector |
|--------|----------|
| Sidebar | `[data-testid='stSidebar']` |
| Main content | `[data-testid='stMainBlockContainer']` |
| Selectbox | `[data-testid='stSelectbox']` |
| Multiselect | `[data-testid='stMultiSelect']` |
| Text input | `[data-testid='stTextInput']` |
| Button | `[data-testid='stBaseButton-primary']` / `stBaseButton-secondary` |
| Alert (success) | `[data-testid='stAlertContentSuccess']` |
| Alert (error) | `[data-testid='stAlertContentError']` |
| Alert (warning) | `[data-testid='stAlertContentWarning']` |
| Alert (info) | `[data-testid='stAlertContentInfo']` |
| Dialog/modal | `[data-testid='stDialog']` |
| Expander | `[data-testid='stExpander']` |
| Metric | `[data-testid='stMetric']` |
| JSON viewer | `[data-testid='stJson']` |
| Dataframe | `[data-testid='stDataFrame']` |
| File uploader | `[data-testid='stFileUploader']` |
| Progress bar | `[role='progressbar']` |
| Tabs (bar) | `[role='tablist']` |
| Tab (individual) | `[role='tab']` |
| Button group | `[data-testid='stButtonGroup']` |
| Plotly chart | `[data-testid='stPlotlyChart']` |
| Status widget | `[data-testid='stStatusWidget']` |

### 1.2 Segmented Controls (st.segmented_control / st.pills)

Streamlit renders segmented controls as `[data-testid='stButtonGroup']`.
Individual options are `button` elements. The **active** option gets:

```
data-testid="stBaseButton-segmented_controlActive"
```

Inactive options have:

```
data-testid="stBaseButton-segmented_control"
```

**Critical bug**: Clicking an already-active option **deselects** it (toggles OFF).
Always check `_is_mode_active()` before clicking:

```python
def _is_mode_active(self, button: Locator) -> bool:
    testid = button.get_attribute("data-testid") or ""
    return "Active" in testid

def ensure_parse_mode(self) -> None:
    if not self._is_mode_active(self.parse_option):
        self.parse_option.click()
        self.wait_for_streamlit()
```

### 1.3 Tabs

Tabs use `[role='tab']`. Access via `get_by_role("tab", name="Tab Name")`.
Active tab has `aria-selected="true"`.

**Critical**: All tab panels are rendered in the DOM simultaneously — hidden ones
use CSS `display: none`. Generic selectors match elements across ALL tabs.
Use the `_by_label()` pattern:

```python
def _by_label(self, test_id: str, label_text: str) -> Locator:
    """Return a widget scoped to its label text."""
    return self.page.locator(f"[data-testid='{test_id}']").filter(has_text=label_text)
```

### 1.4 Dialogs (st.dialog)

- Container: `[data-testid='stDialog']`
- Close button: `button[aria-label='Close']` inside the dialog
- Close via Escape: `page.keyboard.press("Escape")` then wait for dialog `state="hidden"`
- Dialogs are inside the status widget scope — `st.rerun()` may auto-close them

### 1.5 Forms (st.form)

- Form submit buttons inside `st.form()` do NOT trigger `st.rerun()` on click
- They batch all changes and submit together
- Use `page.get_by_role("button", name="Submit Label")` to find submit buttons

---

## 2. Streamlit Lifecycle & Timing

### 2.1 Script Rerun Cycle

Every widget interaction triggers a **full script rerun**. After rerun:
1. Streamlit shows `[data-testid='stStatusWidget']` ("Running...")
2. Script executes top-to-bottom
3. Status widget disappears
4. DOM is updated

**Wait strategy**:
```python
def wait_for_streamlit(self, *, timeout: int | None = None) -> None:
    effective_timeout = timeout or self.RENDER_TIMEOUT
    self.page.wait_for_load_state("networkidle", timeout=effective_timeout)
    running = self.page.locator("[data-testid='stStatusWidget']")
    running.wait_for(state="hidden", timeout=effective_timeout)
```

### 2.2 Fragment Rendering (`@st.fragment`)

Fragments re-run independently without full page rerun:
- Only the fragment's content updates
- Other parts of the page remain unchanged
- Need extra stabilization after fragment rerender:
  ```python
  self.page.wait_for_timeout(500)  # Allow fragment to settle
  ```

### 2.3 Singleton State (`@st.cache_resource`)

`ApplicationAPI` is a singleton via `@st.cache_resource`. This means:
- ALL browser sessions share the same backend state
- Variables added in one test persist in subsequent tests
- Data loaded in one test is visible in all sessions
- **Consequence**: Tests must handle "already exists" scenarios gracefully

### 2.4 `st.rerun()` After Operations

Many operations call `st.rerun()` which:
- Closes any open dialogs
- Rebuilds the page
- May change which elements are visible

**Pattern**: After triggering a rerun, wait for the expected *result* element,
not the intermediate state:
```python
self.click_quick_scan()
# Don't wait for the status widget — wait for the final result
expect(self.scan_result_message).to_be_visible(timeout=timeout)
```

---

## 3. Locator Strategy Priority

1. **`get_by_role("button", name="...")`** — ARIA roles (most resilient)
2. **`get_by_text("...")`** — Visible text content
3. **`_by_label(test_id, label)`** — Widget filtered by label text (for tabs/duplicates)
4. **`locator("[data-testid='...']").filter(has_text=...)`** — Scoped Streamlit widgets
5. **CSS selectors** — Last resort for Streamlit internals

**Anti-patterns to avoid**:
- `.first` / `.nth(n)` without label context (fragile to DOM order)
- `page.wait_for_timeout()` for synchronization (use `expect()` instead)
- Bare `is_visible()` checks (use `expect().to_be_visible()`)

---

## 4. Common Widget Interaction Patterns

### 4.1 Text Input

```python
# Fill and commit (Tab triggers value change event)
input_locator.fill("value")
input_locator.press("Tab")
wait_for_streamlit()
```

### 4.2 Selectbox

```python
# Open dropdown → select option
selectbox.click()
page.wait_for_timeout(300)  # Dropdown animation
option = page.locator("[data-testid='stSelectboxVirtualDropdown'] li")
option.filter(has_text="Option Name").click()
wait_for_streamlit()
```

### 4.3 Multiselect

```python
multiselect = _by_label("stMultiSelect", "Label Text")
multiselect.click()
page.wait_for_timeout(300)
# Type to filter options
page.keyboard.type("option_name")
page.keyboard.press("Enter")
wait_for_streamlit()
```

### 4.4 File Upload

```python
file_input = page.locator("input[type='file']")
file_input.set_input_files("path/to/file.csv")
wait_for_streamlit()
```

### 4.5 Toggle / Checkbox

```python
# Toggle by clicking the label text
page.get_by_text("Toggle Label").click()
wait_for_streamlit()
```

### 4.6 Download Button

```python
with page.expect_download() as dl_info:
    page.get_by_role("button", name="Download").click()
download = dl_info.value
download.save_as(tmp_path / download.suggested_filename)
```

---

## 5. Test Architecture Patterns

### 5.1 Session-Scoped Server, Function-Scoped Page

Current architecture:
- **Session scope**: Streamlit server (one subprocess for all tests)
- **Function scope**: Browser page (new tab per test)

This ensures test isolation but is expensive for tests that share setup.

### 5.2 Class-Scoped Page for Workflow Tests

For ordered tests that build on each other's state:

```python
@pytest.fixture(scope="class")
def shared_page(browser: Browser, browser_context_args: dict) -> Generator[Page, None, None]:
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    yield page
    context.close()
```

Tests within the class share the same browser context and page,
but **tests must be ordered** (use `pytest-order` or natural sort).

### 5.3 Soft Assertions for Multiple Checks

```python
from playwright.sync_api import expect

# Multiple checks in one test without stopping at first failure
expect(locator1).to_be_visible()
expect(locator2).to_have_text("expected")
expect(locator3).to_be_enabled()
```

### 5.4 Fixture-Based Setup Reuse

Instead of repeating navigation + scan + parse in every test:

```python
@pytest.fixture(scope="class")
def parsed_data_page(shared_page, live_server_url):
    """Navigate, scan, add variables, parse — shared across class."""
    ds = DataSourcePage(shared_page)
    ds.goto_and_wait(live_server_url)
    ds.fill_stats_path("/path/to/data")
    ds.scan_and_wait()
    ds.add_variable_from_scan(0)
    ds.parse_and_wait()
    ds.close_parse_dialog_and_reload()
    return shared_page
```

---

## 6. Debugging Toolkit

### 6.1 Headed Mode

```bash
HEADED=1 pytest tests/visual/test_file.py -x -v
```

### 6.2 Slow Motion

```bash
HEADED=1 SLOW_MO=500 pytest tests/visual/test_file.py -x -v
```

### 6.3 Tracing

```bash
TRACING=1 pytest tests/visual/test_file.py -x -v
# Then view:
python -m playwright show-trace tests/visual/artifacts/trace-*.zip
```

### 6.4 Inspector

```bash
PWDEBUG=1 pytest tests/visual/test_file.py::test_name -x
```

---

## 7. Known Streamlit Quirks

| Quirk | Impact | Workaround |
|-------|--------|------------|
| Toggle deselection | Active segmented option deselects on click | Use `ensure_*_mode()` pattern |
| Tab DOM persistence | All tab panels always in DOM | Use `_by_label()` for scoped locators |
| Singleton state | `@st.cache_resource` shares across sessions | Handle "already exists" gracefully |
| Fragment isolation | `@st.fragment` reruns independently | Extra `wait_for_timeout(500)` after fragment ops |
| Dialog auto-close | `st.rerun()` closes open dialogs | Wait for dialog disappearance, not rerun |
| Close button inside st.status | Button is inside collapsed status widget | Wait for status to complete first |
| Virtual dropdown | Selectbox options use virtual scrolling | Filter with `.filter(has_text=...)` |
| Form batching | `st.form` batches changes, no per-widget rerun | Submit button triggers batch commit |
