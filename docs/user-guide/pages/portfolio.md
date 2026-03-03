# Portfolio Page

## Overview

The Portfolio page lets you save and reload your entire RING-5 workspace in a
single operation. Every piece of your analysis session -- loaded data, plots,
shaper pipelines, settings, and operation history -- is captured into one
portfolio file.

You can think of a portfolio as a bookmark for your analysis. If you need to
stop working, share your setup with a colleague, or return to a known good
state after experimenting, portfolios make that possible.

To open the Portfolio page, click **Save/Load Portfolio** in the sidebar
navigation.


## What Gets Saved

When you save a portfolio, RING-5 captures a complete snapshot of your current
session. The following table summarizes everything that is included.

| Category | What is saved |
|---|---|
| Data | The full working DataFrame, including any transformations you have applied |
| Plots | Every plot you have created, with its name, type, and configuration |
| Shaper pipelines | The per-plot shaper pipeline steps and their settings |
| Plot settings | All styling choices -- layout, typography, legends, axes, colors, and advanced settings |
| Parser configuration | Stats directory path, filename pattern, simulator selection, and variable definitions |
| Scanned variables | Variables discovered during scanning, so you do not need to re-scan after loading |
| Data source path | The original CSV file path, if one was used |
| Operation history | The complete audit trail of every data manager operation performed during the session |

This means that when you load a portfolio, you return to exactly the state you
were in when you saved it. You can continue editing plots, applying
transformations, or adding new data without any manual reconfiguration.

**Note:** Plotly figure objects themselves are not stored. They are regenerated
automatically the first time you view a plot after loading a portfolio. This
regeneration is transparent and requires no action on your part.


## Saving a Portfolio

The Save section appears in the left column of the Portfolio page.

### Steps

1. Navigate to the **Save/Load Portfolio** page using the sidebar.
2. In the **Save Portfolio** section on the left, enter a name for your
   portfolio in the **Portfolio Name** text field. The default name is
   `my_portfolio`.
3. Click the **Save Portfolio** button.

You should see a success notification confirming that the portfolio was saved.
The page refreshes, and your new portfolio appears in both the Load selector
and the Manage section below.

### What Happens Behind the Scenes

RING-5 collects the current state from all parts of the application -- your
data, every plot with its configuration and pipeline, the parser settings, and
the full operation history. It writes everything to a single JSON file in the
local `.ring5/portfolios/` directory within the project folder.

If the portfolio name contains special characters such as slashes, they are
automatically replaced with underscores to produce a valid filename.


## Loading a Portfolio

The Load section appears in the right column of the Portfolio page.

### Steps

1. Navigate to the **Save/Load Portfolio** page using the sidebar.
2. In the **Load Portfolio** section on the right, open the **Select
   Portfolio** dropdown. You should see a list of all previously saved
   portfolios.
3. Select the portfolio you want to restore.
4. Click the **Load Portfolio** button.

You should see a success notification confirming that the portfolio was loaded.
The entire application refreshes, and all pages now reflect the restored state.

### After Loading

Once a portfolio is loaded:

- The **Data Source** page shows the original parser configuration, including
  the stats path, filename pattern, and variable definitions. Scanned
  variables are available without needing to re-scan.
- The **Data Managers** page has access to the restored DataFrame. The
  Operations History tab shows all operations from the saved session.
- The **Manage Plots** page displays all plots with their configurations,
  shaper pipelines, and processed data intact. Figures are regenerated on the
  first render.

You can continue working from exactly where you left off -- create new plots,
apply additional transformations, or modify existing configurations.

### If No Portfolios Exist

If you have not saved any portfolios yet, the Load section displays a warning
message: "No portfolios found. Save one first!" You need to save at least one
portfolio before you can load.


## Deleting a Portfolio

Below the Save and Load columns, the **Manage Saved Portfolios** section lists
all existing portfolios. Each portfolio appears as an expandable item.

### Steps

1. Scroll down to the **Manage Saved Portfolios** section.
2. Click on the name of the portfolio you want to delete to expand it.
3. Click the **Delete** button inside the expanded section.

You should see a notification confirming that the portfolio was deleted. The
portfolio is removed from the list and from the Load dropdown.

Deletion is immediate and permanent. There is no undo operation, so make sure
you no longer need the portfolio before deleting it.


## Portfolio Storage

Portfolios are stored as JSON files in the `.ring5/portfolios/` directory
inside your project folder. This directory is created automatically the first
time you save a portfolio.

```
your-project/
  .ring5/
    portfolios/
      my_portfolio.json
      ipc_analysis.json
      cache_study_v2.json
```

### Persistence Between Sessions

Portfolio files remain on disk even after you close the application. When you
restart RING-5, all previously saved portfolios appear in the Load dropdown
and the Manage section, ready to be restored.

### File Format

Each portfolio is a self-contained JSON file. It includes the full dataset
serialized as an embedded CSV string, all plot configurations, pipeline
definitions, parser state, and operation history. You do not need to keep the
original data files accessible for a portfolio to load successfully -- the
data is embedded directly in the portfolio file.

### Schema Compatibility

RING-5 includes an automatic migration system for portfolio files. If you load
a portfolio that was saved with an older version of the application, it is
silently upgraded to the current format. Your original portfolio file is not
modified on disk; the migration happens in memory during the load process.


## Tips for Working with Portfolios

### Save Before Risky Operations

Before applying a complex data transformation or a series of shaper steps that
you are unsure about, save a portfolio. If the result is not what you expected,
you can load the portfolio to return to your previous state without needing to
redo earlier work.

### Use Descriptive Names

Choose portfolio names that help you remember what each one contains.
Names like `ipc_comparison_after_outlier_removal` or
`cache_miss_rates_final` are more useful than `test1` or `backup`.

### Portfolios Capture Everything

A portfolio captures the full state, including all data manager operations you
have performed. This means that if you save a portfolio after reducing seeds
and removing outliers, those transformations are reflected in the restored
data. You do not need to re-apply them after loading.

### Sharing Portfolios

Because portfolio files are self-contained JSON files, you can share them with
colleagues. Copy the `.json` file from your `.ring5/portfolios/` directory and
place it in the same directory on another machine. The portfolio appears in
that user's Load dropdown on the next page visit.

### Working with Multiple Analyses

You can save multiple portfolios for different stages of your analysis or for
different research questions. For example, you might save one portfolio after
initial data loading and cleaning, another after creating a specific set of
plots, and a third with final publication-ready configurations. This lets you
branch your analysis without losing earlier work.

### Storage Considerations

Portfolio file size depends primarily on the size of your dataset. Each
portfolio embeds the full DataFrame as a CSV string. For a dataset with 10,000
rows, expect a portfolio file of roughly 1 MB. Per-plot processed data adds
proportional overhead. If storage space is a concern, delete portfolios you no
longer need using the Manage section.
