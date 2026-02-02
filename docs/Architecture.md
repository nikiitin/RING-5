# Architecture Overview

RING-5 follows a **clean layered architecture** with strict separation of concerns, async-first design, and production-grade patterns.

## High-Level Architecture

```text

 Layer C: Presentation (Streamlit)
 • UI Components • Pages • State Management

 BackendFacade


 Layer B: Domain (Business Logic)
 • Plotting • Transformations • Analysis
 • NO UI imports • Pure functions • Testable




 Layer A: Data (Ingestion & Parsing)
 • File I/O • Perl parsers • Type mapping
 • Async workers • Pattern aggregation

```

## Design Principles

### 1. Layered Architecture

**Layer A (Data)**: File ingestion and parsing

- Parse service and scanner service
- Perl parser integration
- Type mappers for gem5 variables
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
- **Calls** Layer B through BackendFacade

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
facade = BackendFacade() # Single entry point
data = facade.load_csv_file(path)
plot = facade.create_plot("bar", config)
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
 """Process gem5 data from file."""
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
 core/ # Shared utilities
 benchmark.py # Benchmark handling
 performance.py # Performance metrics
 parsers/ # Layer A: Data ingestion
 parser.py # Main parser
 scanner.py # Variable scanner
 parse_service.py # Async orchestration
 scanner_service.py # Async scanning
 type_mapper.py # Type detection
 pattern_aggregator.py # Pattern consolidation
 perl/ # Perl parser scripts
 workers/ # Async task workers
 plotting/ # Layer B/C: Visualization
 base_plot.py # Abstract base
 plot_factory.py # Factory
 plot_renderer.py # Rendering
 export.py # Export utilities
 types/ # Concrete plots
 bar_plot.py
 line_plot.py
 scatter_plot.py
 grouped_bar_plot.py
 grouped_stacked_bar_plot.py
 histogram_plot.py
 config/ # Configuration management
 config_manager.py
 schemas/ # JSON schemas
 web/ # Layer C: UI
 facade.py # Backend facade (MAIN API)
 state_manager.py # Session state
 services/ # UI services
 csv_pool.py
 variable_service.py
 shapers/ # Data transformations
 repositories/ # Data access
 ui/ # Streamlit components
 components/ # Reusable widgets
 pages/ # App pages
 tests/
 unit/ # Unit tests
 integration/ # Integration tests
 e2e/ # End-to-end tests
 data/ # Test fixtures
 .agent/ # AI agent configuration
 rules/ # Project rules
 workflows/ # Development workflows
 skills/ # Reusable knowledge
 docs/ # Documentation (you are here!)
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
create_figure(data, config) → go.Figure
 ↓
PlotRenderer.render(figure)
 ↓
Display in UI or Export
```

## Key Components

### BackendFacade

**Single entry point** to all backend functionality:

```python
class BackendFacade:
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
 def render_plot(...)
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
2. Implement `create_figure()`
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
- [Code Style](Code-Style.md)

**Next**: [Development Setup](Development-Setup.md) to start building with this architecture.
