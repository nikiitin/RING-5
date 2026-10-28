# RING-5 examples

These complete scripts use the supported `ring5` API and small, explicitly synthetic inputs.
The numbers demonstrate workflows; they are not measurements from a simulator run or evidence of
an architectural improvement. Run commands from the repository root after `make dev`.

| Task | Script | Input and expected result |
| --- | --- | --- |
| Compare repeated runs | [compare_configurations.py](python/compare_configurations.py) | 12 observations → four means and sample standard deviations → baseline ratios `1`, candidate ratios `1.2` and `1.5`. |
| Reuse an analysis with parameters | [parameterized_recipe.py](python/parameterized_recipe.py) | IPC/energy scatter, portable recipe/script/notebook, and two serial threshold cases retaining 12 and seven observations. |
| Parse gem5 statistics | [parse_gem5.py](python/parse_gem5.py) | Two tiny synthetic statistics files → typed parser result → CSV; requires Perl. |

```bash
PYTHONPATH=. python_venv/bin/python examples/python/compare_configurations.py
PYTHONPATH=. python_venv/bin/python examples/python/parameterized_recipe.py
PYTHONPATH=. python_venv/bin/python examples/python/parse_gem5.py
```

Each script accepts `--help`, `--input` or a statistics-directory argument, and `--output-dir`.
Outputs default to separate directories under `example-output/`. By default each script sets
`RING5_DATA_DIR` to its output directory's `workspace/` before creating a Session; an existing
`RING5_DATA_DIR` takes precedence. Nothing is downloaded. PDF uses Matplotlib and HTML uses
Plotly, so these examples need neither Chrome nor TeX. The parser example alone uses Perl.

The comparison saves `Documentation IPC comparison` and replays its plot to PDF. A second run
against the same data directory refuses to replace that portfolio unless you add
`--replace-portfolio`. Use that option only for this deliberately reproducible example.

`repeated_runs.csv` contains two benchmarks, two configurations, three seeds per experimental group,
IPC, and energy in joules. Reduction uses the sample standard deviation (`ddof=1`). Normalization
scales each mean and its `.sd` by the same baseline mean; the resulting error bars do not estimate
uncertainty in the ratio or establish statistical significance. The recipe intentionally plots
individual observations instead of reducing them. Its threshold is an exploratory filter, not an
unbiased estimator of performance.

To use your own data:

```bash
PYTHONPATH=. python_venv/bin/python examples/python/compare_configurations.py \
  --input /absolute/path/to/repeated_runs.csv --output-dir example-output/my-comparison
PYTHONPATH=. python_venv/bin/python examples/python/parse_gem5.py /absolute/path/to/results \
  --variable simTicks --variable system.cpu.ipc --output-dir example-output/my-parser
```

The comparison expects the documented CSV columns and exactly one reduced baseline row per
benchmark. The parser accepts a results tree containing `stats.txt`; `--strategy config_aware`
also requires a readable, non-empty `config.ini` beside every selected statistics file. Both tiny
example runs include that companion file. Directory-derived parser column names depend on the
input layout; the parser script prints its actual columns instead of assuming benchmark names.

To inspect all built-in plot types without providing data, use `Session.load_example_portfolio()`
or the web application's **Load example portfolio** action. The [example-portfolio tour](https://nikiitin.github.io/RING-5/user-guide/getting-started/showcase/)
explains the charts and the [Python workflow guide](https://nikiitin.github.io/RING-5/user-guide/workflows/scripting/)
explains the API lifecycle and automation choices.
