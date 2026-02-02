# Skill: Adding New Plot Types

**Skill ID**: `new-plot-type`
**Domain**: Visualization
**Complexity**: Intermediate

## Purpose

Step-by-step guide for adding new plot types to the RING-5 visualization system using the Factory pattern.

## Architecture Context

```
┌──────────────────────────────────────┐
│  UI Layer (Layer C)                  │
│  - Calls PlotFactory.create_plot()   │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  PlotFactory (Factory Pattern)       │
│  - Registers plot types              │
│  - Creates plot instances            │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  BasePlot (Abstract Base Class)      │
│  - Defines interface                 │
│  - Common layout methods             │
└────────────┬─────────────────────────┘
             │
             ▼
┌──────────────────────────────────────┐
│  Concrete Plot Classes               │
│  - BarPlot, LinePlot, etc.           │
│  - Implement create_figure()         │
└──────────────────────────────────────┘
```

## Step-by-Step Implementation

### Step 1: Create the Plot Class

**File**: `src/plotting/types/my_new_plot.py`

```python
\"\"\"
My New Plot Type
Implements a custom visualization for RING-5.
\"\"\"

from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go

from src.plotting.base_plot import BasePlot


class MyNewPlot(BasePlot):
    \"\"\"
    Custom plot type for [describe what it visualizes].

    Configuration:
        x_column: str - Column for X-axis
        y_column: str - Column for Y-axis
        color_by: Optional[str] - Column for color grouping
        [other config options]
    \"\"\"

    def __init__(self, config: Dict[str, Any]):
        \"\"\"
        Initialize the plot with configuration.

        Args:
            config: Plot configuration dict with required keys
        \"\"\"
        super().__init__(config)
        self.x_column = config.get("x_column")
        self.y_column = config.get("y_column")
        self.color_by = config.get("color_by")

    def create_figure(self, data: pd.DataFrame) -> go.Figure:
        \"\"\"
        Create the Plotly figure from data.

        Args:
            data: DataFrame with columns specified in config

        Returns:
            Plotly Figure object ready for rendering

        Raises:
            KeyError: If required columns are missing
            ValueError: If data is invalid
        \"\"\"
        # Validate data
        self._validate_data(data)

        # Create figure
        fig = go.Figure()

        # Add traces based on color grouping
        if self.color_by and self.color_by in data.columns:
            for group_value in data[self.color_by].unique():
                group_data = data[data[self.color_by] == group_value]
                fig.add_trace(go.Scatter(  # Or appropriate trace type
                    x=group_data[self.x_column],
                    y=group_data[self.y_column],
                    name=str(group_value),
                    mode='markers'  # Adjust as needed
                ))
        else:
            fig.add_trace(go.Scatter(
                x=data[self.x_column],
                y=data[self.y_column],
                mode='markers'
            ))

        # Apply common layout
        self.apply_common_layout(fig)

        # Apply custom styling
        fig.update_layout(
            xaxis_title=self.config.get("x_label", self.x_column),
            yaxis_title=self.config.get("y_label", self.y_column),
            # Add more layout options
        )

        return fig

    def _validate_data(self, data: pd.DataFrame) -> None:
        \"\"\"Validate that data has required columns.\"\"\"
        required_columns = [self.x_column, self.y_column]
        missing = [col for col in required_columns if col not in data.columns]

        if missing:
            raise KeyError(f\"Missing required columns: {missing}\")

        if len(data) == 0:
            raise ValueError(\"Data is empty\")

    @staticmethod
    def render_config_ui() -> Dict[str, Any]:
        \"\"\"
        Render Streamlit UI for plot configuration.

        Returns:
            Dict with configuration values from user input
        \"\"\"
        import streamlit as st

        config = {}

        # Get data to show available columns
        from src.web.state_manager import StateManager
        data = StateManager.get_data()

        if data is not None and not data.empty:
            columns = data.columns.tolist()

            config[\"x_column\"] = st.selectbox(\"X-axis Column\", columns)
            config[\"y_column\"] = st.selectbox(\"Y-axis Column\", columns)

            if st.checkbox(\"Color by column\"):
                config[\"color_by\"] = st.selectbox(\"Color Column\", columns)

            # Add more configuration options
            config[\"x_label\"] = st.text_input(\"X-axis Label\", value=config[\"x_column\"])
            config[\"y_label\"] = st.text_input(\"Y-axis Label\", value=config[\"y_column\"])

        return config
```

### Step 2: Register in Factory

**File**: `src/plotting/plot_factory.py`

```python
from src.plotting.types.my_new_plot import MyNewPlot

class PlotFactory:
    \"\"\"Factory for creating plot instances.\"\"\"

    _plot_types = {
        \"bar\": BarPlot,
        \"line\": LinePlot,
        \"scatter\": ScatterPlot,
        \"grouped_bar\": GroupedBarPlot,
        \"grouped_stacked_bar\": GroupedStackedBarPlot,
        \"my_new_plot\": MyNewPlot,  # ← Add your plot here
    }

    # ... rest of the factory code
```

### Step 3: Add UI Integration

**File**: `src/web/ui/components/plot_manager_components.py`

```python
def render_create_plot_section(facade: BackendFacade):
    \"\"\"Render the plot creation interface.\"\"\"

    plot_type = st.selectbox(
        \"Plot Type\",
        [\"bar\", \"line\", \"scatter\", \"grouped_bar\",
         \"grouped_stacked_bar\", \"my_new_plot\"],  # ← Add here
        format_func=lambda x: {
            \"bar\": \"Bar Chart\",
            \"line\": \"Line Chart\",
            \"scatter\": \"Scatter Plot\",
            \"grouped_bar\": \"Grouped Bar Chart\",
            \"grouped_stacked_bar\": \"Grouped Stacked Bar\",
            \"my_new_plot\": \"My New Plot\",  # ← And here
        }[x]
    )
```

### Step 4: Create Unit Tests

**File**: `tests/unit/test_my_new_plot.py`

```python
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch

from src.plotting.types.my_new_plot import MyNewPlot


class TestMyNewPlot:
    \"\"\"Unit tests for MyNewPlot.\"\"\"

    @pytest.fixture
    def sample_data(self):
        \"\"\"Create sample data for testing.\"\"\"
        return pd.DataFrame({
            \"x_col\": [1, 2, 3, 4, 5],
            \"y_col\": [10, 20, 15, 25, 30],
            \"group\": [\"A\", \"A\", \"B\", \"B\", \"A\"]
        })

    @pytest.fixture
    def plot_config(self):
        \"\"\"Create plot configuration.\"\"\"
        return {
            \"x_column\": \"x_col\",
            \"y_column\": \"y_col\",
            \"color_by\": \"group\"
        }

    def test_initialization(self, plot_config):
        \"\"\"Test plot initializes with config.\"\"\"
        plot = MyNewPlot(plot_config)
        assert plot.x_column == \"x_col\"
        assert plot.y_column == \"y_col\"
        assert plot.color_by == \"group\"

    def test_create_figure_basic(self, sample_data, plot_config):
        \"\"\"Test figure creation with valid data.\"\"\"
        plot = MyNewPlot(plot_config)
        fig = plot.create_figure(sample_data)

        assert fig is not None
        assert len(fig.data) > 0  # Has traces

    def test_create_figure_missing_column(self, sample_data):
        \"\"\"Test error when column is missing.\"\"\"
        config = {\"x_column\": \"missing\", \"y_column\": \"y_col\"}
        plot = MyNewPlot(config)

        with pytest.raises(KeyError, match=\"Missing required columns\"):
            plot.create_figure(sample_data)

    def test_create_figure_empty_data(self, plot_config):
        \"\"\"Test error with empty DataFrame.\"\"\"
        plot = MyNewPlot(plot_config)
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match=\"Data is empty\"):
            plot.create_figure(empty_data)

    @patch(\"src.plotting.types.my_new_plot.st\")
    def test_render_config_ui(self, mock_st, sample_data, plot_config):
        \"\"\"Test UI configuration rendering.\"\"\"
        # Mock StateManager
        with patch(\"src.plotting.types.my_new_plot.StateManager\") as mock_sm:
            mock_sm.get_data.return_value = sample_data
            mock_st.selectbox.side_effect = [\"x_col\", \"y_col\", \"group\"]
            mock_st.checkbox.return_value = True
            mock_st.text_input.side_effect = [\"X Label\", \"Y Label\"]

            config = MyNewPlot.render_config_ui()

            assert config[\"x_column\"] == \"x_col\"
            assert config[\"y_column\"] == \"y_col\"
            assert config[\"color_by\"] == \"group\"
```

### Step 5: Create Integration Test

**File**: `tests/integration/test_plot_lifecycle.py`

Add test case:

```python
def test_my_new_plot_lifecycle(self):
    \"\"\"Test complete lifecycle of MyNewPlot.\"\"\"
    data = pd.DataFrame({
        \"x\": [1, 2, 3],
        \"y\": [10, 20, 30]
    })

    config = {
        \"x_column\": \"x\",
        \"y_column\": \"y\",
        \"title\": \"Test Plot\"
    }

    # Create plot via factory
    plot = PlotFactory.create_plot(\"my_new_plot\", config)
    assert isinstance(plot, MyNewPlot)

    # Generate figure
    fig = plot.create_figure(data)
    assert fig is not None
    assert len(fig.data) > 0

    # Verify serialization
    plot_dict = plot.to_dict()
    assert plot_dict[\"type\"] == \"my_new_plot\"
    assert plot_dict[\"config\"] == config
```

## Checklist

- [ ] Created plot class in `src/plotting/types/`
- [ ] Implemented `create_figure()` method
- [ ] Implemented `render_config_ui()` static method
- [ ] Registered in `PlotFactory._plot_types`
- [ ] Added to UI dropdown in `plot_manager_components.py`
- [ ] Created unit tests
- [ ] Created integration test
- [ ] Tested with real data
- [ ] Verified publication quality (14pt+ fonts, vector-ready)
- [ ] Updated documentation if needed

## Common Patterns

### Error Bars

```python
fig.add_trace(go.Scatter(
    x=data[x_col],
    y=data[y_col],
    error_y=dict(
        type='data',
        array=data[error_col]
    )
))
```

### Multiple Y-axes

```python
fig.add_trace(go.Scatter(y=data[y1_col]), yaxis=\"y1\")
fig.add_trace(go.Scatter(y=data[y2_col]), yaxis=\"y2\")

fig.update_layout(
    yaxis=dict(title=\"Y1\"),
    yaxis2=dict(title=\"Y2\", overlaying=\"y\", side=\"right\")
)
```

### Interactive Features

```python
fig.update_traces(
    hovertemplate=\"<b>%{x}</b><br>Value: %{y}<extra></extra>\"
)

fig.update_layout(
    hovermode=\"closest\",
    dragmode=\"zoom\"
)
```

## References

- Base Class: `src/plotting/base_plot.py`
- Factory: `src/plotting/plot_factory.py`
- Examples: `src/plotting/types/grouped_bar_plot.py`
- Tests: `tests/unit/test_plot_classes.py`
