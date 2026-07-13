"""
Simulator-agnostic parsing framework (Layer A, shared).

Reusable infrastructure that every simulator backend builds on, independent of
any one simulator's format or variable model:

- ``work_pool.WorkPool`` — singleton thread pool for parallel parse/scan work.
- ``job.Job`` — the abstract callable work-unit contract pools execute.
- ``file_discovery.find_stats_files`` — recursive stats-file discovery.

Backends (e.g. ``src/parsing/gem5/``) import from here; this package imports
nothing simulator-specific.
"""
