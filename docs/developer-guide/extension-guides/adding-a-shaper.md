---
layout: default
title: Add a Shaper
parent: Extension Guides
grand_parent: Developer Guide
nav_order: 3
permalink: /developer-guide/extension-guides/adding-a-shaper/
---

# Add a shaper

Shapers are stateless, ordered DataFrame transformations in `src/core/services/shapers/`. Each call
returns a new DataFrame and has no Streamlit dependency.

## Implement and register

1. Copy the closest implementation under `src/core/services/shapers/impl/`. Subclass `Shaper` or
   `UniDfShaper` for a single-frame operation.
2. Validate static configuration in `_verify_params` and data-dependent requirements in
   `_verify_preconditions`.
3. Copy the input before transformation. Keep `__call__` pure so pipeline fingerprint caching is
   safe.
4. Add a typed configuration to `src/core/models/shaper_models.py` and include it in the
   discriminated `ShaperStepConfig` union.
5. Register the class under a serialized camel-case identifier and add its display name once in
   `src/core/services/shapers/factory.py`.
6. Add a component under `src/web/components/shapers/` and wire its configuration dispatch through
   `src/web/pages/ui/shaper_config.py` or the relevant selector dispatch.

## Test and verify

Test valid output, input immutability, parameter validation, data preconditions, missing values, and
interaction with adjacent pipeline steps. Assert that `PipelineError` identifies the step at the
public boundary.

```bash
make arch-check
python_venv/bin/mypy src
make test-unit
```

Changing a serialized shaper identifier or configuration shape requires portfolio and pipeline
migration coverage.
