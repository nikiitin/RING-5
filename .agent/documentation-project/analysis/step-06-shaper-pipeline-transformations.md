# Step 06 — Shaper Pipeline & Data Transformations Analysis

> **Objective**: Document the complete data transformation system — the shaper factory,
> pipeline service, every built-in shaper implementation, validation, and the
> composition mechanics.

---

## Scope

This step provides exhaustive documentation of **how parsed data is transformed** before
plotting. The shaper system is one of the most extensible parts of the application.

---

## Files to Analyze

### Shaper Framework
```
src/core/services/shapers/__init__.py
src/core/services/shapers/shapers_api.py           (API interface)
src/core/services/shapers/shapers_impl.py          (implementation wiring)
src/core/services/shapers/factory.py               (shaper factory)
src/core/services/shapers/pipeline_service.py      (pipeline execution)
src/core/services/shapers/shaper.py                (base shaper class/protocol)
src/core/services/shapers/validation.py            (input validation)
src/core/services/shapers/uni_df_shaper.py         (unified DF shaper)
```

### Shaper Implementations
```
src/core/services/shapers/impl/__init__.py
src/core/services/shapers/impl/mean.py             (mean/average aggregation)
src/core/services/shapers/impl/normalize.py        (normalization)
src/core/services/shapers/impl/pivot.py            (pivot operations)
src/core/services/shapers/impl/selector.py         (row/column selection)
src/core/services/shapers/impl/sort.py             (sorting operations)
src/core/services/shapers/impl/split_apply.py      (split-apply-combine)
src/core/services/shapers/impl/transformer.py      (generic transformations)
```

### Selector Algorithms
```
src/core/services/shapers/impl/selector_algorithms/__init__.py
src/core/services/shapers/impl/selector_algorithms/column_selector.py
src/core/services/shapers/impl/selector_algorithms/condition_selector.py
src/core/services/shapers/impl/selector_algorithms/item_selector.py
```

### Shaper Models
```
src/core/models/shaper_models.py                   (configuration models)
```

### Web-Layer Shaper Config UI
```
src/web/pages/ui/shaper_config.py                  (shaper configuration UI)
src/web/components/shapers/__init__.py
src/web/components/shapers/mean_config.py
src/web/components/shapers/normalize_config.py
src/web/components/shapers/pivot_config.py
src/web/components/shapers/selector_transformer_configs.py
src/web/components/shapers/sort_config.py
src/web/components/shapers/split_apply_config.py
```

---

## Questions to Answer

### Shaper Protocol/Interface:
- [ ] What is the base Shaper class/protocol?
- [ ] What methods must every shaper implement?
- [ ] What is the input type? (always DataFrame?)
- [ ] What is the output type? (always DataFrame?)
- [ ] How does a shaper declare its configuration schema?
- [ ] Is there a standard error handling pattern?

### Factory:
- [ ] How does the factory create shaper instances?
- [ ] What is the registry of available shapers?
- [ ] How are shaper names mapped to implementations?
- [ ] Can new shapers be added at runtime?

### Pipeline:
- [ ] How are shapers composed into a pipeline?
- [ ] What is the execution order?
- [ ] How is the DataFrame passed between shapers?
- [ ] Is there intermediate validation between steps?
- [ ] Can the pipeline be inspected/debugged?
- [ ] How are pipeline errors handled?
- [ ] Can pipelines be saved and restored? (portfolio integration)

### Validation:
- [ ] What validation occurs before pipeline execution?
- [ ] What does each validator check?
- [ ] How are validation errors reported to the user?

### For Each Built-in Shaper:

#### Mean Shaper
- [ ] What aggregation functions are supported?
- [ ] How does grouping work?
- [ ] What parameters does it accept?
- [ ] What is the output structure?

#### Normalize Shaper
- [ ] What normalization methods are available?
- [ ] How is the reference/baseline selected?
- [ ] What parameters does it accept?

#### Pivot Shaper
- [ ] How does pivot vs. unpivot work?
- [ ] What are index, columns, and values parameters?
- [ ] How are duplicate entries handled?

#### Selector Shaper
- [ ] What selection algorithms are available?
- [ ] How do column, condition, and item selectors differ?
- [ ] What filter expressions are supported?

#### Sort Shaper
- [ ] What sort criteria are supported?
- [ ] How does multi-key sorting work?
- [ ] Ascending vs. descending handling?

#### Split-Apply Shaper
- [ ] What is the split-apply-combine pattern?
- [ ] What apply functions are available?
- [ ] How does grouping work?

#### Transformer Shaper
- [ ] What transformations are available?
- [ ] How are custom transformations defined?

---

## Information to Extract

### Shaper Contract
```
The exact interface/protocol every shaper must implement, with code example.
```

### Pipeline Execution Model
```
Step-by-step documentation of how a pipeline executes, with state at each stage.
```

### Built-in Shaper Catalog

For each shaper:
```
### ShaperName
- **File**: src/core/services/shapers/impl/xxx.py
- **Purpose**: [what transformation it performs]
- **Parameters**:
  | Parameter | Type | Default | Description |
  |-----------|------|---------|-------------|
  | ...       | ...  | ...     | ...         |
- **Input**: [expected DataFrame structure]
- **Output**: [resulting DataFrame structure]
- **Example**: [before/after DataFrame example]
- **Edge Cases**: [known limitations, error conditions]
- **UI Config**: src/web/components/shapers/xxx_config.py
```

---

## Output Template

### 1. Shaper Protocol Documentation
```
[To be filled]
```

### 2. Factory Documentation
```
[To be filled]
```

### 3. Pipeline Service Documentation
```
[To be filled]
```

### 4. Validation Documentation
```
[To be filled]
```

### 5. Built-in Shaper Catalog (one section per shaper)
```
[To be filled]
```

### 6. Selector Algorithms Documentation
```
[To be filled]
```

### 7. Shaper Configuration Models
```
[To be filled]
```

### 8. Extension Guide Draft
```
[To be filled: Step-by-step "how to add a new shaper"]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `data-pipeline/shaper-architecture.md`, `data-pipeline/shaper-implementations.md`, `data-pipeline/adding-a-new-shaper.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `development/adding-a-shaper.md`
- `USER_GUIDE_PLAN.md` → `data-transformations/shaper-user-guide.md`
- Step 18 (data flow) — shapers are the transformation step
- Step 19 (extension points) — shaper factory is a key extension point
