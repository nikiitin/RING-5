# Step 17 — Configuration, Build System & CI/CD Analysis

> **Objective**: Document all project configuration — Python packaging, build targets,
> linting, formatting, pre-commit hooks, CI/CD pipelines, and the development workflow.

---

## Scope

This step catalogs the **development infrastructure** — everything a developer needs to
know to set up their environment, run builds, and pass CI checks.

---

## Files to Analyze

### Python Project Configuration
```
pyproject.toml                                     (packaging, dependencies, tool configs)
```

### Build System
```
Makefile                                           (all build targets)
```

### Linting & Formatting
```
.flake8                                            (flake8 configuration)
pyrightconfig.json                                 (pyright/type checking)
.pre-commit-config.yaml                            (pre-commit hooks)
```

### Trunk Configuration
```
.trunk/trunk.yaml                                  (trunk check configuration)
.trunk/configs/                                    (trunk tool configs)
```

### CI/CD
```
.github/workflows/ci.yml                           (main CI pipeline)
.github/workflows/codeql.yml                       (CodeQL security scanning)
.github/workflows/architecture-check.yml           (architecture validation)
.github/workflows/dependency-check.yml             (dependency checking)
.github/workflows/pages.yml                        (documentation deployment)
```

### Contributing Guide
```
CONTRIBUTING.md                                    (development workflow)
```

### Scripts
```
scripts/analyze_dependencies.py                    (dependency analysis)
scripts/verify_installation.py                     (installation verification)
```

### VS Code Configuration
```
.vscode/                                           (IDE settings)
```

### Streamlit Configuration
```
.streamlit/                                        (Streamlit app config)
```

### App Launcher
```
launch_webapp.sh                                   (startup script)
```

### GitHub Configuration
```
.github/copilot-instructions.md                    (Copilot AI instructions)
.github/AI-CAPABILITIES.md                         (AI capabilities)
.github/dependabot.yml                             (dependency updates)
.github/CODEQL.md                                  (CodeQL documentation)
.github/CODEQL-SETUP.md                            (CodeQL setup)
```

---

## Questions to Answer

### Project Configuration:
- [ ] What Python version is required? (3.12+)
- [ ] What are all the dependencies? (with versions)
- [ ] What are the dev dependencies?
- [ ] What is the package structure?
- [ ] How is the project installed? (pip install -e ?)
- [ ] What entry points are defined?

### Makefile Targets:
- [ ] What targets are available?
- [ ] What does each target do?
- [ ] What is the target dependency graph?
- [ ] What are the most commonly used targets?
- [ ] Which targets run tests? (and with what options)
- [ ] Which targets run linting?
- [ ] Which targets do formatting?

### Linting & Formatting:
- [ ] What linters are configured? (flake8, pyright, mypy, ruff, trunk)
- [ ] What are the key lint rules?
- [ ] What is the formatting standard? (black? ruff format?)
- [ ] What are the import sorting rules? (isort)
- [ ] What type checking strictness is configured?

### Pre-commit Hooks:
- [ ] What hooks are configured?
- [ ] What runs automatically on commit?
- [ ] What should a developer know about hooks?

### CI Pipelines:
- [ ] What does the CI pipeline run?
- [ ] What are the CI jobs and their order?
- [ ] What must pass before merge?
- [ ] What is the test matrix (Python versions, OS)?
- [ ] What is the code coverage threshold?
- [ ] What security scanning is performed?

### Architecture Check:
- [ ] What does the architecture check workflow verify?
- [ ] What rules does it enforce?
- [ ] How does it detect violations?

### Dependency Check:
- [ ] What does the dependency check verify?
- [ ] How is supply chain security maintained?

---

## Information to Extract

### Makefile Target Catalog
```
| Target | Command | Purpose |
|--------|---------|---------|
| test   | pytest ... | Run full test suite |
| lint   | ... | Run all linters |
| ...    | ... | ... |
```

### CI Pipeline Flow
```
Trigger: push/PR to main
1. Job: lint → [flake8, pyright, trunk check]
2. Job: test → [pytest -n 3, coverage report]
3. Job: security → [codeql, dependency check]
4. Job: architecture → [boundary verification]
```

### Development Workflow
```
1. Clone repository
2. Set up virtual environment
3. Install dependencies (pip install -e .[dev])
4. Set up pre-commit hooks
5. Run tests to verify setup
6. Make changes
7. Run linting and tests
8. Commit (pre-commit hooks run)
9. Push (CI runs)
```

---

## Output Template

### 1. Project Configuration Documentation
```
[To be filled]
```

### 2. Makefile Target Catalog
```
[To be filled]
```

### 3. Linting & Formatting Documentation
```
[To be filled]
```

### 4. Pre-commit Hooks Documentation
```
[To be filled]
```

### 5. CI Pipeline Documentation
```
[To be filled]
```

### 6. Architecture Check Documentation
```
[To be filled]
```

### 7. Dependency Management Documentation
```
[To be filled]
```

### 8. Development Workflow Documentation
```
[To be filled]
```

### 9. IDE Setup Documentation
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `testing/ci-cd-pipeline.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `standards/coding-standards.md`, `standards/quality-gate.md`
- `USER_GUIDE_PLAN.md` → `getting-started/installation.md` (needs dependency info)
