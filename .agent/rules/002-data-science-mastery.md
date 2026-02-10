---
description: Data Science, Pandas, NumPy, and Statistical Analysis best practices.
globs: src/**/*.py
---

# 002-data-science-mastery.md

## 1. The Data Scientist

You treat data with scientific rigor. Every transformation is documented, reproducible, and type-safe.

## 2. Pandas Best Practices (_Python for Data Analysis_)

### 2.1 Data Loading & I/O (PDA Ch 6)

- **Explicit dtypes:** Always specify `dtype=` when loading CSVs to prevent silent type coercion.
- **Chunked Reading:** For large files (>1GB), use `chunksize=` parameter and process iteratively.
- **Missing Data:** Use `na_values=` to explicitly define what constitutes missing data. Document your choices.
- **Date Parsing:** Use `parse_dates=` with explicit format strings. Never rely on pandas auto-detection.

### 2.2 Data Cleaning & Preparation (PDA Ch 7)

- **Immutability:** NEVER use `inplace=True`. Always return new DataFrames.
- **Missing Values:**
  - Document your strategy (drop, fill, interpolate).
  - Use `fillna()` with explicit values or methods (`'ffill'`, `'bfill'`).
  - Use `dropna()` with explicit `subset=` and `thresh=` parameters.
- **Duplicates:** Always check with `df.duplicated()` before analysis.
- **String Operations:** Use `.str` accessor for vectorized operations. Avoid Python loops.

### 2.3 Tidy Data Principles (PDA Ch 8)

- **Wide to Long:** Use `pd.melt()` for pivoting wide data to tidy format.
- **Long to Wide:** Use `pd.pivot_table()` or `df.pivot()` for aggregation.
- **Hierarchical Index:** Use `set_index()` with multiple columns. Access via `.loc[('level1', 'level2')]`.
- **Combining Data:**
  - `pd.concat()`: For stacking along an axis.
  - `pd.merge()`: For SQL-style joins. Always specify `on=`, `how=`, and `validate=`.

### 2.4 Aggregation & Transformation (PDA Ch 10)

- **GroupBy Split-Apply-Combine:**
  - `agg()`: For reducing groups to single values (sum, mean, etc.).
  - `transform()`: For broadcasting results back to original shape.
  - `apply()`: For complex, non-vectorizable operations (use sparingly).
- **Named Aggregations:** Use `agg(new_name=('column', 'func'))` syntax for clarity.
- **Pivot Tables:** Use `pd.pivot_table()` with explicit `aggfunc=`, `margins=`, and `fill_value=`.

### 2.5 Time Series (PDA Ch 11)

- **DatetimeIndex:** Convert time columns to `DatetimeIndex` for time-based operations.
- **Resampling:** Use `.resample()` for downsampling/upsampling with explicit aggregation functions.
- **Rolling Windows:** Use `.rolling()` with explicit `window=` and `min_periods=`.
- **Time Zones:** Be explicit about timezone handling. Use `tz_localize()` and `tz_convert()`.

## 3. NumPy Best Practices (PDA Appendix A)

- **Vectorization First:** Always prefer NumPy vectorized operations over Python loops.
- **Broadcasting:** Understand and leverage NumPy broadcasting rules.
- **Memory Layout:** Be aware of C-order vs Fortran-order for performance-critical code.
- **Views vs Copies:** Understand when slicing creates views vs copies. Use `.copy()` explicitly when needed.

## 4. Plotting Best Practices (PDA Ch 9)

- **Publication Quality:**
  - Font sizes: 14pt+ for readability in two-column papers.
  - Vector formats: Export as PDF/SVG for publications.
  - Color palettes: Use colorblind-friendly palettes.
- **Plotly Graph Objects:** Use `go.Figure` for fine-grained control.
- **Factory Pattern:** All plots must go through `PlotFactory` for consistent styling.
- **Labels:** Always include axis labels, title, and legend. No unlabeled plots.

## 5. Statistical Analysis

### 5.1 Descriptive Statistics

- Always report: mean, median, std, min, max, and percentiles (25th, 75th, 95th).
- Use `df.describe()` as a starting point, but customize for your domain.

### 5.2 Hypothesis Testing

- State null and alternative hypotheses explicitly.
- Report p-values with confidence intervals.
- Use appropriate tests (t-test, Mann-Whitney, ANOVA) based on data characteristics.

### 5.3 Reproducibility

- Set random seeds for any stochastic operations.
- Document all preprocessing steps.
- Version your analysis scripts alongside data.

## 6. Memory Optimization

- **Downcasting:** Use `pd.to_numeric(downcast='integer')` for large datasets.
- **Categorical:** Convert low-cardinality string columns to `category` dtype.
- **Sparse Arrays:** Use sparse dtypes for data with many zeros/NaNs.
- **Memory Profiling:** Use `df.memory_usage(deep=True)` to identify optimization opportunities.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 002**
