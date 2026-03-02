# Step 27 — E2E Tests: Shaper Pipeline (6 Shapers × Pipeline Combinations)

> **Objective**: Design E2E tests for the Shaper Pipeline editor — adding, configuring,
> reordering, and removing shapers — and verifying their effect on plot data.
> Uses Tier 2 state snapshots.

---

## Scope

### Combinatorial Surface
```
6 shapers × multiple configurations each:

1. Column Selector / Item Selector / Condition Selector
   - Select/deselect columns
   - Filter by condition
   - Select specific items

2. Sort
   - Sort column selection
   - Ascending/descending
   - Multi-key sort

3. Mean (Aggregation)
   - Group-by column selection
   - Aggregation function (mean, median, sum, etc.)
   - Result columns

4. Normalize
   - Normalization method (min-max, z-score, baseline, etc.)
   - Reference/baseline column selection
   - Target columns

5. Pivot
   - Index columns
   - Pivot column
   - Value column
   - Aggregation function

6. Split-Apply
   - Split column
   - Apply function
   - Combine strategy

Pipeline combinations:
  - Single shaper
  - Multi-step pipeline (e.g., Select → Sort → Mean)
  - Reorder steps
  - Remove mid-pipeline step
  - Common recipes: Select + Mean + Sort (for bar charts)
```

---

## Files to Analyze
```
src/web/pages/ui/shaper_config.py
src/web/components/shapers/selector_transformer_configs.py
src/web/components/shapers/sort_config.py
src/web/components/shapers/mean_config.py
src/web/components/shapers/normalize_config.py
src/web/components/shapers/pivot_config.py
src/web/components/shapers/split_apply_config.py
src/web/components/common/pipeline.py
src/web/components/common/pipeline_step.py

tests/visual/pages/manage_plots_page.py              (pipeline section)
```

---

## Tests to Design

### Individual Shaper Tests (using Tier 2 bar snapshot)
For each of the 6 shapers:
- [ ] Add shaper to pipeline → verify step appears
- [ ] Configure shaper → verify options
- [ ] Verify data transformation (chart changes)
- [ ] Remove shaper → verify pipeline updates

### Pipeline Composition Tests
- [ ] Add two shapers → verify order
- [ ] Reorder shapers (drag or move) → verify new order
- [ ] Three-step pipeline: Select → Mean → Sort → verify result
- [ ] Remove middle step → verify pipeline adjusts
- [ ] Empty pipeline state → verify no transformation

### Common Recipe Tests (practical workflows)
- [ ] Bar chart recipe: Select columns + Mean by config + Sort descending
- [ ] Line chart recipe: Select columns + Normalize to baseline
- [ ] Scatter recipe: Select columns + Filter by condition
- [ ] Grouped bar recipe: Select + split by group

### Documentation Media
```
Screenshots:
  shaper-pipeline-overview.png (pipeline editor with steps)
  shaper-add-step.png (shaper selection dropdown)

GIFs:
  shaper-add-step.gif (add a new step to pipeline)
  shaper-configure-step.gif (configure a shaper step)
```

### POM Additions Needed
- [ ] Pipeline step locators (add, remove, reorder)
- [ ] Shaper type selection dropdown locator
- [ ] Per-shaper configuration widget locators
- [ ] Pipeline step count assertion
- [ ] Step reordering interaction
- [ ] Data preview/result verification

---

## Output Template

### 1. Per-Shaper Test Specifications
```
[To be filled]
```

### 2. Pipeline Composition Tests
```
[To be filled]
```

### 3. Recipe Tests
```
[To be filled]
```

### 4. POM Additions
```
[To be filled]
```

### 5. Media Asset Manifest
```
[To be filled]
```

---

## Downstream Dependencies

- Uses Tier 2 snapshots from Step 25
- May produce Tier 3 snapshots (data with pipeline applied)
- Media feeds into USER_GUIDE_PLAN → manage-plots.md (pipeline section)
