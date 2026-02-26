---
title: "Architecture"
nav_order: 16
---

## Architecture Overview

RING-5 follows a **clean layered architecture** with strict separation of concerns, async-first design, and production-grade patterns.

## High-Level Architecture

```text

 Layer C: Presentation (Streamlit)
 • UI Components • Pages • State Management
 • Controllers / Presenters / Rendering

 ApplicationAPI


 Layer B: Domain (Business Logic)
 • Plotting • Transformations • Analysis
 • Visualization Models • NO UI imports • Testable




 Layer A: Data (Ingestion & Parsing)
 • File I/O • Perl parsers • Type mapping
 • Async workers • Pattern aggregation

```

## Visualization Pipeline (TraceBuildResult)

The visualization system uses a **trace-based pipeline** where plot types produce typed `TraceBuildResult` objects that are converted to engine-specific figures:

```text
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Plot Type   │───▶│  create_traces() │───▶│ TraceBuildResult  │
│  (bar, line) │    │  (typed traces)  │    │ (List[TraceConfig])│
└─────────────┘    └──────────────────┘    └───────┬──────────┘
                                                    │
                                          ┌─────────▼─────────┐
                                          │  EngineManager     │
                                          │  (dispatch)        │
                                          └──┬──────────────┬──┘
                                             │              │
                                   ┌─────────▼──┐   ┌──────▼────────┐
                                   │  Plotly     │   │  Matplotlib   │
                                   │  Connector  │   │  Connector    │
                                   └─────────┬──┘   └──────┬────────┘
                                             │              │
                                   ┌─────────▼──┐   ┌──────▼────────┐
                                   │  go.Figure  │   │  mpl.Figure   │
                                   └────────────┘   └───────────────┘
```

**Key components**:

- **TraceBuildResult**: Typed model containing traces, barmode, annotations, shapes. Lives in `src/core/models/visualization/`.
- **TraceConfig**: Per-trace typed configuration (name, x, y, trace_type, color, etc.).
- **EngineManager**: Dispatches to the active engine's connector.
- **Connectors**: Engine-specific renderers in `src/web/rendering/` that translate traces into Plotly/Matplotlib API calls.
- **FigureConfig**: Immutable configuration for typography, axes, legend, margins. Lives in `src/core/models/visualization/`.

## Design Principles

### 1. Layered Architecture

**Layer A (Data)**: File ingestion and parsing

- Parse service and scanner service
- Perl parser integration
- Type mappers for simulator variables
- **NO** business logic

**Layer B (Domain)**: Business logic and analysis

- Statistical computations
- Plot generation
- Data transformations
- **NO** UI dependencies

**Layer C (Presentation)**: User interface

- Streamlit components
- State management
- User interactions
- **Calls** Layer B through ApplicationAPI

### 2. Async-First Design

All I/O-bound operations use `concurrent.futures`:

```python
# CORRECT: Async pattern
futures = service.submit_scan_async(path, pattern, limit=10)
results = [f.result() for f in futures]
data = service.finalize_scan(results)

# WRONG: Don't create sync wrappers
def scan_sync(path): # Anti-pattern
 futures = submit_scan_async(path)
 return [f.result() for f in futures]
```

**Key Rules**:

- Always use `submit_*_async()` + `finalize_*()` pattern
- Never block the UI thread
- Use WorkPool for parallel execution
- Handle timeouts gracefully

### 3. Design Patterns

**Factory Pattern** (Plots and Shapers):

```python
plot = PlotFactory.create_plot("bar", plot_id=1, name="My Plot")
shaper = ShaperFactory.create_shaper("normalize", config)
```

**Facade Pattern** (Backend Access):

```python
api = ApplicationAPI() # Single entry point
data = api.load_csv_file(path)
plot = api.create_plot("bar", config)
```

**Strategy Pattern** (Parsing):

```python
# Different strategies for different variable types
scalar_parser = get_parser("scalar")
vector_parser = get_parser("vector")
```

**Singleton** (Configuration and Pools):

```python
WorkPool.initialize(max_workers=8)
ConfigManager.load_config(path)
```

### 4. Type Safety

**Strict typing everywhere**:

```python
def process_data(
 input_file: Path,
 config: Dict[str, Any],
 timeout: int = 30
) -> pd.DataFrame:
 """Process simulation data from file."""
 result: pd.DataFrame = pd.read_csv(input_file)
 return result
```

**Type checking**:

- mypy in strict mode
- No implicit `Any`
- All function signatures typed
- TypedDict for structured data

### 5. Immutability

DataFrames are never modified in-place:

```python
# CORRECT: Return new DataFrame
result = data.drop(columns=['x'])
filtered = result[result['value'] > 0]

# WRONG: In-place modification
data.drop(columns=['x'], inplace=True) #
```

## Project Structure

```text
RING-5/
 src/
 core/ # Layer A+B: Data + Domain
 application_api.py # Facade (MAIN API)
 models/ # Data models
 visualization/ # FigureConfig, TraceConfig, palettes
 parsing_models.py
 plot_config.py
 plot_protocol.py
 state/ # State management
 repositories/ # Plot, data, config, visualization repos
 state_manager.py
 services/ # Business logic
 managers/
 data_services/
 shapers/
 parsing/ # Simulator parsing (multi-backend)
 parser_protocol.py # SimulationParser protocol
 registry.py # SimulatorRegistry
 csv_contract.py # Re-export shim (canonical: core/models/csv_contract.py)
 gem5/ # gem5 implementation
 web/ # Layer C: Presentation
 models/ # UI TypedDicts + Protocols
 controllers/ # Orchestration (MVC)
 plot/
 presenters/ # Widget rendering (MVC)
 plot/
 rendering/ # Engine connectors + widgets
 plotly_connector.py
 matplotlib_connector.py
 engine_manager.py
 trace_to_plotly.py
 widgets/
 state/ # UI state manager
 pages/ # Streamlit pages
 ui/ # Plot types, styles, components
 plotting/
 types/
 styles/
 tests/
 unit/ # Unit tests
 integration/ # Integration tests
 data/ # Test fixtures
```

## Data Flow

### Parsing Workflow

```text
1. User selects stats directory
 ↓
2. Scanner discovers variables (async)
 • Scans multiple files in parallel
 • Detects variable types
 • Aggregates patterns (cpu0, cpu1 → cpu\d+)
 ↓
3. User selects variables to parse
 ↓
4. Parser extracts data (async)
 • Calls appropriate Perl parser per type
 • Processes files in parallel
 • Consolidates into CSVs
 ↓
5. Data loaded into memory
 • CSV pool management
 • Efficient caching
 ↓
6. Ready for analysis and visualization
```

### Transformation Pipeline

```text
Raw Data
 ↓
ColumnSelector: Keep relevant columns
 ↓
Filter: Remove unwanted rows
 ↓
Normalize: Divide by baseline
 ↓
Aggregate: Group and compute means
 ↓
Rename: Clean column names
 ↓
Sort: Order rows
 ↓
Transformed Data → Ready for plotting
```

### Plotting Workflow

```text
Transformed Data + Plot Config
 ↓
PlotFactory.create_plot(type, id, name)
 ↓
Concrete Plot Class (BarPlot, LinePlot, etc.)
 ↓
create_traces(data, config) → TraceBuildResult
 ↓
traces_to_plotly(result) → go.Figure
 ↓
apply_common_layout(fig, config) → styled Figure
 ↓
ChartPresenter.render_chart(fig)
 ↓
Display in UI or Export
```

## Key Components

### ApplicationAPI

**Single entry point** to all backend functionality:

```python
class ApplicationAPI:
 # Scanning
 def submit_scan_async(...)
 def finalize_scan(...)

 # Parsing
 def submit_parse_async(...)
 def finalize_parsing(...)

 # Data Access
 def load_csv_file(...)
 def apply_shapers(...)

 # Plotting
 def create_plot(...)

 # Visualization Config
 def get_visualization_config(...)
 def set_visualization_config(...)
```

### StateManager

**Manages Streamlit session state**:

- Scanned variables
- Selected variables
- Loaded data
- Plot configurations
- Portfolio settings

### WorkPool

**Manages concurrent execution**:

- Fixed thread pool
- Task submission
- Result collection
- Error handling

### ShaperFactory

**Creates data transformers**:

- Column selector
- Filter
- Normalize
- Aggregate
- Rename
- Sort
- Custom shapers

## Testing Strategy

### Unit Tests

- Pure functions tested in isolation
- Mock external dependencies
- Fast execution (<1s per test)

### Integration Tests

- Multi-component workflows
- Real data parsing
- Database interactions

### End-to-End Tests

- Full user workflows
- UI interactions (planned)
- Browser automation (planned)

**Coverage**: 77% (target: 85%)

## Performance Considerations

### Async Parsing

- Parallel file processing
- Non-blocking I/O
- Progress reporting

### Memory Management

- CSV pooling
- Lazy loading
- Garbage collection hints

### Caching

- Scanned variable cache
- Compiled regex patterns
- Plot layout templates

## Error Handling

### Fail Fast

```python
if not stats_path.exists():
 raise FileNotFoundError(f"Path not found: {stats_path}")
```

### User-Friendly Messages

```python
try:
 data = parse_file(path)
except ParseError as e:
 st.error(f"Failed to parse {path.name}: {e}")
 logger.error(f"Parse error: {e}", exc_info=True)
```

### Graceful Degradation

```python
# Continue with other files if one fails
for future in futures:
 try:
 result = future.result(timeout=30)
 results.append(result)
 except Exception as e:
 logger.warning(f"Task failed: {e}")
 # Continue processing other files
```

## Extension Points

### Adding New Plot Types

1. Create class inheriting `BasePlot`
2. Implement `create_traces()` returning `TraceBuildResult`
3. Register in `PlotFactory`
4. Add UI configuration

See [Adding Plot Types](Adding-Plot-Types.md)

### Adding New Shapers

1. Create class with `transform()` method
2. Register in `ShaperFactory`
3. Add UI controls

See [Adding Shapers](Adding-Shapers.md)

### Adding New Variable Types

1. Create Perl parser script
2. Add to `TypeMapper`
3. Update scanner logic
4. Add tests

See [API Reference](api/) for details

## Best Practices

### DO

- Follow layered architecture
- Use async patterns
- Write tests first (TDD)
- Type all functions
- Return new DataFrames
- Handle errors gracefully
- Document public APIs

### DON'T

- Mix UI and business logic
- Create sync wrappers for async APIs
- Modify DataFrames in-place
- Use bare `except` clauses
- Forget type hints
- Skip tests
- Leave TODOs in production code

## Related Documentation

- [Development Setup](Development-Setup.md)
- [Testing Guide](Testing-Guide.md)
- [API Reference](api/)
- [Contributing](../CONTRIBUTING.md)

**Next**: [Development Setup](Development-Setup.md) to start building with this architecture.
