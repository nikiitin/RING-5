# New Plot Type Workflow

> **Invoke with**: `/new-plot-type`
> **Purpose**: Add a new visualization type to the system.
> **Applies to**: `src/plotting/`

## Overview

Adding a plot requires following the **Factory Pattern** and ensuring strict separation between Visualization (Plotly) and UI (Streamlit), as per **Rule 001 (Layer C)**.

## Step-by-Step

### 1. Define the Visualizer (Pure Logic)

Create `src/plotting/visualizers/<Name>Visualizer.py`.

- **Input**: `pd.DataFrame`, `PlotConfig` (TypedDict).
- **Output**: `go.Figure`.
- **Constraint:** **NO** `st.*` calls allowed here. Pure Plotly.

### 2. Define the Configurator (UI)

Create `src/web/ui/configurators/<Name>Configurator.py`.

- **Role**: Render widgets (`st.selectbox`).
- **Output**: The `PlotConfig` dictionary.

### 3. Register in Factory

Update `src/plotting/plot_factory.py`.

- **Mechanism:** Map string key -> Class.
- **OCP:** Do not modify existing logic, just add the new mapping.

### 4. TDD Verification (Rule 004)

- **Unit Test:** Test `Visualizer` with `sample_dataframe`. Assert `fig.data` contains expected traces.
- **Constraint:** Verify "Back-to-Front Sync" involved in the config object.

```python
def test_heatmap_generation(sample_dataframe):
    # Pure logic test - No Streamlit needed
    viz = HeatmapVisualizer()
    fig = viz.create_figure(sample_dataframe, config={...})
    assert len(fig.data) > 0
```
