---
title: "Performance"
parent: Troubleshooting
grand_parent: AI Knowledge Base
nav_order: 3
---

# Performance

> AI-optimized reference. No prose -- tables, bullets, code blocks only.

---

## Performance Utilities (`src/core/performance.py`)

### `SimpleCache` Class

| Property | Value |
|----------|-------|
| File | `src/core/performance.py:24-93` |
| Constructor | `SimpleCache(maxsize=128, ttl=None)` |
| Eviction | LRU (oldest timestamp evicted when at capacity) |
| TTL | Optional, in seconds (`None` = no expiration) |
| Thread safety | Has `threading.Lock` -- but docstring originally said "Thread-safe" when locks were missing (known issue #2 in common-issues.md) |
| Unit tests | **0 tests** -- `src/core/performance.py` has zero test coverage |

```python
# API
cache = SimpleCache(maxsize=32, ttl=300)
cache.get(key: str) -> Any | None      # Returns None on miss or TTL expiry
cache.set(key: str, value: Any) -> None # LRU eviction at maxsize
cache.clear() -> None                   # Reset cache + counters
cache.stats() -> dict                   # {"hits", "misses", "size", "hit_rate"}
```

### Global Plot Cache Instance

```python
# src/core/performance.py:97
_plot_cache = SimpleCache(maxsize=32, ttl=300)  # 5 min TTL, 32 entries max

# Access
from src.core.performance import get_plot_cache, get_cache_stats, clear_all_caches
get_plot_cache()      # Returns _plot_cache singleton
get_cache_stats()     # {"plot_cache": {hits, misses, size, hit_rate}}
clear_all_caches()    # Clears _plot_cache
```

### `@cached` Decorator

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ttl` | `float | None` | `None` | Time-to-live in seconds |
| `maxsize` | `int` | `128` | Max cache entries |
| `cache_instance` | `SimpleCache | None` | `None` | Reuse existing cache |
| `key_func` | `Callable | None` | `None` | Custom key generation |

```python
# Simple usage
@cached(ttl=60)
def simple_op(x: int) -> int:
    return x * 2

# Custom key (avoid stringifying DataFrames)
@cached(ttl=300, key_func=lambda df, fingerprint: fingerprint)
def df_op(data: pd.DataFrame, fingerprint: str) -> pd.DataFrame:
    return expensive_transform(data)

# Access attached cache management
simple_op.cache_clear()   # Clear this function's cache
simple_op.cache_stats()   # Get hit/miss stats
```

### `@timed` Decorator

```python
# src/core/performance.py:164-189
@timed
def slow_operation():
    ...
# Logs WARNING if >100ms, DEBUG otherwise
# Format: "SLOW: func_name took 150.23ms" / "PERF: func_name took 12.45ms"
```

### `compute_data_fingerprint()`

```python
# src/core/performance.py:210-243
compute_data_fingerprint(
    data: pd.DataFrame,
    params: dict[str, Any],
    relevant_cols: list[str],
) -> str  # 16-char hex MD5 digest

# Used by cached shapers (mean, normalize) to detect input changes
# Components: shape + sorted cols + sorted params + sample of first 2 rows
```

---

## Known Performance Bottlenecks

### 1. PerlWorkerPool

| Property | Value |
|----------|-------|
| File | `src/parsing/gem5/impl/strategies/perl_worker_pool.py` (~625 lines) |
| Speedup | 54x via parallelism (pool of persistent Perl subprocesses) |
| Pool size | Default 4 workers |
| Features | Auto-restart on failure, load balancing, health monitoring, stats tracking |
| Communication | Pipes to Perl subprocess stdin/stdout |

- **Bottleneck**: Perl subprocess startup is expensive; pool amortizes cost
- **Debug**: Check `pool.stats()` for worker count, jobs processed, failures

### 2. WorkPool Singleton (Orphaned Pools)

| Property | Value |
|----------|-------|
| File | `src/parsing/framework/work_pool.py:32-104` |
| Pattern | Singleton via `__new__` + `threading.Lock` |
| Executors | `ProcessPoolExecutor` (CPU-bound) + `ThreadPoolExecutor` (IO-bound) |
| Worker count | Process: `cpu_count() - 1`, Thread: `cpu_count() * 2` |
| Shutdown | `atexit.register(_shutdown_workpool)` at module level |
| Known issue | **N hot-reloads = N orphaned process pools** -- `atexit` may not fire on Streamlit rerun |

```python
# WorkPool singleton lifecycle
WorkPool.get_instance()          # Get or create singleton
pool.submit(task, use_threads=False)  # Submit to process or thread pool
pool.shutdown(wait=False)        # Explicit shutdown (rarely called)

# atexit handler (src/parsing/framework/work_pool.py:97-104)
def _shutdown_workpool():
    if WorkPool._instance is not None:
        WorkPool._instance.shutdown(wait=False)
        WorkPool._instance = None
atexit.register(_shutdown_workpool)
```

- **Mitigation**: `atexit` handler registered, but Streamlit's rerun model may bypass interpreter exit
- **Detection**: `ps aux | grep -E "python|perl" | wc -l` to count child processes

### 3. Figure Rendering (Manual Hash Cache)

| Property | Value |
|----------|-------|
| Cache location | `src/core/performance.py:97` (`_plot_cache`, 32 entries, 5min TTL) |
| Key computation | `src/web/controllers/plot/render_controller.py:277` |
| Data hash | `_compute_data_hash()`: shape + first/last row hash |
| Config hash | `_compute_figure_cache_key()`: plot_id + config hash + data_hash |
| NOT used | `@st.cache_data` -- manual cache chosen for control over key generation |

```
Figure cache flow:
  1. Compute data_hash from DataFrame shape + sample rows
  2. Compute cache_key from plot_id + config + data_hash
  3. Check _plot_cache.get(cache_key)
  4. On HIT: return cached figure (skip rendering)
  5. On MISS: render figure, store in _plot_cache.set(cache_key, fig)
```

### 4. matplotlib Figure Memory Leak

| Property | Value |
|----------|-------|
| File | `src/web/rendering/matplotlib_connector.py` |
| Bug | Zero `plt.close()` calls in production rendering code |
| Impact | ~1-5 MB per figure, unbounded growth on repeated exports |
| Severity | HIGH |
| Tests | Tests DO call `plt.close()` (in teardown), but production code does not |
| Chart display | `src/web/components/common/chart_display.py:152,205,233,291` DOES call `plt.close()` |

```python
# FIX pattern for any matplotlib figure creation:
try:
    fig = create_figure(...)
    result = process_figure(fig)
finally:
    plt.close(fig)  # MUST close to free memory
```

---

## Streamlit Caching Strategy

### `@st.cache_resource` for ApplicationAPI

```python
# app.py:54-58
@st.cache_resource(show_spinner="Initializing RING-5...")
def get_api() -> ApplicationAPI:
    return ApplicationAPI(plot_deserializer=BasePlot.from_dict)

api = get_api()
st.session_state.api = api  # Also stored in session_state for component access
```

| Property | Value |
|----------|-------|
| Scope | Global singleton, shared across all sessions |
| Lifecycle | Persists until code change or `st.cache_resource.clear()` |
| Contains | `RepositoryStateManager`, `DefaultServicesAPI`, parser |
| NOT cached | Per-session state (stored in `st.session_state` separately) |

### Manual Hash Cache for Figures

| Component | File | Mechanism |
|-----------|------|-----------|
| Cache instance | `src/core/performance.py:97` | `SimpleCache(maxsize=32, ttl=300)` |
| Key generation | `render_controller.py:277` | `_compute_figure_cache_key(plot_id, config, data_hash)` |
| Data fingerprint | `render_controller.py:300` | `_compute_data_hash(data)` -- shape + boundary rows |
| Data fingerprint (shapers) | `performance.py:210` | `compute_data_fingerprint(data, params, cols)` -- MD5 |

- **Why not `@st.cache_data`**: Need fine-grained control over cache keys; Plotly `Figure` objects are complex to hash automatically
- **Cache invalidation**: Key changes when config or data changes; TTL expires after 5 minutes

---

## Optimization Patterns

### Lazy Imports (Page Modules)

```python
# app.py:138-157 -- only the active page module is loaded
if page == "Data Source":
    from src.web.pages.data_source import DataSourcePage
    DataSourcePage(api).render()
elif page == "Data Managers":
    from src.web.pages.data_managers import show_data_managers_page
    show_data_managers_page(api)
# ... etc.
```

- **Effect**: Unused page modules (and their plot type imports) never load
- **Also applies to**: Plot types (`src/web/pages/ui/plotting/`) -- only loaded when active via `PlotFactory`

### Pipeline-Based Transforms (Shapers)

```python
# All 10 shapers implement __call__(self, df: pd.DataFrame) -> pd.DataFrame
# Compatible with pandas .pipe() for composable transforms

df_result = (
    df.pipe(normalizer)
      .pipe(mean_shaper)
      .pipe(sort_shaper)
)
```

| Shaper | File | Operation |
|--------|------|-----------|
| Mean | `src/core/services/shapers/impl/mean.py` | Arithmetic/geometric/harmonic mean |
| Normalize | `src/core/services/shapers/impl/normalize.py` | Value normalization |
| Sort | `src/core/services/shapers/impl/sort.py` | Row/column sorting |
| Split-Apply | `src/core/services/shapers/impl/split_apply.py` | Group-by operations |
| Selector | `src/core/services/shapers/impl/` | Row/column filtering |
| Transformer | `src/core/services/shapers/impl/` | Type/format transforms |

- **Caching**: Mean and normalize shapers use `compute_data_fingerprint()` to skip recomputation
- **Factory**: `ShaperFactory` in `src/core/services/shapers/` -- single source of display names

### Fragment Isolation for Partial Reruns

```python
# app.py:115-135
@st.fragment
def _data_preview_fragment() -> None:
    current_view = api.get_current_view()
    if current_view["raw_data"] is not None:
        col1, col2, col3 = st.columns(3)
        # ... render metrics
```

- **Effect**: Widget interactions inside fragment do NOT trigger full-app rerun
- **Rule**: Define `@st.fragment` at module level only (never inside loops or render functions)
- **Use case**: Data preview, interactive plot controls, complex forms

---

## Performance Monitoring Commands

```bash
# Check rerun timing (logged by app.py:160-164 when >500ms)
streamlit run app.py --logger.level=debug 2>&1 | grep "Slow rerun"

# Count orphaned processes
ps aux | grep -E "python.*ring5|perl" | grep -v grep | wc -l

# Monitor memory usage during session
watch -n 2 "ps aux | grep streamlit | grep -v grep"

# Cache stats (from Python/Streamlit console)
# from src.core.performance import get_cache_stats
# print(get_cache_stats())
```

---

## Lifecycle & Concurrency Guarantees

The performance-sensitive subsystems carry these guarantees — they are facts of the current
design, not open issues:

| Subsystem | File | Guarantee |
|-----------|------|-----------|
| `SimpleCache` | `src/core/performance.py` | Thread-safe (`threading.Lock`) |
| `CsvPoolService` | `src/core/services/data_services/csv_pool_service.py` | Thread-safe (`threading.Lock`) |
| `WorkPool` | `src/parsing/framework/work_pool.py` | `shutdown()` + `atexit` cleanup |
| `PerlWorkerPool` | `src/parsing/gem5/impl/strategies/perl_worker_pool.py` | `shutdown()` + `atexit` cleanup |
| matplotlib figures | `src/web/rendering/matplotlib_connector.py` | Connector does not close the figure — `st.pyplot` owns it (no leak) |
| matplotlib render cache | `src/web/components/common/chart_display.py` | Session-scoped cache; `plt.close()` is called; never serialized to disk |
