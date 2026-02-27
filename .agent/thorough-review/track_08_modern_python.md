# Track 08: Modern Python 3.12+ Upgrades

> **Priority**: MEDIUM
> **Status**: PENDING
> **Estimated items**: 8
> **Scope**: Entire `src/` — language features, typing, patterns

---

## What to Look At

### 8.1 `StrEnum` for registry keys

**Files**:
- `src/core/services/shapers/factory.py`
- `src/parsing/gem5/impl/strategies/factory.py`

**What**: Registry keys are plain strings. `StrEnum` (Python 3.11+) provides type-safe string constants with IDE autocomplete and exhaustive pattern matching.
**Example**:
```python
class ShaperType(StrEnum):
    MEAN = "mean"
    COLUMN_SELECTOR = "columnSelector"
    NORMALIZE = "normalize"
    SORT = "sort"
    PIVOT_LONGER = "pivotLonger"
    ...
```

### 8.2 `match` statements for dispatch

**Files to convert**:
- `src/core/services/shapers/impl/condition_selector.py`, lines 100-109 (if/elif for mode)
- `src/parsing/gem5/impl/strategies/gem5_parse_work.py`, lines 216-225 (type dispatch)
- `src/parsing/gem5/impl/strategies/factory.py`, lines 21-49 (strategy selection)

**What**: If/elif chains can be converted to `match` statements for cleaner, more exhaustive dispatch.

### 8.3 PEP 695 `type` statements

**Files**: `src/core/models/shaper_models.py`, `src/core/models/data_models.py`, `src/core/models/visualization/plot_models.py`
**What**: Convert `TypeAlias` declarations to Python 3.12+ `type` statements:
```python
# Before:
from typing import TypeAlias
ShaperStepConfig: TypeAlias = Union[MeanShaperConfig, ...]

# After:
type ShaperStepConfig = MeanShaperConfig | NormalizeShaperConfig | ...
```

### 8.4 `typing.override` decorator (Python 3.12+)

**Files**: All method overrides in:
- `BasePlot` subclasses (8 plot types in `src/web/pages/ui/plotting/`)
- `Shaper` subclasses (10 shapers in `src/core/services/shapers/impl/`)
- `StatType` subclasses (5 types in `src/parsing/gem5/types/`)

**What**: `@override` catches typos in method names and ensures the parent class actually has the method being overridden.

### 8.5 Replace `TypeVar` with PEP 695 generics

**What**: Find all `T = TypeVar("T")` patterns and convert to:
```python
# Before:
T = TypeVar("T")
def func(x: T) -> T: ...

# After:
def func[T](x: T) -> T: ...
```

### 8.6 Use `Never` type for exhaustive checks

**What**: Add `case _: assert_never(x)` to all `match` statements for compile-time exhaustiveness checking:
```python
from typing import Never, assert_never

match stat_type:
    case "scalar": ...
    case "vector": ...
    case _: assert_never(stat_type)
```

### 8.7 f-string improvements (PEP 701, Python 3.12)

**What**: Python 3.12 allows nested f-strings and quotes within f-strings. Search for workarounds like:
```python
# Before (workaround):
msg = f"Value is {str(obj)}"
# After:
msg = f"Value is {obj!s}"
```

### 8.8 `ExceptionGroup` for batch parsing errors

**What**: When multiple parse jobs fail, currently they raise individual exceptions. Python 3.11+ `ExceptionGroup` can collect and raise them together:
```python
raise ExceptionGroup("Multiple parse failures", [e1, e2, e3])
```

---

## How to Investigate

1. **For 8.1**: Read both factory files. Extract all registry keys. Design StrEnum classes.
2. **For 8.2**: Read each if/elif chain. Verify all cases are covered. Convert to match with exhaustive `case _`.
3. **For 8.3**: Search for `TypeAlias` in all model files. Convert to `type` statement syntax.
4. **For 8.4**: Find all method overrides using `def method_name(self` in subclasses where parent has same method. Add `@override`.
5. **For 8.5**: Search for `TypeVar(` globally. Evaluate each for conversion.
6. **For 8.6**: After 8.2, add `assert_never()` to all match/case default branches.
7. **For 8.7**: Search for f-string workarounds. Minimal impact, do last.
8. **For 8.8**: Evaluate if ExceptionGroup is appropriate for the parsing pipeline's error model.

---

## What We Expect to Find

- **8.1**: ~15 registry keys across 2 factories. StrEnum adds type safety and autocomplete.
- **8.2**: 3 if/elif chains cleanly convertible to match. No complex conditions.
- **8.3**: ~5-8 TypeAlias declarations to convert.
- **8.4**: ~23+ methods need @override (8 plot types + 10 shapers + 5 stat types).
- **8.5**: ~3-5 TypeVar usages, some convertible, some may need to stay for backward compat.
- **8.8**: ExceptionGroup may be too heavy for this use case. Evaluate carefully.

---

## Outcome

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 8.1 StrEnum | **WARRANTS MODERNIZATION** — 12 registry keys as plain strings across 2 factories (shaper factory: 10 keys, strategy factory: 2 keys). StrEnum provides type safety, IDE autocomplete, prevents string typos. | MEDIUM | Create `ShaperType(StrEnum)` and `StrategyType(StrEnum)`. Non-breaking. |
| 8.2 match statements | **WARRANTS MODERNIZATION** — 2-3 if/elif chains suitable for match/case: condition_selector.py (4-branch mode dispatch), gem5_parse_work.py (type normalization), factory.py (strategy selection). | MEDIUM-HIGH | Convert each if/elif chain to match/case with exhaustive `case _`. |
| 8.3 PEP 695 type | **OPTIONAL** — 0 TypeAlias imports; 3-5 manual type aliases exist (JsonValue, EntryBufferType, VarsDictType). Already using modern union syntax (`\|`). PEP 695 adds formal semantics. | LOW | Convert manual aliases to `type X = ...` syntax. Cosmetic improvement. |
| 8.4 @override | **WARRANTS MODERNIZATION** — 0 @override usage in codebase. ~25-30 methods across shaper subclasses, stat type subclasses, and plot type subclasses override parent methods without @override. Project requires Python >=3.12.  | MEDIUM | Add `from typing import override` and `@override` to all overridden methods. |
| 8.5 PEP 695 generics | **MINIMAL** — Only 1 TypeVar in entire codebase (`T = TypeVar("T")` in performance.py). Very limited scope. | LOW | Convert to `def cached[T](...)` syntax. Single change. |
| 8.6 Never/assert_never | **OPTIONAL** — Not used anywhere. Only useful after match/case adoption (8.2). Secondary implementation. | LOW | Add `case _: assert_never(x)` to match statements after 8.2 is done. |
| 8.7 f-string cleanup | **MINOR** — ~15-20 redundant `str()` conversions in f-strings. f-strings auto-call `str()`. Also `f"{value=}"` debug syntax available. | LOW | Remove redundant `str()` calls. Mechanical substitution. |
| 8.8 ExceptionGroup | **NOT WARRANTED** — Current pattern is fail-fast (single error stops pipeline). ExceptionGroup would require architectural change to error collection pattern. High effort, low current benefit. | N/A | No action. Only implement if batch error reporting becomes a requirement. |

### Key Finding
The codebase is **already well-modernized** (PEP 585 types, union syntax, f-strings). The highest-ROI opportunities are:
1. **match/case** for dispatch clarity (8.2)
2. **@override** for inheritance safety (8.4)
3. **StrEnum** for registry type safety (8.1)

### Recommended Modernization Roadmap
- **Phase 1** (High ROI): @override decorators + match/case + StrEnum registries
- **Phase 2** (Polish): PEP 695 type aliases, f-string cleanup
- **Phase 3** (Event-driven): Never/assert_never after match/case, ExceptionGroup if needed
