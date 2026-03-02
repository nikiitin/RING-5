# Step 04 — State Management & Repositories Analysis

> **Objective**: Document the complete state management system — every repository, the
> state manager, session state integration, and the data lifecycle.

---

## Scope

This step analyzes **how data is stored, retrieved, and mutated** throughout the application
lifecycle. This is critical for understanding side effects and debugging state issues.

---

## Files to Analyze

### State Manager
```
src/core/state/state_manager.py
src/core/state/repository_state_manager.py
```

### All Repositories
```
src/core/state/repositories/__init__.py
src/core/state/repositories/config_repository.py
src/core/state/repositories/data_repository.py
src/core/state/repositories/history_repository.py
src/core/state/repositories/parser_state_repository.py
src/core/state/repositories/plot_repository.py
src/core/state/repositories/preview_repository.py
src/core/state/repositories/session_repository.py
src/core/state/repositories/visualization_repository.py
```

### UI State Manager
```
src/web/state/__init__.py
src/web/state/ui_state_manager.py
```

### Streamlit Session State Integration
```
app.py                                     (session initialization)
```

---

## Questions to Answer

### State Manager Architecture:
- [ ] What is the StateManager class and how is it instantiated?
- [ ] What is the RepositoryStateManager and how does it differ?
- [ ] How is the state manager passed to services?
- [ ] Is there a single global instance or per-session?
- [ ] How does it integrate with Streamlit's session_state?

### For Each Repository:
- [ ] What data does it store?
- [ ] What is the storage backend? (dict, list, session_state key?)
- [ ] What are its CRUD methods? (create/read/update/delete)
- [ ] What are the keys/identifiers used?
- [ ] Is data persistent across page reruns? How?
- [ ] What data types does it store? (models from step 02)
- [ ] Does it perform any validation on write?
- [ ] What are the concurrency considerations?

### Session State Integration:
- [ ] Which session_state keys are used?
- [ ] How is session_state initialized on first load?
- [ ] What is the hydrate-then-render pattern?
- [ ] How do repositories map to session_state keys?
- [ ] Are there any raw session_state accesses outside repositories?

### UI State Manager:
- [ ] What presentation-layer state does it manage?
- [ ] How does it differ from core state?
- [ ] What UI-specific keys does it maintain?

### Data Lifecycle:
- [ ] What happens when a user opens the app? (initial state)
- [ ] What happens when data is parsed? (state transitions)
- [ ] What happens when a plot is created? (state mutations)
- [ ] What happens when a portfolio is loaded? (state restoration)
- [ ] What triggers state cleanup/reset?

---

## Information to Extract

### Repository Catalog

For each repository:

```
### RepositoryName
- **File**: src/core/state/repositories/xxx.py:NN
- **Purpose**: [what data it stores]
- **Storage**: [backend mechanism]
- **Keys/Schema**:
  | Key | Type | Description |
  |-----|------|-------------|
  | ... | ...  | ...         |
- **Methods**:
  | Method | Parameters | Return | Description |
  |--------|-----------|--------|-------------|
  | get_x  | (id: str) | Model  | ...         |
- **Session State Keys**: [mapped keys]
- **Written by**: [which services write to it]
- **Read by**: [which services/components read from it]
```

### State Flow Diagrams

Document the state transitions for key workflows:
1. App initialization flow
2. Data parsing flow (session state changes)
3. Plot creation flow (state mutations)
4. Portfolio save/load flow (state serialization)

---

## Output Template

### 1. State Manager Documentation
```
[To be filled: Complete documentation of StateManager and RepositoryStateManager]
```

### 2. Repository Catalog
```
[To be filled: Every repository with full method docs]
```

### 3. Session State Key Map
```
[To be filled: Every session_state key, its type, and who reads/writes it]
```

### 4. UI State Manager Documentation
```
[To be filled: Complete documentation of UI-layer state]
```

### 5. State Flow Diagrams
```
[To be filled: State transitions for each major workflow]
```

### 6. Data Lifecycle Documentation
```
[To be filled: Complete lifecycle from app open to session end]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `core/state-management.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `architecture/system-overview.md` (state section)
- Step 08 (web pages) — needs to know how pages read/write state
- Step 15 (portfolio) — needs serialization/deserialization flow
- Step 18 (data flow) — needs complete state transition documentation
