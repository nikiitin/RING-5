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

**Status**: INVESTIGATION COMPLETE

| Item | Finding | Severity | Action for Implementation |
| --- | --- | --- | --- |
| 14.1 Normalize division | **CONFIRMED (partial mitigation)** — normalize.py:232-240 checks `if denominator == 0:` and sets to 0.0 (prevents inf). BUT does NOT check for NaN denominator. If baseline values contain NaN, `sum()` returns NaN, the zero-check fails (NaN != 0), and division at lines 244-248 produces NaN throughout all normalized columns. No warning emitted. | MEDIUM | Add `pd.isna(denominator)` check alongside zero check. Raise ValueError or warning for NaN baseline values. |
| 14.2 Mean NaN handling | **CONFIRMED (inconsistent)** — mean.py:218-226 uses different algorithms with different NaN behavior. `arithmean` uses `grouped.mean()` (skipna=True by default — correct). `geomean` uses `scipy.stats.gmean` which does NOT skip NaN (propagates NaN). `hmean` uses `scipy.stats.hmean` which does NOT skip NaN (propagates NaN). A single NaN in a group causes geomean/hmean to return NaN for entire group while arithmean skips it. | HIGH | Filter NaN before scipy calls, or wrap scipy functions with NaN handling. Document behavior per algorithm. Add tests for NaN inputs. |
| 14.3 Outlier detection | **CONFIRMED CRITICAL BUG** — outlier_service.py:18,23-24 uses `q3 = df[col].quantile(0.75)` then `df[df[col] <= q3]`. This removes ALL values above Q3 (top 25% of data). Standard IQR method removes values > Q3 + 1.5×IQR where IQR = Q3 - Q1. No Q1 or IQR calculation exists. Removes ~25% of data arbitrarily vs standard <5%. No small dataset (n<5) handling. Index preservation is correct. | CRITICAL | Replace with proper IQR method: Q1 = quantile(0.25), IQR = Q3-Q1, threshold = Q3 + 1.5*IQR. Add configurable multiplier parameter. |
| 14.4 Distribution precision | **CONFIRMED (low impact)** — distribution.py:200-201,234 uses Python `sum()` (direct accumulation, no Kahan summation). All values converted via `float()` to float64. No intermediate int conversions. For typical gem5 statistics (1-10K values), error is <0.0001%. For 100K+ values with mixed magnitude, error may be noticeable. | LOW | Optional: implement Kahan summation for `sum()` at lines 201 and 234. Only needed for precision-critical domains. |

### Corrections from Initial Hypotheses
- **14.1 was PARTIALLY mitigated** — Zero check exists but NaN check missing
- **14.2 was WORSE than expected** — scipy functions have fundamentally different NaN behavior than pandas
- **14.3 was NOT IQR** — Method is plain Q3 threshold, not IQR-based at all (much worse than hypothesized)
- **14.4 was as expected** — float64 precision is adequate for typical use

### Critical Findings Summary (items requiring fix)
1. **Outlier detection removes top 25% instead of actual outliers** — CRITICAL: Statistically incorrect, data loss
2. **Mean NaN handling inconsistent across algorithms** — HIGH: geomean/hmean silently propagate NaN
3. **Normalization NaN denominator not checked** — MEDIUM: NaN baseline produces silent NaN propagation
