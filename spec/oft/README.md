# RING-5 feature traceability

This directory is the source of truth for RING-5's OpenFastTrace (OFT) feature
catalog. It records what the application already does, the evidence for each
capability, and future requirements that have not been implemented yet.

The trace graph is deliberately small:

```text
feat (feature group) -> req (detailed behavior) -> impl + test + uman
```

`inventory.json` is human-maintained. The Markdown under `generated/` is
deterministic output and must not be edited directly.

## Commands

Run these commands from the repository root:

```shell
make oft-generate    # validate the inventory and regenerate Markdown
make oft-check       # detect invalid evidence, registry drift, or stale output
make oft-trace       # trace the approved/current baseline with OFT
make oft-trace-all   # include draft and proposed requirements to expose gaps
make oft-report      # build the HTML traceability report from native OFT output
```

The trace targets download the pinned OFT JAR into `.cache/openfasttrace/` on
first use. OpenFastTrace requires Java 17 or newer. `oft-check` is also part of
the repository quality gate and does not require Java or a network connection.

## What covered means

<!--
`uman~ring5.trace.inventory-generator.documentation~1`

Covers:
- req~ring5.trace.inventory-generator~1

-->

A requirement is **covered** only when native OpenFastTrace marks the requirement green after it
finds all three required artifact types:

1. `impl`: one or more markers inside the Python symbols that implement the behavior;
2. `test`: one or more markers inside the exact tests that verify it; and
3. `uman`: one or more user-manual items below the documentation heading that specifies it.

The inventory uses `path::qualified.symbol` and `path#heading` references. Schema version 2 makes
`make oft-check` reject a locator unless the corresponding source-level OFT marker exists at that
symbol or heading. OFT reads those real source markers directly; the generator does not create
substitute implementation, test, or documentation artifacts.

Coverage proves that the specification and its three evidence classes are linked in the trace. It
does not prove that a test passed in the latest CI run, that the implementation is correct, or that
the requirement statement is a good description. Those are separate review and test outcomes.

## HTML coverage report

<!--
`uman~ring5.trace.human-html-report.documentation~1`

Covers:
- req~ring5.trace.human-html-report~1

-->

`make oft-report` first asks the pinned OpenFastTrace JAR to generate its native
HTML trace with full artifact detail. RING-5 then adds a coverage overview,
feature-group summaries, covered/uncovered totals, and requirement filters to
that document. Coverage comes from OFT's own green/red requirement markers. Every requirement card
lists the exact specification heading, implementation symbol, test symbol, and source-marker line,
with links to the corresponding native OFT artifact. The complete native artifact graph remains
embedded below the overview.

Open `spec/oft/generated/report.html` in any browser. The report is standalone,
uses no hosted assets, and links each human-readable requirement directly to its
canonical OFT trace item. Generation fails if OFT omits an expected feature or
requirement. `oft-check` verifies the report's inventory fingerprint
without needing Java.

## Requirement status views

<!--
`uman~ring5.trace.future-status-reporting.documentation~1`

Covers:
- req~ring5.trace.future-status-reporting~1

-->

The HTML inventory offers a separate one-click view for each requirement lifecycle status:

- `approved`: accepted current behavior with implementation, test, and documentation evidence;
- `proposed`: candidate future behavior ready for review;
- `draft`: an early requirement whose wording or scope can still change;
- `in-development`: future behavior currently being implemented; and
- `blocked`: future behavior that cannot currently progress.

Counts and group summaries use the same five statuses. Only `approved` belongs to the current
baseline; the other four remain future work until their evidence is reviewed and their status is
changed. These views filter inventory metadata in the human layer. They do not alter OFT's native
requirements, artifacts, links, or green/red coverage results.

## Implementation branches

<!--
`uman~ring5.trace.branch-association.documentation~1`

Covers:
- req~ring5.trace.branch-association~1

-->

Every future requirement records an `implementation_branch` in `inventory.json`. The value is
required for `proposed`, `draft`, `in-development`, and `blocked` items and may be retained after
approval. It is catalog metadata, not the name of the branch currently checked out, so generation
and review remain deterministic after branches are merged or removed.

The generated requirement Markdown places the branch beside the normative statement. The summary
lists future requirements by branch, and the HTML card displays and searches the same association.
`oft-check` rejects missing or unsafe branch names before generating either view.

## Requirement history

<!--
`uman~ring5.trace.requirement-history.documentation~2`

Covers:
- req~ring5.trace.requirement-history~2

-->

The active `revision`, `title`, and `description` remain the normative requirement. When its meaning
changes, increment `revision` and add one `semantic` history record containing the superseded
revision's complete title and description plus a concise reason. Every earlier revision must have
exactly one semantic snapshot; gaps and duplicates fail `oft-check`.

An evidence-only change keeps the active revision unchanged and may add an `evidence` record with
the same revision and a reason. Evidence records cannot contain a title or description, so they
cannot silently redefine behavior. History remains ordinary reviewable inventory data: generated
Markdown summarizes it, and the HTML requirement card shows the old normative text and both change
types without adding obsolete requirements to the native OFT graph.

## Compare requirement revisions

<!--
`uman~ring5.trace.requirement-diff.documentation~1`

Covers:
- req~ring5.trace.requirement-diff~1

-->

Compare the working catalog with any commit, tag, or branch:

```shell
make oft-diff BASE=main
./python_venv/bin/python scripts/diff_oft_inventory.py main --format json
```

The human report separates added and removed IDs from changed fields, including individual evidence
lists. It also lists every currently covered and uncovered requirement plus requirements whose
coverage changed in either direction. JSON output exposes the same stable fields for automation.

Coverage on both sides comes from the green/red results in each revision's committed native-derived
OFT report. The command verifies each report's inventory fingerprint and fails instead of inferring
coverage when a report is missing or stale. Git revisions are resolved to a commit before files are
read, and the comparison never checks out or modifies either revision.

## Requirement readiness

<!--
`uman~ring5.trace.readiness-checklist.documentation~1`

Covers:
- req~ring5.trace.readiness-checklist~1

-->

Every HTML requirement card reports six signals separately: valid specification text, exact
implementation origins, exact test origins, exact documentation origins, the native OFT green/red
result, and the latest supplied execution result. Missing evidence remains visible even if another
dimension is ready. In particular, a test link or green OFT trace never implies that a test ran.

Without execution input, every card says `No execution result supplied`. To add actual results,
provide a bounded JSON document when generating the report:

```json
{
  "format": "ring5.oft-execution-results",
  "schema_version": 1,
  "requirements": {
    "trace.inventory-generator": "passed",
    "trace.approval-gate": "not-run"
  }
}
```

```shell
make oft-report EXECUTION_RESULTS=execution.json
```

Allowed values are `passed`, `failed`, and `not-run`. Results may cover any subset of the inventory;
omitted requirements remain `not recorded`. Unknown IDs, invalid statuses, formats, or schema
versions fail report generation.

## Recording a feature

Add one object to `features` in `inventory.json`:

- Give it a stable lowercase ID under the appropriate feature group.
- Use `approved` for behavior that exists now and supply implementation, test,
  and user-documentation evidence.
- Use `draft`, `proposed`, `in-development`, or `blocked` for future behavior.
  Evidence lists may be empty,
  so `make oft-trace-all` reports exactly which coverage remains missing.
- Record the future item's dedicated `implementation_branch`.
- Increment the revision and retain its semantic snapshot when behavior changes. Evidence-only,
  spelling, and formatting changes keep the current revision.
- Bind registry-backed behavior in `discovery_bindings` when applicable.

Evidence uses repository-relative `path::qualified.symbol` references for Python and `path#heading`
references for documentation. Add the matching native marker inside that exact symbol or below that
heading. The generator validates both sides of the link and rejects unregistered source markers.

## Automatic discovery

<!--
`uman~ring5.trace.registry-drift.documentation~1`

Covers:
- req~ring5.trace.registry-drift~1

-->

The generator compares the inventory with live application surfaces that are
easy to extend accidentally: navigation, plot and shaper registries and schemas,
simulator/parser metadata, rendering configuration and formats, public Python
exports and class members, facade protocols, and CLI commands and options. A
new or changed value fails `make oft-check` until it is mapped to a requirement.
Capabilities without a central registry still need a normal inventory entry and
evidence review.

See `discovery-audit.md` for the reviewed source surfaces, accepted deltas,
rejected candidates, and the zero-delta pass that established convergence.
See `future-roadmap.md` for proposed requirements, their feature branches, and dependency order.

Approved items receive the generated tag `status_approved`; future items use the corresponding
`status_draft`, `status_proposed`, `status_in_development`, or `status_blocked` tag. The default
trace filters by the native OFT `approved` status so source-level evidence without catalog tags
remains in the graph. The all-status trace acts as a development backlog.

<!-- oft:off -->
The generated IDs follow native OFT syntax, for example
`req~ring5.plot.scatter~1`. See the upstream
[OpenFastTrace user guide](https://github.com/itsallcode/openfasttrace/blob/main/doc/user_guide.md)
for the complete authoring and trace-report reference.
<!-- oft:on -->
