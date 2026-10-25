---
layout: default
title: Parsing Subsystem
parent: Subsystems
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/subsystems/parsing/
---

# Parsing subsystem

`src/parsing/parser_protocol.py` defines `SimulationParser`. `src/parsing/registry.py` maps simulator
names to immutable metadata and parser factories. The web application and `ring5.Session` select a
registered backend rather than importing a simulator implementation directly.

## Async contract

<!--
`uman~ring5.ingestion.persistent-workers.documentation~1`

Covers:
- req~ring5.ingestion.persistent-workers~1

-->

Scanning and parsing are submit/finalize operations. Submit methods validate inputs and return
futures owned by the caller or a parse job. Finalization aggregates successful results, preserves
file failures, and assembles the CSV. Cancellation must affect only work owned by the current API
instance or job.

`WorkPool` submits typed callable commands through `submit` or `submit_many`; it retains no batch
futures or results. Concrete scan and parse commands share one bounded executor. Explicit global
shutdown drains accepted work and rejects new submissions with a recoverable error until its
executor threads have settled. A later submission recreates the executor. Repeated waiting
shutdowns can join the same retirement; a worker cannot wait for its own shutdown. Session cleanup
cancels only owned futures and never shuts down this shared pool.
The public `ring5.shutdown()` waits for accepted file tasks and keeps admission closed while
closing their Perl processes. Concurrent global closes serialize; a failed close keeps admission
closed until a global retry succeeds. The next parse or scan then recreates both pools.

Perl processes use strict UTF-8 streams. Startup owns each process generation and its pipe-reader
handles until READY succeeds; failed startup reaps the child and joins its readers before returning
the error. Pool construction also closes workers and monitor threads already started by that attempt.
Worker stop/restart operations serialize and retire only their captured generation. Stream errors
retain their identity through the reader queue; exact known decoding failures become bounded data
errors at their input owner, while unsupported exception subtypes propagate unchanged.
Commands validate their fixed source ID against the batch plan before retaining or submitting
work. Diagnostics read bounded native exception metadata and cause links; Unicode input buffers
and arbitrary exception hooks are excluded.

The gem5 implementation under `src/parsing/gem5/` uses Python orchestration and persistent Perl
workers. Strategies under `src/parsing/gem5/impl/strategies/` control ingestion. Pattern aggregation
can collapse repeated concrete names into a selectable pattern; parsing needs scanned-variable data
to expand those patterns correctly.

## Variable types and CSV

<!--
`uman~ring5.ingestion.pattern-aggregation.documentation~1`

Covers:
- req~ring5.ingestion.pattern-aggregation~1

-->

gem5 stat types register through decorators under `src/parsing/gem5/types/`.
`TypesFormatRegex::classifyLine` is the single Perl classifier used by scanning and persistent
parsing. It returns an ordered list of semantic records carrying a type, source name, source entry,
scan label, and measured value. Dump records flush pending entries and reset context. An empty list
represents deferred geometry; an unrecognized line returns no record. Scanner aggregation consumes
the scan labels, while the persistent worker serializes source entries and values without
reclassifying them. Python types validate, balance, and reduce the parsed measurements. The simulator
registry exposes supported variable-type strings to the UI.

Accumulators collect typed observations through `add_observation`: a numeric point, a literal
configuration string, or a numeric entry mapping for one source/dump. Numeric wire text converts
at the worker boundary; entry names retain their exact spelling. Scalar families represented as
vectors combine their independent source entries into one temporal frame before ingestion.

The shared lifecycle ends collection with `balance_content()`, then computes a result with
`reduce_duplicates()`. Reading `reduced_content` before both stages succeed raises an error;
ingestion after balancing and reduction before balancing also raise. Repeated successful lifecycle
calls are idempotent. Content, result and entry inspection returns defensive snapshots. Numeric
kinds retain one point list or one frame list as their authoritative store. Configuration retains
the first literal string, or its explicit `on_empty` value when no observation is present. Text such
as `NA` remains literal; only absent numeric cells and numeric NaN use the missing-value marker.
All numeric kinds share a population mean that preserves finite results when their intermediate
sum overflows. Missing values propagate, cancellation retains small residuals, and infinite
observations follow explicit IEEE semantics. Missing-output diagnostics and padding share an
actual-observation presence count, so a measured NaN is distinct from an absent entry or source.

Summary measurements are named entries of their source statistic, selected through its
`statistics` field. They use ordinary entry buffering in the worker. Source names retain their
literal spelling, including double underscores; the worker does not reinterpret name suffixes.
Output aliases select their explicit source names and do not request unrelated matching labels.

All parsers produce the generic contract in `src/core/models/csv_contract.py`: a header, rows,
consistent columns, values, and explicit `NaN` for missing numeric data. Simulator-specific column
names remain inside the backend.

The gem5 backend produces one row per input file. `repeat` declares the expected number of dumps
per concrete statistic. Spatial patterns average all concrete instances and dumps; scanner-generated
scalar-pattern vectors retain one entry per selected instance and average its temporal dumps.
Missing variables, expected instances, dumps, or summary measurements remain `NaN`. Only omitted
interior frequency buckets in an otherwise complete observed distribution are inferred as zero.

Every scanned variable declares its raw `source_type` and an immutable tuple of `SourceInstance`
records. A record holds the exact concrete `source_name` and ordered numeric `indices` for display;
literal sources use empty indices. For example, `cpu012.ipc` has coordinates `("012",)` in the
`cpu\d+.ipc` family. Leading zeros remain intact. Scanner-generated scalar families suggest vector
output with `entries=[]`; their output entry schema derives from instance records. Genuine vector
measurement entries remain separate from source coordinates. Numerically similar names with
different raw kinds remain separate literal variables. Optional observed bounds are finite numbers;
unknown bounds are omitted from serialized metadata. Group counts derive from the instance records.
The editor projects both literal and aggregated records through the bounded numeric matcher, so
manual patterns can select concrete sources without reconstructing names or guessing raw kinds.

Every runnable `StatConfig.params` declares `source_type`, including literal requests. It describes
the raw source independently of `StatConfig.type`, the requested output representation. This permits
explicit vector/frequency reinterpretation while keeping raw observation validation precise. The
editor offers separate raw source and output controls; an unfinished raw source choice remains an
explicit draft. Manual callers declare the kind rather than triggering a scan or inference fallback.

`params.selected_sources` contains concrete source names, never numeric labels. Omitted selection
uses all matching current records; an explicit empty selection is nonexecutable. Submission resolves
numeric patterns once against those records, validates bounds and coordinates, and constructs one
private `AccumulatorSpec` per logical output. Each worker owns independent accumulators and uses
an immutable direct source-to-output routing map. It does not rematch patterns or use shared
accumulator identities as aliases. `keep_indices=True` creates separate concrete-named outputs;
otherwise source instances reduce according to the selected output representation. A scalar-family
vector derives entries only from its selected instances; callers must not supply a second entry list.

Current portfolios and recipes require complete scanned metadata and runnable raw source kinds.
Missing fields, numeric-only source selections, and retired metadata shapes fail validation.

Current distribution output uses fixed unit-width integer buckets. Its minimum and maximum must
be integral numbers; integral floating-point metadata converts losslessly when constructing the
accumulator. Fractional geometry is unsupported and raises a clear validation error rather than
truncating bounds. Statistics-only requests need no bucket bounds. Histogram range and rebinning
geometry remain separate from this distribution constraint.

Full and incremental parsing use the same deterministic union of observed columns. A histogram
bucket discovered in a later file remains in the schema, with `NaN` for files lacking that bucket.
Raw gem5 histogram endpoints are inclusive integers (`0-9`, `10-19`). Rebinning treats these as
`[0,10)` and `[10,20)`, and preserves total frequency under the uniform-within-bucket assumption.
New integer output bins retain inclusive labels; fractional boundaries use explicit half-open
labels such as `[0,2.5)`. `10+` includes values at or above ten, and `<0` retains negative mass.
A single target bin is labeled `0+` because it retains all nonnegative values, including overflow.
The figure layer requires nonoverlapping buckets within each observation and explicit
half-open labels for continuous intervals. It resolves each label independently of its neighbors.

gem5 also prints singleton buckets as bare integers, including negative integers. The scanner uses
histogram geometry or the reserved `gmean` summary to recognize these and emits explicit inclusive
labels such as `0-0`. Distribution summaries and boundaries distinguish distributions from numeric
vectors. Geometry-looking vector names retain their measured values unless histogram context
identifies them as metadata. The shared classifier flushes pending entries and resets context at
named and unnamed simulation dump boundaries. Oneline histograms require a positive
`bucket_size` and a payload matching their bounds. Current gem5's `nozero` flag suppresses zero
`min_bucket` and `max_bucket` fields, so omitted bounds within a dump represent zero, as defined by
[gem5's text writer](https://github.com/gem5/gem5/blob/stable/src/base/stats/text.cc#L273-L277).
Missing bucket size, reversed bounds, and inconsistent bucket counts fail visibly. Zero-total
histograms retain measured zero buckets when gem5 omits percentage columns. Scalar and summary
measurements preserve scientific notation and non-finite `nan`/`inf` values. If the output suppresses
all identifying metadata, callers can explicitly select the histogram type; numeric vector entries
remain vectors during scanning.
Histogram-to-vector selections use inclusive singleton labels returned by the scanner, such as
`0-0`; bare histogram point IDs fail validation. Ordinary vector labels continue to match exactly.

Durable job reuse and incremental rows use the same bounded content-fingerprint helper. Statistics
and configuration-aware companion files are hashed in full; unchanged timestamps or sizes never
authorize reusing changed data. Missing companion inputs fail before submission. Inputs are checked
again before finalization; a changed input fails the job instead of publishing under a stale identity.

`finalize_incremental_parsing(batch, results, complete=True)` is the backend and facade contract
for complete and partial incremental work. Complete finalization requires every planned row and
updates the success cache. Passing `complete=False` publishes valid changed and reused rows while
leaving that cache unchanged; no usable rows is an error. Both modes validate input fingerprints
and exact, unique source provenance before publication. Results count accepted changed and reused
rows against the planned `total_files`, so a partial result can contain fewer rows than that total.

`PARSER_RESULT_VERSION` in `src/core/models/parsing_models.py` is the shared semantic revision for
incremental rows and durable parse requests. Changing parser meaning or output labels requires
bumping it so neither cache can return measurements from an older contract.

Config-aware parsing reads `config.ini` as UTF-8 literal values and preserves parameter-name case.
Percent signs and interpolation-looking workload arguments remain unchanged.

## Failure and security rules

Gem5 tasks detach expected data and I/O failures before their Futures retain them. Explicit
`ParseDataValueError`, `ParseDataTypeError`, and `ParseDataRuntimeError` sites preserve the corresponding
builtin error category. `ResultAdmissionError` uses the same boundary for retained-result limits.
Reviewed builtin filesystem/process errors preserve their concrete type,
errno and filenames. Retained errors have no producer traceback, cause or context object; immutable
`failure_facts` contains the planned source ID, the last eight origin locations (2,048 characters),
and a cause summary (1,024 characters). Messages are limited to 1,024 characters, including an
explicit truncation marker. Error logs retain bounded text rather than exceptions or observation
containers. Unmarked programming errors propagate with their identity and traceback intact.

- Do not turn a regex miss, missing statistic, worker failure, or malformed file into zero.
- Numeric index extraction follows the shared matching timeout; execution-bound failures propagate
  during submission rather than becoming missing observations.
- Preserve path validation and leading-dash checks before work reaches subprocesses.
- Keep core services and Streamlit out of parsing imports.
- Release or cancel owned futures without shutting down another session's live work.

See [Add a Parser]({{site.baseurl}}/developer-guide/extension-guides/adding-a-parser/) for
implementation steps.
