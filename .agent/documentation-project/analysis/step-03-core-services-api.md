# Step 03 — Core Services API Analysis

> **Objective**: Document every service class in the core layer — its public API, method
> signatures, parameters, return types, side effects, dependencies, and behavioral contracts.

---

## Scope

This step catalogs the **entire service layer** — the business logic engine of the
application. This is the most critical layer for developers extending the system.

---

## Files to Analyze

### Application Facade
```
src/core/application_api.py                    (main entry point)
src/core/performance.py                        (performance monitoring)
```

### Service APIs (interface definitions)
```
src/core/services/__init__.py
src/core/services/services_api.py
src/core/services/services_impl.py
```

### Configuration Validation
```
src/core/services/config_validation_service.py
```

### Plot Interaction
```
src/core/services/plot_interaction_service.py
```

### Portfolio Migration
```
src/core/services/portfolio_migrator.py
```

### Data Services
```
src/core/services/data_services/__init__.py
src/core/services/data_services/data_services_api.py
src/core/services/data_services/data_services_impl.py
src/core/services/data_services/config_service.py
src/core/services/data_services/csv_pool_service.py
src/core/services/data_services/path_service.py
src/core/services/data_services/pattern_index_service.py
src/core/services/data_services/portfolio_service.py
src/core/services/data_services/variable_service.py
```

### Manager Services (Data Processing)
```
src/core/services/managers/__init__.py
src/core/services/managers/managers_api.py
src/core/services/managers/managers_impl.py
src/core/services/managers/arithmetic_service.py
src/core/services/managers/outlier_service.py
src/core/services/managers/reduction_service.py
```

### Shaper Services (Data Transformation)
```
src/core/services/shapers/__init__.py
src/core/services/shapers/shapers_api.py
src/core/services/shapers/shapers_impl.py
src/core/services/shapers/factory.py
src/core/services/shapers/pipeline_service.py
src/core/services/shapers/shaper.py
src/core/services/shapers/validation.py
src/core/services/shapers/uni_df_shaper.py
```

### Shaper Implementations
```
src/core/services/shapers/impl/__init__.py
src/core/services/shapers/impl/mean.py
src/core/services/shapers/impl/normalize.py
src/core/services/shapers/impl/pivot.py
src/core/services/shapers/impl/selector.py
src/core/services/shapers/impl/sort.py
src/core/services/shapers/impl/split_apply.py
src/core/services/shapers/impl/transformer.py
src/core/services/shapers/impl/selector_algorithms/__init__.py
src/core/services/shapers/impl/selector_algorithms/column_selector.py
src/core/services/shapers/impl/selector_algorithms/condition_selector.py
src/core/services/shapers/impl/selector_algorithms/item_selector.py
```

### Visualization Services
```
src/core/services/visualization/__init__.py
src/core/services/visualization/config_resolver.py
src/core/services/visualization/palette_service.py
src/core/services/visualization/plot_interaction.py
```

### Common Utilities
```
src/core/common/utils.py
```

---

## Questions to Answer

### For the ApplicationAPI Facade:
- [ ] What is every public method?
- [ ] What parameters does each method take?
- [ ] What does each method return?
- [ ] What services does it delegate to?
- [ ] What is the initialization flow?
- [ ] How does it manage service lifecycles?
- [ ] What is the dependency injection pattern used?

### For Each Service Class:
- [ ] What is its constructor signature?
- [ ] What dependencies does it require?
- [ ] What is every public method signature?
- [ ] What are the pre-conditions and post-conditions?
- [ ] Does it mutate state? If so, which repositories?
- [ ] Does it return new data or modify in-place?
- [ ] What exceptions can it raise?
- [ ] Is it stateless or stateful?

### For the API/Impl Pattern:
- [ ] How is the API (interface) separate from the Impl (implementation)?
- [ ] Is there a bootstrap/wiring module?
- [ ] Can implementations be swapped?
- [ ] Are there multiple implementations for any API?

### For the Shaper Pipeline:
- [ ] How does the factory create shapers?
- [ ] How does the pipeline compose shapers?
- [ ] What validation occurs at each stage?
- [ ] What is the shaper execution lifecycle?

### For Data Services:
- [ ] How do path, config, and variable services interact?
- [ ] What is the CSV pool and how does it work?
- [ ] How does pattern indexing work?
- [ ] What is the portfolio service lifecycle?

---

## Information to Extract

### Complete Service Catalog

For each service, produce:

```
### ServiceName
- **File**: src/core/services/xxx.py:NN
- **Purpose**: [one sentence]
- **Dependencies**: [injected via constructor]
- **Stateful**: yes/no
- **Methods**:
  | Method | Parameters | Return Type | Description |
  |--------|-----------|-------------|-------------|
  | do_x   | (a: str, b: int) | DataFrame | ... |
- **Side Effects**: [state mutations, I/O, etc.]
- **Used by**: [callers in the codebase]
```

### Service Dependency Graph

Map which service depends on which:
```
ApplicationAPI
  ├── DataServicesAPI
  │   ├── ConfigService
  │   ├── CsvPoolService
  │   ├── PathService
  │   ├── PatternIndexService
  │   ├── PortfolioService
  │   └── VariableService
  ├── ManagersAPI
  │   ├── ArithmeticService
  │   ├── OutlierService
  │   └── ReductionService
  ├── ShapersAPI
  │   ├── ShaperFactory
  │   └── PipelineService
  └── VisualizationServices
      ├── ConfigResolver
      ├── PaletteService
      └── PlotInteraction
```

---

## Output Template

### 1. Service Inventory
```
[To be filled: Complete list of all services with file locations]
```

### 2. ApplicationAPI Full Documentation
```
[To be filled: Every method with full signature, behavior, delegation]
```

### 3. Service Detail Catalog
```
[To be filled: Full method-level documentation for every service]
```

### 4. Service Dependency Graph
```
[To be filled: Complete dependency tree]
```

### 5. API/Impl Pattern Documentation
```
[To be filled: How the API/implementation separation works]
```

### 6. Shaper Pipeline Flow
```
[To be filled: Step-by-step pipeline execution]
```

### 7. Data Services Interaction Map
```
[To be filled: How data services collaborate]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `core/services-reference.md`, `api-reference/application-api.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `reference/services-catalog.md`
- Step 06 (shaper deep-dive) — uses shaper service catalog
- Step 18 (data flow) — needs service interaction map
- Step 19 (extension points) — needs API/Impl pattern docs
