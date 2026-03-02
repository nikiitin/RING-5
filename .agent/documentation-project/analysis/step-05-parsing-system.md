# Step 05 — Parsing System Analysis

> **Objective**: Document the complete parsing subsystem — the parser protocol, registry,
> gem5 implementation, Perl worker pool integration, scanning, strategies, and the full
> parse lifecycle.

---

## Scope

This step provides an **exhaustive analysis** of how raw simulator output is transformed
into structured data. This is critical for the "Adding a New Parser" developer guide.

---

## Files to Analyze

### Parsing Core
```
src/parsing/__init__.py
src/parsing/parser_protocol.py                 (protocol definition)
src/parsing/parse_service.py                   (main parse service)
src/parsing/registry.py                        (parser registry)
src/parsing/scanner_service.py                 (scanning service)
```

### gem5 Parser — Models
```
src/parsing/gem5/__init__.py
src/parsing/gem5/models.py                     (gem5-specific data models)
```

### gem5 Parser — Types
```
src/parsing/gem5/types/__init__.py
src/parsing/gem5/types/base.py                 (base type)
src/parsing/gem5/types/configuration.py        (configuration type)
src/parsing/gem5/types/distribution.py         (distribution type)
src/parsing/gem5/types/histogram.py            (histogram type)
src/parsing/gem5/types/scalar.py               (scalar type)
src/parsing/gem5/types/type_mapper.py          (type mapping/registry)
src/parsing/gem5/types/vector.py               (vector type)
```

### gem5 Parser — Implementation
```
src/parsing/gem5/impl/__init__.py
src/parsing/gem5/impl/gem5_parser_api.py       (parser API)
src/parsing/gem5/impl/gem5_parser.py           (main parser)
src/parsing/gem5/impl/gem5_scanner.py          (gem5 scanner)
```

### gem5 Parser — Worker Pool
```
src/parsing/gem5/impl/pool/__init__.py
src/parsing/gem5/impl/pool/job.py
src/parsing/gem5/impl/pool/parse_work.py
src/parsing/gem5/impl/pool/pool.py
src/parsing/gem5/impl/pool/scan_work.py
src/parsing/gem5/impl/pool/work_pool.py
```

### gem5 Parser — Strategies
```
src/parsing/gem5/impl/strategies/__init__.py
src/parsing/gem5/impl/strategies/config_aware.py
src/parsing/gem5/impl/strategies/factory.py
src/parsing/gem5/impl/strategies/file_parser_strategy.py
src/parsing/gem5/impl/strategies/gem5_parse_work.py
src/parsing/gem5/impl/strategies/perl_worker_pool.py
src/parsing/gem5/impl/strategies/simple.py
```

### gem5 Parser — Scanning
```
src/parsing/gem5/impl/scanning/__init__.py
src/parsing/gem5/impl/scanning/gem5_scan_work.py
src/parsing/gem5/impl/scanning/pattern_aggregator.py
src/parsing/gem5/impl/scanning/scanner.py
```

### Perl Integration
```
src/parsing/gem5/perl/                         (Perl scripts and libs)
```

---

## Questions to Answer

### Parser Protocol:
- [ ] What methods does the parser protocol define?
- [ ] What is the contract for implementing a new parser?
- [ ] How does the protocol handle scanning vs. parsing phases?
- [ ] What types does the protocol use? (input and output)

### Registry:
- [ ] How are parsers registered?
- [ ] How is a parser looked up/selected?
- [ ] Is registration automatic or manual?
- [ ] Can multiple parsers coexist? How is the right one chosen?

### Parse Lifecycle:
- [ ] What is the complete scanning workflow? (step by step)
- [ ] What is the complete parsing workflow? (step by step)
- [ ] How does scanning discover variables/stats?
- [ ] How does parsing extract actual data values?
- [ ] What is the output format? (DataFrame? Model?)

### gem5 Implementation:
- [ ] What gem5 stat types are supported? (scalar, vector, distribution, histogram, configuration)
- [ ] How does the TypeMapper work?
- [ ] What is the file format parsed? (stats.txt structure)
- [ ] How are multi-config simulations handled?
- [ ] What is the directory structure expected?

### Strategies:
- [ ] What parsing strategies exist? (simple, config_aware, perl_worker_pool)
- [ ] How does the strategy factory select the right strategy?
- [ ] When is each strategy used?
- [ ] How does the Perl worker pool integration work?
- [ ] What is the performance difference between strategies?

### Worker Pool:
- [ ] How does the worker pool parallelize parsing?
- [ ] What is a "job" in the pool context?
- [ ] How is work distributed?
- [ ] How are results collected and merged?
- [ ] What is the Perl subprocess communication protocol?

### Scanning:
- [ ] How does the scanner discover stat patterns?
- [ ] What is pattern aggregation?
- [ ] How does the user select which patterns/variables to parse?
- [ ] What metadata is extracted during scanning?

---

## Information to Extract

### Parser Protocol Contract
```
Document the exact protocol with every method, parameter, and return type.
This is the contract any new parser must implement.
```

### gem5 Parse Lifecycle (Step by Step)
```
1. User provides directory path
2. Scanner scans for stat files → pattern list
3. User selects variables from pattern list
4. Parser is invoked with selected variables
5. Strategy is chosen based on configuration
6. [If Perl] Worker pool is initialized
7. Files are processed (in parallel or serial)
8. Results are aggregated into DataFrame
9. DataFrame is stored in DataRepository
```

### gem5 Type System
```
For each type (scalar, vector, distribution, histogram, configuration):
- What regex pattern identifies it?
- What fields are extracted?
- How is it converted to tabular form?
```

### Perl Integration Detail
```
- How does Python invoke Perl?
- What protocol is used for communication?
- What Perl modules are involved?
- Where are the Perl scripts located?
- What performance gains does Perl provide?
```

---

## Output Template

### 1. Parser Protocol Documentation
```
[To be filled: Complete protocol specification]
```

### 2. Registry Documentation
```
[To be filled: How registration and lookup work]
```

### 3. Parse Lifecycle
```
[To be filled: Step-by-step scanning and parsing workflow]
```

### 4. gem5 Type System
```
[To be filled: Every type with format, regex, extraction logic]
```

### 5. Strategy Pattern Documentation
```
[To be filled: Every strategy with when/why to use]
```

### 6. Worker Pool Architecture
```
[To be filled: Complete pool documentation]
```

### 7. Perl Integration
```
[To be filled: Python-Perl communication protocol]
```

### 8. Extension Guide Draft
```
[To be filled: Step-by-step "how to add a new parser"]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `parsing/parsing-architecture.md`, `parsing/gem5-parser-deep-dive.md`, `parsing/adding-a-new-parser.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `development/adding-a-parser.md`
- Step 18 (data flow) — parsing is the first step in the pipeline
- Step 19 (extension points) — parser protocol is a key extension point
