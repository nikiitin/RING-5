# Commit Plan for Architecture Refactor

## Overview

This refactoring represents a complete migration from a layered architecture (Layer A/B/C) to Clean Architecture with Domain-Driven Design (DDD) principles. The work involved moving from `src/parsers/`, `src/plotting/`, `src/config/` to a new `src/core/` structure following SOLID principles.

## Commit Sequence

### Commit 1: Core Domain Layer - Add domain models and entities

**Type:** feat (new feature)
**Scope:** core
**Message:** `feat(core): implement domain layer with plot and parser models`

**Files:**

- `src/core/__init__.py`
- `src/core/domain/plot.py`
- `src/core/domain/models.py`
- `src/core/common/utils.py`

**Rationale:** Domain entities are the foundation of DDD. These define the core business objects (Plot, Variable, etc.) with no external dependencies.

---

### Commit 2: Core Parsing Layer - Implement parsing domain services

**Type:** feat
**Scope:** parsing
**Message:** `feat(parsing): implement Clean Architecture parsing layer with type system`

**Files:**

- `src/core/parsing/__init__.py`
- `src/core/parsing/base.py`
- `src/core/parsing/type_mapper.py`
- `src/core/parsing/scanner.py`
- `src/core/parsing/parse_service.py`
- `src/core/parsing/scanner_service.py`
- `src/core/parsing/pattern_aggregator.py`
- `src/core/parsing/strategies/`
- `src/core/parsing/types/` (all type implementations)
- `src/core/parsing/workers/` (all worker implementations)
- `src/core/parsing/perl/` (Perl parsing scripts)

**Rationale:** Parsing is a critical domain service. Moving it to `core/parsing/` establishes clear boundaries and ownership.

---

### Commit 3: Core Services Layer - Configuration and data processing

**Type:** feat
**Scope:** services
**Message:** `feat(services): add configuration and data processing services`

**Files:**

- `src/core/config/__init__.py`
- `src/core/config/config_manager.py`
- `src/core/config/schemas/`
- `src/core/services/__init__.py`
- `src/core/services/config_service.py`
- `src/core/services/csv_pool_service.py`
- `src/core/services/data_processing_service.py`
- `src/core/services/pipeline_service.py`
- `src/core/services/paths.py`
- `src/core/services/shapers/` (all shaper implementations)

**Rationale:** Application services orchestrate domain logic. These provide the "use cases" of the application.

---

### Commit 4: Core Plotting Layer - Plotting domain with exports

**Type:** feat
**Scope:** plotting
**Message:** `feat(plotting): migrate plotting subsystem to core with LaTeX export`

**Files:**

- `src/core/plotting/__init__.py`
- `src/core/plotting/base_plot.py`
- `src/core/plotting/plot_factory.py`
- `src/core/plotting/plot_renderer.py`
- `src/core/plotting/types/` (all plot types)
- `src/core/plotting/styles/` (styling system)
- `src/core/plotting/utils/`
- `src/core/plotting/export/` (LaTeX export system)

**Rationale:** Plotting is a bounded context with well-defined responsibilities. Moving to core establishes it as a first-class domain.

---

### Commit 5: State Management Layer - Repositories and state manager

**Type:** feat
**Scope:** state
**Message:** `feat(state): implement repository pattern for state management`

**Files:**

- `src/core/state/__init__.py`
- `src/core/state/state_manager.py`
- `src/core/state/repositories/__init__.py`
- `src/core/state/repositories/config_repository.py`
- `src/core/state/repositories/data_repository.py`
- `src/core/state/repositories/parser_state_repository.py`
- `src/core/state/repositories/plot_repository.py`
- `src/core/state/repositories/preview_repository.py`
- `src/core/state/repositories/session_repository.py`

**Rationale:** Repository pattern abstracts data access. This isolates state management from business logic.

---

### Commit 6: Infrastructure - Multiprocessing and benchmarking

**Type:** feat
**Scope:** infrastructure
**Message:** `feat(infrastructure): add multiprocessing pool and performance monitoring`

**Files:**

- `src/core/multiprocessing/__init__.py`
- `src/core/multiprocessing/pool.py`
- `src/core/multiprocessing/job.py`
- `src/core/application_api.py`
- `src/core/benchmark.py`
- `src/core/performance.py`

**Rationale:** Infrastructure concerns (concurrency, monitoring) are separated from domain logic.

---

### Commit 7: Presentation Layer - UI components migration

**Type:** refactor
**Scope:** ui
**Message:** `refactor(ui): migrate Streamlit UI to new architecture`

**Files:**

- `src/web/pages/ui/` (all new UI components)
- `src/web/pages/__init__.py`
- `src/web/pages/data_managers.py`
- `src/web/pages/data_source.py`
- `src/web/pages/manage_plots.py`
- `src/web/pages/performance.py`
- `src/web/pages/portfolio.py`
- `src/web/pages/upload_data.py`
- `src/web/__init__.py`
- `app.py`

**Rationale:** UI layer now depends on core services, not vice versa. This completes the dependency inversion.

---

### Commit 8: Tests - Comprehensive test suite updates

**Type:** test
**Scope:** all
**Message:** `test: update entire test suite for new architecture`

**Files:**

- All new test files in `tests/unit/`:
  - `test_application_api.py`
  - `test_benchmark.py`
  - `test_config_service.py`
  - `test_configuration_type.py`
  - `test_csv_pool_service.py`
  - `test_distribution_type.py`
  - `test_histogram_type.py`
  - `test_parser_base.py`
  - `test_parser_comprehensive.py`
  - `test_scalar_type.py`
  - `test_scanner_comprehensive.py`
  - `test_state_management_new.py`
  - `test_vector_type.py`
- All new test files in `tests/integration/`:
  - `test_portfolio_fix.py`
  - `test_scanner_fix.py`
- All modified test files (updated imports and assertions)

**Rationale:** Tests validate the new architecture works correctly. This ensures no regressions.

---

### Commit 9: Cleanup - Remove deprecated architecture

**Type:** refactor
**Scope:** cleanup
**Message:** `refactor: remove deprecated layered architecture`

**Files to DELETE:**

- `src/parsers/` (entire directory)
- `src/plotting/` (entire directory)
- `src/config/` (entire directory)
- `src/web/repositories/` (moved to core/state)
- `src/web/services/` (moved to core/services)
- `src/web/ui/components/` (migrated to pages/ui)
- `src/web/ui/data_managers/` (migrated)
- `src/web/facade.py`
- `src/web/state_manager.py`
- `src/web/styles.py`
- `src/web/types.py`
- `src/web/ui/shaper_config.py`
- `src/scanning/__init__.py`
- `src/utils/utils.py`
- `config/latex_presets.yaml` (moved to core/config)
- `verify_installation.py` (moved to scripts/)

**Rationale:** Remove old code to prevent confusion and reduce maintenance burden.

---

### Commit 10: Documentation - Update AI agent instructions

**Type:** docs
**Scope:** agent
**Message:** `docs(agent): update AI instructions for Clean Architecture`

**Files:**

- `.agent/.cursorrules`
- `.agent/ARCHITECTURE.md`
- `.agent/QUICKSTART.md`
- `.agent/README.md`
- `.agent/rules/000-identity-mission.md`
- `.agent/rules/001-architecture-standards.md`
- `.agent/rules/002-data-science-mastery.md`
- `.agent/rules/003-software-engineering.md`
- `.agent/rules/004-qa-testing-mastery.md`
- `.agent/rules/project-context.md`
- `.agent/unified_architecture_manifesto.md`
- `.agent/workflows/README.md`
- `.agent/workflows/new-plot-type.md`
- `.agent/workflows/parsing-workflow.md`
- `.agent/workflows/test-driven-development.md`
- `.agent/DOCKER_GUIDE.md`

**Rationale:** AI agents need updated instructions reflecting the new architecture.

---

### Commit 11: Documentation - Update contributor and CI/CD docs

**Type:** docs
**Scope:** contributing
**Message:** `docs: update CONTRIBUTING guide and GitHub Actions documentation`

**Files:**

- `CONTRIBUTING.md`
- `.github/AI-CAPABILITIES.md`
- `.github/CODEQL-SETUP.md`
- `.github/CODEQL.md`

**Rationale:** Keep contributor documentation in sync with architecture changes.

---

### Commit 12: Build System - Enhanced Makefile and project config

**Type:** build
**Scope:** config
**Message:** `build: enhance Makefile with new targets and update dependencies`

**Files:**

- `Makefile`
- `pyproject.toml`

**Rationale:** Build system needs to understand new structure (type checking, testing paths).

---

### Commit 13: CI/CD - Update CodeQL and pre-commit configuration

**Type:** ci
**Scope:** security
**Message:** `ci: update CodeQL config and pre-commit hooks for new structure`

**Files:**

- `.github/workflows/codeql.yml`
- `.github/codeql/codeql-config.yml`
- `.pre-commit-config.yaml`

**Rationale:** Security scanning and linting need updated paths and exclusions.

---

### Commit 14: Infrastructure - Add Docker containerization

**Type:** feat
**Scope:** docker
**Message:** `feat(docker): add containerization with compose support`

**Files:**

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

**Rationale:** Docker support enables reproducible deployments and development environments.

---

### Commit 15: Utilities - Add development helper scripts

**Type:** chore
**Scope:** scripts
**Message:** `chore: add debugging and installation verification scripts`

**Files:**

- `scripts/debug_imports.py`
- `scripts/verify_installation.py`

**Rationale:** Helper scripts aid development and troubleshooting.

---

## Summary

**Total Commits:** 15
**Major Categories:**

- 6 feature commits (domain, parsing, services, plotting, state, infrastructure)
- 2 refactor commits (UI migration, cleanup)
- 1 test commit (comprehensive test updates)
- 4 documentation commits (agent, contributing, workflows)
- 2 build/CI commits (Makefile, CodeQL, pre-commit)

**Architecture Transformation:**

- **Before:** Layered architecture (Layer A/B/C) with `src/parsers/`, `src/plotting/`, `src/config/`
- **After:** Clean Architecture with DDD - `src/core/` containing domain, services, state, infrastructure

**Benefits:**

- ✅ Dependency inversion (UI depends on core, not vice versa)
- ✅ Clear boundaries between layers
- ✅ Repository pattern for testability
- ✅ SOLID principles throughout
- ✅ Domain-driven design with bounded contexts
