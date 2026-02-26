---
description: Playwright visual/browser testing rules and best practices.
globs: tests/visual/**/*.py
---

# 008-playwright-visual-testing.md

## 1. Purpose & Scope

Playwright-based browser tests form **Layer 4** of our testing pyramid — real browser
interaction tests that verify the **visual rendering** and **end-to-end UI behavior** of
the Streamlit application. They complement (never replace) our existing 3-layer approach:

| Layer | Directory           | Tool                | Speed      | Purpose                            |
| ----- | ------------------- | ------------------- | ---------- | ---------------------------------- |
| 1     | `tests/ui_logic/`   | `@patch("...st")`   | ~ms        | Controller delegation logic        |
| 2     | `tests/ui_unit/`    | Mock `st.columns()` | ~ms        | Widget rendering logic             |
| 3     | `tests/ui/`         | `AppTest`           | ~1-3s      | Widget presence & navigation       |
| **4** | **`tests/visual/`** | **Playwright**      | **~5-15s** | **Visual rendering & screenshots** |

## 2. Absolute Prohibitions

1. **NEVER use Playwright for logic testing** — use Layers 1-3 for that.
2. **NEVER hard-code selectors** — always use Page Object locator properties.
3. **NEVER use `page.wait_for_timeout()`** — use auto-waiting locators or `expect()`.
4. **NEVER commit baseline screenshots** to the repo — they are generated locally.
5. **NEVER run Playwright tests in the default `make test`** — use `requires_browser` marker.
6. **NEVER use `page.$()` or `page.$$()` deprecated APIs** — use `page.locator()`.

## 3. Architecture: Page Object Model (POM)

> _Book Reference: Ch. 7 — "Page Object Model Pattern in Playwright"_

### 3.1 Folder Structure

```text
tests/visual/
├── conftest.py              # Fixtures: server, browser, screenshot utils
├── pages/                   # Page Objects (POM)
│   ├── __init__.py
│   ├── base_page.py         # BasePage with shared locators & methods
│   ├── data_source_page.py  # DataSourcePage POM
│   └── data_managers_page.py # DataManagersPage POM
├── test_data_source.py      # Data Source visual tests
├── test_data_managers.py    # Data Managers visual tests
└── screenshots/             # Auto-generated baseline screenshots (gitignored)
```

### 3.2 Page Object Rules

- Each Streamlit page gets **one Page Object class**.
- Page Objects encapsulate **locators** (as properties) and **actions** (as methods).
- Page Objects **NEVER contain assertions** — assertions belong in test functions.
- Page Objects accept `page: Page` in their constructor.
- Use **descriptive method names**: `navigate()`, `upload_csv()`, `select_tab()`.

```python
# ✅ Correct Page Object
class DataSourcePage:
    def __init__(self, page: Page) -> None:
        self.page = page

    @property
    def header(self) -> Locator:
        return self.page.get_by_role("heading", name="Data Source")

    def navigate(self) -> None:
        self.page.get_by_role("button", name="Data Source").click()
        self.page.wait_for_load_state("networkidle")

# ❌ Wrong — assertions in Page Object
class DataSourcePage:
    def verify_header(self) -> None:
        assert self.page.get_by_text("Data Source").is_visible()
```

### 3.3 Locator Strategy Priority

> _Book Reference: Ch. 3 — "Locator Strategies and Handling Various Actions"_

Use locators in this priority order (most resilient → least):

1. **`get_by_role()`** — ARIA roles (button, heading, textbox, tab)
2. **`get_by_text()`** — Visible text content
3. **`get_by_label()`** — Form labels
4. **`get_by_test_id()`** — `data-testid` attributes (if we add them)
5. **`locator("[data-stale]")`** — CSS selectors (last resort for Streamlit internals)

**Streamlit-specific tips:**

- Streamlit renders inside iframes — use `frame_locator("iframe")` when needed.
- Sidebar uses `[data-testid="stSidebar"]` container.
- Tabs use role `tab` — `page.get_by_role("tab", name="Summary")`.
- Buttons use role `button` — `page.get_by_role("button", name="Parse")`.
- Expanders use `[data-testid="stExpander"]`.

## 4. Complex Element Handling

> _Book Reference: Ch. 4 — "Handling Complex Elements"_

### 4.1 File Upload (Streamlit `st.file_uploader`)

Streamlit's file uploader renders an `<input type="file">` inside its component tree.
Use `set_input_files()` to programmatically upload files:

```python
# Single file upload
file_input = page.locator('input[type="file"]')
file_input.set_input_files("tests/data/sample.csv")

# Multiple files
file_input.set_input_files(["tests/data/file1.csv", "tests/data/file2.csv"])

# Clear uploaded files
file_input.set_input_files([])
```

**Streamlit-specific**: The file uploader widget is inside a `[data-testid="stFileUploader"]`
container. The actual `<input>` may be hidden — `set_input_files()` works regardless.

### 4.2 File Download (CSV/Excel/Plot Exports)

Use `expect_download()` to intercept downloads triggered by Streamlit's `st.download_button`:

```python
# Wait for download event + trigger it
with page.expect_download() as download_info:
    page.get_by_role("button", name="Download CSV").click()

download = download_info.value
assert download.suggested_filename.endswith(".csv")

# Save to specific path for verification
download.save_as(tmp_path / download.suggested_filename)
assert (tmp_path / download.suggested_filename).exists()
```

### 4.3 Iframe Handling (Streamlit Components)

Streamlit renders custom components inside iframes. Use `frame_locator()`:

```python
# Access element inside a Streamlit component iframe
iframe = page.frame_locator("iframe[title='streamlit_component']")
iframe.locator("button.custom-btn").click()

# Nested iframes (rare but possible with embedded Plotly)
inner = page.frame_locator("iframe.outer").frame_locator("iframe.inner")
inner.locator("#chart").screenshot(path="chart.png")
```

### 4.4 JavaScript Dialogs (Alerts/Confirms/Prompts)

Handle browser-native dialogs with the `dialog` event:

```python
# Accept alert
page.on("dialog", lambda dialog: dialog.accept())

# Dismiss confirm dialog
page.on("dialog", lambda dialog: dialog.dismiss())

# Enter text in prompt
page.on("dialog", lambda dialog: dialog.accept("user input"))
```

### 4.5 Multi-Tab / Pop-up Handling

When Streamlit actions open new tabs or windows:

```python
# Wait for new tab/popup
with page.context.expect_page() as new_page_info:
    page.get_by_role("link", name="Open in new tab").click()

new_page = new_page_info.value
new_page.wait_for_load_state()
assert "expected-url" in new_page.url
new_page.close()
```

### 4.6 Shadow DOM

Playwright **auto-pierces** shadow DOM by default — no special handling needed:

```python
# This works even if the element is inside shadow DOM
page.locator("input[name='username']").fill("test")
```

### 4.7 Drag and Drop

For reordering UI elements:

```python
source = page.locator("[data-testid='item-1']")
target = page.locator("[data-testid='item-2']")
source.drag_to(target)
```

## 5. Playwright Tooling

> _Book Reference: Ch. 5 — "Exploring Playwright Tools in Depth"_

### 5.1 Codegen — Discover Selectors

Use Codegen to interactively discover Streamlit element selectors:

```bash
# Record interactions against our running Streamlit app
python -m playwright codegen http://localhost:8501

# Record for specific viewport (mobile)
python -m playwright codegen --viewport-size "375,812" http://localhost:8501

# Record with specific browser
python -m playwright codegen -b chromium http://localhost:8501
```

**Workflow**: Start Streamlit → run Codegen → interact with UI → copy selectors into POM.

### 5.2 Trace Viewer — Debug Failures

Enable tracing to capture detailed execution timeline:

```python
# In conftest.py — capture trace on failure
context.tracing.start(screenshots=True, snapshots=True, sources=True)
yield page
context.tracing.stop(path=f"tests/visual/artifacts/trace-{test_name}.zip")
```

View traces locally:

```bash
python -m playwright show-trace tests/visual/artifacts/trace-failed-test.zip
```

**Trace contains**: Screenshots at every action, DOM snapshots, network requests, console logs.

### 5.3 Playwright Inspector — Interactive Debugging

Debug individual tests with the inspector:

```bash
# Debug all visual tests
PWDEBUG=1 pytest tests/visual/ -m requires_browser -x

# Debug specific test
PWDEBUG=1 pytest tests/visual/test_data_source.py::test_data_source_renders -x
```

The inspector provides:

- Step-through execution
- Live locator editing
- Actionability logs (visible, enabled, stable)
- DOM element highlighting

### 5.4 Pick Locator

Use the locator picker to find the most resilient selector:

```bash
# Open locator picker against running app
python -m playwright codegen --target python-pytest http://localhost:8501
```

Hover over elements to see Playwright's recommended locator strategy.

## 6. Assertions

> _Book Reference: Ch. 6 — "Reporter, Assertion, Annotations, and Hooks"_

### 6.1 Auto-Retrying Assertions (Preferred)

Always prefer Playwright's auto-retrying `expect()` assertions over manual checks:

```python
# ✅ Auto-retrying — waits up to timeout
expect(page.get_by_role("heading", name="Data Source")).to_be_visible()

# ❌ Manual check — races with rendering
assert page.get_by_text("Data Source").is_visible()
```

### 6.2 Key Assertions

| Assertion                      | Use Case                    |
| ------------------------------ | --------------------------- |
| `expect(loc).to_be_visible()`  | Element rendered on screen  |
| `expect(loc).to_have_text()`   | Text content matches        |
| `expect(loc).to_have_count()`  | Number of matching elements |
| `expect(loc).to_be_enabled()`  | Button/input is interactive |
| `expect(loc).to_be_hidden()`   | Element not shown           |
| `expect(page).to_have_title()` | Page title check            |

### 6.3 Soft Assertions

Use `expect(loc).to_be_visible(timeout=...)` with shorter timeouts for non-critical checks.
Reserve hard assertions for critical UI elements.

## 7. Visual Testing & Screenshots

> _Book Reference: Ch. 11 — "Visual Testing with Playwright"_

### 7.1 Screenshot Capture

```python
# Full page screenshot
page.screenshot(path="screenshots/data_source_full.png", full_page=True)

# Element screenshot
page.locator("[data-testid='stSidebar']").screenshot(path="screenshots/sidebar.png")

# Screenshot with masking (hide dynamic content)
page.screenshot(
    path="screenshots/stable.png",
    mask=[page.locator(".stMetric")]  # Mask dynamic metrics
)
```

### 7.2 GIF Generation for Documentation

Use `imageio` to combine sequential screenshots into animated GIFs:

```python
import imageio.v3 as iio

frames = []
for step in workflow_steps:
    step.execute()
    frames.append(iio.imread(f"screenshots/step_{step.name}.png"))

iio.imwrite("docs/workflow.gif", frames, duration=1500, loop=0)
```

### 7.3 Screenshot Naming Convention

```
{page_name}_{scenario}_{step}.png
```

Examples: `data_source_initial_load.png`, `data_managers_summary_tab.png`

## 8. Fixtures & Hooks

> _Book Reference: Ch. 6 — "Hooks in Playwright"_

### 8.1 Core Fixtures

```python
@pytest.fixture(scope="session")
def browser():
    """Session-scoped browser — shared across all tests."""

@pytest.fixture(scope="function")
def page(browser):
    """Function-scoped page — fresh context per test."""

@pytest.fixture(scope="session")
def streamlit_server():
    """Start Streamlit server, yield base_url, teardown on session end."""
```

### 8.2 Fixture Rules

- **`session` scope**: Browser instance, Streamlit server (expensive resources).
- **`function` scope**: Page/context (test isolation).
- Always use `yield` fixtures for cleanup guarantees.
- Server fixture must wait for `/healthz` or HTML response before yielding.

## 9. Test Organization

### 9.1 Test Naming

```python
def test_{page}_{feature}_{scenario}():
    """Tests follow: test_<page>_<what>_<condition>"""

# Examples:
def test_data_source_renders_three_mode_tabs(): ...
def test_data_source_csv_upload_shows_preview(): ...
def test_data_managers_summary_tab_shows_statistics(): ...
```

### 9.2 Markers

All Playwright tests MUST use the `requires_browser` marker:

```python
pytestmark = pytest.mark.requires_browser
```

### 9.3 Test Scope

Playwright tests should verify:

- **Page renders correctly** (no crash, key elements visible)
- **Navigation works** (sidebar buttons switch pages)
- **Visual state** (screenshots for documentation)
- **Multi-step workflows** (GIF capture)

Playwright tests should **NOT** verify:

- Business logic correctness (use unit tests)
- Data transformations (use integration tests)
- Widget callback behavior (use AppTest)

## 10. CI/CD Integration

> _Book Reference: Ch. 12 — "Integrate Playwright Tests with CI/CD"_

### 10.1 Headless Mode

All CI runs use headless Chromium. Local development can use headed mode for debugging:

```bash
# CI (default)
pytest tests/visual/ -m requires_browser

# Local debugging
HEADED=1 pytest tests/visual/ -m requires_browser -x
```

### 10.2 Artifacts on Failure

- Auto-capture screenshot on test failure (via `conftest.py` hook).
- Save traces for debugging: `context.tracing.start()` / `context.tracing.stop()`.
- Store artifacts in `tests/visual/artifacts/` (gitignored).

### 10.3 Parallel Execution

- Playwright tests run **sequentially** (single Streamlit server).
- Use `--dist no` to override xdist when running visual tests.
- Consider separate CI job for visual tests.

## 11. AI-Assisted Test Generation

> _Book Reference: Ch. 13 — "Using AI with Playwright for E2E Testing"_

### 11.1 Guidelines for AI-Generated Tests

- AI-generated Playwright scripts require **human validation** of selectors.
- Always verify locator strategies match actual Streamlit DOM structure.
- AI may generate **inconsistent selectors** — normalize to POM patterns.
- Test dynamic Streamlit elements (st.spinner, st.progress) with proper waits.

### 11.2 Debugging with AI

- Use trace viewer output to diagnose failures.
- Provide full error messages and DOM snapshots for accurate debugging.
- Validate AI-suggested selector corrections against live DOM.

## 12. Anti-Patterns

| Anti-Pattern                                       | Correct Approach                            |
| -------------------------------------------------- | ------------------------------------------- |
| `page.wait_for_timeout(5000)`                      | `expect(locator).to_be_visible()`           |
| `page.$(".class")`                                 | `page.locator(".class")`                    |
| Assertions in Page Objects                         | Assertions in test functions only           |
| `time.sleep()` in tests                            | Playwright auto-waiting                     |
| Testing logic via browser                          | Use unit/integration tests                  |
| Raw CSS selectors everywhere                       | POM with `get_by_role()` / `get_by_text()`  |
| Checking pixel-perfect layout                      | Check element presence + text content       |
| Committing screenshots to git                      | Generate locally, gitignore                 |
| `.first` / `.nth()` without label context          | Use `_by_label(test_id, label)` pattern     |
| Clicking active segmented option                   | Use `ensure_*_mode()` to avoid toggle-off   |
| Function-scoped page for sequential workflow tests | Class-scoped `shared_page` fixture          |
| Ignoring singleton state                           | Handle "already exists" warnings gracefully |

## 13. Test Consolidation Guidelines

### 13.1 When to Consolidate

Consolidate when multiple tests share the same setup:

- Navigate to page + verify N elements → 1 test with N assertions
- Setup + mode1 check, Setup + mode2 check → 1 test cycling modes
- Parse + check DM tab1, Parse + check DM tab2 → 1 test visiting tabs

### 13.2 Class-Scoped Page Fixture

```python
@pytest.fixture(scope="class")
def shared_page(
    browser: Browser,
    browser_context_args: dict[str, object],
) -> Generator[Page, None, None]:
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    yield page
    context.close()
```

### 13.3 Ordered Test Classes

Tests in a class execute top-to-bottom. Each builds on prior state:

```python
class TestWorkflow:
    def test_step_1_navigate(self, shared_page, live_server_url): ...
    def test_step_2_configure(self, shared_page, live_server_url): ...
    def test_step_3_verify(self, shared_page, live_server_url): ...
```

### 13.4 The `_by_label()` Pattern

Always scope Streamlit widgets by their label text to avoid cross-tab matches:

```python
def _by_label(self, test_id: str, label_text: str) -> Locator:
    return self.page.locator(f"[data-testid='{test_id}']").filter(has_text=label_text)
```

## 14. Knowledge Base Reference

Detailed reference documentation for E2E testing is maintained in:

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
**Source:** _"Web Automation Testing Using Playwright"_ — Kailash Pathak (BPB, 2025)
**Acknowledgement:** ✅ **Acknowledged Rule 008**
