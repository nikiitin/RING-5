# AI Knowledge Base Generation Plan

> **Target**: `.agent/knowledge/`
> **Audience**: AI agents (Claude Code, Copilot, Cursor, any LLM-based developer tool)
> **Purpose**: Machine-actionable, always-up-to-date source of truth for AI-assisted development

---

## 1. Philosophy

This knowledge base is **fundamentally different** from human documentation:

- **Density over readability**: Pack maximum information per line
- **Code-first**: Show exact file paths, class names, method signatures
- **Actionable**: Every guide can be followed mechanically by an AI agent
- **Self-contained**: Each file should be independently useful without reading all others
- **Always current**: This is the **canonical truth** — if it contradicts other docs, this is correct
- **Trigger-ready**: These files are what trigger workflows and inform AI decisions

---

## 2. Relationship to Other Documentation

```
.agent/knowledge/          ← SOURCE OF TRUTH (for AI agents)
    ↓ extracted from ↓
.agent/documentation-project/analysis/  ← RAW ANALYSIS (intermediate)
    ↓ also feeds ↓
docs/developer-guide/      ← HUMAN-READABLE (for developers)
docs/user-guide/           ← HUMAN-READABLE (for users)
```

The knowledge base is **more detailed and technical** than the developer guide, and
includes machine-specific information (exact file paths, line numbers, import paths)
that would be overwhelming in human docs.

---

## 3. Complete File Structure

```
.agent/knowledge/
├── README.md                               # Index: what's here, how to use it, update policy
│
├── architecture/
│   ├── system-overview.md                  # Complete architecture with module map
│   ├── layer-boundaries.md                 # Every package → layer mapping, import rules
│   ├── design-patterns.md                  # Every pattern instance with file:line references
│   ├── data-flow.md                        # End-to-end data flow with types at each stage
│   └── visualization-pipeline.md           # FigureConfig → Connector → Render with code refs
│
├── development/
│   ├── adding-a-parser.md                  # Machine-actionable: files to create, code to write
│   ├── adding-a-plot.md                    # Machine-actionable: files to create, code to write
│   ├── adding-a-shaper.md                  # Machine-actionable: files to create, code to write
│   ├── adding-a-component.md               # Machine-actionable: patterns, keys, state
│   ├── adding-a-service.md                 # Machine-actionable: API/Impl, DI, registration
│   └── adding-export-format.md             # Machine-actionable: preset schema, registration
│
├── reference/
│   ├── models-catalog.md                   # EVERY model with ALL fields, types, defaults
│   ├── services-catalog.md                 # EVERY service with ALL methods, signatures
│   ├── components-catalog.md               # EVERY UI component with parameters, usage
│   ├── file-index.md                       # EVERY source file with one-line purpose
│   └── test-catalog.md                     # Test structure, fixture reference, run commands
│
└── standards/
    ├── coding-standards.md                 # ALL coding rules, naming, imports, typing
    ├── testing-standards.md                # Testing rules, patterns, fixture conventions
    └── quality-gate.md                     # Definition of Done, CI requirements
```

---

## 4. File Generation Details

### 4.1 README.md
- **Content**:
  - What this knowledge base is
  - Who it's for (AI agents)
  - How to navigate it
  - Update policy ("must be updated when source code changes")
  - How it relates to other docs
  - Quick directory guide
- **Format**: Dense, link-heavy index

### 4.2 architecture/system-overview.md
- **Source**: Steps 01, 04, 08
- **Content**:
  - ASCII architecture diagram (3 layers)
  - Module-to-layer mapping (every package)
  - Entry points (app.py, ApplicationAPI)
  - Service wiring and dependency injection
  - State management overview
  - Rendering engine overview
  - Key files to know (top 20 most important files)
- **Must include**: Exact file paths, class names, line numbers
- **Length**: ~500-800 lines

### 4.3 architecture/layer-boundaries.md
- **Source**: Step 01
- **Content**:
  - STRICT import rules (with examples of allowed/forbidden)
  - Package → Layer table (every src/ package)
  - Protocol interfaces at each boundary (with file:line refs)
  - How to check boundaries (commands)
- **Length**: ~200-400 lines

### 4.4 architecture/design-patterns.md
- **Source**: Steps 01, 03
- **Content**:
  - Every pattern used in the codebase with:
    - Pattern name
    - Where it's used (file:line)
    - Concrete example from the codebase
    - When to use it
- **Must include**: Repository, Factory, Protocol, Facade, DI, FCIS, Discriminated Union
- **Length**: ~400-600 lines

### 4.5 architecture/data-flow.md
- **Source**: Step 18
- **Content**:
  - Complete data flow: raw files → parsed DataFrame → shaped DataFrame → FigureConfig → rendered plot → exported file
  - Data type at each stage (exact Python types)
  - Service methods at each stage (exact signatures)
  - State mutations at each stage (exact repository keys)
- **Length**: ~400-600 lines

### 4.6 architecture/visualization-pipeline.md
- **Source**: Steps 07, 11
- **Content**:
  - FigureConfig hierarchy (complete tree)
  - Config builder → FigureConfig mapping
  - Connector protocol (exact methods)
  - Plotly connector code path
  - Matplotlib connector code path
  - Engine selection logic
- **Length**: ~300-500 lines

### 4.7 development/adding-a-parser.md
- **Source**: Steps 05, 19
- **Required format** (machine-actionable):
  ```
  ## Files to Create
  - src/parsing/{name}/__init__.py
  - src/parsing/{name}/parser.py
  - src/parsing/{name}/scanner.py
  - tests/unit/test_{name}_parser.py
  - tests/integration/test_{name}_parsing.py

  ## Protocol to Implement
  [exact protocol with all methods]

  ## Registration
  [exact code to add to registry.py]

  ## Required Tests
  [exact test patterns to follow]
  ```
- **Length**: ~300-500 lines

### 4.8-4.12 development/ (remaining guides)
- Same machine-actionable format as adding-a-parser
- Each shows exact files, protocols, registration, tests
- **Length**: ~200-400 lines each

### 4.13 reference/models-catalog.md
- **Source**: Step 02
- **Content**: EVERY model in the codebase, each with:
  - Full qualified name and file:line
  - All fields with types and defaults
  - Relationships to other models
  - Where it's created and consumed
- **This is exhaustive** — no model can be missing
- **Length**: ~1000-1500 lines

### 4.14 reference/services-catalog.md
- **Source**: Step 03
- **Content**: EVERY service, with:
  - Class name and file:line
  - Constructor dependencies
  - All public methods with exact signatures
  - Brief behavioral description per method
- **Length**: ~800-1200 lines

### 4.15 reference/components-catalog.md
- **Source**: Step 09
- **Content**: EVERY UI component, with:
  - Function name and file:line
  - Parameters
  - Widgets rendered
  - State interactions
  - Where it's used
- **Length**: ~600-1000 lines

### 4.16 reference/file-index.md
- **Source**: All steps
- **Content**: EVERY Python source file with a one-line purpose
- **Format**:
  ```
  src/core/application_api.py       | Main facade — single entry point for all business logic
  src/core/models/data_models.py    | Core data models: ParsedData, DataSet, Variable
  ...
  ```
- **Length**: ~200-300 lines (one per file)

### 4.17 reference/test-catalog.md
- **Source**: Step 16
- **Content**:
  - Test directory structure
  - Key fixtures and their scope
  - How to run tests (exact commands)
  - Marker list and usage
  - Where to put new tests per category
- **Length**: ~300-500 lines

### 4.18 standards/coding-standards.md
- **Source**: Steps 01, 17 + existing .agent/rules/
- **Content**:
  - Naming conventions
  - Import ordering rules
  - Type annotation rules (mandatory, no Any)
  - Documentation standards
  - Error handling patterns
  - Streamlit-specific rules
  - Anti-patterns to avoid
- **Length**: ~300-500 lines

### 4.19 standards/testing-standards.md
- **Source**: Step 16 + rule 004
- **Content**:
  - Test naming conventions
  - Fixture patterns
  - Mock path rules (Rule 009)
  - Assertion patterns
  - TDD workflow
  - Max 3 threads rule
- **Length**: ~200-400 lines

### 4.20 standards/quality-gate.md
- **Source**: Step 17 + workflows/code-quality-gate.md
- **Content**:
  - All 8 quality gates with commands
  - What must pass before any task is complete
  - CI requirements
  - Architecture validation commands
- **Length**: ~200-300 lines

---

## 5. Update Policy

This section defines **when and how** the knowledge base must be updated:

1. **After any structural change** — New file, moved file, deleted file → update file-index.md
2. **After any model change** — New or modified model → update models-catalog.md
3. **After any service change** — New or modified service → update services-catalog.md
4. **After any new feature** — New parser, plot, shaper → update development/ guides
5. **After any architecture change** — Layer change, pattern change → update architecture/
6. **After any test infrastructure change** — update test-catalog.md and testing-standards.md

**The knowledge base is the source of truth for AI development. If it's wrong, the AI
will make wrong decisions. Keeping it current is non-negotiable.**

---

## 6. Integration with Agent Instructions

After the knowledge base is generated, the following must be added to agent instructions:

### In `.github/copilot-instructions.md`:
```markdown
## Knowledge Base
The definitive source of project knowledge for AI agents is located at:
`.agent/knowledge/`

Before making any architectural decision, code change, or extension, consult:
- `.agent/knowledge/architecture/` — for system design understanding
- `.agent/knowledge/development/` — for step-by-step guides on adding features
- `.agent/knowledge/reference/` — for model, service, and component details
- `.agent/knowledge/standards/` — for coding and testing rules

This knowledge base MUST always be up-to-date and supersedes any other documentation
when there are conflicts.
```

### In `.agent/rules/` (new rule or amendment):
```markdown
## Knowledge Base Usage (MANDATORY)
- ALWAYS consult `.agent/knowledge/` before starting any task
- When adding new features, follow the guides in `.agent/knowledge/development/`
- When uncertain about architecture, consult `.agent/knowledge/architecture/`
- After completing any task that changes structure, UPDATE the knowledge base
```

---

## 7. Estimated Total Size

| Section | Files | Estimated Lines |
|---------|-------|-----------------|
| README.md | 1 | ~80 |
| architecture/ | 5 | ~2000 |
| development/ | 6 | ~2000 |
| reference/ | 5 | ~3500 |
| standards/ | 3 | ~800 |
| **Total** | **20 files** | **~8,380 lines** |
