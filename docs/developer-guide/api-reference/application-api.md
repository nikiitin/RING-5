---
layout: default
title: Application API
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 2
permalink: /developer-guide/api-reference/application-api/
---

# Application API

<!--
`uman~ring5.quality.application-facade.documentation~1`

Covers:
- req~ring5.quality.application-facade~1

-->

`ApplicationAPI` is the internal facade composed by `app.py` and `ring5.Session`. Web pages receive
one instance per browser session rather than constructing services or repositories.

The facade exposes focused sub-APIs for managers, data services, and shapers, plus state operations
needed by pages. `get_current_view` supplies `raw_data`, `processed_data`, analysis `config`,
the canonical workspace `csv_path`, and `selected_dataset_name` for display. Identity fields
remain separate from configuration. The selected dataset name identifies active named data;
the workspace CSV path is a file association, not provenance for every retained dataset.
The header prefers the active name, then the CSV basename, then **Uploaded** when neither exists.
Plot deserialization is injected so core does not import the web plot factory.

## Scan and parse

`submit_scan_async` returns futures; `finalize_scan` aggregates completed file results. The API tracks
only scans submitted by that instance, allowing `cancel_pending_scans` and `release_settled_scans`
to avoid affecting another browser session.

`submit_parse_async` returns a batch with futures and variable names. `finalize_parsing` assembles
completed parse results. Runnable submissions accept only typed `StatConfig` values. The UI keeps
editable `ParseVariableConfig` drafts and calls `compile_parse_variables` at submission; unfinished
names, entry selections, or bounds raise a visible validation error without starting workers.
`StatConfigCodec` owns validation, exact wire serialization, and draft projection. Its fields and
per-type options use snake_case, integer repetition counts, and separate `entries`/`statistics`
lists inside one nested `params` dictionary. Every editor draft has the same structural fields
as `StatConfig`, plus its UI-only `_id`; no flat option shape is accepted.
`draft_from_scanned_variable` uses the selected simulator metadata to project scanner entries and
summaries through that same codec. Backend creation, durable jobs, the public parse API, and recipes use the same codec.
Every runnable value declares `params.source_type` independently of its requested output type.
Callers preserve failures and pass current scanned-variable records for numeric source patterns.
Each record requires concrete `SourceInstance` identities and numeric display coordinates.
`params.selected_sources` selects concrete names; workers receive a precompiled direct routing plan.

Portfolio schema 7 stores each parser variable as exactly `{state: "draft", fields: ...}` or
`{state: "runnable", config: ...}`. Drafts preserve incomplete current editor input; runnable
snapshots contain every `StatConfig` field. UI identifiers never enter the saved format and are
regenerated when restored. Recipes require runnable variables and use recipe schema 3. Template
operands are validated as declared placeholders, then compiled after materialization.

`finalize_incremental_parsing` accepts the keyword-only `complete` flag, defaulting to `True`.
Both modes retain accepted reusable rows and validate provenance. `complete=False` permits partial
output without promoting the success cache; no usable rows fails visibly. Returned counts describe
accepted changed/reused files and the planned total. Every backend implements this same contract.

Entry-filtering methods require the selected `SimulatorInfo.internal_stats` explicitly. A
simulator's summary names are metadata, so a generic service never guesses a gem5 default.

## Data and previews

`load_data` stores a validated table through the state manager. Preview methods isolate tentative
manager output until the user confirms it. Use `api.shapers.process_pipeline(data, config)` for
stateless transformation execution, which returns a new DataFrame. Pipeline configuration and CSV
pool operations use `api.data_services`; numerical manager operations use `api.managers`.
Facade methods coordinate state, owned jobs, or multiple services.

`capture_preview_inputs(dataset_names=())` returns immutable active-source identities by default,
or ordered named dataset identities when names are supplied. Capture before computation, then
call `set_preview(..., operation_config=options, inputs=captured)`; both review arguments are
required. Publication rejects changed sources. `get_preview` returns an owned frame only while
its captured sources remain current; `preview_matches` additionally checks current options.
`confirm_preview` applies only an active-source transformation. Named comparison previews are
for display and cannot replace active data. Named identities include the workspace generation,
so reset, restore and another session cannot reuse an earlier capture. Their monotonic mutation
identity also rejects work spanning a source change and undo to the captured revision.


## Change rules

- Add behavior to a focused sub-API when it belongs to one service family.
- Keep Streamlit types and calls out of the facade.
- Accept injected callbacks or protocols for presentation-owned reconstruction.
- Preserve async submit/finalize ownership and specific errors.
- Test facade composition in integration tests rather than copying every service unit test.

## Resource lifetime

`ApplicationAPI.close()` cancels owned work and releases session resources. Parser file workers
settle before their workspace is removed. Use `close(wait=True)` when a caller also needs to wait
for background transformations and exports; repeated waiting closes settle an already requested
shutdown. Closed job services reject new background and managed parse jobs.
