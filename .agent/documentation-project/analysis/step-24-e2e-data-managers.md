# Step 24 — E2E Tests: Data Managers (5 Managers × All Configurations)

> **Objective**: Design comprehensive E2E tests for all 5 Data Manager components,
> covering every tab, every configuration option, and their effect on data.
> Uses Tier 1 state snapshot (parsed data from step 23).

---

## Scope

### Combinatorial Surface
```
5 data managers × configurations per manager:

Seeds Reducer:
  - Column selection (any categorical ≤20 unique values)
  - Reduction execution
  - Result verification
  - No valid column scenario

Outlier Remover:
  - Threshold configuration (IQR, Z-score, etc.)
  - Column selection
  - Removal execution
  - Before/after comparison

Preprocessor:
  - Preprocessing options (fill NaN, type conversion, etc.)
  - Application
  - Result verification

Mixer:
  - Mixing configuration
  - Cross-dataset operations
  - Result verification

History:
  - Track changes across operations
  - Undo/revert
```

---

## Files to Analyze
```
src/web/pages/data_managers.py
src/web/components/data_managers/data_manager.py
src/web/components/data_managers/data_manager_components.py
src/web/components/data_managers/seeds_reducer.py
src/web/components/data_managers/outlier_remover.py
src/web/components/data_managers/preprocessor.py
src/web/components/data_managers/mixer.py
tests/visual/pages/data_managers_page.py             (existing POM — 454 lines)
tests/visual/test_data_managers.py
```

---

## Tests to Design

### Tab Navigation Tests
- [ ] Visit with data → verify all tabs visible
- [ ] Visit without data → verify warning message
- [ ] Switch between all 7 tabs → verify content changes
- [ ] Verify tab state preservation on switch

### Seeds Reducer Tests (using Tier 1 snapshot)
- [ ] Open tab → verify column selector visible
- [ ] Select valid column → verify options
- [ ] Execute reduction → verify data size change
- [ ] Verify aggregation is correct

### Outlier Remover Tests (using Tier 1 snapshot)
- [ ] Open tab → verify configuration widgets
- [ ] Configure threshold → verify preview
- [ ] Execute removal → verify outliers removed
- [ ] Edge case: no outliers found

### Preprocessor Tests (using Tier 1 snapshot)
- [ ] Open tab → verify options
- [ ] Apply preprocessing → verify changes
- [ ] Multiple preprocessing steps

### Mixer Tests (using Tier 1 snapshot)
- [ ] Open tab → verify configuration
- [ ] Configure mix → verify preview
- [ ] Execute mix → verify result

### History Tests
- [ ] Perform operations → verify history tracking
- [ ] Navigate history entries

### Documentation Media
```
Screenshots:
  data-managers-landing.png
  data-managers-no-data.png
  seeds-reducer-tab.png
  outlier-remover-tab.png
  preprocessor-tab.png
  mixer-tab.png
  history-tab.png

GIFs:
  seeds-reducer-workflow.gif
  outlier-remover-workflow.gif
  tab-navigation.gif
```

### POM Additions Needed for DataManagersPage
- [ ] Per-tab widget locators (all configuration fields)
- [ ] Result/preview area locators
- [ ] Action button locators per tab
- [ ] History entry locators
- [ ] Before/after data comparison helpers

---

## State Snapshot Output

After data manager operations, optionally save:
- **Tier 1.5 snapshot**: Parsed data with seeds reduced (common for plot tests)

---

## Output Template

### 1. Existing Coverage Audit
```
[To be filled]
```

### 2. New Test Specifications
```
[To be filled]
```

### 3. POM Additions
```
[To be filled]
```

### 4. Media Asset Manifest
```
[To be filled]
```

---

## Downstream Dependencies

- Uses Tier 1 snapshot from Step 23
- Optionally produces Tier 1.5 snapshot for Steps 25-27
- Media feeds into USER_GUIDE_PLAN → data-managers.md
