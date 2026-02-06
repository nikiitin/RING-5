# Parsing Implementation Workflow

> **Invoke with**: `/parsing-workflow`
> **Purpose**: Standard process for implementing or modifying Gem5 parsers.
> **Applies to**: `src/parsers/` changes.

## Overview

Gem5 parsing follows a **Dual-Strategy** approach (Rule 000). You must support both Legacy (stats.txt) and Modern (stats.txt + config.ini) modes.

## Step-by-Step

### 1. Strategy Selection (Rule 000)

Identify the target strategy:

- **LegacyGem5Parser**: Logic for standalone stats.
- **ModernGem5Parser**: Logic for topology-aware stats.

### 2. Performance Engineering (Rule 002)

For large trace files (> 1GB):

- **Mandatory:** Use `np.memmap` if binary formats are available.
- **Parsing:** Use Regex for text extraction (compiled once).

### 3. TDD - Write the Test Case

Create a test using the `files_dict` fixture to simulate the file system.

```python
# tests/unit/parsers/test_legacy_parser.py
def test_parse_legacy_format(mock_filesystem):
    parser = LegacyGem5Parser(path="stats.txt")
    result = parser.parse()  # Returns Domain Object
    assert result.context.sim_seconds == 0.5
```

### 4. Implementation Constraints

- **Extraction:** Regex based.
- **Simpoints:** Handle `begin`/`end` dumps.
- **Output:** **Long Format** (Entity-Attribute-Value) DataFrame initially.

### 5. Integration Verification

Run the full parsing test suite against `tests/data/legacy` and `tests/data/modern`.

```bash
pytest tests/integration/test_parser_strategies.py
```
