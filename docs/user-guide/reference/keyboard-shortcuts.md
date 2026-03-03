# Keyboard Shortcuts

RING-5 is a Streamlit web application. Most interactions happen through the sidebar navigation, dropdown menus, pills, toggles, and buttons. There are no application-specific keyboard shortcuts.

However, a few shortcuts from Streamlit and the Plotly charting library are available.

---

## Streamlit Shortcuts

These shortcuts work anywhere in the application.

| Shortcut | Action |
|----------|--------|
| `R` | Rerun the app (refreshes all components). |
| `C` | Clear the Streamlit cache and rerun. |

---

## Plotly Chart Interactions

When you hover your mouse over an interactive Plotly chart, the following mouse and keyboard actions are available.

| Action | Effect |
|--------|--------|
| Scroll wheel | Zoom in or out on the chart. |
| Click and drag | Pan the chart view. |
| Double-click | Reset the chart to its original zoom level and position. |
| Click a legend item | Toggle that data series on or off. |
| Double-click a legend item | Isolate that series (hide all others). |
| Hover over a data point | Display a tooltip with the exact value. |

The Plotly toolbar in the top-right corner of the chart provides additional actions: download as PNG, zoom to selection, autoscale, and reset axes.

These interactions apply only to the Plotly rendering engine. Matplotlib-rendered charts are static images and do not support interactive gestures.

---

## Dialog Shortcuts

| Shortcut | Action |
|----------|--------|
| `Escape` | Close an open dialog or modal window. |

---

## Plotly Toolbar Buttons

The Plotly toolbar appears in the top-right corner of each interactive chart when you hover over it. Each icon provides a specific action.

| Button | Action |
|--------|--------|
| Camera icon | Download the current chart view as a PNG image. |
| Magnifying glass | Switch to box-select zoom mode (click and drag to zoom into a region). |
| Pan icon | Switch to pan mode (click and drag to move the view). |
| Home icon | Reset the chart axes to the original auto-scaled range. |
| Autoscale icon | Fit the chart view to the current data extents. |

---

## Navigating the Application

All primary functionality is accessed through the sidebar on the left side of the screen. Click a page name in the sidebar to navigate between Data Source, Data Managers, Manage Plots, Portfolio, and Documentation pages.

On each page, you interact with controls directly. Settings pills (the horizontal tab-like buttons) switch between configuration sections. Toggles, dropdowns, number inputs, and color pickers all respond to mouse clicks. There are no hidden keyboard-only features to discover.
