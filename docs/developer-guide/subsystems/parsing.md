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
file failures, and publishes a schema-bound typed output. Cancellation must affect only work owned by the current API
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

## Variable types and typed output

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
kinds retain only actual points or frames as their authoritative store. `content` exposes actual
observations, including NaN for absent entries within an observed frame; it never appends absent
frames. Balancing records their exact logical missing count in `padded_count` and
`missing_measurement_count`. Reduction propagates that missingness without allocating in proportion
to the expected repeat count. Statistic representations show compact metadata without copying
observation content. Configuration retains
the first literal string, or its explicit `on_empty` value when no observation is present. Text such
as `NA` remains literal; only absent numeric cells and numeric NaN use the missing-value marker.
All numeric kinds share a population mean that preserves finite results when their intermediate
sum overflows. Missing values propagate, cancellation retains small residuals, and infinite
observations follow explicit IEEE semantics. Missing-output diagnostics and padding share an
actual-observation presence count, so a measured NaN is distinct from an absent entry or source.
Active histogram rebinning checks the requested bin count as a lower bound on emitted width
against the existing physical-column budget before constructing bucket labels. It then validates
the exact emitted width, including negative buckets and distinct selected summaries, before
constructing raw-bucket mappings. Explicit bucket selection and summaries-only mode take
precedence over unused rebin geometry.

Summary measurements are named entries of their source statistic, selected through its
`statistics` field. They use ordinary entry buffering in the worker. Source names retain their
literal spelling, including double underscores; the worker does not reinterpret name suffixes.
Output aliases select their explicit source names and do not request unrelated matching labels.

Workers finish balancing and reduction before resolving their Futures with immutable
`ParsedFileResult` values. Each logical variable explicitly declares its numeric or text kind and
`scalar` or `entries` shape. Scalar output has exactly one cell; entry output may have no observed
columns. Cells preserve exact physical names, including names containing `..`; ownership never
derives from punctuation. Metadata columns have a separate owner namespace, and any physical
column collision fails visibly. Numeric union gaps remain NaN. Missing text is invalid rather than
inventing a label.

`src/core/common/parsed_output.py::ParsedOutputIO` is the single schema resolver, CSV publisher and
reader. It enforces bounded variable, column, row, cell and byte budgets, publishes atomically, and
returns `ParsedOutput(csv_path, sha256, schema)`. The digest binds the canonical ordered schema and
CSV bytes with domain-separated framing. It detects content/schema substitution, but does not
authenticate an author. Reading checks stable file identity, exact schema/header, canonical cell
encoding and digest before exposing a frame. Literal `NA`, `nan`, empty strings, leading zeros,
Unicode, whitespace and control characters remain text. Explicit numeric NaN/infinity/zero and
representable subnormal values remain numbers. Finite wire tokens outside the nonzero Float64
range reject before publication.

CSV is an external exchange representation. In-process consumers retain the descriptor. Public
scripts call `session.load(parsed_result)`; passing `parsed_result.csv_path` deliberately invokes
ordinary external CSV inference and null handling. No filename lookup or portable schema sidecar
changes that behavior.

The gem5 backend produces one row per input file. `repeat` declares the expected number of dumps
per concrete statistic. Spatial patterns average all concrete instances and dumps; scanner-generated
scalar-pattern vectors retain one entry per selected instance and average its temporal dumps.
Missing variables, expected instances, dumps, or summary measurements remain `NaN`. Only omitted
interior frequency buckets in an otherwise complete observed distribution are inferred as zero.

Every scanned variable owns `source_evidence`: either a resolved compatible contract with its
`wire_contract` or `backend_metadata` basis, or an explicit set of ambiguous compatible contracts.
The gem5 scanner and persistent parser consume the same structured decoder events. Printed labels
remain literal observations; they do not establish hidden native geometry or a physical C++ class.
Ambiguous sources have `type=None`, so selecting one requires an explicit output type and compatible
`params.source_type`. The scanner never chooses between overlapping native wire forms by priority.

Each record owns an immutable tuple of `SourceInstance` identities. A record holds the exact concrete
`source_name` and ordered numeric `indices` for display; literal sources use empty indices. For
example, `cpu012.ipc` has coordinates `("012",)` in the `cpu\d+.ipc` family. Leading zeros remain
intact. Resolved scalar families suggest vector output with `entries=[]`; their output entries derive
from those source instances. Measurement entries remain separate from source coordinates. Conflicting
source contracts remain visible failures while unrelated valid sources survive a partial scan. Strict
public scans reject incomplete discovery before publishing editor state.

Every runnable `StatConfig.params` declares `source_type`, including literal requests. This is a
caller-supplied compatible decoder contract, independent of `StatConfig.type`, the requested output
representation. Submission checks it against scanned evidence; workers check it again against actual
completed source evidence before ingestion. This permits explicit vector/frequency reinterpretation
without claiming that text uniquely reveals the physical producer. The editor offers separate source
contract and output controls; an unfinished choice remains an explicit draft. Deep scans retain
printed labels and compatible evidence, and never derive minimum/maximum grid bounds. Oneline
Histogram execution requires complete observed integral geometry; absent zero-valued header fields
are not silently supplied. Numeric records retain the first measurement while accepting up to two
derived percentage fields and the native trailing unit annotation. Those decorations do not declare
scientific column semantics; literal configuration text is preserved independently.

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

Native Distribution frequency output requires explicit finite `minimum`, `maximum`, positive
`bucket_size`, and `zero_policy` (`"missing"` or `"nozero"`). The native cell count is
`ceil((maximum - minimum + 1) / bucket_size)`, including allocated cells above the tracked maximum.
Bounds and width retain native-double precision; printed labels and rounded geometry headers do
not replace the declaration. Statistics-only extraction needs no grid and allocates no buckets.

The omission policy is explicit: `"missing"` keeps omitted frequency cells and tails as
NaN. `"nozero"` asserts an external producer omission guarantee and supplies zero only for omitted
frequency cells or tails in an actually present compatible observation. Missing summaries, observed
NaN, missing whole sources/dumps and missing expected repetitions stay missing. Text cannot verify a
falsely asserted omission guarantee. Actual native `samples` headers bind repeated sparse frames;
header-free complete observations retain their actual fractional means.

Each full native output carries an immutable request-basis layout with geometry, omission policy,
and explicit physical-column/source-label/role/native-index bindings. An unchanged Vector view from
an explicitly declared Distribution source carries opaque source-label bindings, without a grid or
omission claim. Declaring `source_type="vector"` retains ordinary Vector semantics even for identical
label text. Explicit generic Histogram conversion remains available only for its supported integer
point/range labels. Fractional native cells require Distribution output; no truncation or guessed
continuous width is supplied. The Histogram renderer rejects native/opaque Distribution declarations
when native cell rendering is unavailable, rather than interpreting them as continuous ranges.

Full and incremental parsing use the same deterministic union of observed columns. A histogram
bucket discovered in a later file remains in the schema, with `NaN` for files lacking that bucket.
Raw gem5 histogram endpoints are inclusive integers (`0-9`, `10-19`). Rebinning treats these as
`[0,10)` and `[10,20)`, and preserves total frequency under the uniform-within-bucket assumption.
New integer output bins retain inclusive labels; fractional boundaries use explicit half-open
labels such as `[0,2.5)`. `10+` includes values at or above ten, and `<0` retains negative mass.
A single target bin is labeled `0+` because it retains all nonnegative values, including overflow.
The figure layer requires nonoverlapping buckets within each observation and explicit
half-open labels for continuous intervals. It resolves each label independently of its neighbors.

gem5 also prints singleton buckets as bare integers, including negative integers. Discovery retains
literal source labels and compatible contract evidence; it does not certify a hidden physical
producer from familiar labels or summaries. Histogram consumers canonicalize declared integer
singletons to inclusive labels such as `0-0`; ordinary Vector labels continue to match exactly.
The shared classifier flushes pending entries and resets context at named and unnamed dump
boundaries. Scalar and summary measurements preserve scientific notation and non-finite `nan`/`inf`.

Oneline execution checks every selected target against its own declared grid and exact allocated
cell count. Full native Distribution checks fixed-format headers at their observed decimal precision.
Width is mandatory; an omitted bound is accepted only when that exact declared bound is zero and
`zero_policy="nozero"`. Generic Histogram requires complete observed integral geometry. Neither
representation pads a shortened oneline sequence or shifts later values into omitted positions.

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

## Request and result ownership

Every full batch owns the planned source paths, logical variable order, output directory and
strategy. Finalization receives that batch and only finalized typed file results. Complete output
requires exact coverage. Partial output rejects duplicate or unplanned sources and requires usable
rows; it never promotes an incremental or background result to a complete success cache. Incremental
cache format 3 stores the same typed records and validates them before retaining reused rows.

Parser schema format 2 requires a nullable `layout` on every logical variable. Typed file results,
cache records and table attrs use one current layout codec. Tables retain a whole layout only while
all explicit numeric bindings remain valid and the operation preserves their coordinates. Ordinary
copies, row filters/sorts and complete column projections retain declarations; destructive reshaping,
unknown plugins and incompatible concat drop inherited declarations. Explicit caller attrs remain
caller declarations, not authentication of the producer. Parser origin/replay ownership is separate.

One selected-file owner serves full, subset, preview and incremental execution. Before constructing
labels/templates or decoding cached rows, planning admits all selected files against known physical
columns, including aliases, native cells/tails/summaries and config-aware metadata. Bounds are 10,000
physical columns, one million matrix cells, 4 MiB canonical schema and 256 MiB complete per-batch
result records. Cache input is bounded to 64 MiB before JSON decoding. Every returned file charges
its complete repeated layout bytes even when workers share the same immutable Python layout.

Gem5 batches share a retained-result admission budget of one million cells and 256 MiB of complete
canonical record encoding, separate from the CSV output budget. Accepted Futures retain their quota
even when cancellation is requested. Known data failures detach bounded primitive diagnostics before
the Future completes; unexpected programming exceptions retain their original identity and trace.

The actual parser request travels with public parse results and durable background receipts. Loading
publishes frame and replay origin together. Submitting a different request changes editor controls
without changing the loaded frame's origin. Generic manager edits clear reusable origin; exact named
selection and revision restoration retain the corresponding origin. Automatic recipe capture refuses
partial or undeclared-backend origins instead of guessing a complete replay source.
