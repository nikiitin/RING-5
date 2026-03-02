# Step 23 — E2E Tests: Data Source Page (3 Modes × All Workflows)

> **Objective**: Design comprehensive E2E tests for the Data Source page covering all 3
> modes (Parse, CSV, Recent), all form variants, error scenarios, and documentation media.
> These tests establish the **Tier 1 state snapshot** (parsed data) used by all subsequent steps.

---

## Scope

The Data Source page is the **entry point** for all data in the application. Testing it
thoroughly also produces the parsed-data state that all later tests depend on.

### Combinatorial Surface
```
3 data source modes × scenarios per mode:

Parse Mode:
  - Path configuration (valid, invalid, empty)
  - Scan workflow (pattern discovery → results)
  - Variable selection (search, manual add, remove)
  - Strategy selection (simple vs config-aware)
  - Parse execution (success, failure, timeout)
  - Multi-benchmark directories

CSV Mode:
  - Upload valid CSV
  - Upload invalid CSV
  - Upload large CSV
  - Column detection
  - Data preview

Recent Mode:
  - Pool listing
  - Load from pool
  - Preview from pool
  - Delete from pool
  - Empty pool state
```

---

## Files to Analyze
```
src/web/pages/data_source.py
src/web/components/data_source/data_source_components.py
src/web/components/data_source/pattern_index_selector.py
src/web/components/data_source/variable_editor.py
tests/visual/pages/data_source_page.py              (existing POM — 881 lines)
tests/visual/test_ds_rendering.py
tests/visual/test_ds_parser_config.py
tests/visual/test_ds_csv_recent.py
tests/visual/test_ds_add_variable.py
tests/visual/test_ds_screenshots.py
tests/visual/test_e2e_parse_workflow.py
```

---

## Tests to Design

### Parse Mode Tests (produces Tier 1 snapshot)
- [ ] Land on page → verify parse mode is default
- [ ] Fill paths → verify form state
- [ ] Scan → verify patterns discovered
- [ ] Add variables (search) → verify selection
- [ ] Add variables (manual) → verify dialog
- [ ] Select strategy → verify config-aware options
- [ ] Execute parse → verify data loaded
- [ ] **Save Tier 1 state snapshot after successful parse**
- [ ] Error: empty path → verify error message
- [ ] Error: invalid path → verify error message
- [ ] Error: no variables selected → verify error

### CSV Mode Tests
- [ ] Switch to CSV mode → verify UI change
- [ ] Upload valid CSV → verify data loaded
- [ ] Upload invalid file → verify error
- [ ] Verify column detection
- [ ] Verify data preview

### Recent Mode Tests
- [ ] Switch to Recent mode → verify pool listing
- [ ] Load from pool → verify data loaded
- [ ] Preview entry → verify preview
- [ ] Delete entry → verify removal
- [ ] Empty pool state → verify message

### Documentation Media (from these tests)
```
Screenshots:
  data-source-landing.png
  parse-mode-overview.png
  variable-selection.png
  add-variable-dialog-search.png
  add-variable-dialog-manual.png
  parse-progress.png
  parse-complete.png
  csv-upload-mode.png
  recent-data-mode.png
  strategy-selection.png

GIFs:
  scan-workflow.gif (fill → scan → results)
  data-source-complete-workflow.gif (full parse flow)
```

### POM Additions Needed for DataSourcePage
- [ ] Audit: what methods/properties are missing for the above tests
- [ ] Error message locators
- [ ] CSV upload file input locator
- [ ] Data preview area locator
- [ ] Pool management action locators

---

## State Snapshot Output

After successful parse, save:
- **Browser state** (Playwright storageState)
- **Portfolio snapshot** (if portfolio save can capture parsed state)
- **Session state keys** (document which keys hold the parsed data)

This snapshot becomes the input for Steps 24-30.

---

## Output Template

### 1. Existing Test Coverage Audit
```
[To be filled: What's already tested in the 6 existing test files]
```

### 2. Gap Analysis
```
[To be filled: What scenarios are NOT covered]
```

### 3. New Test Specifications
```
[To be filled: Every new test with name, steps, assertions, media output]
```

### 4. POM Additions
```
[To be filled: New properties and methods for DataSourcePage]
```

### 5. Media Asset Manifest (Data Source section)
```
[To be filled: Every screenshot and GIF with test that produces it]
```

### 6. State Snapshot Specification (Tier 1)
```
[To be filled: How to create, save, and restore the parsed-data state]
```

---

## Downstream Dependencies

- The Tier 1 state snapshot from this step is used by Steps 24-30
- Media assets feed into USER_GUIDE_PLAN → data-source.md
