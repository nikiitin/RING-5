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

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 8.1 StrEnum | PENDING | | |
| 8.2 match statements | PENDING | | |
| 8.3 PEP 695 type | PENDING | | |
| 8.4 @override | PENDING | | |
| 8.5 PEP 695 generics | PENDING | | |
| 8.6 Never/assert_never | PENDING | | |
| 8.7 f-string cleanup | PENDING | | |
| 8.8 ExceptionGroup | PENDING | | |
