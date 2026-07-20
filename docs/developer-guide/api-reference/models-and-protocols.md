---
layout: default
title: Models and Protocols
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 4
permalink: /developer-guide/api-reference/models-and-protocols/
redirect_from:
  - /developer-guide/core/
  - /developer-guide/core/models-reference/
  - /engineering-reference/reference/models-catalog/
  - /engineering-reference/reference/protocol-catalog/
---

# Models and protocols

Cross-layer models live in `src/core/models/`. Prefer a dataclass for validated structured state, a
`TypedDict` for JSON-compatible mappings, and a protocol for behavior owned by another layer.

Parsing models carry scan results, parse batches, variable configuration, and simulator metadata.
Import models carry immutable delimiter/encoding corrections, inferred column types, accepted-row
previews, rejected source lines, and the source fingerprint used at confirmation time.
`BrowserUpload` records validated upload type, original-byte fingerprint, staged paths, and bounded
dataset or portfolio summary metadata without retaining browser bytes in application state.
Remote-source models separate HTTP, SSH, and S3 configuration; credential fields are excluded from
representations. `RemoteSourcePolicy` records the explicit host, private-address, and TLS boundary,
while `RemoteDownload` keeps response bytes out of its representation before upload validation.
Data models carry plot serialization and current-view shapes. Portfolio models define persisted
fields and `RestoreReport`. Shaper models form a discriminated configuration union. Visualization
models describe engines, traces, axes, legends, annotations, labels, palettes, and full figure
configuration without backend imports.

## Compatibility

- A field serialized to JSON or CSV needs a default or migration when changed.
- A `TypedDict` discriminator must match its factory identifier.
- Protocols remain narrow; do not turn them into catalogs of an implementation.
- Models do not call services, read application state, or import Streamlit or rendering engines.
- Round-trip tests cover `to_dict` and `from_dict` behavior for persisted models.

Use the source definitions as the field-level reference. This page records ownership and stability,
not a copied inventory that can drift.
