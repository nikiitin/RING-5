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

## HTML coverage report

`make oft-report` first asks the pinned OpenFastTrace JAR to generate its native
HTML trace with full artifact detail. RING-5 then adds a coverage overview,
feature-group summaries, covered/uncovered totals, and requirement filters to
that document. Coverage comes from OFT's own green/red requirement markers; the
complete native artifact graph remains embedded below the overview.

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

Evidence uses repository-relative file paths. Add `::symbol` or `#heading` to
make a reference more precise; the generator validates the file portion.

## Automatic discovery

The generator compares the inventory with live application surfaces that are
easy to extend accidentally: navigation, plot and shaper registries and schemas,
simulator/parser metadata, rendering configuration and formats, public Python
exports and class members, facade protocols, and CLI commands and options. A
new or changed value fails `make oft-check` until it is mapped to a requirement.
Capabilities without a central registry still need a normal inventory entry and
evidence review.

See `discovery-audit.md` for the reviewed source surfaces, accepted deltas,
rejected candidates, and the zero-delta pass that established convergence.

Approved items receive the generated tag `status_approved`; future items use
`status_draft` or `status_proposed`. This lets the default trace verify today's
baseline while the all-status trace acts as a development backlog.

<!-- oft:off -->
The generated IDs follow native OFT syntax, for example
`req~ring5.plot.scatter~1`. See the upstream
[OpenFastTrace user guide](https://github.com/itsallcode/openfasttrace/blob/main/doc/user_guide.md)
for the complete authoring and trace-report reference.
<!-- oft:on -->
