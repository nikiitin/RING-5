# Portfolios

## Overview

Portfolios save your entire RING-5 workspace as a single snapshot. When you save
a portfolio, RING-5 captures everything in your current session: loaded data, all
plots with their configurations and shaper pipelines, parser settings, data
manager operation history, and global application configuration.

You can restore a portfolio later to pick up exactly where you left off. This
makes portfolios useful for preserving your analysis state between sessions,
sharing setups with collaborators, and keeping backups before trying destructive
data operations.


## Why Use Portfolios

Portfolios solve several common problems in data analysis workflows.

**Session persistence.** RING-5 runs as a web application, and your session data
is lost when you close the browser or restart the server. Saving a portfolio
preserves your entire analysis state so you can resume later.

**Experiment snapshots.** When you are comparing multiple gem5 configurations,
you may want to save the state of your analysis at key milestones. Portfolios
let you capture a snapshot before and after major changes.

**Safe experimentation.** Before applying a data manager operation that modifies
your dataset (such as filtering rows or renaming columns), you can save a
portfolio as a checkpoint. If the operation produces unexpected results, you can
load the portfolio to restore your previous state.

**Sharing configurations.** If a colleague needs to reproduce your plots or
analysis pipeline, you can share the portfolio JSON file. They can load it into
their RING-5 instance to get your exact setup.


## What Gets Saved

A portfolio captures the following data from your session:

| Component              | Description                                      |
|------------------------|--------------------------------------------------|
| Loaded dataset         | The full working DataFrame, serialized as CSV     |
| All plots              | Plot type, name, configuration, and processed data|
| Shaper pipelines       | The per-plot data transformation steps            |
| Legend mappings         | Custom legend label assignments per plot          |
| Parser configuration   | Stats path, file pattern, and variable definitions|
| Scanned variables      | Variables discovered by the stats file scanner    |
| Application config     | Global settings such as the original CSV path     |
| Operation history      | Complete audit trail of data manager operations   |

Portfolios do not save transient UI state such as auto-refresh toggles, dialog
positions, or widget focus. These reset to their defaults when you load a
portfolio. Plot figures (the rendered chart objects) are also not saved -- they
are regenerated automatically when you view a plot after loading.


## Saving a Portfolio

1. Navigate to the **Portfolio** page using the sidebar.
2. In the **Save Portfolio** section on the left, enter a descriptive name in
   the text field.
3. Click the **Save Portfolio** button.

You should see a confirmation toast message saying "Portfolio saved" followed by
the name you entered. The portfolio now appears in both the Load section and the
Manage section on the same page.

If the name field is empty when you click Save, RING-5 displays an error. Enter
a name and try again.

You can save a portfolio even when no data is loaded. This creates a
"config-only" portfolio that captures your parser settings and application
configuration without any dataset. This is useful for saving a parser
configuration that you want to reuse with different stats files.


## Loading a Portfolio

1. Navigate to the **Portfolio** page using the sidebar.
2. In the **Load Portfolio** section on the right, select a portfolio from the
   dropdown.
3. Click the **Load Portfolio** button.

You should see a confirmation toast message saying "Portfolio loaded" followed by
the portfolio name. The application reloads completely, and all pages reflect the
restored state.

When you load a portfolio, your current session is fully replaced. Any unsaved
changes to your data, plots, or configurations are lost. If you want to keep
your current work, save it as a separate portfolio before loading a different
one.

After loading, you can verify the restoration:

- **Data Source page** -- Your parser configuration, stats path, and file
  pattern are restored. Scanned variables are available without needing to
  re-scan.
- **Data Managers page** -- The loaded DataFrame is ready for further
  transformations. The Operations History tab shows all operations from the
  saved session.
- **Manage Plots page** -- All your plots appear with their configurations,
  shaper pipelines, and processed data. Figures render automatically on first
  view.


## Managing Portfolios

The bottom section of the Portfolio page, titled **Manage Saved Portfolios**,
lists all saved portfolios. Each portfolio appears as an expandable entry with
a **Delete** button.

To delete a portfolio you no longer need:

1. Scroll to the **Manage Saved Portfolios** section.
2. Expand the entry for the portfolio you want to remove.
3. Click the **Delete** button.

You should see a toast confirmation that the portfolio was deleted. The entry
disappears from both the management list and the load dropdown.

Deletion is permanent. There is no undo. If you might need the portfolio later,
consider keeping it rather than deleting it.


## Where Portfolios Are Stored

Portfolios are saved as JSON files in the `.ring5/portfolios/` directory inside
your project root. Each portfolio is a single `.json` file named after the
portfolio name you provided.

These files persist on disk between application sessions. As long as the
`.ring5/portfolios/` directory is not deleted, your portfolios remain available
every time you start RING-5.

Portfolio files are plain-text JSON that you can inspect or back up manually.
The dataset is embedded as a CSV string within the JSON, so each file is
self-contained.


## Best Practices

**Save before major data operations.** Before running a data manager operation
that modifies your dataset -- such as filtering, pivoting, or dropping columns
-- save a portfolio. This gives you a rollback point if the operation does not
produce the results you expected.

**Use descriptive names.** Include the date, experiment name, or purpose in your
portfolio name. For example, `ipc_analysis_march03` or
`baseline_vs_optimized_final` are easier to find later than `my_portfolio`.

**Save frequently during long sessions.** If you are spending an extended period
on data analysis, save portfolios at regular intervals. This protects against
browser crashes, server restarts, or accidental data changes.

**Save before switching data sources.** If you plan to load a different CSV file
or re-run the parser with different settings, save your current state first.
Loading new data replaces the current dataset, and without a portfolio you
cannot return to your previous analysis.

**Keep portfolios for reproducibility.** When you publish results, keep the
portfolio that produced your final figures. This allows you or your reviewers
to reproduce the exact analysis and plot configurations later.
