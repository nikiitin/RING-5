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
needed by pages. `get_current_view` supplies a read-oriented snapshot for display. Plot
deserialization is injected so core does not import the web plot factory.

## Scan and parse

`submit_scan_async` returns futures; `finalize_scan` aggregates completed file results. The API tracks
only scans submitted by that instance, allowing `cancel_pending_scans` and `release_settled_scans`
to avoid affecting another browser session.

`submit_parse_async` returns a batch with futures and variable names. `finalize_parsing` assembles
completed parse results. Callers preserve failures and pass scanned-variable metadata for pattern
expansion.

## Data and previews

`load_data` stores a validated table through the state manager. Preview methods isolate tentative
manager output until the user confirms it. Shaper execution delegates to the pipeline service and
returns a new DataFrame.

## Change rules

- Add behavior to a focused sub-API when it belongs to one service family.
- Keep Streamlit types and calls out of the facade.
- Accept injected callbacks or protocols for presentation-owned reconstruction.
- Preserve async submit/finalize ownership and specific errors.
- Test facade composition in integration tests rather than copying every service unit test.
