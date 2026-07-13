---
title: "Portfolio System"
parent: Web Layer
grand_parent: Developer Guide
nav_order: 4
---

# Portfolio System

## Overview

The portfolio system implements the **Memento design pattern** for the RING-5 Unified
Engine v2.  A portfolio is a complete snapshot of a user's working session -- data,
plots, configurations, parser state, and operation history -- serialized into a single
JSON file.  Users can save a portfolio and reload it later to resume exactly where
they left off, share reproducible analysis sessions with colleagues, or compare
different analysis configurations side by side.

All portfolio files are stored under `<project_root>/.ring5/portfolios/` as
human-readable JSON with embedded CSV data.

### Key operations

| Operation | Entry point | Description |
|-----------|-------------|-------------|
| **Save**  | `PortfolioService.save_portfolio()` | Serialize session state to a JSON file |
| **Load**  | `PortfolioService.load_portfolio()` | Read JSON, migrate schema, return typed dict |
| **List**  | `PortfolioService.list_portfolios()` | Enumerate `*.json` files in the portfolios directory |
| **Delete**| `PortfolioService.delete_portfolio()` | Remove a portfolio file from disk |

### Source files

| File | Role |
|------|------|
| `src/core/models/portfolio_models.py` | `PortfolioData` TypedDict (serialization schema) |
| `src/core/services/data_services/portfolio_service.py` | Save / load / list / delete logic |
| `src/core/services/portfolio_migrator.py` | Forward-compatible schema migration |
| `src/core/state/repositories/session_repository.py` | State restoration across repositories |
| `src/web/pages/portfolio.py` | Streamlit page for the portfolio UI |

---

## Portfolio Models

### PortfolioData

`PortfolioData` is a `TypedDict` with `total=False`, making every field optional so
that older portfolios missing newer fields load without `KeyError`.

```python
# src/core/models/portfolio_models.py

class PortfolioData(TypedDict, total=False):
    parse_variables: list[ParseVariableConfig]
    stats_path: str
    stats_pattern: str
    csv_path: str
    use_parser: bool
    scanned_variables: list[ScannedVariableDict]
    data_csv: str
    plots: list[dict[str, Any]]
    plot_counter: int
    config: dict[str, Any]
    shapers: list[ShaperStepConfig]
    manager_history: list[OperationRecord]
    portfolio_history: list[OperationRecord]
```

| Field | Type | Purpose |
|-------|------|---------|
| `parse_variables` | `list[ParseVariableConfig]` | Simulator variable configurations for the parser |
| `stats_path` | `str` | Filesystem path to the simulator statistics directory |
| `stats_pattern` | `str` | Glob pattern for locating stats files (e.g. `"stats.txt"`) |
| `csv_path` | `str` | Path to the original CSV data file |
| `use_parser` | `bool` | Whether parser mode was active at save time |
| `scanned_variables` | `list[ScannedVariableDict]` | Variables discovered by the scanner |
| `data_csv` | `str` | Full dataset serialized via `DataFrame.to_csv(index=False)` |
| `plots` | `list[dict]` | Serialized plot objects from `BasePlot.to_dict()` |
| `plot_counter` | `int` | Monotonic counter for generating unique plot IDs |
| `config` | `dict` | Global application configuration |
| `shapers` | `list[ShaperStepConfig]` | Reserved for global shaper steps (not currently populated) |
| `manager_history` | `list[OperationRecord]` | Rolling list of recent data manager operations |
| `portfolio_history` | `list[OperationRecord]` | Unbounded audit trail of all operations |

### Envelope fields

`PortfolioService.save_portfolio()` adds three envelope fields that are *not* part of
the `PortfolioData` TypedDict:

| Field | Type | Purpose |
|-------|------|---------|
| `schema_version` | `int` | Schema version for migration (currently `2`) |
| `version` | `str` | Human-readable format version (`"2.0"`) |
| `timestamp` | `str` | ISO-8601 timestamp of the save |

### OperationRecord

Each history entry follows the `OperationRecord` TypedDict defined in
`src/core/models/history_models.py`:

```python
class OperationRecord(TypedDict):
    source_columns: list[str]
    dest_columns: list[str]
    operation: str
    timestamp: str
```

---

## Portfolio Service

`PortfolioService` lives at `src/core/services/data_services/portfolio_service.py`
and is constructed with a `StateManager` reference so it can pull parser state and
history during save.

### save_portfolio

```python
def save_portfolio(
    self, name, data, plots, config, plot_counter,
    csv_path=None, parse_variables=None, figure_spec_enricher=None,
) -> None:
```

1. **Validate** -- raises `ValueError` if `name` is empty.
2. **Serialize plots** -- calls `plot.to_dict()` for each plot.  If
   `figure_spec_enricher` is provided, it converts each plot's config into a
   `FigureConfig` dict and attaches it as `plot_dict["figure_spec"]`.
3. **Serialize data** -- calls `data.to_csv(index=False)` (empty string if no data).
4. **Read state** -- pulls `stats_path`, `stats_pattern`, `scanned_variables`,
   `manager_history`, and `portfolio_history` from the `StateManager`.
5. **Assemble envelope** -- adds `schema_version`, `version`, and `timestamp`.
6. **Write file** -- sanitizes the filename, validates the path stays within the
   portfolios directory, and writes via `json.dump()` with `indent=2`.

### load_portfolio

```python
def load_portfolio(self, name: str) -> PortfolioData:
```

1. Constructs the file path and validates it.
2. Raises `FileNotFoundError` if the file does not exist.
3. Reads the JSON into a raw dict.
4. Passes the dict through `PortfolioMigrator.migrate()` for schema upgrades.
5. Returns the migrated dict cast to `PortfolioData`.

### list_portfolios and delete_portfolio

`list_portfolios()` globs for `*.json` in the portfolios directory and returns a
list of stem names.  `delete_portfolio()` removes the file if it exists; a missing
file is silently ignored.

---

## Figure Spec Enrichment

The `figure_spec_enricher` callback bridges the dependency gap between the core
layer and the web layer.  The core service must not import web-layer classes, so
the portfolio page injects a callback at call time:

```python
# src/web/pages/portfolio.py

def _build_figure_spec(config: dict[str, Any], plot_type: str) -> dict[str, Any] | None:
    spec = ConfigSpecBuilder.from_config(config, plot_type)
    return spec.to_dict()
```

This converts each plot's flat config dict into a full `FigureConfig` dataclass via
`ConfigSpecBuilder.from_config()`, then serializes it back to a dict.  The resulting
dict is stored as `figure_spec` inside the plot entry in the portfolio JSON,
providing a snapshot of the complete rendering specification for cross-engine
compatibility (Plotly / Matplotlib).

If the enricher raises an exception for a given plot, the error is caught and
logged -- the plot is still saved without its spec.

---

## Schema Migration

### Version history

| Version | Characteristics |
|---------|-----------------|
| **V1** (original) | No `engine` field per plot; contains `export_format`, `export_dpi`, `export_path` keys; no `schema_version` field |
| **V2** (current) | `schema_version: 2`; each plot config carries an `engine` field; all `export_*` keys removed |

### PortfolioMigrator

`PortfolioMigrator` at `src/core/services/portfolio_migrator.py` applies forward
migrations.  A missing `schema_version` is treated as version 1.

```python
class PortfolioMigrator:
    CURRENT_VERSION: int = 2

    @staticmethod
    def migrate(portfolio_data: dict[str, Any]) -> dict[str, Any]:
        version = int(portfolio_data.get("schema_version", 1))
        if version < 2:
            portfolio_data = PortfolioMigrator._migrate_v1_to_v2(portfolio_data)
        portfolio_data["schema_version"] = PortfolioMigrator.CURRENT_VERSION
        return portfolio_data
```

### V1 to V2 migration

`_migrate_v1_to_v2` performs two changes on each plot config:

1. Adds `engine: "plotly"` via `setdefault` (preserving any explicit engine value).
2. Removes all keys starting with `export_`.

The method deep-copies the entire dict before mutating, so the caller's data is
never modified.

### Migration properties

- **Idempotent**: migrating an already-V2 portfolio is a no-op.
- **Forward-compatible**: unknown keys are preserved through migration.
- **Non-destructive**: uses `copy.deepcopy()` to avoid side effects.
- **Graceful**: missing `plots` key or empty plots lists are handled without error.

---

## Save Flow

When the user clicks "Save Portfolio" in the UI, the following sequence executes:

1. The portfolio page collects state from the `ApplicationAPI`:
   - `get_data()`, `get_plots()`, `get_config()`, `get_plot_counter()`,
     `get_csv_path()`, `get_parse_variables()`
2. Calls `api.data_services.save_portfolio(...)` with the collected state and the
   `_build_figure_spec` callback.
3. `DefaultDataServicesAPI` delegates to `PortfolioService.save_portfolio()`.
4. The service serializes each plot via `to_dict()`, optionally enriches it with
   `figure_spec`, serializes the DataFrame to CSV, reads parser and history state
   from the `StateManager`, and packages everything into a dict with envelope fields.
5. The dict is written to `<portfolios_dir>/<sanitized_name>.json`.
6. On success, a toast notification is displayed and the fragment reruns.

### What is serialized

| Category | Method | Format |
|----------|--------|--------|
| Primary DataFrame | `df.to_csv(index=False)` | CSV string |
| Per-plot processed data | `df.to_csv(index=False)` | CSV string |
| Plot configurations | `plot.to_dict()` | JSON dict |
| Plot pipelines | Direct | List of `PipelineStep` dicts |
| Legend mappings | Direct | `dict[str, str]` |
| Parser variables | Direct | List of `ParseVariableConfig` dicts |
| Operation history | Direct | List of `OperationRecord` dicts |
| Figure specs | `ConfigSpecBuilder.from_config().to_dict()` | `FigureConfig` dict |

### What is NOT serialized

Plotly `Figure` objects, `TraceBuildResult` caches, preview DataFrames, and
transient UI state (dialog flags, widget keys) are not included.  These are
regenerated on demand when the restored session is rendered.

---

## Load Flow

When the user selects a portfolio and clicks "Load Portfolio":

1. `api.data_services.load_portfolio(name)` delegates to `PortfolioService`.
2. The service reads the JSON file and passes it through `PortfolioMigrator.migrate()`.
3. The migrated `PortfolioData` is returned to the UI.
4. The UI calls `api.state_manager.restore_session(data)`, which delegates to
   `SessionRepository.restore_from_portfolio()`.

### Restoration sequence

`SessionRepository.restore_from_portfolio()` restores state across five repository
domains in a fixed order:

1. **Parser state** -- `parse_variables`, `stats_path`, `stats_pattern`,
   `scanned_variables`, `use_parser` are written to the `ParserStateRepository`.
2. **Config state** -- `csv_path` and `config` are written to the `ConfigRepository`.
3. **Data** -- the `data_csv` string is deserialized via
   `pd.read_csv(io.StringIO(data_csv))` and stored in the `DataRepository`.
   If the CSV is empty (config-only portfolio), data is left unset.
   If parsing fails, the error is logged and the session continues without data.
4. **Plots** -- each plot dict is deserialized via the injected `PlotDeserializer`
   callable (`PlotFactory.from_dict` in production).  Failed plots are logged and
   skipped.  The plot counter defaults to the count of successfully loaded plots
   if absent from the portfolio.
5. **History** -- `manager_history` and `portfolio_history` are written to the
   `HistoryRepository`.

After restoration, the UI calls `st.rerun(scope="app")` to force a full re-render
across all pages.

---

## Portfolio Page UI

### Entry point

`show_portfolio_page(api)` at `src/web/pages/portfolio.py` renders the page title and
description, then delegates the interactive content to a Streamlit fragment:

```python
st.fragment(_portfolio_fragment)(api)
```

The fragment can rerun independently during button clicks without reloading the outer
page shell.

### Layout

The page is divided into two columns and a management section:

| Section | Column | Contents |
|---------|--------|----------|
| Save Portfolio | Left | Text input for name (default `"my_portfolio"`), primary save button |
| Load Portfolio | Right | Selectbox listing available portfolios, primary load button |
| Manage Saved Portfolios | Full width | Expandable list of portfolios, each with a delete button |

The portfolio list is fetched once from `list_portfolios()` at the top of the
fragment and reused for both the load selectbox and the management section.

### Delete handling

Each portfolio is rendered inside an `st.expander`.  The delete button uses an
`on_click` callback with the portfolio name captured via a default argument to avoid
the Python closure-in-a-loop variable capture issue:

```python
def _delete_portfolio(name: str = pname) -> None:
    api.data_services.delete_portfolio(name)
    st.toast(f"Deleted {name}")
```

### Error handling

Both save and load are wrapped in `try/except Exception`.  Errors are shown to the
user via `st.exception(e)` and logged with `logger.error(..., exc_info=True)`.

---

## See Also

- [State Management](../core/state-management.md) -- repository architecture and
  `SessionRepository` details
- [API Reference: StateManager](../api-reference/state-manager.md) -- protocol
  definition for `restore_session()` and state getters
