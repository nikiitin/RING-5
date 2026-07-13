---
title: "Automated Contributor Guidance"
---

# Automated contributor guidance

RING-5 keeps repository-specific contribution guidance in [`AGENTS.md`](../../../AGENTS.md).
Task recipes for common maintenance and extension work live in
[`/.agents/skills/`](../../../.agents/skills/).

These files complement the developer guide; they do not replace tests or source inspection. The
code and executable checks remain authoritative when documentation has drifted.

## Expected workflow

1. Read `AGENTS.md` and the guide relevant to the change.
2. Inspect the affected implementation, tests, and public documentation before editing.
3. Preserve the architecture boundaries and serialized compatibility contracts.
4. Add focused tests for the requested behavior.
5. Run the repository quality and test gates.
6. Review the final diff for unsupported claims, generated files, secrets, and unrelated changes.

## Documentation standard

Automated contributions follow the same standard as human contributions:

- Public Python APIs use concise Google-style docstrings.
- Comments explain intent, constraints, or non-obvious decisions rather than restating code.
- User-facing behavior is documented in the user guide.
- Architectural contracts and extension points are documented in the developer guide.
- Plans, transcripts, model-specific settings, and tool caches are not committed.

## Verification

Run the narrowest relevant tests while iterating, followed by:

```bash
make quality-gate
make test-ci
make test-e2e
```

Rendering changes must be exercised through both Plotly and Matplotlib. Parser changes must cover
missing data, malformed input, cancellation, and worker cleanup. Public API changes must extend
`tests/integration/test_ring5_public_api.py`.
