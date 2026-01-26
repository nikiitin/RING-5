# RING-5 Architecture Improvement Plan
## Comprehensive Code Quality & Design Enhancement Strategy

**Date**: January 26, 2026  
**Objective**: Transform RING-5 into a bulletproof, publication-quality scientific data analysis tool  
**Scope**: Type safety, architecture, SOLID principles, design patterns, performance, maintainability

---

## Executive Summary

**Current State**:
- ✅ 457/457 tests passing
- ⚠️ 167 mypy strict errors remaining
- ⚠️ Architectural debt in several areas
- ⚠️ Inconsistent abstraction levels
- ⚠️ Mixed concerns in some modules

**Target State**:
- 🎯 0 mypy strict errors
- 🎯 Clean Architecture with clear boundaries
- 🎯 SOLID principles throughout
- 🎯 Production-grade error handling
- 🎯 Comprehensive documentation
- 🎯 Performance optimizations

---

## Phase 1: Type Safety Foundation (Priority: CRITICAL)
**Estimated Effort**: 8-12 hours  
**Impact**: High - Prevents runtime errors, enables IDE autocomplete

### 1.1 Critical Files (Top 10 by Error Count)
```
Priority 1 (Must Fix First):
├── src/web/ui/components/variable_editor.py         (14 errors) - User-facing UI
├── src/core/multiprocessing/pool.py                 (13 errors) - Core async infrastructure
├── src/web/ui/components/plot_manager_components.py (10 errors) - Plot orchestration
├── src/web/ui/components/data_source_components.py  (10 errors) - Data loading
└── src/web/services/shapers/multiprocessing/        (10 errors) - Data transformation

Priority 2 (High Impact):
├── src/plotting/types/grouped_stacked_bar_plot.py   (9 errors)  - Complex plotting
├── src/plotting/styles/colors.py                    (7 errors)  - Shared utilities
├── src/parsers/types/distribution.py                (7 errors)  - gem5 parsing
├── src/plotting/styles/base_ui.py                   (6 errors)  - UI components
└── src/plotting/styles/applicator.py                (6 errors)  - Style engine
```

### 1.2 Systematic Fixes by Error Type

#### A. Missing Type Annotations (`no-untyped-def`)
**Problem**: Functions without parameter/return type hints  
**Fix Strategy**:
```python
# BEFORE
def process_data(data):
    return data.mean()

# AFTER
def process_data(data: pd.DataFrame) -> pd.Series:
    """Calculate mean across DataFrame columns."""
    return data.mean()
```
**Files**: 40+ functions across codebase

#### B. Any Return Issues (`no-any-return`)
**Problem**: Functions returning untyped external library results  
**Fix Strategy**:
```python
# BEFORE
def get_colors() -> List[str]:
    return px.colors.qualitative.Plotly  # Returns Any

# AFTER
def get_colors() -> List[str]:
    colors: List[str] = list(px.colors.qualitative.Plotly)
    return colors
```
**Files**: All plotly/streamlit interactions

#### C. Type Parameter Issues (`type-arg`)
**Problem**: Generic types without parameters  
**Fix Strategy**:
```python
# BEFORE
def create_tuple() -> tuple:
    return (1, 2, 3)

# AFTER
def create_tuple() -> Tuple[int, int, int]:
    return (1, 2, 3)
```
**Files**: 15+ occurrences

#### D. List Item Incompatibility (`list-item`)
**Problem**: Mixing None with expected types  
**Fix Strategy**:
```python
# BEFORE
items = [config.get("x"), "default"]  # x might be None

# AFTER
x_value = config.get("x")
items = [x_value if x_value is not None else "default", "default"]
```
**Files**: Plot configuration modules

---

## Phase 2: Architectural Improvements (Priority: HIGH)
**Estimated Effort**: 12-16 hours  
**Impact**: Very High - Maintainability, extensibility, team scalability

### 2.1 Separation of Concerns Violations

#### Issue 1: UI Logic Mixed with Business Logic
**Location**: `src/web/ui/components/variable_editor.py`  
**Problem**: Direct session state manipulation in UI components  
**Current**:
```python
def render_variable_editor():
    variables = st.session_state['parse_variables']  # Tight coupling
    # ... render logic mixed with state management
```

**Proposed Architecture**:
```
┌─────────────────────────────────────────┐
│ UI Layer (Streamlit Components)        │
│ - Render functions only                 │
│ - No business logic                     │
│ - Delegate to services                  │
└────────────┬────────────────────────────┘
             │
             ↓ Uses
┌─────────────────────────────────────────┐
│ Service Layer (Business Logic)         │
│ - VariableEditorService                │
│ - Validates data                        │
│ - Coordinates state changes             │
└────────────┬────────────────────────────┘
             │
             ↓ Uses
┌─────────────────────────────────────────┐
│ State Layer (StateManager)              │
│ - Pure data access                      │
│ - No business logic                     │
└─────────────────────────────────────────┘
```

**Implementation**:
```python
# NEW: src/web/services/variable_editor_service.py
class VariableEditorService:
    """Business logic for variable editing."""
    
    @staticmethod
    def add_variable(name: str, var_type: str) -> bool:
        """
        Add a variable with validation.
        Returns True if successful, False otherwise.
        """
        # Validation
        if not name or not var_type:
            return False
        
        # Business logic
        variables = StateManager.get_parse_variables()
        if any(v["name"] == name for v in variables):
            return False  # Duplicate
        
        # State update
        variables.append({"name": name, "type": var_type, "_id": str(uuid.uuid4())})
        StateManager.set_parse_variables(variables)
        return True

# REFACTORED: src/web/ui/components/variable_editor.py
def render_variable_editor():
    """Pure UI rendering - delegates to service."""
    with st.form("add_variable"):
        name = st.text_input("Variable Name")
        var_type = st.selectbox("Type", ["scalar", "vector", "..."])
        
        if st.form_submit_button("Add"):
            if VariableEditorService.add_variable(name, var_type):
                st.success("Variable added!")
            else:
                st.error("Invalid or duplicate variable")
```

**Benefits**:
- ✅ Testable business logic (no Streamlit dependency)
- ✅ Reusable across different UIs
- ✅ Clear responsibilities
- ✅ Easy to mock for testing

#### Issue 2: God Classes
**Location**: `src/web/state_manager.py`  
**Problem**: StateManager has 40+ methods, managing too many concerns  
**Proposed Refactoring**:

```
Current:
StateManager (40+ methods)
├── Data management
├── Configuration
├── Parser state
├── CSV pool
├── Plot orchestration
├── Session restoration
└── Widget cleanup

Proposed:
StateManager (Core)
├── DataStateManager (data, processed_data)
├── ConfigStateManager (config, parse_variables)
├── CsvPoolStateManager (csv_pool, saved_configs)
├── PlotStateManager (plots, plot_counter)
└── SessionStateManager (restore, clear)
```

**Implementation**:
```python
# NEW: src/web/state/data_state.py
class DataStateManager:
    """Manages data-related state only."""
    
    KEY_DATA = "data"
    KEY_PROCESSED = "processed_data"
    
    @staticmethod
    def get_data() -> Optional[pd.DataFrame]:
        """Get raw data."""
        return cast(Optional[pd.DataFrame], st.session_state.get(DataStateManager.KEY_DATA))
    
    @staticmethod
    def set_data(data: Optional[pd.DataFrame]) -> None:
        """Set raw data with validation."""
        if data is not None and data.empty:
            raise ValueError("Cannot set empty DataFrame")
        st.session_state[DataStateManager.KEY_DATA] = data

# Facade for backward compatibility
class StateManager:
    """Facade delegating to specialized state managers."""
    data = DataStateManager
    config = ConfigStateManager
    plots = PlotStateManager
    # etc.
```

### 2.2 Design Pattern Improvements

#### Pattern 1: Strategy Pattern for Shapers
**Current State**: Working correctly  
**Enhancement**: Add builder pattern for complex pipelines

```python
# NEW: src/web/services/shapers/shaper_pipeline_builder.py
class ShaperPipelineBuilder:
    """Fluent builder for shaper pipelines."""
    
    def __init__(self) -> None:
        self._shapers: List[Shaper] = []
    
    def add_column_selector(self, columns: List[str]) -> 'ShaperPipelineBuilder':
        """Add column selection step."""
        self._shapers.append(
            ShaperFactory.create_shaper("columnSelector", {"columns": columns})
        )
        return self
    
    def add_normalizer(self, baseline: Dict[str, str]) -> 'ShaperPipelineBuilder':
        """Add normalization step."""
        self._shapers.append(
            ShaperFactory.create_shaper("normalize", {"baseline": baseline})
        )
        return self
    
    def build(self) -> List[Shaper]:
        """Build the pipeline."""
        return self._shapers.copy()

# Usage
pipeline = (ShaperPipelineBuilder()
    .add_column_selector(["ipc", "runtime"])
    .add_normalizer({"config": "baseline"})
    .build())
```

#### Pattern 2: Observer Pattern for State Changes
**Problem**: UI doesn't reactively update when state changes outside Streamlit  
**Proposed**:

```python
# NEW: src/web/state/state_observer.py
from typing import Callable, Dict, List, Protocol

class StateObserver(Protocol):
    """Observer for state changes."""
    def on_state_change(self, key: str, old_value: Any, new_value: Any) -> None:
        ...

class ObservableStateManager:
    """State manager with observer pattern."""
    
    _observers: Dict[str, List[StateObserver]] = {}
    
    @classmethod
    def register_observer(cls, key: str, observer: StateObserver) -> None:
        """Register an observer for a state key."""
        if key not in cls._observers:
            cls._observers[key] = []
        cls._observers[key].append(observer)
    
    @classmethod
    def _notify(cls, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all observers of a change."""
        for observer in cls._observers.get(key, []):
            observer.on_state_change(key, old_value, new_value)
    
    @classmethod
    def set_data(cls, data: Optional[pd.DataFrame]) -> None:
        """Set data and notify observers."""
        old_value = cls.get_data()
        st.session_state[cls.DATA] = data
        cls._notify(cls.DATA, old_value, data)
```

#### Pattern 3: Command Pattern for Undo/Redo
**Use Case**: User wants to undo shaper application  
**Proposed**:

```python
# NEW: src/web/services/commands/base_command.py
from abc import ABC, abstractmethod

class Command(ABC):
    """Base command for undoable operations."""
    
    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass
    
    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass

# NEW: src/web/services/commands/apply_shaper_command.py
class ApplyShaperCommand(Command):
    """Command to apply a shaper with undo support."""
    
    def __init__(self, shaper: Shaper, plot_id: int) -> None:
        self.shaper = shaper
        self.plot_id = plot_id
        self.previous_data: Optional[pd.DataFrame] = None
    
    def execute(self) -> None:
        """Apply shaper and save previous state."""
        plot = StateManager.plots.get_plot_by_id(self.plot_id)
        self.previous_data = plot.processed_data.copy()
        plot.processed_data = self.shaper(plot.processed_data)
    
    def undo(self) -> None:
        """Restore previous state."""
        if self.previous_data is not None:
            plot = StateManager.plots.get_plot_by_id(self.plot_id)
            plot.processed_data = self.previous_data

# NEW: src/web/services/commands/command_manager.py
class CommandManager:
    """Manages command history for undo/redo."""
    
    def __init__(self) -> None:
        self._history: List[Command] = []
        self._position: int = -1
    
    def execute(self, command: Command) -> None:
        """Execute command and add to history."""
        command.execute()
        # Clear redo history
        self._history = self._history[:self._position + 1]
        self._history.append(command)
        self._position += 1
    
    def undo(self) -> bool:
        """Undo last command. Returns False if nothing to undo."""
        if self._position < 0:
            return False
        self._history[self._position].undo()
        self._position -= 1
        return True
    
    def redo(self) -> bool:
        """Redo next command. Returns False if nothing to redo."""
        if self._position >= len(self._history) - 1:
            return False
        self._position += 1
        self._history[self._position].execute()
        return True
```

### 2.3 SOLID Principles Enforcement

#### Single Responsibility Principle (SRP)
**Violations Found**:
1. `BackendFacade` - Does too much (parsing, scanning, shapers, CSV loading, config)
2. `BasePlot` - Mixes plotting logic with UI rendering
3. `StyleManager` - Handles both style application AND UI rendering

**Fix Plan**:
```
BackendFacade (Current: 15+ responsibilities)
↓ Split into:
├── ParsingFacade (scan, parse operations)
├── DataFacade (CSV loading, shaper application)
├── ConfigFacade (save/load configurations)
└── PortfolioFacade (portfolio operations)
```

#### Open/Closed Principle (OCP)
**Violations Found**:
1. Adding new plot types requires modifying PlotFactory
2. Adding new variable types requires modifying TypeMapper

**Fix Plan**:
```python
# CURRENT: Modification required
class PlotFactory:
    _plot_classes = {
        "bar": BarPlot,
        "line": LinePlot,
        # Adding new type requires editing this dict
    }

# PROPOSED: Plugin system
class PlotFactory:
    _plot_classes: Dict[str, Type[BasePlot]] = {}
    
    @classmethod
    def auto_discover_plots(cls) -> None:
        """Auto-discover plot types from src/plotting/types/."""
        for module in pkgutil.iter_modules([plotting_types_path]):
            # Auto-register @plot_type decorated classes
            ...
    
# Usage in plot implementation
@plot_type("heatmap")  # Auto-registers
class HeatmapPlot(BasePlot):
    ...
```

#### Liskov Substitution Principle (LSP)
**Potential Violations**:
1. Shapers with different preconditions
2. Plot types with incompatible render_theme_options signatures

**Fix Plan**: Ensure all subclasses honor base class contracts

#### Interface Segregation Principle (ISP)
**Violations Found**:
1. BasePlot forces all plots to implement theme_options even if not needed

**Fix Plan**:
```python
# Split into smaller interfaces
class IPlot(Protocol):
    """Core plotting interface."""
    def create_figure(self, data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        ...

class IConfigurable(Protocol):
    """Plots that support configuration UI."""
    def render_config_ui(self, data: pd.DataFrame, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        ...

class IThemeable(Protocol):
    """Plots that support theming."""
    def render_theme_options(self, saved_config: Dict[str, Any]) -> Dict[str, Any]:
        ...

# Plots implement only what they need
class SimplePlot(IPlot, IConfigurable):
    """Simple plot without theming."""
    ...

class AdvancedPlot(IPlot, IConfigurable, IThemeable):
    """Full-featured plot."""
    ...
```

#### Dependency Inversion Principle (DIP)
**Violations Found**:
1. High-level modules depend on low-level Streamlit directly
2. Services depend on concrete StateManager instead of abstraction

**Fix Plan**:
```python
# Define abstractions
class IStateStore(Protocol):
    """Abstract state storage."""
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...

class IDataService(Protocol):
    """Abstract data operations."""
    def load_csv(self, path: str) -> pd.DataFrame: ...
    def apply_shapers(self, data: pd.DataFrame, shapers: List[Shaper]) -> pd.DataFrame: ...

# Implementations
class StreamlitStateStore(IStateStore):
    """Streamlit-specific implementation."""
    def get(self, key: str) -> Any:
        return st.session_state.get(key)

class InMemoryStateStore(IStateStore):
    """In-memory implementation for testing."""
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
    
    def get(self, key: str) -> Any:
        return self._store.get(key)

# Dependency injection
class PlotManager:
    def __init__(self, state_store: IStateStore, data_service: IDataService) -> None:
        self.state = state_store
        self.data = data_service
    
    def create_plot(self, plot_type: str) -> BasePlot:
        """No direct Streamlit dependency!"""
        data = self.data.load_csv(self.state.get("csv_path"))
        ...
```

---

## Phase 3: Error Handling & Resilience (Priority: MEDIUM)
**Estimated Effort**: 4-6 hours  
**Impact**: Medium - Production reliability

### 3.1 Current Issues
1. **Silent failures**: Many functions return None on error
2. **Bare except**: Some places catch Exception without logging
3. **No error recovery**: UI crashes require refresh

### 3.2 Proposed Error Strategy

#### A. Custom Exception Hierarchy
```python
# NEW: src/core/exceptions.py
class Ring5Error(Exception):
    """Base exception for all RING-5 errors."""
    pass

class DataError(Ring5Error):
    """Data-related errors (invalid CSV, missing columns)."""
    pass

class ParsingError(Ring5Error):
    """gem5 parsing errors."""
    pass

class ConfigurationError(Ring5Error):
    """Configuration validation errors."""
    pass

class ValidationError(Ring5Error):
    """Input validation errors."""
    pass

# Usage
def load_csv(path: str) -> pd.DataFrame:
    """Load CSV with proper error handling."""
    if not Path(path).exists():
        raise DataError(f"CSV file not found: {path}")
    
    try:
        df = pd.read_csv(path)
        if df.empty:
            raise DataError(f"CSV file is empty: {path}")
        return df
    except pd.errors.ParserError as e:
        raise DataError(f"Invalid CSV format: {e}") from e
```

#### B. Result Type Pattern
```python
# NEW: src/core/result.py
from typing import Generic, TypeVar, Union

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

class Result(Generic[T, E]):
    """Result type for operations that can fail."""
    
    def __init__(self, value: Optional[T] = None, error: Optional[E] = None) -> None:
        self._value = value
        self._error = error
    
    @property
    def is_ok(self) -> bool:
        return self._error is None
    
    @property
    def is_err(self) -> bool:
        return self._error is not None
    
    def unwrap(self) -> T:
        """Get value or raise error."""
        if self._error:
            raise self._error
        assert self._value is not None
        return self._value
    
    def unwrap_or(self, default: T) -> T:
        """Get value or default."""
        return self._value if self.is_ok else default

# Usage
def parse_gem5_stats(path: str) -> Result[pd.DataFrame, ParsingError]:
    """Parse gem5 stats with Result type."""
    try:
        data = _do_parsing(path)
        return Result(value=data)
    except Exception as e:
        return Result(error=ParsingError(f"Parsing failed: {e}"))

# In UI
result = parse_gem5_stats(stats_path)
if result.is_ok:
    st.success("Parsed successfully!")
    data = result.unwrap()
else:
    st.error(f"Parsing failed: {result._error}")
```

#### C. Error Recovery UI
```python
# NEW: src/web/ui/components/error_boundary.py
def error_boundary(func: Callable[[], None]) -> None:
    """Wraps UI components with error recovery."""
    try:
        func()
    except Ring5Error as e:
        st.error(f"❌ {type(e).__name__}: {e}")
        if st.button("Retry"):
            st.rerun()
    except Exception as e:
        logger.exception("Unexpected error in UI component")
        st.error("❌ Unexpected error occurred. Please report this bug.")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        if st.button("Reset Application"):
            StateManager.clear_all()
            st.rerun()

# Usage
def show_data_source_page():
    error_boundary(lambda: _render_data_source_ui())
```

---

## Phase 4: Performance Optimization (Priority: LOW)
**Estimated Effort**: 6-8 hours  
**Impact**: Medium - User experience for large datasets

### 4.1 Identified Bottlenecks
1. **Synchronous CSV loading**: Blocks UI for large files
2. **DataFrame copies**: Excessive memory usage
3. **No caching**: Recomputes same data multiple times

### 4.2 Optimization Strategies

#### A. Async Data Loading
```python
# NEW: src/web/services/async_data_loader.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

class AsyncDataLoader:
    """Async data loading with progress."""
    
    _executor = ThreadPoolExecutor(max_workers=4)
    
    @classmethod
    async def load_csv_async(cls, path: str, progress_callback: Optional[Callable[[float], None]] = None) -> pd.DataFrame:
        """Load CSV asynchronously with progress updates."""
        loop = asyncio.get_event_loop()
        
        def _load() -> pd.DataFrame:
            # Chunked reading for large files
            chunks = []
            total_size = Path(path).stat().st_size
            bytes_read = 0
            
            for chunk in pd.read_csv(path, chunksize=10000):
                chunks.append(chunk)
                bytes_read += chunk.memory_usage(deep=True).sum()
                if progress_callback:
                    progress_callback(bytes_read / total_size)
            
            return pd.concat(chunks, ignore_index=True)
        
        return await loop.run_in_executor(cls._executor, _load)

# Usage in UI
async def load_data_with_progress(path: str) -> pd.DataFrame:
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    def update_progress(pct: float) -> None:
        progress_bar.progress(pct)
        status_text.text(f"Loading... {pct*100:.0f}%")
    
    data = await AsyncDataLoader.load_csv_async(path, update_progress)
    progress_bar.empty()
    status_text.empty()
    return data
```

#### B. Data Caching Strategy
```python
# NEW: src/core/cache.py
from functools import wraps
import hashlib
import pickle
from typing import Any, Callable, TypeVar

F = TypeVar('F', bound=Callable[..., Any])

def cache_result(ttl_seconds: Optional[int] = None) -> Callable[[F], F]:
    """Cache function results with optional TTL."""
    cache: Dict[str, Tuple[Any, float]] = {}
    
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create cache key from arguments
            key_data = pickle.dumps((args, kwargs))
            key = hashlib.md5(key_data).hexdigest()
            
            # Check cache
            if key in cache:
                result, timestamp = cache[key]
                if ttl_seconds is None or (time.time() - timestamp) < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        
        return wrapper  # type: ignore
    return decorator

# Usage
@cache_result(ttl_seconds=300)  # 5 minute cache
def compute_statistics(data: pd.DataFrame) -> Dict[str, float]:
    """Expensive statistical computation."""
    return {
        "mean": data.mean().mean(),
        "std": data.std().mean(),
        # ...
    }
```

#### C. Lazy Loading for Plots
```python
# NEW: src/plotting/lazy_plot.py
class LazyPlot:
    """Lazy-loading plot that only renders when visible."""
    
    def __init__(self, plot: BasePlot) -> None:
        self.plot = plot
        self._figure: Optional[go.Figure] = None
        self._rendered = False
    
    @property
    def figure(self) -> go.Figure:
        """Generate figure on first access."""
        if not self._rendered:
            logger.info(f"Lazy-generating figure for {self.plot.name}")
            self._figure = self.plot.generate_figure()
            self._rendered = True
        assert self._figure is not None
        return self._figure
    
    def invalidate(self) -> None:
        """Invalidate cache, force regeneration."""
        self._rendered = False
        self._figure = None
```

---

## Phase 5: Testing & Documentation (Priority: HIGH)
**Estimated Effort**: 8-10 hours  
**Impact**: Very High - Long-term maintainability

### 5.1 Test Coverage Improvements

#### A. Missing Test Categories
```
Current Coverage: ~70% (457 tests)
Gaps:
├── Error handling paths (edge cases)
├── Async operations (cancellation, timeout)
├── UI component integration
├── Performance tests (large datasets)
└── Security tests (input validation)
```

#### B. Proposed Test Structure
```python
tests/
├── unit/                    # Existing, good coverage
├── integration/             # Existing, good coverage
├── performance/             # NEW: Performance benchmarks
│   ├── test_csv_loading_speed.py
│   ├── test_shaper_pipeline_perf.py
│   └── test_plot_rendering_time.py
├── security/                # NEW: Security tests
│   ├── test_input_validation.py
│   ├── test_path_traversal.py
│   └── test_code_injection.py
├── resilience/              # NEW: Error recovery tests
│   ├── test_malformed_csv.py
│   ├── test_corrupt_stats.py
│   └── test_network_failures.py
└── contract/                # NEW: API contract tests
    ├── test_shaper_contracts.py
    ├── test_plot_contracts.py
    └── test_state_contracts.py
```

#### C. Property-Based Testing
```python
# NEW: tests/property/test_shaper_properties.py
from hypothesis import given, strategies as st

@given(
    data=st.data_frames(
        columns=[
            st.column('x', dtype=float),
            st.column('y', dtype=float),
        ],
        rows=st.integers(min_value=1, max_value=1000)
    )
)
def test_shaper_preserves_row_count(data: pd.DataFrame) -> None:
    """Property: Column selector should preserve row count."""
    shaper = ColumnSelector({"columns": ["x"]})
    result = shaper(data)
    assert len(result) == len(data)

@given(
    data=st.data_frames([st.column('value', dtype=float)]),
    baseline=st.floats(min_value=0.1, max_value=100.0)
)
def test_normalizer_scales_correctly(data: pd.DataFrame, baseline: float) -> None:
    """Property: Normalizer should scale values proportionally."""
    data['baseline'] = baseline
    normalizer = Normalize({"baseline": {"baseline": baseline}, "columns": ["value"]})
    result = normalizer(data)
    
    # Property: normalized baseline should be 1.0
    baseline_normalized = result[result['baseline'] == baseline]['value_normalized'].iloc[0]
    assert abs(baseline_normalized - 1.0) < 0.001
```

### 5.2 Documentation Standards

#### A. Module Documentation Template
```python
"""
Module: src/web/services/variable_editor_service.py

Purpose:
    Business logic for managing gem5 variable definitions in the parser configuration.
    Validates variable names, types, and handles duplicate detection.

Responsibilities:
    - Add/remove/update variable definitions
    - Validate variable configurations
    - Check for naming conflicts
    - Generate unique IDs for variables

Dependencies:
    - StateManager: For state persistence
    - TypeMapper: For variable type validation
    - Logger: For audit trail

Usage Example:
    >>> from src.web.services.variable_editor_service import VariableEditorService
    >>> 
    >>> # Add a scalar variable
    >>> success = VariableEditorService.add_variable("system.cpu.ipc", "scalar")
    >>> assert success
    >>> 
    >>> # Try adding duplicate (should fail)
    >>> success = VariableEditorService.add_variable("system.cpu.ipc", "scalar")
    >>> assert not success

Design Patterns:
    - Service Layer Pattern: Separates business logic from UI
    - Validation Pattern: Ensures data integrity before state changes

Performance Characteristics:
    - O(n) duplicate check where n = number of existing variables
    - Typical: <1ms for <100 variables

Error Handling:
    - Returns False on validation failures (doesn't raise)
    - Logs warnings for suspicious operations
    - Never modifies state on validation failure

Thread Safety:
    - Not thread-safe (relies on Streamlit's single-thread model)
    - If used in multi-threaded context, wrap with locks

Testing:
    - Unit tests: tests/unit/test_variable_editor_service.py
    - Integration tests: tests/integration/test_variable_workflow.py

Version: 2.0.0
Author: RING-5 Team
Last Modified: 2026-01-26
"""
```

#### B. Function Documentation Template
```python
def apply_shaper_pipeline(
    data: pd.DataFrame, 
    pipeline: List[Shaper],
    validate: bool = True
) -> Result[pd.DataFrame, DataError]:
    """
    Apply a sequence of data shapers to a DataFrame.
    
    This function processes data through a transformation pipeline,
    applying each shaper in sequence. Each shaper receives the output
    of the previous shaper.
    
    Args:
        data: Input DataFrame to transform. Must not be empty.
        pipeline: Ordered list of Shaper instances to apply.
                  Empty pipeline returns data unchanged.
        validate: If True, validates preconditions before each shaper.
                  Set to False for performance in trusted pipelines.
    
    Returns:
        Result containing transformed DataFrame on success, or DataError on failure.
        
        Success Example:
            Result(value=pd.DataFrame(...), error=None)
        
        Error Example:
            Result(value=None, error=DataError("Missing required column: 'x'"))
    
    Raises:
        ValueError: If data is None (programming error, not user error)
    
    Performance:
        - Time Complexity: O(n * p) where n=rows, p=pipeline length
        - Space Complexity: O(n) (creates DataFrame copy per shaper)
        - Typical Performance: 100ms for 10k rows, 5 shapers
    
    Thread Safety:
        Thread-safe. Each call works on independent DataFrame copies.
    
    Example:
        >>> data = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        >>> pipeline = [
        ...     ColumnSelector({"columns": ["x"]}),
        ...     Normalize({"baseline": {"x": 1}, "columns": ["x"]})
        ... ]
        >>> result = apply_shaper_pipeline(data, pipeline)
        >>> assert result.is_ok
        >>> transformed = result.unwrap()
        >>> print(transformed)
           x  x_normalized
        0  1          1.0
        1  2          2.0
        2  3          3.0
    
    See Also:
        - ShaperFactory: For creating shapers
        - Shaper: Base class interface
        - tests/integration/test_shaper_pipeline.py: Integration tests
    
    Version: 2.0.0
    Since: 1.0.0
    """
    if data is None:
        raise ValueError("Data cannot be None. Use Result type for expected failures.")
    
    if data.empty:
        return Result(error=DataError("Cannot process empty DataFrame"))
    
    result = data.copy()
    
    for i, shaper in enumerate(pipeline):
        try:
            if validate:
                shaper._verify_preconditions(result)
            result = shaper(result)
        except Exception as e:
            error_msg = f"Shaper {i} ({shaper.__class__.__name__}) failed: {e}"
            logger.error(error_msg)
            return Result(error=DataError(error_msg))
    
    return Result(value=result)
```

---

## Phase 6: Code Quality Metrics & CI/CD (Priority: MEDIUM)
**Estimated Effort**: 4-6 hours  
**Impact**: High - Prevents regression

### 6.1 Automated Quality Checks

#### A. Pre-commit Hooks
```yaml
# NEW: .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: ['--maxkb=1000']
  
  - repo: https://github.com/psf/black
    rev: 24.1.1
    hooks:
      - id: black
        language_version: python3.12
  
  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203,W503']
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--strict, --config-file=mypy.ini]
        additional_dependencies: [pandas-stubs, types-jsonschema]
  
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        args: [tests/, --tb=short]
        language: system
        pass_filenames: false
        always_run: true
```

#### B. GitHub Actions CI Pipeline
```yaml
# NEW: .github/workflows/quality-check.yml
name: Code Quality & Tests

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pandas-stubs types-jsonschema scipy-stubs
      
      - name: Type checking (mypy)
        run: mypy src/ --strict --config-file mypy.ini
      
      - name: Linting (flake8)
        run: flake8 src/ tests/ --max-line-length=100
      
      - name: Code formatting (black)
        run: black --check src/ tests/
      
      - name: Run tests with coverage
        run: |
          pytest tests/ --cov=src --cov-report=xml --cov-report=term
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
      
      - name: Security scan (bandit)
        run: bandit -r src/ -ll
      
      - name: Dependency audit
        run: pip-audit
```

### 6.2 Code Metrics Dashboard

#### A. Metrics to Track
```python
# NEW: scripts/code_metrics.py
"""
Generate code quality metrics report.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any

def get_metrics() -> Dict[str, Any]:
    """Collect various code metrics."""
    
    # Lines of code
    loc_result = subprocess.run(
        ["cloc", "src/", "--json"],
        capture_output=True,
        text=True
    )
    loc_data = json.loads(loc_result.stdout)
    
    # Cyclomatic complexity
    complexity_result = subprocess.run(
        ["radon", "cc", "src/", "-a", "-j"],
        capture_output=True,
        text=True
    )
    complexity_data = json.loads(complexity_result.stdout)
    
    # Test coverage
    coverage_result = subprocess.run(
        ["pytest", "--cov=src", "--cov-report=json"],
        capture_output=True
    )
    coverage_data = json.loads(Path("coverage.json").read_text())
    
    # Maintainability index
    mi_result = subprocess.run(
        ["radon", "mi", "src/", "-j"],
        capture_output=True,
        text=True
    )
    mi_data = json.loads(mi_result.stdout)
    
    return {
        "lines_of_code": loc_data["SUM"]["code"],
        "test_coverage": coverage_data["totals"]["percent_covered"],
        "avg_complexity": sum(complexity_data.values()) / len(complexity_data),
        "maintainability": sum(mi_data.values()) / len(mi_data),
        "num_tests": len([f for f in Path("tests/").rglob("test_*.py")]),
    }

# Target Thresholds
THRESHOLDS = {
    "test_coverage": 80.0,  # Minimum 80% coverage
    "avg_complexity": 10.0,  # Max average complexity
    "maintainability": 60.0,  # Min maintainability index
}
```

---

## Implementation Roadmap

### Sprint 1 (Week 1): Type Safety Foundation
**Goal**: Achieve 0 mypy errors  
**Tasks**:
- [ ] Fix top 10 files with most errors (70% of issues)
- [ ] Add type stubs for remaining untyped code
- [ ] Update mypy.ini with appropriate strictness
- [ ] Run full type check in CI

**Success Criteria**:
- ✅ `mypy src/ --strict` returns 0 errors
- ✅ All tests passing (457/457)
- ✅ No regression in functionality

### Sprint 2 (Week 2): Architectural Refactoring
**Goal**: Implement clean architecture patterns  
**Tasks**:
- [ ] Split StateManager into specialized managers
- [ ] Create service layer for UI components
- [ ] Implement dependency injection for testability
- [ ] Refactor BackendFacade into specialized facades

**Success Criteria**:
- ✅ Clear separation between layers
- ✅ All services testable without Streamlit
- ✅ No circular dependencies
- ✅ Tests still passing

### Sprint 3 (Week 3): Error Handling & Resilience
**Goal**: Production-grade error handling  
**Tasks**:
- [ ] Implement custom exception hierarchy
- [ ] Add Result type pattern
- [ ] Create error boundary UI components
- [ ] Add comprehensive error tests

**Success Criteria**:
- ✅ No bare except blocks
- ✅ All errors properly logged
- ✅ UI recovers gracefully from errors
- ✅ Error tests cover edge cases

### Sprint 4 (Week 4): Performance & Optimization
**Goal**: Handle large datasets efficiently  
**Tasks**:
- [ ] Implement async data loading
- [ ] Add result caching layer
- [ ] Optimize DataFrame operations
- [ ] Add performance benchmarks

**Success Criteria**:
- ✅ 10k row CSV loads in <2s
- ✅ Plot generation <500ms
- ✅ Memory usage <500MB for 100k rows

### Sprint 5 (Week 5): Testing & Documentation
**Goal**: Comprehensive coverage and docs  
**Tasks**:
- [ ] Add property-based tests
- [ ] Create performance test suite
- [ ] Document all public APIs
- [ ] Create architecture decision records (ADRs)

**Success Criteria**:
- ✅ >85% test coverage
- ✅ All public APIs documented
- ✅ ADRs for major decisions
- ✅ Updated README and guides

### Sprint 6 (Week 6): CI/CD & Quality Gates
**Goal**: Automated quality enforcement  
**Tasks**:
- [ ] Set up pre-commit hooks
- [ ] Create GitHub Actions pipeline
- [ ] Add code metrics dashboard
- [ ] Set up automated releases

**Success Criteria**:
- ✅ Pre-commit hooks installed
- ✅ CI passing on all PRs
- ✅ Automated test reports
- ✅ Quality metrics tracked

---

## Success Metrics

### Before (Current State)
```
Type Safety:       ⚠️  167 mypy errors
Architecture:      ⚠️  Mixed concerns, god classes
Test Coverage:     ✅  70% (~457 tests)
Documentation:     ⚠️  Inconsistent
Error Handling:    ⚠️  Silent failures common
Performance:       ⚠️  No optimization
CI/CD:             ⚠️  Basic make test only
Code Quality:      ⚠️  No automated checks
```

### After (Target State)
```
Type Safety:       ✅  0 mypy strict errors
Architecture:      ✅  Clean, layered, SOLID
Test Coverage:     ✅  >85% (600+ tests)
Documentation:     ✅  Comprehensive, examples
Error Handling:    ✅  Robust, recoverable
Performance:       ✅  Optimized, cached
CI/CD:             ✅  Automated, comprehensive
Code Quality:      ✅  Enforced, tracked
```

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking changes during refactor | High | Medium | Maintain 100% test pass rate throughout |
| Performance degradation | Medium | Low | Add performance benchmarks first |
| Learning curve for team | Medium | High | Comprehensive documentation and examples |
| Time overrun | Medium | Medium | Prioritize phases, can skip Phase 4 if needed |
| Scope creep | Low | Medium | Stick to plan, log extras for future |

---

## Next Steps

1. **Review this plan** - Discuss priorities and timeline
2. **Get approval** - Confirm scope and effort allocation
3. **Set up project tracking** - Create GitHub issues for each task
4. **Start Sprint 1** - Begin with type safety fixes
5. **Weekly reviews** - Track progress and adjust plan

---

## Questions for Discussion

1. **Timeline**: Is 6 weeks acceptable, or should we compress/extend?
2. **Priority**: Any phases that are more/less important than outlined?
3. **Resources**: Will this be solo work or team collaboration?
4. **Breaking changes**: Are API changes acceptable if they improve architecture?
5. **Testing**: Should we aim for >85% coverage or is 80% sufficient?

---

**Status**: DRAFT - Awaiting Review  
**Version**: 1.0  
**Last Updated**: January 26, 2026  
**Owner**: GitHub Copilot (Claude Sonnet 4.5)
