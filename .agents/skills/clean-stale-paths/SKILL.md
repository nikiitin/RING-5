---
name: clean-stale-paths
description: Sweep code and docs for dead, duplicated, or stale paths/symbols and remove them — repoint drifted paths, delete docs for removed subsystems, and enforce canon-only docs (no "was X, now Y" history). Use when asked to clean up stale references, dead paths, doc debt, or legacy shims/aliases.
---

# Clean dead / duplicated / stale paths (code + docs)

RING-5 has **one canonical contract** per operation and document kind (see [AGENTS.md](../../../AGENTS.md)). Anything that
points at a path/symbol that no longer exists — or documents a removed feature as if it's current —
is cruft. This skill finds and removes it, in both code and docs, and enforces the canon-only doc
rule defined in AGENTS.md.

## Method (the sweep that actually works)
1. **Extract cited paths and test them for existence.** Treat this as a first pass, not proof that
   a subsystem is unused:
   ```bash
   rg -o --no-filename 'src/[A-Za-z0-9_./]+' docs/ AGENTS.md .agents/skills/ \
     | sed -E 's/[.,:;`)"]+$//' | sort -u \
     | while read -r p; do [ -e "$p" ] || echo "MISSING: $p"; done
   ```
2. **Triage each MISSING into one of three buckets — do not blindly delete:**
   - **Genuinely stale** — a real, current path that drifted. → repoint to the real location.
   - **Legitimate hypothetical** — an example in an extension guide (`sniper/`, `my_simulator/`,
     `waterfall_*`, `violin_plot`, `cumulative_sum`, `*_bokeh`, `some_service`). → keep.
   - **Grep artifact** — a real file with a stripped suffix/symbol (`common/utils` → `utils.py`,
     `trace_to_` → `trace_to_plotly.py`, `_connector_protocol.STYLING_PIPELINE_ORDER`). → keep.
   Confirm the bucket by checking which file cites it:
   `rg -l -F "<path>" docs/ AGENTS.md .agents/skills/`.
3. **Find the real location** for stale ones with `rg --files` and `rg -n "class <Name>" src/`.
4. **Removed entirely vs. moved:**
   - Moved → repoint the path.
   - Removed → verify the tracked source, imports, registries, public exports, CLI entry points,
     callbacks, subprocess assets and packaging declarations before deleting its current guide.
     Compiled caches are not evidence of the supported source contract.
5. **Code-side cruft** — dead/duplicate modules and **legacy aliases/shims**. Removing these is a
   refactor: migrate **all** importers + tests to the canonical name first, then delete (substitute,
   don't adapt). Search tracked source, tests, docs, scripts and configuration with `rg` before
   deleting. Verify callers through string references and dynamic registration too. (Verify the alias is real first —
   a `from X import Canonical as OldName` inside a test file is a local binding, not a production shim.)
   Current simulator variants, Linux architectures, output-column naming and revision history remain
   supported features; their presence alone does not establish a legacy execution path.

## Canon-only docs (enforce while you're in there)
- Docs and AGENTS.md state **only the current canonical way**, present tense. Delete "an earlier
  audit found…", "this used to be X", "deprecated shim kept for…", "removal in Phase 10".
- The **one** allowed home for history is `docs/developer-guide/architecture/history.md`. Past-tense
  names there are fine and expected — don't "fix" them.
- When you delete a numbered section, **renumber** the siblings and fix any in-page anchor links.

## Verify after (must all be clean)
```bash
# 1. re-run the existence sweep — only legit examples / history / artifacts may remain
rg -o --no-filename 'src/[A-Za-z0-9_./]+' docs/ AGENTS.md .agents/skills/ | sed -E 's/[.,:;`)"]+$//' | sort -u \
  | while read -r p; do [ -e "$p" ] || echo "MISSING: $p"; done
# 2. removed symbols gone from docs (example)
rg -n 'RingConfig|ConfigValidationService|PlotInteractionService' docs/
# 3. inspect compatibility/history wording outside the history document
rg -ni 'deprecated.shim|backward.compat' docs/ -g '!history.md'
```
Record durable contracts in the repository developer guide.

## Keep this skill sharp
Canon, not history — edit in place when the method improves:
- When a new class of false positive shows up in the sweep, add it to the triage buckets so the
  heuristic stays trustworthy.
- The example/history/artifact lists above are illustrative — refresh them from the latest sweep
  rather than letting them ossify.

This skill governs itself too: keep it present-tense and canonical.
