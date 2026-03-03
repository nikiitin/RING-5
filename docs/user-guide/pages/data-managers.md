# Data Managers

The Data Managers page is where you clean, transform, and prepare your loaded
dataset before creating plots. It sits between the Data Source page (where you
load data) and the Manage Plots page (where you visualize it).

You can reach it by clicking **Data Managers** in the sidebar after loading data
on the Data Source page. If no data has been loaded yet, the page displays a
warning: "No data loaded. Please load data from the Data Source page."

The page is organized into seven tabs:

| Tab | Purpose |
|-----|---------|
| Summary | Inspect row count, column types, and basic statistics |
| Data Visualization | Browse the full dataset with search and pagination |
| Seeds Reducer | Aggregate repeated simulation runs into summary statistics |
| Outlier Remover | Detect and remove statistical outliers from numeric columns |
| Preprocessor | Create new computed columns from arithmetic on existing ones |
| Mixer | Merge multiple columns into a single column |
| Operations History | Review every transformation applied in the current session |

Each tab operates independently. Changing settings in one tab does not trigger
reloads in the others. Every transformation tab follows a two-step
**preview-then-confirm** workflow so you can inspect results before committing
changes to your dataset.

---

## Summary Tab

The Summary tab gives you a quick overview of the dataset currently in memory.
You should see it by default when you first open the Data Managers page.

At the top, four metric cards report:

- **Rows** -- total number of data rows
- **Columns** -- total number of columns
- **Memory** -- approximate memory footprint in megabytes
- **Missing Values** -- total count of null or missing cells across the dataset

Below the metrics, a quick preview table shows the first 20 rows.
An expandable **Column Details** section lists each column with its data type,
non-null count, null count, and number of unique values.

At the bottom, a **Data Statistics** section is split into two columns. The left
column shows the standard `describe()` summary for all numeric columns (count,
mean, standard deviation, min, quartiles, max). The right column lists each
categorical column with its unique-value count and, for columns with ten or
fewer unique values, the actual values.

---

## Data Visualization Tab

The Data Visualization tab lets you explore the full dataset interactively. Click
the **Data Visualization** tab to open it.

### Searching

At the top you will find two controls for filtering rows:

1. **Search in column** -- a dropdown that defaults to "All Columns." You can
   select a specific column to narrow the search.
2. **Search term** -- a text field where you type a case-insensitive substring to
   match against.

When you enter a search term, the table updates to show only matching rows. An
info bar reports how many rows matched out of the total.

### Display Options

Below the search area you can customize what you see:

- **Select columns to display** -- a multiselect that lets you hide columns you
  do not need. Leave it empty to show all columns.
- **Rows per page** -- choose 20, 50, 100, 500, or "All" rows visible at once.

When pagination is active, a **Page** number input appears so you can navigate
between pages. An info bar shows which row range is currently displayed.

### Downloading

At the bottom, a **Download Current View as CSV** button exports whatever is
currently displayed (including any active search filter and column selection) as
a CSV file.

---

## Seeds Reducer Tab

When you run gem5 simulations with multiple random seeds, your dataset contains
repeated measurements for each configuration. The Seeds Reducer aggregates
those repeated runs into a single mean value per configuration, with an
accompanying standard deviation column.

Click the **Seeds Reducer** tab to open it.

### When to Use It

Use the Seeds Reducer when your data contains a column like `random_seed`,
`iteration`, or `run_id` that distinguishes repeated runs of the same
configuration. After reduction, each unique configuration appears as one row
with mean and standard deviation computed across all its seeds.

### Step-by-Step

1. **Select the column to reduce over.** A dropdown labeled "Column to reduce
   over" lists all columns with 50 or fewer unique values as well as all
   text-type columns. If your data contains a `random_seed` column, it is
   selected by default.

2. **Choose group-by columns.** In the left panel under "Group by columns,"
   select the categorical columns that define a unique configuration (for
   example, `benchmark_name` and `config_description`). All categorical columns
   are selected by default.

3. **Choose numeric columns.** In the right panel under "Calculate stats for,"
   select the numeric columns you want to aggregate. All numeric columns are
   selected by default.

4. **Click "Apply Seeds Reducer."** You should see a success message reporting
   how many rows were reduced (for example, "Reduced from 500 to 50 rows!"),
   along with before/after metric cards and a preview table.

5. **Review the preview.** Check that the row count and values look correct.

6. **Click "Confirm and Apply Seeds Reducer."** This replaces your working
   dataset with the reduced version. A confirmation toast appears and the page
   refreshes.

### What It Produces

For each numeric column you selected, the reducer creates:

- The original column name, now containing the **mean** across seeds.
- A companion column with a `.sd` suffix containing the **standard deviation**.

These `.sd` columns are recognized throughout RING-5. When you later normalize
data in the plotting pipeline, the standard deviation columns are automatically
scaled by the same baseline value so that error bars remain correct.

---

## Outlier Remover Tab

The Outlier Remover filters out rows containing extreme values in a numeric
column. It uses a Q3-based detection method: within each group, any row where
the target column exceeds the third quartile (75th percentile) is flagged for
removal.

Click the **Outlier Remover** tab to open it.

### When to Use It

Use the Outlier Remover when a handful of simulation runs produced anomalously
high values that would distort your analysis. Grouping ensures that the Q3
threshold is calculated per configuration rather than globally.

### Step-by-Step

1. **Select the target column.** A dropdown labeled "Column to check for
   outliers" lists all numeric columns. Pick the column you want to clean.

2. **Select group-by columns (optional).** The "Group by columns" multiselect
   lists all categorical columns. The tool intelligently excludes seed-like
   columns (`random_seed`, `iteration`, `run_id`) from the default selection
   because grouping by seed creates single-row groups where Q3 filtering is
   meaningless.

3. **Review the distribution.** Four metric cards display the current **Min**,
   **Q3**, **Max**, and **Mean** for the selected column so you can gauge
   how much outlier pressure exists.

4. **Click "Apply Outlier Remover."** You should see a success message reporting
   how many rows were removed and what percentage of the data they represent.
   Three metric cards show Original Rows, Filtered Rows, and Removed count,
   followed by a preview table.

5. **Review the preview.** Verify that the removal is reasonable.

6. **Click "Confirm and Apply Outlier Remover."** This commits the filtered
   dataset. A confirmation toast appears and the page refreshes.

---

## Preprocessor Tab

The Preprocessor creates new computed columns by applying arithmetic operations
to two existing numeric columns. This is useful for deriving metrics that gem5
does not report directly.

Click the **Preprocessor** tab to open it.

### Common Use Cases

- **IPC (Instructions Per Cycle):** divide `total_instructions` by `total_cycles`.
- **Cache miss rate:** divide `cache_misses` by `cache_accesses`.
- **Combined time:** sum `user_time` and `kernel_time`.

### Step-by-Step

1. **Select Source Column 1.** A dropdown lists all numeric columns.

2. **Select the Operation.** The available operations come from the backend and
   typically include Division, Sum, Subtraction, and Multiplication.

3. **Select Source Column 2.** A second dropdown lists all numeric columns.

4. **Name the result.** A text field labeled "New column name" is pre-filled with
   a descriptive default based on the operation and source columns. For example,
   dividing `instructions` by `cycles` generates the name
   `instructions_per_cycles`. You can change this to any name you prefer.

5. **Click "Preview Result."** You should see a success message, a preview table
   showing the two source columns alongside the new column, and descriptive
   statistics for the new column.

6. **Review the preview.** Check for unexpected values such as division-by-zero
   results.

7. **Click "Confirm and Add Column to Dataset."** The new column is appended to
   your working dataset. A confirmation toast appears and the page refreshes.

You can repeat this process multiple times to create several derived columns
before moving on.

---

## Mixer Tab

The Mixer merges multiple columns into a single new column using either a
numerical aggregation (Sum or Mean) or string concatenation. It also propagates
standard deviations automatically when companion `.sd` or `_stdev` columns
exist.

Click the **Mixer** tab to open it.

### Modes

A segmented control at the top lets you choose between two modes:

- **Numerical Operations** -- available columns are limited to numeric columns
  (excluding `.sd` and `_stdev` columns). Operations: Sum and Mean (Average).
- **Configuration Merge** -- all columns are available. Operation: Concatenate.

### Step-by-Step (Numerical)

1. **Select columns to merge.** Use the multiselect labeled "Select columns to
   merge" to pick two or more numeric columns.

2. **Select the operation.** Choose Sum or Mean (Average).

3. **Name the result.** A text field labeled "New Column Name" is pre-filled
   based on the operation and selected columns. You can change it.

4. **Click "Preview Merge."** You should see a preview of the new column. If
   the source columns have associated `.sd` columns, the tool also creates a
   new `.sd` column with properly propagated standard deviations (using
   `sqrt(sd1^2 + sd2^2 + ...)` for Sum, divided by N for Mean).

5. **Click "Confirm and Merge."** The merged column is added to your dataset.

### Step-by-Step (Configuration Merge)

1. **Select columns to merge.** Pick the text columns you want to combine.

2. **Set the separator.** A text field labeled "Separator" defaults to `_`. You
   can change it to any string (for example, `-` or `/`).

3. **Name the result.** The default name uses the prefix `concat_`.

4. **Click "Preview Merge."** Review the concatenated values.

5. **Click "Confirm and Merge."** The new column is added to your dataset.

---

## Operations History Tab

The Operations History tab provides a read-only log of every data transformation
you have applied during the current session.

Click the **Operations History** tab to open it. If no transformations have been
performed yet, you will see a "No operations" warning.

Once you have applied one or more transformations, this tab displays:

- A **Total Operations** metric showing the count.
- A table listing each operation in reverse chronological order with columns for
  Timestamp, Operation name, Source Columns, and Destination Columns.

Each of the four transformation tabs (Seeds Reducer, Outlier Remover,
Preprocessor, Mixer) also shows its own filtered history at the bottom of the
tab. Those per-tab histories include **Load** and **Delete** buttons for each
record. Clicking Load pre-fills the tab with the settings from that past
operation, making it easy to re-apply a similar transformation.

---

## Workflow Tips

### Recommended Order

While you can use the tabs in any order, the following sequence generally
produces the best results:

1. **Seeds Reducer first.** Aggregate seeds early so that downstream operations
   work on clean, averaged data rather than duplicated rows.

2. **Outlier Remover second.** Remove extreme values from the already-reduced
   dataset. This avoids a situation where outlier rows survive because they were
   averaged away during seed reduction.

3. **Preprocessor third.** Derive new computed columns from the cleaned data.
   This ensures that ratios and sums are calculated from outlier-free values.

4. **Mixer last.** Combine columns after all other transformations are complete.

### Reverting Changes

All transformations modify the in-memory working dataset. There is no built-in
undo button for individual operations. To revert your data to its original state,
return to the **Data Source** page and reload your CSV file. This replaces the
working dataset with the original data and clears all transformations.

Alternatively, if you saved a portfolio before transforming, you can restore it
from the **Save/Load Portfolio** page.

### Keeping Track

The Operations History tab and the per-tab history sections let you see exactly
what was done and in what order. Before creating plots, it is good practice to
check the Operations History tab to confirm that all intended transformations
were applied.
