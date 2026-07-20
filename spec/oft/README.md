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

## Recording a feature

Add one object to `features` in `inventory.json`:

- Give it a stable lowercase ID under the appropriate feature group.
- Use `approved` for behavior that exists now and supply implementation, test,
  and user-documentation evidence.
- Use `draft` or `proposed` for future behavior. Evidence lists may be empty,
  so `make oft-trace-all` reports exactly which coverage remains missing.
- Increment the revision when the behavior changes semantically. Spelling or
  formatting corrections do not require a revision bump.
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

Approved items receive the generated tag `status_approved`; future items use
`status_draft` or `status_proposed`. The default trace filters by the native OFT
`approved` status so source-level evidence without catalog tags remains in the graph. The
all-status trace acts as a development backlog.

<!-- oft:off -->
The generated IDs follow native OFT syntax, for example
`req~ring5.plot.scatter~1`. See the upstream
[OpenFastTrace user guide](https://github.com/itsallcode/openfasttrace/blob/main/doc/user_guide.md)
for the complete authoring and trace-report reference.
<!-- oft:on -->
