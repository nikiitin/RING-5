---
name: clean-stale-paths
description: Sweep code and docs for dead, duplicated, or stale paths/symbols and remove them — repoint drifted paths, delete docs for removed subsystems, and enforce canon-only docs (no "was X, now Y" history). Use when asked to clean up stale references, dead paths, doc debt, or legacy shims/aliases.
---

# Clean dead / duplicated / stale paths (code + docs)

RING-5 has **one canonical way** to do everything ([[substitute-not-adapt-ring5]]). Anything that
points at a path/symbol that no longer exists — or documents a removed feature as if it's current —
is cruft. This skill finds and removes it, in both code and docs, and enforces the canon-only doc
rule ([[ring5-docs-canon-only]]).

## Method (the sweep that actually works)
1. **Extract every cited path and test it for existence.** This single heuristic surfaces most rot:
   ```bash
   { grep -rhoE "src/[A-Za-z0-9_./]+" docs/ CLAUDE.md .claude/skills/ 2>/dev/null; } \
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
   `grep -rlF "<path>" docs/ CLAUDE.md`.
3. **Find the real location** for stale ones: `find src -name "<file>.py"` /
   `grep -rn "class <Name>" src/`.
4. **Removed entirely vs. moved:**
   - Moved → repoint the path.
   - Removed (no class/symbol anywhere in `src/`; a stray `__pycache__/*.pyc` with **no** sibling
     `.py` proves the source was deleted) → **delete the doc section**. Do not leave a tombstone.
5. **Code-side cruft** — dead/duplicate modules and **legacy aliases/shims**. Removing these is a
   refactor: migrate **all** importers + tests to the canonical name first, then delete (substitute,
   don't adapt). `grep -rn "<oldname>" src/ tests/` before deleting. (Verify the alias is real first —
   a `from X import Canonical as OldName` inside a test file is a local cosmetic, not a production shim.)

## Canon-only docs (enforce while you're in there)
- Docs and CLAUDE.md state **only the current canonical way**, present tense. Delete "an earlier
  audit found…", "this used to be X", "deprecated shim kept for…", "removal in Phase 10".
- The **one** allowed home for history is `docs/developer-guide/architecture/history.md`. Past-tense
  names there are fine and expected — don't "fix" them.
- When you delete a numbered section, **renumber** the siblings and fix any in-page anchor links.

## Verify after (must all be clean)
```bash
# 1. re-run the existence sweep — only legit examples / history / artifacts may remain
{ grep -rhoE "src/[A-Za-z0-9_./]+" docs/ CLAUDE.md 2>/dev/null; } | sed -E 's/[.,:;`)"]+$//' | sort -u \
  | while read -r p; do [ -e "$p" ] || echo "MISSING: $p"; done
# 2. removed symbols gone from docs (example)
grep -rnE "RingConfig|ConfigValidationService|PlotInteractionService" docs/
# 3. no dangling anchors to removed sections
grep -rniE "deprecated.shim|backward.compat" docs/ | grep -v history.md
```
Then update `MEMORY.md` / the relevant memory ([[ring5-doc-debt-followup]]) so the next sweep starts
from the new baseline.

## Keep this skill sharp
Canon, not history — edit in place when the method improves:
- When a new class of false positive shows up in the sweep, add it to the triage buckets so the
  heuristic stays trustworthy.
- The example/history/artifact lists above are illustrative — refresh them from the latest sweep
  rather than letting them ossify.

This skill governs itself too: keep it present-tense and canonical.
