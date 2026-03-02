# Step 16 — Testing Architecture Analysis

> **Objective**: Document the complete testing system — directory structure, test taxonomy,
> fixtures, conftest hierarchy, markers, strategies, helper utilities, and testing patterns
> for each architectural layer.

---

## Scope

This step analyzes **how the project is tested** — the testing pyramid, fixture
infrastructure, and patterns that developers must follow when writing new tests.

---

## Files to Analyze

### Root Conftest
```
tests/conftest.py                                  (global fixtures and configuration)
```

### Unit Tests
```
tests/unit/                                        (all files — catalog and patterns)
tests/unit/core/visualization/                     (visualization unit tests)
```

### Integration Tests
```
tests/integration/conftest.py                      (integration-specific fixtures)
tests/integration/                                 (all files — catalog and patterns)
```

### UI Logic Tests
```
tests/ui_logic/conftest.py                         (UI logic fixtures)
tests/ui_logic/                                    (all files — catalog and patterns)
```

### UI Unit Tests
```
tests/ui_unit/                                     (all remaining files)
```

### UI Tests
```
tests/ui/                                          (all files)
```

### Visual Tests
```
tests/visual/                                      (visual regression tests)
```

### Performance Tests
```
tests/performance/                                 (benchmark tests)
```

### Compliance Tests
```
tests/tests_principle_compliance/                  (TDD compliance tests)
```

### Test Helpers
```
tests/helpers/                                     (shared test utilities)
```

### Test Data
```
tests/data/mock/config_files/                      (mock configurations)
tests/data/mock/expects/                           (expected outputs)
tests/data/mock/inputs/                            (test inputs)
tests/data/results-micro26-sens/                   (real gem5 data)
```

### Test Configuration
```
pyproject.toml                                     (pytest section)
```

---

## Questions to Answer

### Test Taxonomy:
- [ ] What test categories exist? (unit, integration, ui_logic, ui_unit, ui, visual, performance, compliance)
- [ ] What is the purpose of each category?
- [ ] How many tests are in each category?
- [ ] What is the testing pyramid distribution?
- [ ] What markers are defined? (slow, integration, ui, visual, etc.)

### Conftest Hierarchy:
- [ ] What fixtures does the root conftest.py provide?
- [ ] What fixtures does each sub-conftest provide?
- [ ] How is fixture scoping used? (function, module, session?)
- [ ] What mock objects are provided?
- [ ] Are there fixture factories?

### Test Patterns by Layer:

#### Unit Tests:
- [ ] How are core models tested?
- [ ] How are services tested? (with mocks? with real deps?)
- [ ] How are shapers tested? (input/output DataFrame assertions?)
- [ ] How are visualization configs tested?
- [ ] What assertion patterns are common?

#### Integration Tests:
- [ ] What counts as integration? (multiple services? state + service?)
- [ ] How is state set up for integration tests?
- [ ] Are there end-to-end integration tests?
- [ ] How is test data provided?

#### UI Logic Tests:
- [ ] How are UI components tested without Streamlit?
- [ ] What mocking infrastructure exists for Streamlit?
- [ ] How are controllers tested?
- [ ] How are component outputs asserted?

#### Visual Tests:
- [ ] What visual testing framework is used? (Playwright?)
- [ ] How are baseline images managed?
- [ ] What is the visual comparison threshold?

### Test Data:
- [ ] What mock data is available?
- [ ] What real data is available?
- [ ] How is test data structured?
- [ ] Is there a test data generation utility?

### Test Helpers:
- [ ] What helper functions are shared across tests?
- [ ] What builder/factory patterns exist for test setup?
- [ ] Are there custom assertion functions?

### CI Integration:
- [ ] How are tests run in CI?
- [ ] What is the test matrix?
- [ ] What is the coverage target?
- [ ] What parallelism is used? (max 3 threads per rules)

---

## Information to Extract

### Test Taxonomy Table
```
| Category | Directory | Count | Purpose | Markers |
|----------|-----------|-------|---------|---------|
| Unit     | tests/unit/ | ~100 | Isolated unit tests | — |
| Integration | tests/integration/ | 37 | Cross-component tests | @integration |
| UI Logic | tests/ui_logic/ | 12 | UI without Streamlit | @ui_logic |
| ...      | ...       | ...   | ...     | ...     |
```

### Conftest Fixture Catalog
```
For each fixture:
- Name
- Scope
- What it provides
- Dependencies (other fixtures)
- Used by (which test files)
```

### Test Pattern Guide
```
For each layer, provide:
- Standard test structure (Arrange-Act-Assert)
- Common fixtures used
- Mocking patterns
- Assertion patterns
- Example test (annotated)
```

---

## Output Template

### 1. Test Taxonomy Documentation
```
[To be filled]
```

### 2. Conftest Hierarchy Documentation
```
[To be filled]
```

### 3. Fixture Catalog
```
[To be filled]
```

### 4. Test Patterns per Layer
```
[To be filled]
```

### 5. Test Data Documentation
```
[To be filled]
```

### 6. Test Helpers Documentation
```
[To be filled]
```

### 7. CI Integration Documentation
```
[To be filled]
```

### 8. Coverage Report
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `testing/testing-architecture.md`, `testing/writing-tests.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `reference/test-catalog.md`, `standards/testing-standards.md`
- Step 17 (CI/CD) — test execution in CI
