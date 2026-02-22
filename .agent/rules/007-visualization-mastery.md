---
description: Visualization, Plotly Graph Objects, and Matplotlib.
globs: src/web/components/plots/**/*.py
---

# 007-visualization-mastery.md

## 1. The Data Visualizer

You are responsible for "Publication Quality" scientific figures that must impress highly critical academic reviewers at ISCA, MICRO, and ASPLOS. You use best practices from "Matplotlib for Python Developers" and "Interactive Data Visualization with Python".

## 2. Visual Principles

### 2.1 Data-to-Ink Ratio

- Erase non-data ink. Remove background grids unless strictly necessary. Eliminate top and right spines in Matplotlib.
- Use whitespace effectively in Plotly templates (`plotly_white` as a base).
- **Legibility:** Font sizes must be large enough to read when printed in two-column format. (Ticks > 8pt, Labels > 10pt, Titles > 12pt).
- **Scientific Accuracy:** All axes MUST include units where applicable (e.g., "IPC (instructions/cycle)", "Memory Latency (ns)").

### 2.2 Color & Accessibility

- **Colorblind-Safe Palettes:** Always default to palettes accessible to Deuteranomaly (Red/Green blind) such as Wong palette.
- **Categorical Data:** Use distinct, high-contrast discrete palettes.
- **Sequential Data:** Use perceptually uniform colormaps (e.g., Viridis, Cividis) for heatmaps. NEVER use 'Jet'.
- Include `st.caption()` or detailed legends explaining what colors indicate.

## 3. Matplotlib for Developers (For Static Export)

### 3.0 Immutable Data & NaN Handling (Critical)

As taught in "Python for Data Analysis", Matplotlib arrays MUST be strictly sanitized before rendering.

- **The Bug Vector:** Passing `None` types into `ax.bar` or `ax.plot` will immediately crash the C-backend interpolator.
- **The Fix:** Always explicitly map dataset missing values using Numpy (e.g., `np.nan` or `0.0`) or Pandas `fillna()` before invoking drawing functions.
- **No Mutation:** Do not mutate `TraceConfig` or input datasets during rendering logic (e.g. `spec.bar_width = foo`).
- **Vectorization Advantage:** As prioritized in **"Python for Data Analysis"**, avoid looping over dataframe rows to prepare plot data. Use vectorized pandas operations or `.to_numpy()` for bulk processing Before passing to the plotting backend to maintain high performance with large gem5 datasets.

### 3.1 Object-Oriented Interface ONLY

- **Strict Prohibition:** The use of `plt.plot()`, `plt.title()` (state-machine interface) is FORBIDDEN.
- **Mandatory Pattern:**
  ```python
  fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
  ax.plot(x, y)
  ax.set_title("Distribution")
  ```
- **Constraint Layout:** Always use `layout="constrained"` to automatically adjust subplots and external legends without clipping, replacing the older `tight_layout()`.
- **Publication Grade Dimensions:** Use the Golden Ratio (approx. 1.618) for aspect ratios unless the facet layout demands otherwise, as suggested in **"Matplotlib for Python Developers"**.
- **Memory Management:** Ensure Streamlit integrations explicitly close Matplotlib figures to avoid memory leaks: `plt.close(fig)`.
- **Venue-Specific Backends:** When generating assets for ISCA/MICRO papers, prefer the `PDF` or `EPS` backends (via `fig.savefig()`) for lossless vector output. Use CMYK-compatible coloring for printed proceedings.

### 3.2 Advanced Styling

- Use `.mplstyle` files or strict dictionaries for defining conference constraints.
- When generating LaTeX assets, configure PGF backend appropriately to output vector graphics ready for `\input{}`.

## 4. Plotly Mastery (For Web Interaction)

### 4.1 Graph Objects (`go.Figure`)

- Do not use `plotly.express` for final production components. Express is only for prototyping. Use explicit Graph Objects (`go.Scatter`, `go.Bar`, `go.Heatmap`) to guarantee full structural control.
- **Dict/JSON Parity:** Construct visualizations using exact dictionaries when it aids testing or serialization, matching the architecture's PlotFactory.

### 4.2 Interactivity Configuration

- Customize the Plotly `config` dictionary sent to `st.plotly_chart()`:
  - `"displayModeBar": True`
  - `"displaylogo": False`
  - Provide download image constraints (SVG format for Web, higher scale).
- **Subplots:** When using `make_subplots`, strictly control `row_heights` and `column_widths`.

---

**Status:** ✅ Active
**Priority:** HIGH
**Acknowledgement:** ✅ **Acknowledged Rule 007**
