# Step 21 — Playwright Infrastructure & State Snapshot Strategy Analysis

> **Objective**: Deep audit of the current Playwright infrastructure, fixture architecture,
> and — critically — design a state snapshot/restore strategy that allows efficient E2E
> testing of the massive combinatorial space without repeating expensive setup steps.

---

## Scope

The application has a **massive combinatorial testing surface**:
- 9 plot types × 11 settings panels × 2 engines = **198 basic settings combos**
- 6 shapers × multiple configs = **dozens of pipeline variations**
- 13 export presets × 2 engines = **26 export combos**
- 5 data managers × multiple operations each
- 3 data source modes

Parsing real data takes **3+ minutes**. Without a state snapshot strategy, E2E testing
this surface is infeasible. This step designs the infrastructure to make it tractable.

---

## Files to Analyze

### Current Infrastructure
```
tests/visual/conftest.py                            (264 lines — all current fixtures)
tests/visual/pages/base_page.py                     (161 lines — base POM)
tests/visual/pages/data_source_page.py              (881 lines)
tests/visual/pages/data_managers_page.py            (454 lines)
tests/visual/pages/manage_plots_page.py             (870 lines)
tests/visual/pages/portfolio_page.py                (68 lines)
```

### State Management (for snapshot understanding)
```
src/core/state/state_manager.py
src/core/state/repository_state_manager.py
src/core/state/repositories/*.py                    (all 9 repositories)
src/web/state/ui_state_manager.py
app.py                                              (session initialization)
```

### Streamlit Session State
```
# Need to understand: what session_state keys exist after parsing?
# What can be serialized? What can be restored?
```

### Existing Knowledge Base
```
.agent/knowledge_for_e2e_testing/01-streamlit-playwright-patterns.md
.agent/knowledge_for_e2e_testing/02-test-consolidation-map.md
.agent/knowledge_for_e2e_testing/03-manage-plots-reference.md
.agent/knowledge_for_e2e_testing/05-comprehensive-master-plan.md
.agent/knowledge_for_e2e_testing/06-pom-test-inventory.md
.agent/rules/008-playwright-visual-testing.md
.agent/workflows/playwright-visual-testing.md
```

---

## Questions to Answer

### Current Fixture Architecture:
- [ ] What fixtures exist at each scope? (session, class, function)
- [ ] How is the Streamlit server managed? (lifecycle, port allocation)
- [ ] How is the browser context managed? (shared vs. isolated)
- [ ] What is the shared_page pattern? How reliable is it?
- [ ] What failure artifact capture exists? (screenshots, traces)
- [ ] What environment variables control test behavior?

### State Snapshot Strategy (CRITICAL):
- [ ] Can Streamlit session_state be serialized and restored via the browser?
- [ ] Can we use Portfolio save/load as a snapshot mechanism?
- [ ] Can we parse data once (session fixture), save a portfolio, and load it per test class?
- [ ] Can we inject session_state via JavaScript in Playwright?
- [ ] Can we use `localStorage` or `sessionStorage` for state transfer?
- [ ] Can we use Playwright's `storageState` to capture and restore browser state?
- [ ] What is the cost of parsing data via E2E? (wall-clock time)
- [ ] What is the cost of loading a portfolio via E2E? (wall-clock time)
- [ ] Can multiple test files share a parsed-data state?

### Snapshot Tiers (design these):
```
Tier 0: App launched, no data loaded
  → Used by: navigation tests, empty state tests

Tier 1: Data parsed and available (post-scan + parse)
  → Used by: data manager tests, plot creation tests
  → EXPENSIVE to create (~3 min with real data)
  → Must be created ONCE and shared across many test classes

Tier 2: Tier 1 + specific plot created and configured
  → Used by: settings tests, engine toggle tests
  → One snapshot per plot type (9 snapshots)

Tier 3: Tier 2 + shaper pipeline configured
  → Used by: shaper-specific tests, data transformation tests

Tier 4: Tier 2 + export preset applied
  → Used by: export/download tests
```

### POM Completeness:
- [ ] For each POM, what properties and methods exist?
- [ ] For each POM, what is MISSING for full coverage?
- [ ] What new POM classes are needed?
- [ ] What helper methods are shared via BasePage?
- [ ] How does the GIF creation work? (BasePage.create_gif)

### Existing Media Inventory:
- [ ] Every screenshot in docs/webapp/images/ (file, what it shows, resolution, still accurate?)
- [ ] Every screenshot in tests/visual/screenshots/ (per-test vs shared)
- [ ] The existing navigation_workflow.gif — how was it created?
- [ ] Tests in test_ds_screenshots.py — what media do they produce?

---

## Information to Extract

### Fixture Architecture Map
```
session scope:
  _streamlit_port → live_server_url → browser_context_args → browser_type_launch_args

class scope:
  shared_page → shared_screenshot_dir

function scope:
  screenshot_dir → _capture_failure_artifacts (autouse)
```

### State Snapshot Design
```
[To be designed: How to create, save, and restore state snapshots at each tier]
```

### POM Gap Analysis
```
For each POM:
  | Property/Method | Exists? | Needed For |
  |-----------------|---------|------------|
  | ...             | ...     | ...        |
```

---

## Output Template

### 1. Current Fixture Architecture (complete documentation)
```
[To be filled]
```

### 2. State Snapshot Strategy (detailed design)
```
[To be filled]
```

### 3. POM Gap Analysis (per POM)
```
[To be filled]
```

### 4. Existing Media Inventory
```
[To be filled]
```

### 5. GIF Generation Capability Assessment
```
[To be filled]
```

### 6. Test Execution Metrics (run times, reliability)
```
[To be filled]
```

---

## Downstream Dependencies

This step feeds into ALL subsequent E2E steps (22-30).
The state snapshot strategy designed here determines how efficiently all subsequent tests run.
