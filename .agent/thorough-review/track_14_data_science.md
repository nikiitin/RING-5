# Track 14: Data Science Quality

> **Priority**: MEDIUM
> **Status**: PENDING
> **Estimated items**: 4
> **Scope**: Statistical operations, normalization, data transformations

---

## What to Look At

### 14.1 Normalization numerics — division by zero handling

**File**: `src/core/services/shapers/impl/normalize.py`
**What**: Normalization divides by a reference value. If the reference value is zero, this produces `inf` or `NaN`. Need to verify the current handling:
- Does it check for zero reference?
- Does it produce a warning?
- Does `inf` propagate through downstream operations (mean calculation, plotting)?

### 14.2 Mean calculation with NaN values

**File**: `src/core/services/shapers/impl/mean.py`
**What**: When averaging columns that contain NaN, the result depends on whether `np.nanmean()` or `df.mean()` is used:
- `df.mean()` skips NaN by default
- Manual sum + division does NOT handle NaN
Need to verify which approach is used and whether NaN handling is correct.

### 14.3 Outlier detection method accuracy

**File**: `src/core/services/shapers/impl/outlier_service.py`
**What**: The outlier removal method (IQR-based, Z-score, or custom) needs verification:
- Is the IQR multiplier correct (typically 1.5 for mild, 3.0 for extreme)?
- Does it handle small datasets (n < 5) where outlier detection is unreliable?
- Does it preserve the index correctly after removal?

### 14.4 Distribution reduce numerical precision

**File**: `src/parsing/gem5/types/distribution.py`
**What**: Distribution buckets may contain floating-point values that accumulate rounding errors during reduce operations. For publication-quality results, need to verify:
- Is double-precision (float64) used throughout?
- Are there any intermediate int conversions that lose precision?
- Do reduce operations preserve statistical properties (mean, variance)?

---

## How to Investigate

1. **For 14.1**: Read normalize.py. Find the division operation. Trace what happens with a zero reference value. Write a test with `reference_value=0`.
2. **For 14.2**: Read mean.py. Find the averaging operation. Test with DataFrame containing NaN values. Verify result matches `df.mean(skipna=True)`.
3. **For 14.3**: Read outlier_service.py. Identify the outlier detection method. Test with n=3 dataset, dataset with all identical values, dataset with single extreme outlier.
4. **For 14.4**: Read distribution.py reduce operations. Check numeric types. Test with values that expose floating-point precision issues (e.g., 0.1 + 0.2).

---

## What We Expect to Find

- **14.1**: Division by zero is likely handled by pandas (produces inf), but no explicit check exists. Users see inf in plots without warning.
- **14.2**: Mean calculation likely uses `df.mean()` which handles NaN correctly. But if any manual averaging exists, it may not.
- **14.3**: IQR method is likely correct but may not handle n < 5 gracefully.
- **14.4**: Distribution uses float64 throughout. Precision is adequate for scientific use.

---

## Outcome

**Status**: PENDING

| Item | Result | Fix Applied | Notes |
| --- | --- | --- | --- |
| 14.1 Normalize division | PENDING | | |
| 14.2 Mean NaN handling | PENDING | | |
| 14.3 Outlier detection | PENDING | | |
| 14.4 Distribution precision | PENDING | | |
