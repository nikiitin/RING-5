# Performance Analysis & LaTeX Export Strategy for RING-5

## 📊 Current Performance Issues

### Identified Bottlenecks

1. **Figure Generation on Every Rerun**
   - **Issue**: Cache key computation happens on every render
   - **Impact**: Data hashing (MD5 of first/last rows) + config serialization on every Streamlit rerun
   - **Location**: `plot_renderer.py:_compute_data_hash()` and `_compute_figure_cache_key()`

2. **Custom Interactive Component Overhead**
   - **Issue**: Using custom HTML component (`interactive_plotly_chart`) instead of native `st.plotly_chart()`
   - **Impact**: Extra serialization (fig.to_json()) + component communication overhead
   - **Location**: `plot_renderer.py:render_plot()` line 220

3. **Legend Customization UI Per Plot**
   - **Issue**: Rendering text inputs for every unique legend value on every rerun
   - **Impact**: Multiple `st.text_input()` calls that trigger widget reconciliation
   - **Location**: `plot_renderer.py:render_legend_customization()`

4. **No Debouncing on User Interactions**
   - **Issue**: Every pan/zoom/legend drag triggers immediate rerun
   - **Impact**: Multiple figure regenerations during continuous interactions
   - **Location**: `plot_renderer.py:render_plot()` relayout_data handling

5. **Serialization Overhead**
   - **Issue**: DataFrame caching uses `df.to_csv()` and then re-parsing
   - **Impact**: Slow serialization for large datasets (>10k rows)
   - **Location**: Multiple places using `to_csv(index=False)`

### Performance Measurements Needed

Add these timing decorators to critical paths:
- `create_figure()` in each plot type
- `apply_styles()` in StyleApplicator
- `apply_shapers()` in shaper pipeline
- Figure serialization (to_json)

---

## 🎨 Plotly vs Alternatives for Streamlit

### Current: Plotly

**Pros:**
- ✅ Rich interactivity (zoom, pan, hover)
- ✅ Publication-quality vector export (SVG, PDF via Kaleido)
- ✅ Native Streamlit support
- ✅ Large ecosystem
- ✅ Good for complex multi-trace plots

**Cons:**
- ❌ **Heavy JavaScript bundle** (~3MB minified)
- ❌ **Slow initial load** in browser
- ❌ **Figure serialization overhead** (JSON)
- ❌ **Limited font control** for LaTeX compatibility
- ❌ Not optimized for Streamlit's reactive model

### Alternative 1: **Altair** (Vega-Lite)

**Pros:**
- ✅ Declarative grammar (cleaner code)
- ✅ Better Streamlit integration (native caching)
- ✅ Smaller bundle size (~500KB)
- ✅ **Faster rendering** for simple plots
- ✅ Better handling of large datasets (aggregation)

**Cons:**
- ❌ Less feature-rich than Plotly
- ❌ Limited 3D support
- ❌ Export quality not as good (PDF relies on vega-lite-cli)
- ❌ Less control over fine-tuning

### Alternative 2: **Matplotlib** (with mplcursors)

**Pros:**
- ✅ **Best LaTeX integration** (native TeX rendering)
- ✅ **Publication-ready** by default
- ✅ **Perfect font control** (Computer Modern, etc.)
- ✅ **Deterministic output** (no JS variability)
- ✅ Lightweight in Streamlit (static images)

**Cons:**
- ❌ **No native interactivity** (need workarounds)
- ❌ Static images only (unless using mpld3)
- ❌ Slower for complex multi-trace plots
- ❌ Less "modern" feel

### Alternative 3: **Plotly + Static Mode** (Recommended)

**Hybrid Approach:**
- Use Plotly for **interactive preview** in Streamlit
- Export via **Matplotlib backend** for LaTeX papers
- Best of both worlds

---

## 📐 LaTeX Export Strategy

### Problem: Current Export Limitations

1. **Inconsistent Fonts**: Plotly uses system fonts (Arial), papers need Computer Modern or specific serif fonts
2. **Size Mismatch**: Plots sized for screen (800x500px) don't match LaTeX column widths
3. **Resolution Issues**: Export scale doesn't match journal requirements
4. **Font Size Inconsistency**: 12pt in plot ≠ 12pt in LaTeX document

### Solution: LaTeX-Optimized Export Pipeline

#### Step 1: Define LaTeX Presets

Add to `config/plot_presets.yaml`:

```yaml
latex_presets:
  single_column:
    width_inches: 3.5  # Single column width (88mm)
    height_inches: 2.625  # 3:4 aspect ratio
    font_family: "serif"  # Use serif fonts
    font_size_base: 9  # Match LaTeX \small
    font_size_labels: 8
    font_size_title: 10
    font_size_ticks: 7
    line_width: 1.0
    marker_size: 4
    dpi: 300  # For raster fallback

  double_column:
    width_inches: 7.0  # Full page width (180mm)
    height_inches: 5.25  # 3:4 aspect ratio
    font_family: "serif"
    font_size_base: 10
    font_size_labels: 9
    font_size_title: 11
    font_size_ticks: 8
    line_width: 1.2
    marker_size: 5
    dpi: 300

  nature_format:
    # Nature: 89mm single, 183mm double
    width_inches: 3.5
    height_inches: 3.5  # Square for Nature
    font_family: "Arial"  # Nature requires Arial
    font_size_base: 7
    font_size_labels: 6
    font_size_title: 8
    dpi: 600  # Nature requires 300-600 DPI
```

#### Step 2: Create LaTeX Export Service

New file: `src/plotting/export_latex.py`

```python
class LaTeXExportService:
    """
    Export plots optimized for LaTeX documents.
    Handles font matching, size conversion, and format optimization.
    """

    @staticmethod
    def export_for_latex(
        fig: go.Figure,
        preset: str = "single_column",  # or "double_column", "nature_format"
        format: str = "pdf",  # or "pgf", "eps"
        use_matplotlib: bool = True,  # Recommended for LaTeX
        font: str = "Computer Modern"
    ) -> bytes:
        """
        Export figure optimized for LaTeX inclusion.

        - Converts to Matplotlib for better font control
        - Applies LaTeX-specific sizing
        - Outputs in publication formats (PDF/PGF/EPS)
        """
        preset_config = load_preset(preset)

        if use_matplotlib:
            return export_via_matplotlib_latex(fig, preset_config, format, font)
        else:
            return export_via_kaleido_latex(fig, preset_config, format)
```

#### Step 3: Matplotlib LaTeX Backend

```python
def export_via_matplotlib_latex(
    fig: go.Figure,
    preset: dict,
    format: str,
    font: str
) -> bytes:
    """Convert Plotly figure to Matplotlib with LaTeX optimization."""

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import rc

    # Configure LaTeX rendering
    rc('text', usetex=True)
    rc('font', family=font, size=preset['font_size_base'])
    rc('axes', labelsize=preset['font_size_labels'])
    rc('xtick', labelsize=preset['font_size_ticks'])
    rc('ytick', labelsize=preset['font_size_ticks'])
    rc('legend', fontsize=preset['font_size_labels'])

    # Create figure with exact dimensions
    mpl_fig, ax = plt.subplots(
        figsize=(preset['width_inches'], preset['height_inches']),
        dpi=preset['dpi']
    )

    # Convert Plotly traces to Matplotlib
    convert_plotly_to_matplotlib(fig, ax, preset)

    # Export
    buf = io.BytesIO()
    if format == 'pgf':
        # PGF: Best for LaTeX (vector + TeX fonts)
        mpl_fig.savefig(buf, format='pgf', bbox_inches='tight')
    elif format == 'pdf':
        # PDF: Good fallback
        mpl_fig.savefig(buf, format='pdf', bbox_inches='tight',
                       metadata={'Creator': 'RING-5'})
    elif format == 'eps':
        # EPS: Legacy journals
        mpl_fig.savefig(buf, format='eps', bbox_inches='tight')

    buf.seek(0)
    return buf.read()
```

#### Step 4: Update UI for LaTeX Export

Add to plot export options:

```python
export_format = st.selectbox(
    "Export Format",
    options=[
        "Interactive HTML",
        "PNG (Screen)",
        "PDF (Standard)",
        "PDF (LaTeX Single Column)",
        "PDF (LaTeX Double Column)",
        "PGF (LaTeX - Best)",
        "EPS (Legacy)",
    ]
)

if "LaTeX" in export_format:
    font_option = st.selectbox(
        "Font",
        options=["Computer Modern (TeX)", "Times New Roman", "Arial"],
        help="Computer Modern matches LaTeX defaults"
    )
```

---

## 🚀 Recommended Performance Optimizations

### Priority 1: Cache Improvements

```python
# Replace MD5 hashing with xxhash (10x faster)
import xxhash

def _compute_data_hash(data: pd.DataFrame) -> str:
    """Fast hash using xxhash instead of MD5."""
    h = xxhash.xxh64()
    h.update(f"{data.shape[0]}x{data.shape[1]}")
    if len(data) > 0:
        h.update(data.columns.to_numpy().tobytes())
        h.update(data.iloc[0].values.tobytes())
        h.update(data.iloc[-1].values.tobytes())
    return h.hexdigest()[:12]
```

### Priority 2: Switch to Native st.plotly_chart

Replace custom component with native for 2-3x speedup:

```python
# Old (slow)
relayout_data = interactive_plotly_chart(fig, config=plotly_config, key=f"chart_{plot.plot_id}")

# New (fast)
st.plotly_chart(
    fig,
    use_container_width=True,
    key=f"chart_{plot.plot_id}",
    on_select="rerun",  # Streamlit 1.31+
    config=plotly_config
)
```

### Priority 3: Lazy Legend Customization

Only render legend inputs when user clicks "Customize Legend" button:

```python
if st.button("🎨 Customize Legend Labels"):
    st.session_state[f"show_legend_editor_{plot_id}"] = True

if st.session_state.get(f"show_legend_editor_{plot_id}", False):
    # Render text inputs
    pass
```

### Priority 4: Debounce Interactions

Add 500ms debounce to prevent rerun spam:

```python
if relayout_data and relayout_data != last_event:
    # Store timestamp
    now = time.time()
    last_update = st.session_state.get(f"last_update_{plot_id}", 0)

    if now - last_update > 0.5:  # 500ms debounce
        # Process update
        st.session_state[f"last_update_{plot_id}"] = now
        st.rerun()
```

---

## 📋 Implementation Plan

### Phase 1: Quick Wins (1-2 hours)
1. Switch to native `st.plotly_chart()` (if interactivity allows)
2. Add lazy loading for legend customization UI
3. Replace MD5 with xxhash

### Phase 2: LaTeX Export (3-4 hours)
1. Create `export_latex.py` module
2. Add LaTeX presets configuration
3. Implement Matplotlib LaTeX backend
4. Add UI for LaTeX export options

### Phase 3: Advanced (1-2 days)
1. Add interaction debouncing
2. Implement figure caching at session level
3. Add performance monitoring dashboard
4. Optimize shaper pipeline (if needed)

---

## 🎯 Final Recommendations

### For Current Work (Streamlit):
- **Keep Plotly** for interactive exploration
- Optimize render path (native st.plotly_chart)
- Add proper caching layer

### For Publications (LaTeX):
- **Add Matplotlib LaTeX export** with proper font handling
- Provide preset templates for common journals
- Use PGF format for best integration
- Ensure consistent font sizes across all plots

### Alternative Consideration:
If you find Plotly too slow even after optimizations, consider **Altair** for simple plots (bar, line) and keep Plotly only for complex visualizations. Altair is ~5x faster in Streamlit.

---

## 📚 References for LaTeX Integration

- [Matplotlib PGF Backend](https://matplotlib.org/stable/users/explain/text/pgf.html)
- [LaTeX Column Widths](https://en.wikibooks.org/wiki/LaTeX/Page_Layout)
- Nature Guidelines: 89mm (single), 183mm (double), 600 DPI
- IEEE: 3.5" (single), 7.16" (double), 300-600 DPI
- ACM: 3.33" (single), 6.875" (double), 300 DPI

Would you like me to provide your LaTeX repo location so I can create a specific integration guide?
