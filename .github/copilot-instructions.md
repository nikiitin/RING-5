# GitHub Copilot instructions for RING-5

**The canonical, verified project guide is [`/CLAUDE.md`](../CLAUDE.md).** Read it first and follow it.

It is the single source of truth for architecture, layer boundaries, commands, conventions, gotchas,
and extension recipes (with task-specific guides under [`/.claude/skills/`](../.claude/skills/)).

This file used to hold a long, separate copy of those instructions; it drifted out of date
(dead file paths, an obsolete "critical bugs" list). To avoid two sources of truth it now just
points at `CLAUDE.md`. If you update project guidance, update `CLAUDE.md`.

Quick reminders (full detail in `CLAUDE.md`):

- Version control is **human-only** — never run `git` mutations.
- `src/core/` and `src/parsing/` must not import Streamlit or touch `st.session_state`.
- Never `inplace=True`, never bare `except:`, never `eval`/`exec` in `src/`. Never fabricate stats.
- Run `make arch-check` / `make quality-gate` and `./python_venv/bin/mypy src/` before declaring done.
