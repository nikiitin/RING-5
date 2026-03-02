# Step 15 — Portfolio System Analysis

> **Objective**: Document the complete portfolio system — models, service, persistence,
> migration, save/load lifecycle, and schema evolution.

---

## Scope

This step analyzes the **portfolio feature** — how users save their entire session
(data configuration, plot settings, shaper pipelines) and restore it later.

---

## Files to Analyze

### Portfolio Models
```
src/core/models/portfolio_models.py                (portfolio data structures)
```

### Portfolio Service
```
src/core/services/data_services/portfolio_service.py (save/load/manage portfolios)
```

### Portfolio Migrator
```
src/core/services/portfolio_migrator.py            (version migration)
```

### Portfolio UI
```
src/web/pages/portfolio.py                         (portfolio page)
```

### Config Validation (portfolio validation)
```
src/core/services/config_validation_service.py     (validates restored config)
```

### State Serialization
```
src/core/state/repositories/*.py                   (what gets serialized per repository)
```

### Tests
```
tests/integration/test_portfolio_fix.py
tests/integration/test_portfolio_migration.py
tests/integration/test_portfolio_persistence.py
tests/integration/test_portfolio_round_trip.py
tests/integration/test_portfolio_service_integration.py
```

---

## Questions to Answer

### Portfolio Model:
- [ ] What is the portfolio data structure?
- [ ] What data does a portfolio contain? (parsed data ref? shaper config? plot settings?)
- [ ] How is any session data serializable?
- [ ] What is the serialization format? (JSON? pickle? custom?)
- [ ] What is the portfolio file extension?
- [ ] Is there a schema version in the portfolio?

### Portfolio Service:
- [ ] How does save work? (what is collected and serialized)
- [ ] How does load work? (what is deserialized and restored)
- [ ] How are portfolios listed/discovered?
- [ ] Where are portfolios stored on disk?
- [ ] Can portfolios be renamed, deleted?
- [ ] Is there portfolio validation on load?

### Migration:
- [ ] How does version migration work?
- [ ] What migration paths exist?
- [ ] How are breaking changes in config models handled?
- [ ] What happens when a portfolio is from an older version?
- [ ] Are migrations automatic or user-triggered?

### Save/Load Lifecycle:
- [ ] What is the complete save flow? (step by step)
- [ ] What is the complete load flow? (step by step)
- [ ] What state is saved? (all repositories? subset?)
- [ ] What state is NOT saved? (computed caches? UI-only state?)
- [ ] How are large DataFrames handled in serialization?
- [ ] What error handling exists for corrupted portfolios?

### Portfolio UI:
- [ ] What does the portfolio page look like?
- [ ] What actions can the user perform?
- [ ] How does the save dialog work?
- [ ] How does the load dialog work?
- [ ] Is there a portfolio browser/manager?

---

## Information to Extract

### Portfolio Schema
```
Complete schema of what a portfolio file contains, field by field.
```

### Save/Load Flow
```
Save:
1. User clicks "Save Portfolio"
2. Portfolio service collects state from repositories
3. State is serialized to portfolio schema
4. Portfolio is written to disk
5. Confirmation displayed

Load:
1. User selects portfolio file
2. Portfolio is read from disk
3. Schema version is checked
4. Migration applied if needed
5. Portfolio is validated
6. State is restored to repositories
7. UI is refreshed
```

---

## Output Template

### 1. Portfolio Model Documentation
```
[To be filled]
```

### 2. Portfolio Service Documentation
```
[To be filled]
```

### 3. Migration System Documentation
```
[To be filled]
```

### 4. Save/Load Lifecycle
```
[To be filled]
```

### 5. Portfolio Schema (complete)
```
[To be filled]
```

### 6. Portfolio UI Documentation
```
[To be filled]
```

### 7. Error Handling Documentation
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `portfolio/portfolio-system.md`
- `USER_GUIDE_PLAN.md` → `webapp/portfolios.md`
- Step 18 (data flow) — portfolio is the serialization/restoration step
