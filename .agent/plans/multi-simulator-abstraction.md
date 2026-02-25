# Refactor Plan: Multi-Simulator Abstraction & Deep Cleanup

## Objective

Transform RING-5 from a gem5-only tool into a simulator-agnostic analysis platform. Restructure the parsing layer as `src/parsing/` (Layer A), make `src/core/` simulator-independent (Layer B), keep `src/web/` as presentation (Layer C). Perform deep cleanup of dead files, docs, and add E2E test coverage with UI documentation.

## Success Criteria

- [ ] `src/parsing/` is a top-level module independent from `src/core/`
- [ ] `ScannedVariable` is an abstract protocol; gem5 has its own implementation
- [ ] Explicit CSV format contract for all parsers
- [ ] Simulator selector in data source UI (gem5 as only current option)
- [ ] Factory-based parser/scanner instantiation via `ApplicationAPI`
- [ ] Zero gem5-specific references in `src/core/` (except generic comments)
- [ ] Dead files removed (books, .dockerignore, MCP logs, etc.)
- [ ] .gitignore updated for node/playwright dev dependencies
- [ ] Documentation updated with architecture changes
- [ ] E2E tests with screenshots for UI documentation
- [ ] All tests pass, quality gate clean

## Current State (Pre-Refactor)

- **Test baseline**: 3229 passed, 2 skipped, 88.59% coverage
- **Parsing location**: `src/parsing/` (4,682 lines, 38 Python files + 8 Perl files)
- **ScannedVariable**: Concrete dataclass in `src/core/models/parsing_models.py` with gem5-specific type field
- **SimulationParser protocol**: Exists at `src/parsing/parser_protocol.py` but NOT used by ApplicationAPI
- **ApplicationAPI**: Hardwires `ParseService` (=Gem5Parser) and `ScannerService` (=Gem5Scanner) via static calls
- **Data Source UI**: Entirely gem5-specific, no simulator selector
- **Gem5 leaks in core**: `config_validation_service.py` hardcodes `"parser": "gem5_stats"`, `variable_service.py` has gem5-specific `INTERNAL_STATS` set
- **Cleanup needed**: 2 tracked book files (56 MB), orphaned `.dockerignore`, `package.json`/`package-lock.json` tracked, MCP debug logs on disk

---

## Phase Inventory

| Phase | Description | Status | Test Count |
|-------|-------------|--------|------------|
| 0 | Deep cleanup (dead files, books, docker, .gitignore) | ✅ | 3229 |
| 1 | Move `src/core/parsing/` → `src/parsing/` | ✅ | 3229 |
| 2 | Abstract ScannedVariable protocol + Gem5 implementation | ✅ | 3229 |
| 3 | Define explicit CSV format contract | ✅ | 3249 |
| 4 | Simulator registry & factory-based parser injection | ⬜ | — |
| 5 | Remove gem5-specific references from `src/core/` | ⬜ | — |
| 6 | Simulator selector in data source UI | ⬜ | — |
| 7 | Update ApplicationAPI with dependency injection | ⬜ | — |
| 8 | Update documentation & architecture files | ⬜ | — |
| 9 | E2E tests with screenshots for UI documentation | ⬜ | — |
| 10 | Final validation & quality gate | ⬜ | — |

---

## Phase 0: Deep Cleanup

### 0.1 Remove tracked book files from git
```
git rm "Matplotlib for Python Developers...epub"
git rm "Web Automation Testing Using Playwright...azw3"
```

### 0.2 Remove orphaned .dockerignore
```
git rm .dockerignore
```

### 0.3 Handle package.json/package-lock.json
Decision: Remove from git tracking, add to .gitignore. These should be generated on-demand when user wants to run visual/E2E tests.
```
git rm package.json package-lock.json
```
Add `package.json` and `package-lock.json` to .gitignore.

### 0.4 Clean Playwright MCP debug logs
```
rm -rf .playwright-mcp/
```
Already gitignored, just clean from disk.

### 0.5 Review .gitattributes
Current content: Just `* text=auto` + a comment about test data.
Decision: Keep — LF normalization is useful for cross-platform development.

### 0.6 Delete local book PDFs from disk
Not tracked by git, just local cleanup:
```
rm -f *.pdf *.epub *.azw3
```

### 0.7 Update .gitignore
Add rules for:
- `package.json` and `package-lock.json`
- Remove redundant comments, consolidate

### 0.8 Dead code scan
- Check for Docker references in code → Only 1 comment in test, harmless
- Check for unused imports across `src/`
- Verify `REFACTOR_PLAN.txt` on disk is not needed (gitignored, old artifact)

---

## Phase 1: Move `src/parsing/` → `src/parsing/`

### Rationale
Parsing is Layer A (Data Ingestion). It should NOT be inside `src/core/` (Layer B: Domain). This restructure makes the architecture physically match the logical layers:
- `src/parsing/` — Layer A: Reads simulator files, produces CSV
- `src/core/` — Layer B: Business logic, visualization config, shapers
- `src/web/` — Layer C: Streamlit UI

### Steps
1. `git mv src/parsing/ src/parsing/`
2. Update ALL imports across src/ and tests/
3. Update `src/__init__.py` if needed
4. Move `parser_protocol.py` to `src/parsing/` (it's the protocol for ALL simulators)
5. Keep `src/core/models/parsing_models.py` in core — these are the shared DTOs
6. Run full test suite

### Import changes needed
- `from src.parsing` → `from src.parsing`
- `from src.parsing.gem5` → `from src.parsing.gem5`
- `from src.parsing.parser_protocol` → `from src.parsing.parser_protocol`
- ApplicationAPI imports of ParseService/ScannerService
- All test patches referencing parsing paths

---

## Phase 2: Abstract ScannedVariable Protocol + Gem5 Implementation

### Current State
`ScannedVariable` is a concrete frozen dataclass in `src/core/models/parsing_models.py` with:
- `type: str` hardcoded to gem5 values ("scalar", "vector", "distribution", "histogram", "configuration")
- `entries`, `minimum`, `maximum`, `pattern_indices` — all gem5-specific

### Target State
```python
# src/core/models/parsing_models.py — abstract base
@dataclass(frozen=True)
class ScannedVariable:
    """Base metadata for a variable discovered by any simulator parser."""
    name: str
    type: str  # Simulator-specific type string
    entries: list[str] = field(default_factory=list)
    pattern_indices: list[str] | None = None

    def to_dict(self) -> ScannedVariableDict: ...
    @classmethod
    def from_dict(cls, data: ScannedVariableDict) -> "ScannedVariable": ...

# src/parsing/gem5/models.py — gem5-specific extension
@dataclass(frozen=True)
class Gem5ScannedVariable(ScannedVariable):
    """Gem5-specific scanned variable with distribution/histogram metadata."""
    minimum: float | None = None
    maximum: float | None = None
```

### Key decisions
- Keep `ScannedVariable` as a base dataclass (not Protocol) — dataclasses compose better
- `minimum`/`maximum` move to `Gem5ScannedVariable` — only distributions/histograms use these
- `entries` stays on base — all simulators may have multi-value variables
- `pattern_indices` stays on base — pattern aggregation is simulator-agnostic (any simulator can have numbered components)

---

## Phase 3: Define Explicit CSV Format Contract

### Rationale
Parsers output CSV. The domain layer reads CSV. We need an explicit contract for what that CSV looks like.

### Contract Definition
Create `src/parsing/csv_contract.py`:

```python
"""
CSV Format Contract for RING-5 Parsers.

All simulator parsers MUST produce CSV files conforming to this contract.
The CSV is the "common language" between Layer A (Parsing) and Layer B (Core).

Format Rules:
1. Header row is mandatory
2. Each row represents one simulation run/configuration
3. Column names are variable names (hierarchical, dot-separated)
4. Vector entries are expanded as: `variable_name..entry_name`
5. Values are numeric (float) or string (for configuration variables)
6. Missing values are represented as empty string or NaN
7. No simulator-specific metadata in the CSV — only data values
"""

VECTOR_ENTRY_SEPARATOR = ".."  # Separates variable name from entry index
MISSING_VALUE = ""  # Empty string for missing values
```

### Validation
Add a `validate_parser_csv(path: Path) -> list[str]` function that checks:
- Has header row
- No duplicate column names
- All numeric columns parseable as float
- Returns list of validation warnings (empty = valid)

---

## Phase 4: Simulator Registry & Factory-Based Parser Injection

### Design
```python
# src/parsing/registry.py
class SimulatorRegistry:
    """Registry of available simulator parsers."""
    _parsers: dict[str, type[SimulationParser]] = {}

    @classmethod
    def register(cls, name: str, parser_cls: type[SimulationParser]) -> None: ...

    @classmethod
    def get_parser(cls, name: str) -> SimulationParser: ...

    @classmethod
    def available_simulators(cls) -> list[str]: ...

# Auto-registration
SimulatorRegistry.register("gem5", Gem5ParserAPI)
```

### SimulationParser Protocol Update
The existing `SimulationParser` protocol in `parser_protocol.py` is already good. We just need to:
1. Ensure `Gem5ParserAPI` properly implements it
2. Add `scanner_file_pattern` property (default: `"stats.txt"` for gem5)
3. Add `supported_variable_types` property (returns list of valid type strings)

---

## Phase 5: Remove gem5-Specific References from `src/core/`

### Targets
1. `config_validation_service.py` L154: `"parser": "gem5_stats"` → parametric
2. `variable_service.py`: `INTERNAL_STATS` set → move to gem5 module or make configurable
3. Docstrings/comments: Change "gem5 stats" → "simulation stats" where generic
4. `portfolio_models.py`: Field docstrings referencing gem5

### Approach
- `INTERNAL_STATS` filter should be part of the parser registry's metadata
- Each simulator declares its own internal/excluded stats patterns
- `config_validation_service.py` should not hardcode parser type

---

## Phase 6: Simulator Selector in Data Source UI

### Current State
Data source component (`data_source_components.py`, 508 lines) has:
- Title: "### gem5 Stats Parser Configuration"
- Button: "Parse gem5 Stats Files"
- Hardcoded gem5 help text

### Target State
- Add `st.selectbox("Simulator", options=SimulatorRegistry.available_simulators())` at the top
- Change labels to be dynamic based on selected simulator
- File pattern default changes per simulator (e.g., gem5 = "stats.txt")
- Variable types shown dynamically from parser's `supported_variable_types`

### Backward Compatibility
With only gem5 registered, the UI behavior is identical to current state.

---

## Phase 7: Update ApplicationAPI with Dependency Injection

### Current State
```python
# Hardwired to gem5
return ParseService.submit_parse_async(...)
return ScannerService.submit_scan_async(...)
```

### Target State
```python
class ApplicationAPI:
    def __init__(self, ..., parser: SimulationParser | None = None):
        self._parser = parser or SimulatorRegistry.get_parser("gem5")

    def submit_parse_async(self, ...):
        return self._parser.submit_parse_async(...)

    def submit_scan_async(self, ...):
        return self._parser.submit_scan_async(...)
```

The parser instance is injected, with gem5 as the default.

---

## Phase 8: Update Documentation & Architecture Files

### Files to Update
- `.agent/rules/001-architecture-standards.md` — new 3-module structure (parsing/core/web)
- `.agent/rules/project-context.md` — updated architecture description
- `.github/copilot-instructions.md` — updated file structure, CSV contract
- `docs/Architecture.md` — new architecture diagram
- `docs/parsing-architecture.md` — updated for multi-simulator
- `docs/Web-Interface.md` — add UI screenshots section
- `README.md` — update project description

### New Documentation
- `docs/Multi-Simulator-Support.md` — how to add a new simulator parser
- `docs/CSV-Format-Contract.md` — the CSV contract specification

---

## Phase 9: E2E Tests with Screenshots for UI Documentation

### Approach
1. Use existing Playwright infrastructure in `tests/visual/`
2. Create screenshot-generation tests that capture UI states
3. Collapse sidebar in screenshots for cleanliness
4. Generate artifacts for docs embedding

### Test Targets
- Data Source page: parser config, file selection, scanning
- Data Managers: each manager type
- Plot creation: each plot type
- Settings: each settings pill

### Documentation Integration
- Screenshots saved to `docs/images/` (gitignored in `.gitignore`, generated on demand)
- GIFs for multi-step workflows
- Embedded in `docs/Web-Interface.md`

---

## Phase 10: Final Validation & Quality Gate

1. Architecture boundaries check (3 greps)
2. Type safety (mypy --strict)
3. Formatting (black --check)
4. Linting (flake8)
5. Security scan
6. Full test suite
7. Coverage report
8. Documentation review

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-02-25 | Keep .gitattributes | LF normalization is useful cross-platform |
| 2026-02-25 | Remove books from git history | 56 MB of tracked books is unacceptable |
| 2026-02-25 | Remove package.json from tracking | Node deps should be on-demand only |
| 2026-02-25 | ScannedVariable as base dataclass, not Protocol | Dataclasses compose better for frozen data |
| 2026-02-25 | CSV contract as explicit module | Makes the parser↔core boundary formal |
| 2026-02-25 | SimulatorRegistry as class registry | Factory pattern, consistent with PlotFactory/ShaperFactory |

---

## Lessons Learned

(To be updated as phases are executed)

---

## Git Strategy

User has explicitly allowed git operations (except push):
- Use `git rm` for tracked file removal
- Use `git mv` for directory moves
- Commit after each phase with descriptive messages
- NEVER push
