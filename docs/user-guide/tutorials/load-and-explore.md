---
title: "Tutorial: Load and Explore Data"
parent: Tutorials
grand_parent: User Guide
nav_order: 1
---

# Tutorial: Load and Explore Data

In this tutorial, you will learn how to load simulation data into RING-5 and
explore it using the Data Managers tools. You will walk through two loading
methods -- importing a CSV file from the recent pool and parsing raw gem5
stats files -- then inspect, reduce, and clean your dataset.

## Prerequisites

Before starting, make sure you have:

- RING-5 running in your browser (typically at `http://localhost:8501`)
- Either a CSV file with gem5 simulation results, or a directory containing
  raw gem5 output (`stats.txt` files)

If you want to follow along with the sample data shipped with RING-5, the
file is located at `tests/e2e/fixtures/sample_data.csv`. It contains 18 rows
and 8 columns covering 3 benchmarks, 3 configurations, and 2 random seeds.

---

## Option A: Load from CSV (Quick Path)

This is the fastest way to get data into RING-5 when you already have a
CSV file from a previous parsing session or from an external source.

### Navigate to Data Source

Open RING-5 in your browser. The application starts on the **Data Source**
page by default. You should see a heading that reads **Step 1: Choose Data
Source**, followed by an information box and a segmented control with three
options.

### Select Load from Recent

Click **Load from Recent** in the segmented control. This section displays
CSV files that have been previously parsed or added to the RING-5 data pool.

You should see a list of available CSV files, each displayed as a card with
**Load**, **Preview**, and **Delete** buttons. If the list is empty, you
have not parsed any data yet -- skip ahead to Option B below.

### Load Your CSV File

Click the **Load** button on the CSV file you want to work with. RING-5
reads the file and loads it into the active session.

You should see a success message reporting the number of rows loaded
(for example, "Loaded 18 rows!"), followed by a data preview table and
column details.

### Verify the Data

After loading, a summary bar appears at the top of the main content area
showing three metrics: row count, column count, and source filename. Confirm
these match your expectations.

Your CSV file should include at least two categorical columns that identify
each experiment:

| Required Column | Purpose |
|-----------------|---------|
| `benchmark_name` | Identifies the workload (e.g., `mcf`, `omnetpp`, `xalancbmk`) |
| `config_description` | Identifies the hardware configuration (e.g., `baseline`, `optimized`) |

Additional numeric columns such as `system.cpu.ipc`, `system.cpu.numCycles`,
`simTicks`, or `system.cpu.dcache.overall_miss_rate` provide the metrics you
will analyze and plot on later pages.

---

## Option B: Parse from gem5 Stats Files (Full Path)

Use this method when you have raw gem5 simulator output and need to extract
specific metrics into a structured dataset.

### Navigate to Data Source in Parse Mode

Open the **Data Source** page. The segmented control defaults to
**Parse gem5 Stats Files**, which is the option you want. You should see the
**gem5 Stats Parser Configuration** section appear below.

### Set the Root Path

In the **File Location** section, enter the absolute path to your gem5
output directory in the **Stats directory path** field. RING-5 searches
this directory recursively, so you can point it at a parent directory that
contains multiple benchmark results in subdirectories.

For example:

```
/home/user/gem5-results/spec2017/
```

### Set the File Pattern

In the **File pattern** field, confirm the filename RING-5 should look for.
The default value is `stats.txt`, which is the standard gem5 output filename.
If your simulations use a different naming convention, update this value
(for example, `*.txt` to match all text files).

### Scan for Variables

Click the **Quick Scan** button to discover which metrics are available in
your stats files. RING-5 scans a sample of files and reports the variables
it finds.

You should see a progress indicator while scanning is in progress. When the
scan completes, a success message appears reporting the number of variables
found (for example, "Scanner found 142 variables"). The scan results are
stored in the session so you can select from them in the next step.

If you need an exhaustive scan of all files, check the **Deep Scan (check
all files)** checkbox before clicking Quick Scan. Deep scans take longer but
ensure no variables are missed.

### Select Variables to Extract

Click the **Add Variable** button to open the variable selection dialog. You
have two choices:

**Search Scanned Variables** -- Type a variable name in the search box to
filter the scan results. Select the variable you want and click **Add to
Configuration**. Repeat for each variable you need.

**Manual Entry** -- If you know the exact variable name and type, switch to
manual entry mode. Enter the variable name, select its type (scalar, vector,
distribution, or configuration), and provide any required details.

Common variable types you might add:

| Type | Example | Description |
|------|---------|-------------|
| Scalar | `system.cpu.ipc` | A single numeric value per simulation dump |
| Vector | `system.cpu.op_class` | An array of values with named entries |
| Distribution | `system.l2.miss_latency` | A statistical distribution with buckets |
| Configuration | `system.cpu.type` | A metadata string from `config.ini` |

After adding variables, you should see them listed in the Variables to
Extract section with their types and configuration details.

### Choose a Parsing Strategy

In the **Parsing Strategy** section, select one of the two available
strategies:

**Simple (stats.txt only)** -- Parses only the stats files. This is the
fastest option and works for most use cases where you need statistical
counters from your simulation runs.

**Config-Aware (Integrates config.ini)** -- Reads both stats files and the
`config.ini` files that gem5 generates. Choose this when you want to extract
simulation configuration parameters (such as CPU type, cache sizes, or clock
frequency) as additional columns in your dataset.

### Parse the Data

Click the **Parse gem5 Stats Files** button at the bottom of the page. A
progress dialog opens showing the parsing status as each file is processed.

You should see a progress bar advancing as files complete. When parsing
finishes, a finalization step aggregates the results into a single CSV file
and loads it into the session. The dialog reports the total number of rows
generated (for example, "Done! Generated 18 rows.").

Click **Close & Reload** to dismiss the dialog. The parsed CSV is
automatically added to the recent file pool, so you can reload it later
without re-parsing.

---

## Step 1: Explore Your Data

With data loaded through either option, click the **Data Managers** button
in the sidebar to navigate to the Data Managers page.

You should see a header reading **Data Managers & Transformations**, an
information box, and a row of seven tabs.

### Summary Tab

The Summary tab is selected by default. At the top, four metric cards
report the current dataset shape:

- **Rows** -- total number of data rows (18 for the sample data)
- **Columns** -- total number of columns (8 for the sample data)
- **Memory** -- approximate memory footprint in megabytes
- **Missing Values** -- total count of null cells across the dataset

Below the metrics, a quick preview shows the first 20 rows of your data.
An expandable **Column Details** section lists each column with its data
type, non-null count, and number of unique values.

At the bottom, the **Data Statistics** section splits into two columns. The
left column shows standard descriptive statistics (count, mean, standard
deviation, min, quartiles, max) for all numeric columns. The right column
lists each categorical column with its unique-value count.

### Data Visualization Tab

Click the **Data Visualization** tab to browse the full dataset. You should
see an interactive table with search and pagination controls.

Use the **Search in column** dropdown and **Search term** field to filter
rows. For example, select `benchmark_name` in the dropdown and type `mcf`
to see only the mcf benchmark rows. You should see an info bar reporting the
number of matching rows (for example, "Found 6 matching rows out of 18
total").

Under **Display Options**, you can select specific columns to show and
adjust the number of rows per page (20, 50, 100, 500, or All).

Try clicking column headers in the data table to sort by different values.
Sorting by `system.cpu.ipc` in descending order quickly reveals which
configuration achieves the highest throughput.

---

## Step 2: Reduce Seeds

If your dataset contains multiple random seeds per experiment (as the sample
data does with seeds 0 and 1), the Seeds Reducer lets you aggregate them
into summary statistics.

### Open the Seeds Reducer

Click the **Seeds Reducer** tab in Data Managers. You should see a
description of the tool and a **Column to reduce over** dropdown.

### Configure the Reduction

Select the column that represents repeated runs. In the sample data, this is
the `seed` column. If your data uses a different name (such as
`random_seed`, `iteration`, or `run_id`), select that instead.

Below the dropdown, two multiselect widgets appear side by side:

**Categorical columns (for grouping)** -- These columns define the groups.
For the sample data, `benchmark_name` and `config_description` should be
selected. Each unique combination of these values becomes one row in the
output.

**Numeric columns (for statistics)** -- These are the columns that will be
averaged. All numeric columns are selected by default, including
`system.cpu.ipc`, `system.cpu.numCycles`, `simTicks`,
`system.cpu.dcache.overall_miss_rate`, and `system.cpu.committedInsts`.

### Apply the Reduction

Click the **Apply Seeds Reducer** button. You should see a success message
showing the reduction (for example, "Reduced from 18 to 9 rows!"), along
with metric cards showing the original and reduced row counts and a preview
of the result.

The reducer calculates the mean for each numeric column and creates
additional `.sd` columns containing the standard deviation. These standard
deviation columns are useful later when you want to display error bars on
your plots.

### Confirm the Result

Review the preview table to verify the results look correct. When you are
satisfied, click the **Confirm and Apply Seeds Reducer** button (highlighted
in blue). This replaces the active dataset with the reduced version.

You should see a confirmation notification. The Summary tab will now show
9 rows instead of 18, and the column count will have increased to account
for the new `.sd` columns.

---

## Step 3: Remove Outliers (Optional)

If your dataset contains extreme values that could skew your analysis, the
Outlier Remover helps you identify and remove them.

### Open the Outlier Remover

Click the **Outlier Remover** tab. You should see a description explaining
that the tool removes outliers using the IQR (interquartile range) method —
rows outside `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]` (per group) are removed.

### Select a Numeric Column

In the **Column to check for outliers** dropdown, select the metric you
want to clean. For example, choose `system.cpu.ipc` to look for unusually
high or low IPC values.

Below the dropdown, four metric cards display the current distribution of
the selected column: Min, Q3, Max, and Mean. These give you a quick sense
of whether outliers might be present.

### Configure Grouping

In the **Group by columns** multiselect on the right, choose the
categorical columns that define your experimental groups. For the sample
data, select `benchmark_name` and `config_description`.

Grouping ensures that outlier detection is performed within each
experimental group rather than across the entire dataset. Avoid including
seed or iteration columns in the grouping, as this would create single-row
groups where outlier detection cannot work.

### Apply and Confirm

Click the **Apply Outlier Remover** button. You should see a report showing
how many rows were flagged as outliers and removed, along with metric cards
comparing original, filtered, and removed row counts.

Review the filtered data preview. If the results look correct, click
**Confirm and Apply Outlier Remover** to commit the changes. The active
dataset is updated and a confirmation notification appears.

---

## Summary

In this tutorial, you learned how to:

1. **Load data** into RING-5 -- either from the recent CSV pool or by
   parsing raw gem5 stats files with the built-in scanner and parser
2. **Inspect your dataset** using the Summary and Data Visualization tabs
   on the Data Managers page
3. **Reduce seeds** to aggregate multiple simulation runs into mean values
   with standard deviations
4. **Remove outliers** to clean extreme values from your dataset

Your data is now loaded, explored, and cleaned. You are ready to create
your first visualization.

---

## Next Steps

Continue to the [Create a Bar Chart](create-bar-chart.md) tutorial to learn
how to build a grouped bar chart comparing performance metrics across your
benchmarks and configurations.
