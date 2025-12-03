# RING-5 Examples

This directory contains example configuration files demonstrating various features of RING-5.

## Available Examples

### complete_example.json

A comprehensive example showcasing all major features:

- **Multiple variable types**: scalar, configuration
- **All data managers**: 
  - Seeds reducer
  - Outlier removal
  - Normalization
- **All plot types**:
  - Bar plot (simple and with aggregation)
  - Line plot
  - Heatmap
  - Grouped bar
  - Box plot
  - Scatter plot
- **Advanced features**:
  - Filtering
  - Geometric mean aggregation
  - Custom styling
  - Legend configuration

## Usage

### Validate an example
```bash
python ring5.py validate --config examples/complete_example.json
```

### Use as starting point
```bash
# Copy to your working directory
cp examples/complete_example.json my_config.json

# Edit paths and variables
nano my_config.json

# Run analysis
python ring5.py analyze --config my_config.json
```

### Create custom from template
```bash
# Generate minimal config
python ring5.py create-template \
    --output-path ./my_output \
    --stats-path /path/to/gem5/stats \
    --config-file my_config.json

# Or use interactive generator
python tools/create_config.py
```

## Example Scenarios

### Scenario 1: Simple Performance Comparison

```json
{
  "outputPath": "./output",
  "parseConfig": {
    "parser": "gem5_stats",
    "statsPath": "/path/to/stats",
    "variables": [
      {"name": "simTicks", "type": "scalar"},
      {"name": "benchmark_name", "type": "configuration"}
    ]
  },
  "dataManagers": {
    "seedsReducer": true
  },
  "plots": [{
    "type": "bar",
    "output": {"filename": "performance"},
    "data": {
      "x": "benchmark_name",
      "y": "simTicks"
    },
    "style": {
      "title": "Execution Time",
      "ylabel": "Ticks",
      "grid": true
    }
  }]
}
```

### Scenario 2: Multi-Config Comparison with Normalization

```json
{
  "outputPath": "./output",
  "parseConfig": {
    "parser": "gem5_stats",
    "statsPath": "/path/to/stats",
    "variables": [
      {"name": "simTicks", "type": "scalar"},
      {"name": "benchmark_name", "type": "configuration"},
      {"name": "config", "type": "configuration"}
    ]
  },
  "dataManagers": {
    "seedsReducer": true,
    "normalizer": {
      "enabled": true,
      "baseline": {"config": "baseline_config"},
      "columns": ["simTicks"],
      "groupBy": ["benchmark_name"]
    }
  },
  "plots": [{
    "type": "bar",
    "output": {"filename": "normalized_perf"},
    "data": {
      "x": "benchmark_name",
      "y": "simTicks",
      "hue": "config"
    },
    "style": {
      "title": "Normalized Performance",
      "ylabel": "Speedup",
      "ylim": [0, 2],
      "legend": {"title": "Configuration"}
    }
  }]
}
```

### Scenario 3: Cache Analysis

```json
{
  "parseConfig": {
    "variables": [
      {"name": "system.l1d.overall_misses::total", "type": "scalar", "rename": "l1d_misses"},
      {"name": "system.l2.overall_misses::total", "type": "scalar", "rename": "l2_misses"},
      {"name": "benchmark_name", "type": "configuration"}
    ]
  },
  "plots": [
    {
      "type": "heatmap",
      "output": {"filename": "cache_heatmap"},
      "data": {
        "x": "benchmark_name",
        "y": "config",
        "value": "l1d_misses"
      },
      "style": {"title": "L1D Cache Misses"}
    },
    {
      "type": "scatter",
      "output": {"filename": "l1_vs_l2"},
      "data": {
        "x": "l1d_misses",
        "y": "l2_misses",
        "hue": "benchmark_name"
      },
      "style": {"title": "L1D vs L2 Misses"}
    }
  ]
}
```

## Tips

### Plot Type Selection

- **Bar**: Comparing discrete categories (benchmarks, configs)
- **Line**: Trends across ordered values
- **Heatmap**: Many-to-many comparisons (all benchmarks × all configs)
- **Box/Violin**: Distribution analysis across seeds
- **Scatter**: Finding correlations between two metrics

### Aggregation

Use geometric mean for normalized values:
```json
"aggregate": {
  "method": "geomean",
  "groupBy": ["config"]
}
```

### Filtering

Focus on specific benchmarks:
```json
"filters": {
  "benchmark_name": ["bzip2", "gcc", "mcf"]
}
```

### Styling

Publication-ready plots:
```json
"style": {
  "width": 12,
  "height": 6,
  "theme": "whitegrid",
  "grid": true,
  "legend": {
    "show": true,
    "location": "upper right"
  }
}
```

## More Examples

Check the test files in `tests/pytests/mock/config_files/` for additional configuration examples used in testing.
