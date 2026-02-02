# Adding Plot Types

Step-by-step guide to extending RING-5 with custom plot types.

## Overview

RING-5's plotting system uses the **Factory Pattern** to create plot instances. Adding a new plot type involves:

1. Creating plot class (inherit from `BasePlot`)
2. Implementing `create_figure()` method
3. Registering in `PlotFactory`
4. Writing tests
5. Adding UI configuration

## Step 1: Create Plot Class

### File Location

Create new file in `src/plotting/types/`:

```text
src/plotting/types/
├── my_new_plot.py     # Your new plot
├── bar_plot.py
├── line_plot.py
└── ...
```

### Class Template

```python
from typing import Dict, Any, Optional
import pandas as pd
import plotly.graph_objects as go
from src.plotting.base_plot import BasePlot


class MyNewPlot(BasePlot):
    """
    Custom plot type for [specific use case].

    Configuration:
        x_column (str): X-axis data column
        y_column (str): Y-axis data column
        title (str): Plot title
        [additional config fields]
    """

    def __init__(self, plot_id: int, name: str = "My Plot") -> None:
        """
        Initialize plot.

        Args:
            plot_id: Unique plot identifier
            name: Plot name for UI
        """
        super().__init__(plot_id, name)
        self.plot_type = "my_new_plot"  # Must match factory key

    def create_figure(self, data: pd.DataFrame) -> go.Figure:
        """
        Create Plotly figure from data.

        Args:
            data: DataFrame with required columns

        Returns:
            Configured Plotly Figure

        Raises:
            KeyError: If required columns missing
            ValueError: If data invalid
        """
        # Extract configuration
        x_col = self.config.get("x_column")
        y_col = self.config.get("y_column")
        title = self.config.get("title", "My Plot")

        # Validate
        if not x_col or not y_col:
            raise ValueError("x_column and y_column required")

        if x_col not in data.columns or y_col not in data.columns:
            raise KeyError(f"Columns {x_col}, {y_col} not in data")

        # Create figure
        fig = go.Figure()

        # Add trace
        fig.add_trace(go.Scatter(
            x=data[x_col],
            y=data[y_col],
            mode="markers",
            name=self.name
        ))

        # Layout
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            template="plotly_white",
            font=dict(size=14)
        )

        return fig
```

## Step 2: Register in Factory

Edit `src/plotting/plot_factory.py`:

```python
from src.plotting.types.my_new_plot import MyNewPlot

class PlotFactory:
    _plot_types: Dict[str, type] = {
        "bar": BarPlot,
        "line": LinePlot,
        "my_new_plot": MyNewPlot,  # Add here
        # ...
    }
```

## Step 3: Write Tests

Create `tests/unit/test_my_new_plot.py`:

```python
import pytest
import pandas as pd
from src.plotting.types.my_new_plot import MyNewPlot


@pytest.fixture
def sample_data():
    """Sample data for testing."""
    return pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [10, 20, 15, 25, 30]
    })


class TestMyNewPlot:
    """Test suite for MyNewPlot."""

    def test_initialization(self):
        """Test plot initialization."""
        plot = MyNewPlot(plot_id=1, name="Test Plot")

        assert plot.plot_id == 1
        assert plot.name == "Test Plot"
        assert plot.plot_type == "my_new_plot"

    def test_create_figure_basic(self, sample_data):
        """Test basic figure creation."""
        plot = MyNewPlot(plot_id=1)
        plot.config = {
            "x_column": "x",
            "y_column": "y",
            "title": "Test"
        }

        fig = plot.create_figure(sample_data)

        assert fig is not None
        assert len(fig.data) > 0
        assert fig.layout.title.text == "Test"

    def test_missing_columns(self, sample_data):
        """Test error on missing columns."""
        plot = MyNewPlot(plot_id=1)
        plot.config = {
            "x_column": "missing",
            "y_column": "y"
        }

        with pytest.raises(KeyError):
            plot.create_figure(sample_data)

    def test_missing_config(self, sample_data):
        """Test error on missing config."""
        plot = MyNewPlot(plot_id=1)
        plot.config = {}  # Empty config

        with pytest.raises(ValueError):
            plot.create_figure(sample_data)
```

Run tests:

```bash
pytest tests/unit/test_my_new_plot.py -v
```

## Step 4: Add UI Configuration

Edit `src/web/ui/components/plot_config.py`:

```python
def render_plot_config(plot):
    if plot.plot_type == "my_new_plot":
        render_my_new_plot_config(plot)
    # ... other plot types


def render_my_new_plot_config(plot):
    """Render configuration UI for MyNewPlot."""
    st.subheader("Plot Configuration")

    # Column selectors
    columns = StateManager.get_columns()

    x_col = st.selectbox(
        "X-Axis Column",
        options=columns,
        key=f"x_col_{plot.plot_id}"
    )

    y_col = st.selectbox(
        "Y-Axis Column",
        options=columns,
        key=f"y_col_{plot.plot_id}"
    )

    # Title
    title = st.text_input(
        "Plot Title",
        value="My Plot",
        key=f"title_{plot.plot_id}"
    )

    # Additional options
    show_grid = st.checkbox(
        "Show Grid",
        value=True,
        key=f"grid_{plot.plot_id}"
    )

    # Update config
    plot.config = {
        "x_column": x_col,
        "y_column": y_col,
        "title": title,
        "show_grid": show_grid
    }
```

## Step 5: Document Your Plot

Create `docs/plots/My-New-Plot.md`:

```markdown
# My New Plot

Description of what this plot visualizes and when to use it.

## Configuration

- **X-Axis Column**: Data for X-axis
- **Y-Axis Column**: Data for Y-axis
- **Title**: Plot title
- [Additional options]

## Use Cases

- Use case 1
- Use case 2

## Example

[Include example configuration and resulting plot]

## Best Practices

- Tip 1
- Tip 2
```

## Advanced: Multi-Trace Plots

For plots with multiple traces (grouped, overlaid):

```python
def create_figure(self, data: pd.DataFrame) -> go.Figure:
    group_col = self.config.get("group_by")

    fig = go.Figure()

    if group_col:
        # Multiple traces
        for group in data[group_col].unique():
            group_data = data[data[group_col] == group]

            fig.add_trace(go.Scatter(
                x=group_data[x_col],
                y=group_data[y_col],
                name=str(group),
                mode="lines+markers"
            ))
    else:
        # Single trace
        fig.add_trace(go.Scatter(
            x=data[x_col],
            y=data[y_col],
            name=self.name
        ))

    return fig
```

## Best Practices

1. **Type Hints**: Full type annotations on all methods
2. **Validation**: Check config and data before plotting
3. **Error Messages**: Clear, actionable error messages
4. **Documentation**: Docstrings on class and methods
5. **Testing**: Unit tests for all code paths
6. **Styling**: Follow Plotly best practices (fonts 14pt+, clear legends)

## Common Patterns

### Color Mapping

```python
color_map = self.config.get("color_map", {})
colors = [color_map.get(val, "blue") for val in data[group_col]]

fig.add_trace(go.Bar(
    x=data[x_col],
    y=data[y_col],
    marker=dict(color=colors)
))
```

### Conditional Formatting

```python
def get_marker_style(value):
    if value > threshold:
        return dict(color="red", size=10)
    return dict(color="blue", size=6)

markers = [get_marker_style(v) for v in data[y_col]]
```

### Custom Hover Text

```python
hover_text = [
    f"{row['benchmark']}<br>IPC: {row['ipc']:.2f}<br>Config: {row['config']}"
    for _, row in data.iterrows()
]

fig.add_trace(go.Scatter(
    ...,
    hovertext=hover_text,
    hoverinfo="text"
))
```

## Troubleshooting

**Plot not showing up**:

- Check `plot_type` matches factory key
- Verify registration in `PlotFactory._plot_types`

**Config not working**:

- Check UI component is updating `plot.config`
- Verify config keys in `create_figure()`

**Data errors**:

- Add validation for required columns
- Check for empty DataFrames

## Next Steps

- Plot Styling: [Creating-Plots.md](Creating-Plots.md)
- Testing: [Testing-Guide.md](Testing-Guide.md)
- Plotly Reference: <https://plotly.com/python/>
