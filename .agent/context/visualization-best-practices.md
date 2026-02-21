# Visualization Best Practices — RING-5 Reference

> **Purpose**: Authoritative reference for publication-quality plotting across
> both Plotly (interactive) and matplotlib (LaTeX export) engines.

---

## 1. Publication rcParams by Venue

| Venue                        | Width (in) | Height (in) | DPI | Font Family | Base Font Size |
| ---------------------------- | ---------- | ----------- | --- | ----------- | -------------- |
| IEEE single column           | 3.5        | 2.625       | 300 | serif       | 8 pt           |
| IEEE double column           | 7.0        | 5.25        | 300 | serif       | 8 pt           |
| ISCA / MICRO / ASPLOS / HPCA | 3.5        | 2.5         | 300 | serif       | 8 pt           |
| Nature                       | 3.5        | 3.5         | 600 | Arial       | 7 pt           |
| Science                      | 3.5        | 2.5         | 600 | sans-serif  | 7 pt           |
| Poster                       | 10.0       | 7.0         | 150 | sans-serif  | 24 pt          |
| Slides                       | 8.0        | 4.5         | 150 | sans-serif  | 18 pt          |

**DPI rules**:

- Screen / interactive: 100–150 DPI
- Print (IEEE, ACM): 300 DPI minimum
- High-impact journals (Nature, Science): 600 DPI

---

## 2. Font Size Guidelines

| Element          | Minimum (pt) | Recommended (pt) | Notes                               |
| ---------------- | ------------ | ---------------- | ----------------------------------- |
| Tick labels      | 7            | 7–8              | Must be legible at final print size |
| Axis labels      | 8            | 8–9              | Slightly larger than ticks          |
| Title            | 9            | 9–10             | Largest text element                |
| Legend text      | 7            | 7–8              | Compact but readable                |
| Data annotations | 6            | 6–7              | On-bar or near-point labels         |

**Rule**: Always verify readability at the _final rendered size_ (e.g., 3.5" column
width). A 7pt font at 3.5" is very different from 7pt at 10".

---

## 3. Colorblind-Safe Palettes

### Wong Palette (8 discrete colors — default)

```python
WONG_PALETTE = [
    "#000000",  # Black
    "#E69F00",  # Orange
    "#56B4E9",  # Sky Blue
    "#009E73",  # Bluish Green
    "#F0E442",  # Yellow
    "#0072B2",  # Blue
    "#D55E00",  # Vermillion
    "#CC79A7",  # Reddish Purple
]
```

### Additional Palettes

- **Viridis**: Perceptually uniform, continuous. Good for heatmaps.
- **Plasma**: Perceptually uniform, high contrast at ends.
- **seaborn-colorblind**: 6-color categorical, good for small datasets.

### Contrast Rules

- **Minimum contrast ratio**: 4.5:1 for text on colored backgrounds (WCAG AA).
- **Auto-contrast**: For bar data labels, compute luminance of bar color and choose
  white or black text:
  ```python
  luminance = 0.299*R + 0.587*G + 0.114*B
  text_color = "white" if luminance < 128 else "black"
  ```

---

## 4. Matplotlib Patterns

### 4.1 OO API Only — MANDATORY

```python
# ✅ CORRECT
fig, ax = plt.subplots(layout="constrained")
ax.set_xlabel("Benchmark")
ax.bar(x, y)

# ❌ WRONG — pyplot state machine
plt.xlabel("Benchmark")
plt.bar(x, y)
plt.show()
```

### 4.2 `layout='constrained'`

Prefer over `tight_layout()`, which is deprecated for complex layouts:

```python
fig, ax = plt.subplots(
    figsize=(3.5, 2.5),
    dpi=300,
    layout="constrained",
)
```

Benefits: handles external legends, multi-axis, colorbars correctly.

### 4.3 PGF Backend for LaTeX

```python
import matplotlib
matplotlib.rcParams.update({
    "pgf.texsystem": "xelatex",
    "font.family": "serif",
    "text.usetex": False,  # True only if TeX available
    "pgf.rcfonts": True,
})

fig.savefig(buf, format="pgf", backend="pgf")
```

PGF output produces native LaTeX commands — fonts match the document automatically.

### 4.4 Always Close Figures

```python
# After Streamlit rendering
st.pyplot(fig, clear_figure=True)
plt.close(fig)

# Or for bytes export
buf = io.BytesIO()
fig.savefig(buf, format="pdf", bbox_inches="tight")
pdf_bytes = buf.getvalue()
buf.close()
plt.close(fig)
```

**Never store figure objects** in session state — store bytes instead.

### 4.5 rcParams Context Managers

```python
with plt.rc_context({"font.size": 8, "font.family": "serif"}):
    fig, ax = plt.subplots(layout="constrained")
    # All text in this block uses 8pt serif
```

### 4.6 `bbox_inches='tight'`

Always use on `savefig()` to prevent label/legend clipping:

```python
fig.savefig(path, format="pdf", bbox_inches="tight", dpi=300)
```

---

## 5. Plotly Patterns

### 5.1 Graph Objects Only

```python
# ✅ CORRECT
import plotly.graph_objects as go
fig = go.Figure()
fig.add_trace(go.Bar(x=x, y=y, name="Series 1"))

# ❌ WRONG — Plotly Express
import plotly.express as px
fig = px.bar(df, x="x", y="y")
```

### 5.2 Custom Templates for Theming

```python
import plotly.io as pio
import plotly.graph_objects as go

ring5_base = go.layout.Template(
    layout=go.Layout(
        font=dict(family="serif", size=8),
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#E5E5E5"),
        yaxis=dict(showgrid=True, gridcolor="#E5E5E5"),
    )
)
pio.templates["ring5_base"] = ring5_base
```

### 5.3 Template Composition

```python
fig.update_layout(template="plotly_white+ring5_isca")
```

Custom template always layered on top of base theme.

### 5.4 Kaleido v1 for Static Export

```python
# PNG at 2× scale
png_bytes = fig.to_image(format="png", width=700, height=500, scale=2)

# Supported: png, jpeg, webp, svg, pdf
# Uses system Chrome (no bundled browser)
```

### 5.5 Magic Underscore Notation

```python
# These are equivalent:
fig.update_layout(title_font_size=24)
fig.update_layout(title=dict(font=dict(size=24)))
```

Prefer underscore in code, explicit dicts in templates for clarity.

### 5.6 Streamlit Integration

```python
# Use theme=None when custom template is applied
st.plotly_chart(fig, theme=None)

# Or use interactive_plotly_chart() for legend dragging support
interactive_plotly_chart(fig)
```

---

## 6. Data-Ink Ratio (Tufte Principles)

- **Remove non-data-ink**: decorative borders, shadows, 3D effects, background images.
- **Remove top/right spines** by default:
  ```python
  ax.spines["top"].set_visible(False)
  ax.spines["right"].set_visible(False)
  ```
- **Gridlines**: light gray (`#E5E5E5`), thin (0.5–1pt). Only on the value axis.
- **Prefer direct labeling** over legends when practical (fewer than 4 series).
- **White backgrounds** for print. No gradient fills.
- **No chartjunk**: remove all decoration that doesn't convey data.

---

## 7. Hatching Patterns (B&W-Friendly)

For distinguishing categories in grayscale or B&W printing:

```python
HATCHING_PATTERNS = ["/", "\\", "|", "-", "+", "x", "o", "O", ".", "*"]
```

- matplotlib: `ax.bar(..., hatch="//")`
- Plotly: `fig.update_traces(marker_pattern_shape="/")` (Plotly 5.4+)

Combine with color for maximum accessibility.

---

## 8. Memory Discipline

### Matplotlib Figure Lifecycle

1. **Create**: `fig, ax = plt.subplots(...)`
2. **Populate**: add traces, labels, annotations
3. **Render/Export**: `st.pyplot(fig)` or `fig.savefig(buf)`
4. **Close**: `plt.close(fig)` — ALWAYS

### Rules

- **Never store `Figure` objects** in `st.session_state` — store bytes.
- **Use `clear_figure=True`** in `st.pyplot(fig, clear_figure=True)`.
- **Close BytesIO** buffers after extracting bytes.
- **matplotlib tracks all open figures** globally — unclosed figures accumulate
  and eventually crash long-running Streamlit sessions.

### Pattern for Streamlit Export

```python
def export_figure(fig: Figure, format: str) -> bytes:
    """Export figure to bytes and close it."""
    buf = io.BytesIO()
    fig.savefig(buf, format=format, bbox_inches="tight")
    result = buf.getvalue()
    buf.close()
    plt.close(fig)
    return result
```
