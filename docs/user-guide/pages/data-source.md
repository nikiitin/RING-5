# Data Source Page

The Data Source page is your starting point in RING-5. This is where you load
simulation data into the application so you can analyze and visualize it on the
subsequent pages.

RING-5 supports three ways to bring data in: parsing raw gem5 stats files,
uploading a CSV you already have, or reloading a dataset you parsed earlier.
All three options are accessible from a single control at the top of the page.

---

## Page Layout

When you open RING-5, the Data Source page loads by default. You should see a
heading that reads **Step 1: Choose Data Source**, followed by an information
box that summarizes the three loading methods.

Below the information box is a **segmented control** with three options:

| Option | Purpose |
|--------|---------|
| **Parse gem5 Stats Files** | Parse raw `stats.txt` output from gem5 simulations |
| **I already have CSV data** | Upload a pre-formatted CSV file directly |
| **Load from Recent** | Re-load a CSV from a previous parsing session |

The Parse mode is selected by default. The page content below the segmented
control changes depending on which option you choose.

---

## Parse Mode

Parse mode walks you through configuring and running the gem5 stats parser.
This is the primary workflow for loading fresh simulation data. It has five
sections that appear in order: simulator selection, file location, parsing
strategy, variables to extract, and configuration preview.

### Simulator Selection

At the top of the Parse section you will see a **pill selector** labeled
"Simulator." Currently, the only registered backend is **gem5**. If future
simulator backends are added to RING-5, they will appear here as additional
pills.

You should see the gem5 pill already selected. The heading below it reads
**gem5 Stats Parser Configuration**.

### File Location

The **File Location** section contains two text inputs arranged side by side.

**Stats directory path** (left input) -- Enter the absolute path to the
top-level directory that contains your gem5 output. RING-5 searches this
directory recursively, so you can point it at a parent directory that holds
multiple benchmark results in subdirectories.

**File pattern** (right input) -- This is the filename that RING-5 looks for
inside the directory tree. The default value is `stats.txt`, which is the
standard gem5 output filename. If your simulation uses a different name or you
want to match multiple files with a glob pattern (for example, `*.txt`), change
this value accordingly.

After filling in both fields, press Tab or click outside the input to confirm
your entry. You should see the values reflected in the Configuration Preview
section further down the page.

### Parsing Strategy

Below the file location inputs you will find the **Parsing Strategy** section.
This is a second segmented control with two options:

**Simple (stats.txt only)** -- Parses only the stats files themselves. This is
the fastest option and works for most use cases. Choose this when you only need
statistical counters from your simulation runs.

**Config-Aware (Integrates config.ini)** -- In addition to parsing stats files,
this strategy reads the `config.ini` files that gem5 generates alongside each
simulation. This lets you extract simulation configuration parameters (such as
CPU type, cache sizes, or clock frequency) as variables in your dataset.

The Simple strategy is selected by default. If you need configuration metadata
in your analysis, switch to Config-Aware before parsing.

### Variables to Extract

The **Variables to Extract** section is where you tell RING-5 which statistics
to pull from the stats files. gem5 stats files can contain thousands of
variables, so rather than extracting everything, you select the specific ones
you need.

The section begins with a brief description of the four variable types that
RING-5 understands:

| Type | Description | Example |
|------|-------------|---------|
| **Scalar** | A single numeric value per dump interval | `system.cpu.ipc`, `simTicks` |
| **Vector** | An array of named entries | `system.cpu.op_class` with entries like `IntAlu`, `MemRead` |
| **Distribution** | A statistical distribution with bucket values | `system.l2.miss_latency` with numeric bucket boundaries |
| **Configuration** | A metadata key-value pair extracted from config files | `system.cpu.type=DerivO3CPU` |

#### Scanning for Variables

Before you can add variables, you typically need to discover what is available
in your stats files. RING-5 provides a scanner for this purpose.

You will see a **Deep Scan (check all files)** checkbox and a **Quick Scan**
button.

**Quick Scan** examines a small sample of your stats files (up to 10 files by
default) and reports all variables it finds. This is usually sufficient because
gem5 stats files from the same simulation setup contain the same variable
names. Click the Quick Scan button to start.

You should see a status indicator that reports progress as each file is
scanned. When the scan finishes, the page reloads and a green success
message appears: "Scanner found N variables. Use 'Add Variable' to select
them."

**Deep Scan** examines every stats file in the directory tree. Enable the
checkbox before clicking Quick Scan if you suspect that different simulation
configurations produce different sets of variables. Deep scans take longer
but guarantee a complete picture.

#### Adding Variables

Once the scan completes, you have two ways to add variables to your parse
configuration.

**Add Variable button** -- Click the "Add Variable" button below the variable
list to open the **Add Variable** dialog. This dialog has two modes, selectable
via pill buttons at the top:

- **Search Scanned Variables** -- This is the default mode. It presents a
  searchable dropdown populated with all variables discovered during scanning.
  Start typing a variable name (for example, `system.cpu`) and the list filters
  in real time. Each entry shows the variable name, its type, and for vectors,
  the number of sub-entries. Select a variable, review the configuration form
  that appears below, and click **Add to Configuration**. The dialog closes and
  the variable is added to your list.

- **Manual Entry** -- Switch to this mode if you know the exact variable name
  and it was not found by the scanner (or if you have not scanned yet). Enter
  the variable name in the text input, select the type from the dropdown, and
  click **Add to Configuration**.

For vector and distribution variables, additional configuration fields appear
after you select the variable. Vectors require you to specify which entries
(sub-items) to extract. Distributions let you set a min/max range for the
buckets. If the variable came from a scan, these fields are pre-populated with
discovered values.

An **Advanced Options** expander at the bottom of the dialog contains a
**Repeat Count** field. Leave this at 1 unless you know your stats files
contain a variable that repeats in a strict sequence (this is uncommon).

#### Variable Editor

Once you have added at least one variable, the **Current Variables** section
appears on the page. Each variable is displayed as a row with four columns:
the variable name, an optional alias, the type, and a delete button.

You can edit the name or alias directly in the text inputs. If you change a
variable's type using the dropdown, additional type-specific fields appear
below that row. For example, switching a variable to "vector" reveals entry
selection controls.

For variables with pattern-based names (names containing numeric indices like
`system.cpu0.ipc`), RING-5 detects the pattern automatically and shows index
selection controls so you can choose which CPU cores or components to include.

### Configuration Preview

Below the variable editor, the **Configuration Preview** section displays a
JSON summary of your entire parse configuration. This includes:

- The selected simulator backend
- The stats directory path
- The file pattern
- The chosen parsing strategy
- The complete list of variables with their types and settings

Review this preview to confirm everything looks correct before parsing.

### Parse Button

At the very bottom of the Parse mode section, a full-width primary button reads
**Parse gem5 Stats Files**. Click it to start the parsing process.

If the stats directory path is empty, an error message appears asking you to
specify a path. If the path is valid, a **Parsing Stats** dialog opens.

The dialog shows a progress bar that updates as each stats file is processed.
You should see messages like "Processed 5/20" as parsing proceeds. When all
files are done, RING-5 finalizes the results by aggregating per-file outputs
into a single consolidated CSV.

On success, you will see a green message: "Done! Generated N rows." Click
**Close & Reload** to dismiss the dialog. The parsed data is now loaded into
your session and the CSV is saved to the recent files pool for future use.

If errors occur during parsing, they are listed inside an expandable section
within the dialog. Partial results (from files that parsed successfully) are
still available.

Once data is loaded, a metrics bar appears at the top of the page showing the
total number of rows, columns, and the source filename.

---

## CSV Mode

Select **I already have CSV data** from the segmented control to switch to CSV
mode. This mode is for users who already have their simulation data in CSV
format and do not need to run the parser.

You should see a success message confirming that CSV mode is selected, along
with a **file uploader** widget.

### CSV Format Requirements

Your CSV file must follow these conventions to work correctly with RING-5:

- The first row must be a **header row** with column names.
- Column names should be descriptive. The downstream analysis tools (Data
  Managers, plot configuration) use column names to build selectors and labels.
- Values should be numeric for statistical columns. String values are accepted
  for metadata columns (such as benchmark names or configuration descriptions).
- Missing values should be represented as empty strings, not as `NaN` or
  `null`.

There is no strict requirement for specific column names when uploading a CSV
directly. However, having columns that identify your benchmarks and
configurations (for example, `benchmark_name` and `config_description`) makes
the downstream grouping and plotting features significantly more useful.

### Uploading a File

Click the file uploader or drag and drop your CSV file onto it. After the file
uploads and processes, RING-5 loads the data into the session. You should see
the metrics bar at the top of the page update with the row count, column count,
and source filename.

You can then proceed to the Data Managers page for data transformations or go
directly to Manage Plots.

---

## Recent Mode

Select **Load from Recent** from the segmented control to see previously parsed
datasets. This is the fastest way to get back to a dataset you worked with
earlier without re-running the parser.

### Recent CSV Files List

You should see a heading that reads **Recent CSV Files**, followed by an info
message showing how many files are in the pool: "Found N CSV file(s) in the
pool."

If no files have been parsed yet, a warning message appears instead: "No CSV
files in the pool yet. Parse some stats to populate this list."

### File Cards

Each file in the pool is displayed as an expandable card showing the file name
and metadata. Each card provides three action buttons:

**Load This File** -- Loads the CSV into the current session. On success, you
will see a confirmation message with the row count, a data preview table, and
column details. A prompt directs you to proceed to the pipeline configuration
step.

**Preview** -- Displays the first five rows of the CSV so you can verify the
contents before loading.

**Delete** -- Removes the file from the pool. A brief toast notification
confirms the deletion.

---

## Tips and Best Practices

**Start with CSV for quick exploration.** If you have a colleague's CSV output
or a pre-processed dataset, uploading it directly is the fastest way to start
exploring RING-5's visualization capabilities. You can always switch to the
parser later for your own simulation data.

**Use Parse mode for real gem5 data.** The parser handles the complex structure
of gem5 stats files, including vector entries, distribution buckets, and
histogram ranges. It produces a clean, analysis-ready CSV that follows RING-5's
internal data contract.

**Scan before adding variables manually.** The Quick Scan takes only a few
seconds and discovers all variables present in your stats files. Searching the
scan results is faster and less error-prone than typing variable names by hand.
Use Manual Entry only when you need a variable that the scanner did not find.

**Use Config-Aware parsing for comparative studies.** If your analysis compares
different CPU configurations or memory hierarchies, the Config-Aware strategy
extracts those parameters directly from gem5's `config.ini` files. This saves
you from having to encode configuration details in directory names or separate
metadata files.

**Check the Configuration Preview before parsing.** The JSON preview at the
bottom of the Parse section gives you a complete summary. Verify that the
variable list, strategy, and file paths are correct before committing to a
potentially long parsing operation.

**Large datasets may take time to parse.** Parsing hundreds of stats files is
I/O-intensive. RING-5 uses a high-performance worker pool to parallelize the
work, but very large datasets (hundreds of files with many variables) can still
take a minute or more. The progress dialog keeps you informed throughout the
process.
