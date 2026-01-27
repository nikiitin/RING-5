# Workflow: Adding Support for New gem5 Variable Types

**Workflow ID**: `new-variable-type`  
**Complexity**: Advanced  
**Domain**: Parsing

## Overview

Guide for extending the parser to support new gem5 statistics variable types beyond the current scalar, vector, distribution, histogram, and configuration types.

## Current Architecture

```
┌─────────────────────────────────────────┐
│  gem5 stats.txt                         │
│  - Multiple variable types              │
│  - Custom formats                       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  TypeMapper                             │
│  - Maps variable types to Perl parsers  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Perl Parser Scripts                    │
│  - perl/parse_scalar.pl                 │
│  - perl/parse_vector.pl                 │
│  - perl/parse_distribution.pl           │
│  - perl/parse_histogram.pl              │
│  - perl/parse_config.pl                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  CSV Output                             │
│  - Structured data for analysis         │
└─────────────────────────────────────────┘
```

## Example: Adding "Formula" Variable Type

gem5 supports formula variables that compute derived statistics:

```
system.cpu.ipc_formula                   1.745234   # cycles / instructions
```

### Step 1: Identify the Format

Examine gem5 stats.txt output:

```
---------- Begin Simulation Statistics ----------
...
system.cpu.ipc_formula                   1.745234   # cycles / instructions
system.cpu.bandwidth_formula             2.456789   # bytes / time
...
```

**Characteristics**:

- Single numeric value (like scalar)
- Has formula expression in comment
- May have special naming convention (`_formula` suffix)

### Step 2: Create Perl Parser

**File**: `src/parsers/perl/parse_formula.pl`

```perl
#!/usr/bin/perl

use strict;
use warnings;
use Getopt::Long;

# Parse command-line arguments
my $stats_file;
my $pattern;
my $output_csv;
my $scanned_vars_json;

GetOptions(
    'stats-file=s' => \$stats_file,
    'pattern=s' => \$pattern,
    'output-csv=s' => \$output_csv,
    'scanned-vars=s' => \$scanned_vars_json
) or die "Error parsing command-line options\n";

# Validate required arguments
die "Missing required --stats-file\n" unless $stats_file;
die "Missing required --pattern\n" unless $pattern;
die "Missing required --output-csv\n" unless $output_csv;

# Open stats file
open(my $stats_fh, '<', $stats_file) or die "Cannot open $stats_file: $!\n";

# Prepare output
open(my $csv_fh, '>', $output_csv) or die "Cannot open $output_csv: $!\n";

# Write CSV header
print $csv_fh "variable,value,formula\n";

# Parse file
while (my $line = <$stats_fh>) {
    chomp $line;

    # Match formula variable line
    # Format: "variable_name    value    # formula_expression"
    if ($line =~ /^($pattern)\s+([0-9.e+-]+)\s*#\s*(.+)$/) {
        my $variable = $1;
        my $value = $2;
        my $formula = $3;

        # Clean up formula (remove extra whitespace)
        $formula =~ s/^\s+|\s+$//g;

        # Write to CSV
        print $csv_fh "$variable,$value,\"$formula\"\n";
    }
}

close($stats_fh);
close($csv_fh);

print "Formula parsing complete: $output_csv\n";
```

### Step 3: Add to TypeMapper

**File**: `src/parsers/type_mapper.py`

```python
class TypeMapper:
    """Maps variable types to their parsing strategies."""

    # Mapping of variable types to Perl parser scripts
    TYPE_TO_SCRIPT = {
        "scalar": "parse_scalar.pl",
        "vector": "parse_vector.pl",
        "distribution": "parse_distribution.pl",
        "histogram": "parse_histogram.pl",
        "configuration": "parse_config.pl",
        "formula": "parse_formula.pl",  # ← Add new type
    }

    # Mapping of variable types to expected output columns
    TYPE_TO_COLUMNS = {
        "scalar": ["variable", "value"],
        "vector": ["variable", "entry", "value"],
        "distribution": ["variable", "min", "max", "value"],
        "histogram": ["variable", "range_start", "range_end", "count"],
        "configuration": ["variable", "value"],
        "formula": ["variable", "value", "formula"],  # ← Add columns
    }

    @staticmethod
    def map_variable_to_parse_config(variable_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map variable configuration to parse parameters.

        Args:
            variable_config: Config with 'name', 'type', and type-specific params

        Returns:
            Dict with 'type', 'pattern', 'script', and additional params
        """
        var_type = variable_config.get("type")

        if var_type not in TypeMapper.TYPE_TO_SCRIPT:
            raise ValueError(f"Unknown variable type: {var_type}")

        parse_config = {
            "type": var_type,
            "pattern": variable_config.get("name", ""),
            "script": TypeMapper.TYPE_TO_SCRIPT[var_type],
        }

        # Type-specific parameters
        if var_type == "formula":
            # Formula variables may have optional parameters
            parse_config["extract_formula"] = True

        # ... handle other types ...

        return parse_config
```

### Step 4: Update Scanner

The scanner needs to detect formula variables:

**File**: `src/parsers/scanner.py`

```python
def scan_gem5_stats(
    stats_path: Path,
    pattern: str,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Scan gem5 stats file for matching variables.

    Returns:
        Dict with variable metadata including type detection
    """
    results = {}

    with open(stats_path, 'r') as f:
        for line in f:
            # ... existing scalar/vector/distribution detection ...

            # Detect formula variables (have "# formula" in comment)
            if re.match(rf"^{pattern}\s+[0-9.e+-]+\s*#\s*.+", line):
                var_name = line.split()[0]
                results[var_name] = {
                    "type": "formula",
                    "name": var_name,
                    "sample_line": line.strip()
                }

    return results
```

### Step 5: Create Unit Tests

**File**: `tests/unit/test_formula_parser.py`

```python
import pandas as pd
import pytest
from pathlib import Path
import subprocess

from src.parsers.type_mapper import TypeMapper


class TestFormulaParser:
    """Unit tests for formula variable parsing."""

    @pytest.fixture
    def stats_file(self, tmp_path):
        """Create test stats file with formula variables."""
        content = """---------- Begin Simulation Statistics ----------
system.cpu.ipc_formula                   1.745234   # cycles / instructions
system.cpu.bandwidth_formula             2.456789   # bytes / time
---------- End Simulation Statistics ----------
"""
        stats_path = tmp_path / "stats.txt"
        stats_path.write_text(content)
        return stats_path

    def test_perl_parser_execution(self, stats_file, tmp_path):
        """Test that Perl parser executes and produces CSV."""
        output_csv = tmp_path / "output.csv"

        # Run Perl script directly
        result = subprocess.run([
            "perl",
            "src/parsers/perl/parse_formula.pl",
            f"--stats-file={stats_file}",
            f"--pattern=system\\.cpu\\..+_formula",
            f"--output-csv={output_csv}"
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Parser failed: {result.stderr}"
        assert output_csv.exists()

        # Verify CSV content
        df = pd.read_csv(output_csv)
        assert len(df) == 2
        assert "variable" in df.columns
        assert "value" in df.columns
        assert "formula" in df.columns

        # Check specific values
        ipc_row = df[df["variable"] == "system.cpu.ipc_formula"]
        assert float(ipc_row["value"].iloc[0]) == pytest.approx(1.745234)
        assert ipc_row["formula"].iloc[0] == "cycles / instructions"

    def test_type_mapper_formula_config(self):
        """Test TypeMapper generates correct config for formula type."""
        variable_config = {
            "name": "system.cpu.ipc_formula",
            "type": "formula"
        }

        parse_config = TypeMapper.map_variable_to_parse_config(variable_config)

        assert parse_config["type"] == "formula"
        assert parse_config["script"] == "parse_formula.pl"
        assert parse_config["pattern"] == "system.cpu.ipc_formula"
        assert parse_config["extract_formula"] is True
```

### Step 6: Create Integration Test

**File**: `tests/integration/test_formula_parsing.py`

```python
import pytest
from pathlib import Path

from src.web.facade import BackendFacade


class TestFormulaParsingIntegration:
    """Integration tests for formula variable end-to-end parsing."""

    @pytest.fixture
    def facade(self):
        """Create BackendFacade instance."""
        return BackendFacade()

    @pytest.fixture
    def stats_file(self, tmp_path):
        """Create realistic gem5 stats with formula variables."""
        content = """---------- Begin Simulation Statistics ----------
simSeconds                                   0.100000
system.cpu.ipc                               1.500000
system.cpu.ipc_formula                       1.745234   # cycles / instructions
system.cpu.bandwidth_formula                 2.456789   # bytes / time
---------- End Simulation Statistics ----------
"""
        stats_path = tmp_path / "stats.txt"
        stats_path.write_text(content)
        return stats_path

    def test_formula_scan_and_parse(self, facade, stats_file, tmp_path):
        """Test scanning and parsing formula variables."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Step 1: Scan for formula variables
        scan_futures = facade.submit_scan_async(
            str(stats_file),
            "system\\.cpu\\..+_formula",
            limit=10
        )
        scan_results = [f.result(timeout=10) for f in scan_futures]
        scanned_vars = facade.finalize_scan(scan_results)

        # Verify scan detected formula type
        assert len(scanned_vars) == 2
        for var in scanned_vars:
            assert var["type"] == "formula"

        # Step 2: Parse formula variables
        parse_futures = facade.submit_parse_async(
            str(stats_file),
            "system\\.cpu\\..+_formula",
            scanned_vars,
            str(output_dir),
            scanned_vars=scanned_vars
        )
        parse_results = [f.result(timeout=10) for f in parse_futures]
        csv_path = facade.finalize_parsing(str(output_dir), parse_results)

        # Verify CSV output
        assert csv_path is not None
        assert Path(csv_path).exists()

        # Load and verify data
        data = facade.load_csv(csv_path)
        assert len(data) == 2
        assert "formula" in data.columns

        # Verify specific formula
        ipc_row = data[data["variable"] == "system.cpu.ipc_formula"]
        assert ipc_row["formula"].iloc[0] == "cycles / instructions"
```

### Step 7: Update Documentation

**File**: `docs/variable-types.md` (create if doesn't exist)

```markdown
# Supported gem5 Variable Types

## Formula Variables

**Type ID**: `formula`

**Description**: Derived statistics computed from formulas

**Format in stats.txt**:
```

variable_name value # formula_expression

```

**Example**:
```

system.cpu.ipc_formula 1.745234 # cycles / instructions

````

**CSV Output Columns**:
- `variable`: Variable name
- `value`: Computed numeric value
- `formula`: Formula expression string

**Configuration**:
```json
{
    "name": "system.cpu.ipc_formula",
    "type": "formula"
}
````

**Parser**: `parse_formula.pl`

````

### Step 8: Update UI

Add formula type to variable editor:

**File**: `src/web/ui/components/variable_editor.py`

```python
def render_variable_type_selector():
    """Render variable type selector."""
    return st.selectbox(
        "Variable Type",
        ["scalar", "vector", "distribution", "histogram", "configuration", "formula"],
        format_func=lambda x: {
            "scalar": "Scalar (single value)",
            "vector": "Vector (array with entries)",
            "distribution": "Distribution (min/max/value)",
            "histogram": "Histogram (binned data)",
            "configuration": "Configuration (metadata)",
            "formula": "Formula (derived statistic)",
        }[x]
    )
````

## Testing Checklist

- [ ] Perl parser runs without errors
- [ ] Parser produces valid CSV output
- [ ] CSV columns match TypeMapper definition
- [ ] Scanner detects new variable type
- [ ] TypeMapper maps type correctly
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] UI updated (if needed)
- [ ] Full test suite passes (`make test`)

## Common Patterns

### Pattern 1: Regex-based Detection

Many variable types can be detected by regex patterns:

```python
# In scanner.py
patterns = {
    "scalar": r"^{pattern}\s+[0-9.e+-]+\s*$",
    "vector": r"^{pattern}\s+[0-9]+\s+[0-9.e+-]+",
    "formula": r"^{pattern}\s+[0-9.e+-]+\s*#\s*.+"
}
```

### Pattern 2: Multi-line Variables

Some gem5 stats span multiple lines:

```perl
# In Perl parser
my $buffer = "";
while (my $line = <$fh>) {
    if ($line =~ /^$pattern/) {
        $buffer = $line;
    } elsif ($buffer && $line =~ /^\s+/) {
        # Continuation line
        $buffer .= $line;
    } elsif ($buffer) {
        # Process complete variable
        parse_multiline_variable($buffer);
        $buffer = "";
    }
}
```

### Pattern 3: Conditional Parsing

Variables may have optional fields:

```python
# In TypeMapper
if var_type == "advanced_histogram":
    parse_config["with_percentiles"] = variable_config.get("percentiles", False)
    parse_config["with_cumulative"] = variable_config.get("cumulative", True)
```

## Troubleshooting

| Issue                       | Solution                                       |
| --------------------------- | ---------------------------------------------- |
| Perl parser not found       | Check file path in `TypeMapper.TYPE_TO_SCRIPT` |
| CSV columns mismatch        | Update `TypeMapper.TYPE_TO_COLUMNS`            |
| Scanner doesn't detect type | Add detection regex in `scanner.py`            |
| Parser produces invalid CSV | Validate Perl output format with test data     |
| Integration test fails      | Check async workflow (scan → parse → load)     |

## References

- TypeMapper: `src/parsers/type_mapper.py`
- Existing parsers: `src/parsers/perl/parse_*.pl`
- Scanner: `src/parsers/scanner.py`
- Tests: `tests/unit/test_parsers.py`, `tests/integration/test_gem5_parsing.py`
