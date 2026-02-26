# Playwright Visual Testing Workflow

> **Invoke with**: `/playwright-visual-testing`
> **Purpose**: Guide creation and maintenance of browser-based visual tests
> **Applies to**: All Playwright/browser tests in `tests/visual/`

## Overview

This workflow guides the creation of Playwright visual tests for the Streamlit UI.
Visual tests verify **rendering correctness** and capture **screenshots/GIFs for documentation**.

**Source**: _"Web Automation Testing Using Playwright"_ — Kailash Pathak (BPB, 2025)

## Prerequisites

```bash
# Verify Playwright installation
./python_venv/bin/python -m playwright --version

# Verify Chromium is installed
ls ~/.cache/ms-playwright/chromium-*

# Verify pytest-playwright is available
./python_venv/bin/python -c "import pytest_playwright; print('OK')"
```

## Step-by-Step Process

### 1. Identify Test Target (Rule 008, §1)

Determine which **Layer 4** test to write:

- **Page rendering**: Does the page load without errors?
- **Navigation flow**: Do sidebar buttons switch pages correctly?
- **Visual capture**: Need screenshots for documentation?
- **Workflow GIF**: Need animated walkthrough of multi-step process?
- **File operations**: Upload/download working via browser?

> **Guard**: If the test verifies _logic_ (not rendering), use Layers 1-3 instead.

### 2. Create/Update Page Object (Rule 008, §3 + Ch. 7)

Before writing tests, ensure the target page has a Page Object:

```python
# tests/visual/pages/data_source_page.py
from playwright.sync_api import Locator, Page


class DataSourcePage:
    """Page Object for Data Source page."""

    def __init__(self, page: Page) -> None:
        self.page = page

    # --- Locators (properties, never methods) ---
    @property
    def header(self) -> Locator:
        return self.page.get_by_role("heading", name="Data Source")

    @property
    def parse_tab(self) -> Locator:
        return self.page.get_by_text("Parse gem5")

    # --- Actions (methods) ---
    def navigate(self) -> None:
        sidebar = self.page.locator("[data-testid='stSidebar']")
        sidebar.get_by_role("button", name="Data Source").click()
        self.page.wait_for_load_state("networkidle")
```

**Checklist**:

- [ ] Locators use `get_by_role()` / `get_by_text()` priority (§3.3)
- [ ] No assertions in Page Object (§3.2)
- [ ] Constructor accepts `page: Page`
- [ ] All methods have type annotations

### 3. Write the Test (Rule 008, §9)

```python
# tests/visual/test_data_source.py
import pytest
from playwright.sync_api import Page, expect

from tests.visual.pages.data_source_page import DataSourcePage

pytestmark = pytest.mark.requires_browser


def test_data_source_renders_header(page: Page, live_server_url: str) -> None:
    """Data Source page shows header after navigation."""
    page.goto(live_server_url)
    ds = DataSourcePage(page)
    ds.navigate()
    expect(ds.header).to_be_visible()
```

**Naming**: `test_{page}_{feature}_{scenario}`

### 4. Add Screenshot Capture (Rule 008, §7 + Ch. 11)

```python
def test_data_source_initial_state(
    page: Page, live_server_url: str, screenshot_dir: Path
) -> None:
    page.goto(live_server_url)
    ds = DataSourcePage(page)
    ds.navigate()
    expect(ds.header).to_be_visible()

    # Capture for documentation
    page.screenshot(
        path=str(screenshot_dir / "data_source_initial.png"),
        full_page=True,
    )
```

### 5. Handle Complex Elements (Rule 008, §4 + Ch. 4)

For file uploads:

```python
def test_csv_upload(page: Page, live_server_url: str) -> None:
    page.goto(live_server_url)
    ds = DataSourcePage(page)
    ds.navigate()
    ds.select_upload_mode()

    # Upload file via hidden input
    file_input = page.locator("input[type='file']")
    file_input.set_input_files("tests/data/sample.csv")

    # Verify upload succeeded
    expect(page.get_by_text("Rows")).to_be_visible()
```

For file downloads:

```python
def test_csv_download(page: Page, live_server_url: str, tmp_path: Path) -> None:
    # ... load data first ...
    with page.expect_download() as download_info:
        page.get_by_role("button", name="Download").click()
    download = download_info.value
    download.save_as(tmp_path / download.suggested_filename)
    assert (tmp_path / download.suggested_filename).exists()
```

### 6. Generate Documentation GIF (Rule 008, §7.2)

```python
def test_workflow_gif(
    page: Page, live_server_url: str, screenshot_dir: Path
) -> None:
    import imageio.v3 as iio

    page.goto(live_server_url)
    frames = []

    # Step 1: Landing page
    page.screenshot(path=str(screenshot_dir / "step_1.png"))
    frames.append(iio.imread(str(screenshot_dir / "step_1.png")))

    # Step 2: Navigate to page
    ds = DataSourcePage(page)
    ds.navigate()
    page.screenshot(path=str(screenshot_dir / "step_2.png"))
    frames.append(iio.imread(str(screenshot_dir / "step_2.png")))

    # Combine into GIF
    iio.imwrite(
        str(screenshot_dir / "workflow.gif"),
        frames,
        duration=1500,
        loop=0,
    )
```

### 7. Debug Failures (Rule 008, §5 + Ch. 5)

If a test fails:

1. **Check trace** (if enabled):

   ```bash
   python -m playwright show-trace tests/visual/artifacts/trace-*.zip
   ```

2. **Run with inspector**:

   ```bash
   PWDEBUG=1 ./python_venv/bin/pytest tests/visual/test_data_source.py -x --no-cov -p no:xdist
   ```

3. **Use Codegen** to find correct selectors:
   ```bash
   # Start Streamlit first, then:
   python -m playwright codegen http://localhost:8501
   ```

### 8. Run Visual Tests

```bash
# Run all visual tests (no xdist, no coverage)
./python_venv/bin/pytest tests/visual/ -m requires_browser --no-cov -p no:xdist -v

# Run specific test
./python_venv/bin/pytest tests/visual/test_data_source.py -m requires_browser --no-cov -p no:xdist -v

# Run headed (see browser)
HEADED=1 ./python_venv/bin/pytest tests/visual/ -m requires_browser --no-cov -p no:xdist -v

# Run with tracing
TRACING=1 ./python_venv/bin/pytest tests/visual/ -m requires_browser --no-cov -p no:xdist -v
```

## Quality Checklist

Before declaring visual tests complete:

- [ ] All tests use `pytestmark = pytest.mark.requires_browser`
- [ ] All locators go through Page Objects (no raw selectors in tests)
- [ ] `expect()` auto-retrying assertions used (no `assert loc.is_visible()`)
- [ ] No `page.wait_for_timeout()` calls
- [ ] Screenshots saved to `tests/visual/screenshots/` (gitignored)
- [ ] Type annotations on all functions
- [ ] Tests pass: `pytest tests/visual/ -m requires_browser --no-cov -p no:xdist`
- [ ] `flake8 tests/visual/` clean
- [ ] `black --check tests/visual/` clean

## Common Patterns

### Wait for Streamlit to Finish Rendering

Use `BasePage.wait_for_streamlit()` — waits for `networkidle` + status widget hidden:

```python
# Via BasePage (preferred):
ds = DataSourcePage(page)
ds.wait_for_streamlit()

# Or wait for specific result after an action:
expect(page.get_by_text("Expected content")).to_be_visible(timeout=10000)
```

### Navigate Between Pages

```python
# Via BasePage (preferred):
base = BasePage(page)
base.navigate_to("Data Managers")

# Or use page-specific navigate():
dm = DataManagersPage(page)
dm.navigate()
```

### Handle Streamlit Tabs

```python
page.get_by_role("tab", name="Summary").click()
expect(page.get_by_text("Dataset Overview")).to_be_visible()
```

### Scope Locators Across Tabs (`_by_label` Pattern)

Streamlit renders ALL tab panels in the DOM simultaneously (hidden via CSS).
Generic selectors match elements across all tabs. Use `_by_label()`:

```python
def _by_label(self, test_id: str, label_text: str) -> Locator:
    """Return a widget scoped to its label text (avoids cross-tab matching)."""
    return self.page.locator(f"[data-testid='{test_id}']").filter(has_text=label_text)

# Usage:
selectbox = self._by_label("stSelectbox", "Column to check for outliers")
multiselect = self._by_label("stMultiSelect", "Group by columns")
```

### Segmented Control Toggle Protection

Clicking an already-active segmented option **deselects** it. Always
check activation state first:

```python
def ensure_parse_mode(self) -> None:
    """Only click if not already active — prevents toggle-off."""
    if not self._is_mode_active(self.parse_option):
        self.parse_option.click()
        self.wait_for_streamlit()

def _is_mode_active(self, button: Locator) -> bool:
    testid = button.get_attribute("data-testid") or ""
    return "Active" in testid
```

### Class-Scoped Page for Consolidated Tests

For tests that share state, use a class-scoped page fixture:

```python
@pytest.fixture(scope="class")
def shared_page(
    browser: Browser,
    browser_context_args: dict[str, object],
) -> Generator[Page, None, None]:
    """One browser tab shared across all tests in a class."""
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    yield page
    context.close()

class TestDataSourceRendering:
    """Tests run in definition order, sharing browser state."""

    def test_initial_load(self, shared_page, live_server_url):
        ds = DataSourcePage(shared_page)
        ds.goto_and_wait(live_server_url)
        ds.assert_step_header_visible()
        ds.assert_info_box_visible()
        ds.assert_segmented_control_visible()

    def test_mode_switching(self, shared_page, live_server_url):
        ds = DataSourcePage(shared_page)
        # Page already loaded from previous test
        ds.select_csv_mode()
        ds.assert_csv_mode_message_visible()
```

### Singleton State Handling

`@st.cache_resource` makes `ApplicationAPI` a singleton shared across all
browser sessions. Tests must handle "already exists" gracefully:

```python
def add_manual_variable(self, name: str, var_type: str = "scalar") -> None:
    self.open_add_variable_dialog()
    self.switch_dialog_to_manual()
    self.fill_dialog_manual_name(name)
    self.dialog_add_button.click()
    try:
        expect(self.dialog_overlay).not_to_be_visible(timeout=5_000)
    except (AssertionError, Exception):
        # Variable may already exist from prior session
        warning = self.dialog_overlay.locator("[data-testid='stAlertContentWarning']")
        if warning.count() > 0 and "already exists" in (warning.inner_text() or ""):
            self.close_dialog()
        else:
            raise
```

## Knowledge Base

Detailed reference documentation is maintained in:

```
.agent/knowledge_for_e2e_testing/
├── 01-streamlit-playwright-patterns.md   # DOM selectors, lifecycle, quirks
├── 02-test-consolidation-map.md          # 148→37 test reduction plan
├── 03-manage-plots-reference.md          # All plot widgets & interactions
├── 04-seeds-reducer-refactoring.md       # Generic reducer plan
├── 05-comprehensive-master-plan.md       # Multi-phase implementation plan
└── 06-pom-test-inventory.md              # Current POM & test inventory
```

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Workflow**
