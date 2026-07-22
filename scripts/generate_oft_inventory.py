#!/usr/bin/env python3
"""Generate and validate RING-5's OpenFastTrace feature inventory.

The inventory is deliberately data-driven.  Stable requirement identifiers and
human descriptions live in ``spec/oft/inventory.json`` while this script:

* validates evidence paths and the feature hierarchy;
* compares registry-backed capabilities with explicit inventory bindings; and
* renders deterministic OpenFastTrace Markdown artifacts.

Run with ``--check`` in CI to reject stale generated files or newly registered
capabilities that have not yet been assigned to a requirement.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import fields
from pathlib import Path
from typing import Any, cast, get_args

if __package__:
    from scripts.oft_evidence import collect_evidence_markers, validate_source_evidence
    from scripts.oft_html_report import (
        OftHtmlReportError,
        evidence_fingerprint,
        extract_oft_coverage,
        inventory_fingerprint,
    )
    from scripts.oft_status import requirement_status_tag, requirement_status_views
else:
    from oft_evidence import collect_evidence_markers, validate_source_evidence
    from oft_html_report import (
        OftHtmlReportError,
        evidence_fingerprint,
        extract_oft_coverage,
        inventory_fingerprint,
    )
    from oft_status import requirement_status_tag, requirement_status_views

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "spec" / "oft" / "inventory.json"
DEFAULT_OUTPUT_DIR = ROOT / "spec" / "oft" / "generated"
GENERATED_FILENAMES = ("features.md", "requirements.md", "summary.md")
HTML_REPORT_FILENAME = "report.html"
CI_WORKFLOW_PATH = Path(".github/workflows/ci.yml")
ALLOWED_STATUSES = frozenset(view.key for view in requirement_status_views())
HISTORY_CHANGE_TYPES = frozenset({"semantic", "evidence"})
ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
TAG_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
BRANCH_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._/-]*$")


class InventoryError(ValueError):
    """The feature inventory is malformed, incomplete, or out of sync."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting ambiguous duplicate keys."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError(f"Inventory contains duplicate JSON key {key!r}.")
        result[key] = value
    return result


def load_inventory(path: Path = DEFAULT_INVENTORY) -> dict[str, Any]:
    """Load an inventory JSON document.

    Args:
        path: Inventory file to read.

    Returns:
        Parsed inventory mapping.

    Raises:
        InventoryError: The file cannot be read as a JSON object.
    """
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError(f"Could not load inventory {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise InventoryError(f"Inventory {path} must contain a JSON object.")
    return cast(dict[str, Any], raw)


def _literal_list_assignment(path: Path, variable: str) -> list[str]:
    """Read a module-level literal string list without importing the module."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == variable for target in targets):
            continue
        value_node = node.value
        if value_node is None:
            continue
        value = ast.literal_eval(value_node)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return cast(list[str], value)
    raise InventoryError(f"Could not discover literal {variable} in {path.relative_to(ROOT)}.")


def _public_class_members(class_: type[Any]) -> tuple[str, ...]:
    """Return callable and property names exposed by a public class or protocol."""
    members: set[str] = set()
    for name, value in inspect.getmembers(class_):
        if name.startswith("_"):
            continue
        raw = inspect.getattr_static(class_, name)
        if callable(value) or isinstance(raw, property):
            members.add(name)
    return tuple(sorted(members))


def _dataclass_field_names(class_: type[Any]) -> tuple[str, ...]:
    """Return stable field names from a dataclass configuration model."""
    return tuple(sorted(field.name for field in fields(class_)))


def _cli_options(parser: argparse.ArgumentParser) -> tuple[str, ...]:
    """Return command-qualified CLI argument destinations.

    Help switches and argparse's dispatch-only fields are intentionally omitted;
    the remaining values are inputs whose behavior needs a catalog decision.
    """
    discovered: set[str] = set()

    def visit(current: argparse.ArgumentParser, command: str = "") -> None:
        for action in current._actions:  # argparse has no public action iterator
            choices = getattr(action, "choices", None)
            if isinstance(action, argparse._SubParsersAction):
                for name, child in choices.items():
                    visit(child, str(name))
                continue
            if action.dest in {"help", "command", "func"} or not command:
                continue
            discovered.add(f"{command}:{action.dest}")

    visit(parser)
    return tuple(sorted(discovered))


def discover_live_capabilities(root: Path = ROOT) -> dict[str, tuple[str, ...]]:
    """Return registry and API capabilities that must be bound to requirements.

    The imports intentionally use the same public registries as the application.
    This makes ``--check`` fail when an extension is registered without a matching
    inventory decision.

    Args:
        root: Repository root used for source-only discoveries.

    Returns:
        Mapping of discovery source to sorted stable capability values.
    """
    # [impl->req~ring5.trace.discovery-convergence~1]
    # [impl->req~ring5.trace.registry-drift~1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import ring5
    import ring5.shapers as public_shapers
    from ring5._parse import ParseJob
    from ring5._scan import ScanJob
    from ring5._session import Session
    from ring5.cli import build_parser
    from ring5.data import Table
    from ring5.decorations import FigureDecorations
    from ring5.figure_spec import FigureSpec, FigureSpecBuilder
    from src.core.application_api import ApplicationAPI
    from src.core.models.data_models import ParseVariableConfig
    from src.core.models.parsing_models import ScanResult, ScannedVariable, StatConfig
    from src.core.models.portfolio_models import RestoreReport
    from src.core.models.shaper_models import ShaperStepConfig
    from src.core.models.visualization.axis_config import AxesConfig, AxisConfig
    from src.core.models.visualization.data_label_config import DataLabelConfig
    from src.core.models.visualization.engine import VALID_ENGINES
    from src.core.models.visualization.figure_config import (
        DimensionConfig,
        FigureConfig,
        MarginsConfig,
    )
    from src.core.models.visualization.legend_config import (
        ColorbarConfig,
        LegendConfig,
        LegendSpacingConfig,
    )
    from src.core.models.visualization.series_style_config import SeriesStyleConfig
    from src.core.models.visualization.typography_config import TypographyConfig
    from src.core.services.data_services.data_services_api import DataServicesAPI
    from src.core.services.managers.managers_api import ManagersAPI
    from src.core.services.shapers.shapers_api import ShapersAPI
    from src.parsing.gem5.types import StatTypeRegistry
    from src.parsing.registry import SimulatorRegistry
    from src.web.pages.ui.plotting.settings_pills import SETTINGS_SECTIONS
    from src.web.rendering.figure_export import MatplotlibFormat, PlotlyFormat

    parser = build_parser()
    cli_commands: set[str] = set()
    for action in parser._actions:  # argparse exposes no public subparser iterator
        choices = getattr(action, "choices", None)
        if isinstance(choices, dict):
            cli_commands.update(str(choice) for choice in choices)

    simulators = SimulatorRegistry.available_simulator_info()
    strategies = {
        f"{simulator.name}:{strategy.name}"
        for simulator in simulators
        for strategy in simulator.parsing_strategies
    }
    variable_types = {
        f"{simulator.name}:{variable_type}"
        for simulator in simulators
        for variable_type in simulator.variable_types
    }
    variable_type_params = {
        f"{type_name}:{parameter}"
        for type_name, stat_class in StatTypeRegistry._types.items()
        for parameter in stat_class.required_params
    }
    shaper_config_fields = {
        f"{config_class.__name__}:{','.join(sorted(config_class.__annotations__))}"
        for config_class in get_args(ShaperStepConfig)
    }
    session_methods = {
        name
        for name, value in inspect.getmembers(Session, predicate=inspect.isfunction)
        if not name.startswith("_")
    }

    return {
        "navigation_pages": tuple(
            sorted(_literal_list_assignment(root / "app.py", "_NAV_OPTIONS"))
        ),
        "plot_types": tuple(sorted(ring5.available_plot_types())),
        "shaper_types": tuple(sorted(ring5.available_shaper_types())),
        "simulators": tuple(sorted(simulator.name for simulator in simulators)),
        "parser_strategies": tuple(sorted(strategies)),
        "variable_types": tuple(sorted(variable_types)),
        "variable_type_params": tuple(sorted(variable_type_params)),
        "simulator_internal_stats": tuple(
            sorted(
                f"{simulator.name}:{stat}"
                for simulator in simulators
                for stat in simulator.internal_stats
            )
        ),
        "simulator_file_patterns": tuple(
            sorted(f"{simulator.name}:{simulator.file_pattern}" for simulator in simulators)
        ),
        "shaper_config_fields": tuple(sorted(shaper_config_fields)),
        "render_engines": tuple(sorted(VALID_ENGINES)),
        "plotly_formats": tuple(sorted(str(item) for item in get_args(PlotlyFormat))),
        "matplotlib_formats": tuple(sorted(str(item) for item in get_args(MatplotlibFormat))),
        "settings_sections": tuple(sorted(section.key for section in SETTINGS_SECTIONS)),
        "public_exports": tuple(sorted(ring5.__all__)),
        "session_methods": tuple(sorted(session_methods)),
        "cli_commands": tuple(sorted(cli_commands)),
        "cli_options": _cli_options(parser),
        "application_api_members": _public_class_members(ApplicationAPI),
        "managers_api_members": _public_class_members(ManagersAPI),
        "data_services_api_members": _public_class_members(DataServicesAPI),
        "shapers_api_members": _public_class_members(ShapersAPI),
        "table_members": _public_class_members(Table),
        "figure_builder_members": _public_class_members(FigureSpecBuilder),
        "figure_decoration_members": _public_class_members(FigureDecorations),
        "parse_job_members": _public_class_members(ParseJob),
        "scan_job_members": _public_class_members(ScanJob),
        "figure_spec_fields": _dataclass_field_names(FigureSpec),
        "parse_variable_fields": tuple(sorted(ParseVariableConfig.__annotations__)),
        "stat_config_fields": _dataclass_field_names(StatConfig),
        "scanned_variable_fields": _dataclass_field_names(ScannedVariable),
        "scan_result_fields": _dataclass_field_names(ScanResult),
        "restore_report_fields": _dataclass_field_names(RestoreReport),
        "figure_config_fields": _dataclass_field_names(FigureConfig),
        "dimension_config_fields": _dataclass_field_names(DimensionConfig),
        "margin_config_fields": _dataclass_field_names(MarginsConfig),
        "axis_config_fields": _dataclass_field_names(AxisConfig),
        "axes_config_fields": _dataclass_field_names(AxesConfig),
        "data_label_config_fields": _dataclass_field_names(DataLabelConfig),
        "legend_config_fields": _dataclass_field_names(LegendConfig),
        "legend_spacing_config_fields": _dataclass_field_names(LegendSpacingConfig),
        "colorbar_config_fields": _dataclass_field_names(ColorbarConfig),
        "series_style_config_fields": _dataclass_field_names(SeriesStyleConfig),
        "typography_config_fields": _dataclass_field_names(TypographyConfig),
        "public_shaper_exports": tuple(sorted(public_shapers.__all__)),
    }


def _list_of_strings(value: object, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        errors.append(f"{label} must be a list of strings")
        return []
    return cast(list[str], value)


def _evidence_path(reference: str) -> str:
    """Return the path portion of an evidence reference.

    ``::symbol`` and ``#heading`` suffixes are accepted for readable, precise
    evidence descriptions while path validation remains filesystem based.
    """
    return reference.split("::", 1)[0].split("#", 1)[0]


def _validate_evidence(
    references: Sequence[str], label: str, root: Path, errors: list[str]
) -> None:
    for reference in references:
        relative = Path(_evidence_path(reference))
        if relative.is_absolute() or ".." in relative.parts:
            errors.append(f"{label} contains unsafe path {reference!r}")
            continue
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{label} escapes the repository: {reference!r}")
            continue
        if not candidate.is_file():
            errors.append(f"{label} references missing file {reference!r}")


def _valid_branch_name(value: object) -> bool:
    """Return whether a stored implementation branch is safe and reviewable."""
    return (
        isinstance(value, str)
        and BRANCH_PATTERN.fullmatch(value) is not None
        and ".." not in value
        and "//" not in value
        and not value.endswith(("/", ".", ".lock"))
    )


def validate_ci_oft_artifact(root: Path = ROOT) -> list[str]:
    """Return errors when CI does not generate and publish the OFT HTML report."""
    # [impl->req~ring5.trace.ci-html-artifact~1]
    workflow_path = root / CI_WORKFLOW_PATH
    try:
        lines = workflow_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"could not read {CI_WORKFLOW_PATH.as_posix()}: {exc}"]

    header = "  oft:"
    try:
        start = lines.index(header) + 1
    except ValueError:
        return ["CI workflow is missing the dedicated 'oft' job"]

    end = len(lines)
    for index in range(start, len(lines)):
        line = lines[index]
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            end = index
            break
    job = "\n".join(lines[start:end])
    required_tokens = {
        "the human-readable job name": "name: OpenFastTrace HTML report",
        "Java setup": "uses: actions/setup-java@v5",
        "the pinned Java runtime": 'java-version: "17"',
        "application installation": "python_venv/bin/pip install -e .",
        "OFT report generation": "make oft-report",
        "artifact upload": "uses: actions/upload-artifact@v7",
        "the report artifact name": "name: ring5-openfasttrace-report",
        "the generated HTML path": "path: spec/oft/generated/report.html",
        "missing-artifact failure behavior": "if-no-files-found: error",
    }
    return [
        f"CI OFT job is missing {label} ({token!r})"
        for label, token in required_tokens.items()
        if token not in job
    ]


def _validate_requirement_history(
    feature: Mapping[str, Any], label: str, errors: list[str]
) -> None:
    """Validate complete semantic snapshots and evidence-only history records."""
    # [impl->req~ring5.trace.requirement-history~2]
    history = feature.get("history", [])
    if not isinstance(history, list):
        errors.append(f"{label}.history must be a list")
        return

    current_revision = feature.get("revision")
    valid_current_revision = (
        isinstance(current_revision, int)
        and not isinstance(current_revision, bool)
        and current_revision >= 1
    )
    semantic_revisions: list[int] = []
    previous_revision = 0
    for index, record in enumerate(history):
        record_label = f"{label}.history[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{record_label} must be an object")
            continue
        revision = record.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            errors.append(f"{record_label}.revision must be a positive integer")
            continue
        if revision < previous_revision:
            errors.append(f"{label}.history must be ordered by revision")
        previous_revision = revision
        if valid_current_revision and revision > current_revision:
            errors.append(f"{record_label}.revision exceeds the current revision")

        change_type = record.get("change_type")
        if change_type not in HISTORY_CHANGE_TYPES:
            errors.append(
                f"{record_label}.change_type must be one of {sorted(HISTORY_CHANGE_TYPES)}"
            )
            continue
        reason = record.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"{record_label}.reason must be a non-empty string")
        if change_type == "semantic":
            semantic_revisions.append(revision)
            for field in ("title", "description"):
                if not isinstance(record.get(field), str) or not record[field].strip():
                    errors.append(f"{record_label}.{field} must be a non-empty string")
        elif "title" in record or "description" in record:
            errors.append(f"{record_label} evidence changes cannot redefine requirement text")

    if valid_current_revision:
        expected = list(range(1, current_revision))
        if semantic_revisions != expected:
            errors.append(
                f"{label}.history semantic revisions must be exactly {expected}, "
                f"got {semantic_revisions}"
            )


def validate_inventory(
    inventory: Mapping[str, Any],
    *,
    root: Path = ROOT,
    live_capabilities: Mapping[str, Sequence[str]] | None = None,
) -> None:
    """Validate structure, evidence, IDs, and live discovery bindings.

    Args:
        inventory: Parsed inventory mapping.
        root: Repository root for evidence validation.
        live_capabilities: Optional precomputed discoveries. Live values are
            discovered when omitted.

    Raises:
        InventoryError: Any validation rule fails.
    """
    # [impl->req~ring5.trace.discovery-convergence~1]
    # [impl->req~ring5.trace.inventory-generator~1]
    # [impl->req~ring5.trace.registry-drift~1]
    # [impl->req~ring5.trace.branch-association~1]
    # [impl->req~ring5.trace.approval-gate~1]
    errors: list[str] = []
    schema_version = inventory.get("schema_version")
    if schema_version != 2:
        errors.append("schema_version must be 2")

    groups_raw = inventory.get("groups")
    features_raw = inventory.get("features")
    bindings_raw = inventory.get("discovery_bindings")
    if not isinstance(groups_raw, list):
        errors.append("groups must be a list")
        groups_raw = []
    if not isinstance(features_raw, list):
        errors.append("features must be a list")
        features_raw = []
    if not isinstance(bindings_raw, dict):
        errors.append("discovery_bindings must be an object")
        bindings_raw = {}

    group_ids: set[str] = set()
    for index, group_raw in enumerate(groups_raw):
        label = f"groups[{index}]"
        if not isinstance(group_raw, dict):
            errors.append(f"{label} must be an object")
            continue
        group_id = group_raw.get("id")
        if not isinstance(group_id, str) or not ID_PATTERN.fullmatch(group_id):
            errors.append(f"{label}.id is invalid: {group_id!r}")
            continue
        if group_id in group_ids:
            errors.append(f"duplicate group id {group_id!r}")
        group_ids.add(group_id)
        for field in ("title", "description"):
            if not isinstance(group_raw.get(field), str) or not group_raw[field].strip():
                errors.append(f"{label}.{field} must be a non-empty string")
        tags = _list_of_strings(group_raw.get("tags", []), f"{label}.tags", errors)
        if not tags:
            errors.append(f"{label}.tags must contain at least one tag")
        for tag in tags:
            if not TAG_PATTERN.fullmatch(tag):
                errors.append(f"{label}.tags contains invalid OFT tag {tag!r}")

    feature_ids: set[str] = set()
    covered_groups: set[str] = set()
    for index, feature_raw in enumerate(features_raw):
        label = f"features[{index}]"
        if not isinstance(feature_raw, dict):
            errors.append(f"{label} must be an object")
            continue
        feature_id = feature_raw.get("id")
        if not isinstance(feature_id, str) or not ID_PATTERN.fullmatch(feature_id):
            errors.append(f"{label}.id is invalid: {feature_id!r}")
            continue
        if feature_id in feature_ids:
            errors.append(f"duplicate feature id {feature_id!r}")
        feature_ids.add(feature_id)

        group_id = feature_raw.get("group")
        if group_id not in group_ids:
            errors.append(f"{label}.group references unknown group {group_id!r}")
        elif isinstance(group_id, str):
            covered_groups.add(group_id)

        revision = feature_raw.get("revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            errors.append(f"{label}.revision must be a positive integer")
        _validate_requirement_history(feature_raw, label, errors)
        status = feature_raw.get("status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{label}.status must be one of {sorted(ALLOWED_STATUSES)}")
        branch = feature_raw.get("implementation_branch")
        if status != "approved" and branch is None:
            errors.append(f"{label}.implementation_branch is required for future requirements")
        elif branch is not None and not _valid_branch_name(branch):
            errors.append(f"{label}.implementation_branch is invalid: {branch!r}")
        for field in ("title", "description"):
            if not isinstance(feature_raw.get(field), str) or not feature_raw[field].strip():
                errors.append(f"{label}.{field} must be a non-empty string")

        tags = _list_of_strings(feature_raw.get("tags", []), f"{label}.tags", errors)
        if not tags:
            errors.append(f"{label}.tags must contain at least one tag")
        for tag in tags:
            if not TAG_PATTERN.fullmatch(tag):
                errors.append(f"{label}.tags contains invalid OFT tag {tag!r}")

        evidence = feature_raw.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{label}.evidence must be an object")
            evidence = {}
        for kind in ("implementation", "tests", "documentation"):
            references = _list_of_strings(
                evidence.get(kind, []), f"{label}.evidence.{kind}", errors
            )
            if status == "approved" and not references:
                errors.append(f"approved {feature_id!r} needs {kind} evidence")
            _validate_evidence(references, f"{label}.evidence.{kind}", root, errors)

    for group_id in sorted(group_ids - covered_groups):
        errors.append(f"group {group_id!r} has no requirements")

    discovered = (
        discover_live_capabilities(root) if live_capabilities is None else live_capabilities
    )
    unknown_sources = set(bindings_raw) - set(discovered)
    missing_sources = set(discovered) - set(bindings_raw)
    for source in sorted(unknown_sources):
        errors.append(f"discovery_bindings contains unknown source {source!r}")
    for source in sorted(missing_sources):
        errors.append(f"discovery_bindings is missing source {source!r}")

    for source, live_values in discovered.items():
        binding = bindings_raw.get(source, {})
        if not isinstance(binding, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in binding.items()
        ):
            errors.append(f"discovery_bindings.{source} must map strings to requirement IDs")
            continue
        binding_map = cast(dict[str, str], binding)
        live_set = set(live_values)
        bound_set = set(binding_map)
        for value in sorted(live_set - bound_set):
            errors.append(f"untracked {source} capability {value!r}")
        for value in sorted(bound_set - live_set):
            errors.append(f"stale {source} capability binding {value!r}")
        for value, feature_id in sorted(binding_map.items()):
            if feature_id not in feature_ids:
                errors.append(
                    f"discovery_bindings.{source}[{value!r}] references unknown "
                    f"requirement {feature_id!r}"
                )

    errors.extend(validate_ci_oft_artifact(root))
    if not errors:
        errors.extend(validate_source_evidence(cast(dict[str, Any], inventory), root))

    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise InventoryError(f"Feature inventory validation failed:\n{details}")


def validate_approved_native_coverage(
    inventory: Mapping[str, Any], native_coverage: Mapping[str, bool]
) -> None:
    """Reject approved requirements that native OpenFastTrace does not cover.

    Future requirements may remain red while they are being specified or
    implemented. Approval is the boundary that requires a present, green OFT
    result in addition to the exact evidence checks in :func:`validate_inventory`.

    Args:
        inventory: Validated inventory mapping.
        native_coverage: Requirement IDs mapped to native OFT green/red results.

    Raises:
        InventoryError: An approved requirement is missing or uncovered.
    """
    # [impl->req~ring5.trace.approval-gate~1]
    features = cast(list[dict[str, Any]], inventory["features"])
    approved_ids = sorted(
        str(feature["id"]) for feature in features if feature["status"] == "approved"
    )
    missing = [
        requirement_id for requirement_id in approved_ids if requirement_id not in native_coverage
    ]
    uncovered = [
        requirement_id
        for requirement_id in approved_ids
        if requirement_id in native_coverage and not native_coverage[requirement_id]
    ]
    if not missing and not uncovered:
        return

    failures = [
        *(f"missing native OFT result: {requirement_id}" for requirement_id in missing),
        *(f"native OFT reports uncovered: {requirement_id}" for requirement_id in uncovered),
    ]
    raise InventoryError(
        "Approved requirements must be covered by native OpenFastTrace:\n"
        + "\n".join(f"- {failure}" for failure in failures)
    )


def _generated_header(title: str) -> list[str]:
    return [
        f"# {title}",
        "",
        "<!-- Generated by scripts/generate_oft_inventory.py. Do not edit directly. -->",
        "",
    ]


def _tags(tags: Iterable[str]) -> str:
    return ", ".join(sorted(set(tags)))


def _feature_id(group_id: str) -> str:
    return f"feat~ring5.{group_id}~1"


def _requirement_id(feature: Mapping[str, Any]) -> str:
    return f"req~ring5.{feature['id']}~{feature['revision']}"


def _group_status(features: Sequence[Mapping[str, Any]]) -> str:
    """Derive the maturity of a feature group from its requirements."""
    statuses = {feature["status"] for feature in features}
    return next(view.key for view in requirement_status_views() if view.key in statuses)


def render_inventory(inventory: Mapping[str, Any]) -> dict[str, str]:
    """Render deterministic OpenFastTrace Markdown files.

    Args:
        inventory: Validated inventory mapping.

    Returns:
        Filename-to-content mapping.
    """
    # [impl->req~ring5.trace.inventory-generator~1]
    # [impl->req~ring5.trace.future-status-reporting~1]
    # [impl->req~ring5.trace.branch-association~1]
    # [impl->req~ring5.trace.requirement-history~2]
    groups = cast(list[dict[str, Any]], inventory["groups"])
    features = cast(list[dict[str, Any]], inventory["features"])
    by_group: dict[str, list[dict[str, Any]]] = {group["id"]: [] for group in groups}
    for feature in features:
        by_group[feature["group"]].append(feature)

    feature_lines = _generated_header("RING-5 Feature Groups")
    feature_lines.extend(
        [
            "These high-level capabilities organize the detailed requirements in the inventory.",
            "",
        ]
    )
    for group in groups:
        status = _group_status(by_group[group["id"]])
        group_tags = _tags([*group.get("tags", [group["id"]]), requirement_status_tag(status)])
        feature_lines.extend(
            [
                f"## {group['title']}",
                "",
                f"`{_feature_id(group['id'])}`",
                f"Status: {status}",
                "",
                group["description"],
                "",
                "Needs: req",
                "",
                f"Tags: {group_tags}",
                "",
            ]
        )

    requirement_lines = _generated_header("RING-5 Detailed Feature Requirements")
    requirement_lines.extend(
        [
            "Approved items describe current behavior. Proposed, draft, in-development, and",
            "blocked items describe future behavior and remain visibly uncovered until",
            "implementation, tests, and documentation are supplied.",
            "",
        ]
    )
    for group in groups:
        requirement_lines.extend([f"## {group['title']}", ""])
        for feature in by_group[group["id"]]:
            branch = feature.get("implementation_branch")
            history = cast(list[dict[str, Any]], feature.get("history", []))
            requirement_lines.extend(
                [
                    f"### {feature['title']}",
                    "",
                    f"`{_requirement_id(feature)}`",
                    f"Status: {feature['status']}",
                    "",
                    feature["description"],
                    "",
                    *([f"Implementation branch: {branch}", ""] if branch else []),
                    *([f"History records: {len(history)}", ""] if history else []),
                    "Covers:",
                    f"- {_feature_id(group['id'])}",
                    "",
                    "Needs: impl, test, uman",
                    "",
                    "Tags: " + _tags([*feature["tags"], requirement_status_tag(feature["status"])]),
                    "",
                ]
            )

    status_views = requirement_status_views()
    status_counts = {
        view.key: sum(feature["status"] == view.key for feature in features)
        for view in status_views
    }
    bindings = cast(dict[str, dict[str, str]], inventory["discovery_bindings"])
    summary_lines = _generated_header("RING-5 Feature Inventory Summary")
    summary_lines.extend(
        [
            "<!-- oft:off -->",
            "This file is informative; normative items are in the other generated files.",
            "",
            f"- Feature groups: {len(groups)}",
            f"- Detailed requirements: {len(features)}",
            *[
                f"- {view.label} {view.scope} requirements: {status_counts[view.key]}"
                for view in status_views
            ],
            f"- Generated specification items: {len(groups) + len(features)}",
            f"- Live capability bindings: {sum(len(values) for values in bindings.values())}",
            "",
            "## Requirements by feature group",
            "",
            "| Feature group | Approved | Proposed | Draft | In development | Blocked | Total |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            *[
                "| {title} | {approved} | {proposed} | {draft} | {in_development} | "
                "{blocked} | {total} |".format(
                    title=group["title"],
                    approved=sum(
                        feature["status"] == "approved" for feature in by_group[group["id"]]
                    ),
                    proposed=sum(
                        feature["status"] == "proposed" for feature in by_group[group["id"]]
                    ),
                    draft=sum(feature["status"] == "draft" for feature in by_group[group["id"]]),
                    in_development=sum(
                        feature["status"] == "in-development" for feature in by_group[group["id"]]
                    ),
                    blocked=sum(
                        feature["status"] == "blocked" for feature in by_group[group["id"]]
                    ),
                    total=len(by_group[group["id"]]),
                )
                for group in groups
            ],
            "",
            "## Drift-checked capability sources",
            "",
            *[f"- `{source}`: {len(values)}" for source, values in sorted(bindings.items())],
            "",
            "## Future requirements by implementation branch",
            "",
            "| Requirement | Status | Implementation branch |",
            "| --- | --- | --- |",
            *[
                f"| `{feature['id']}` | {feature['status']} | "
                f"`{feature['implementation_branch']}` |"
                for feature in features
                if feature["status"] != "approved"
            ],
            "",
            "## Requirement history",
            "",
            "| Requirement | Revision | Change | Reason |",
            "| --- | ---: | --- | --- |",
            *[
                f"| `{feature['id']}` | {record['revision']} | "
                f"{('Evidence only' if record['change_type'] == 'evidence' else 'Semantic')} | "
                f"{record['reason']} |"
                for feature in features
                for record in feature.get("history", [])
            ],
            "",
            "<!-- oft:on -->",
        ]
    )

    return {
        "features.md": "\n".join(feature_lines).rstrip() + "\n",
        "requirements.md": "\n".join(requirement_lines).rstrip() + "\n",
        "summary.md": "\n".join(summary_lines).rstrip() + "\n",
    }


def write_or_check(rendered: Mapping[str, str], output_dir: Path, *, check: bool) -> None:
    """Write rendered files or verify that existing files match exactly."""
    if check:
        failures: list[str] = []
        for filename in GENERATED_FILENAMES:
            path = output_dir / filename
            expected = rendered[filename]
            try:
                actual = path.read_text(encoding="utf-8")
            except OSError:
                failures.append(f"missing generated file {_display_path(path)}")
                continue
            if actual != expected:
                failures.append(
                    f"stale generated file {_display_path(path)}; run `make oft-generate`"
                )
        if failures:
            raise InventoryError("Generated OFT artifacts are stale:\n" + "\n".join(failures))
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in GENERATED_FILENAMES:
        (output_dir / filename).write_text(rendered[filename], encoding="utf-8")


def check_html_report(inventory: Mapping[str, Any], output_dir: Path) -> None:
    """Verify that the committed OFT-derived HTML matches the inventory.

    The report itself can only be rebuilt by native OpenFastTrace, but its
    embedded fingerprints and native coverage can be checked without Java or
    network access as part of the normal quality gate.
    """
    # [impl->req~ring5.trace.approval-gate~1]
    path = output_dir / HTML_REPORT_FILENAME
    try:
        report = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InventoryError(
            f"Missing OFT HTML report {_display_path(path)}; run `make oft-report`."
        ) from exc
    expected = (
        '<meta name="ring5-inventory-sha256" ' f'content="{inventory_fingerprint(inventory)}">'
    )
    if expected not in report:
        raise InventoryError(
            f"OFT HTML report {_display_path(path)} is stale; run `make oft-report`."
        )
    source_expected = (
        '<meta name="ring5-evidence-sha256" '
        f'content="{evidence_fingerprint(collect_evidence_markers(ROOT))}">'
    )
    if source_expected not in report:
        raise InventoryError(
            f"OFT HTML report {_display_path(path)} has stale source origins; "
            "run `make oft-report`."
        )
    if '<main id="oft-native-report">' not in report:
        raise InventoryError(f"OFT HTML report {_display_path(path)} lacks the native OFT trace.")
    try:
        native_coverage = extract_oft_coverage(report, inventory)
    except OftHtmlReportError as exc:
        raise InventoryError(f"OFT HTML report {_display_path(path)} is invalid: {exc}") from exc
    validate_approved_native_coverage(inventory, native_coverage)


def _display_path(path: Path) -> Path:
    """Return a concise repository-relative path where possible."""
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def build_parser() -> argparse.ArgumentParser:
    """Build the inventory generator command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate discoveries and fail if generated files are stale",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the generator and return a process-style status code."""
    args = build_parser().parse_args(argv)
    try:
        inventory = load_inventory(args.inventory)
        validate_inventory(inventory)
        rendered = render_inventory(inventory)
        write_or_check(rendered, args.output_dir, check=args.check)
        if args.check:
            check_html_report(inventory, args.output_dir)
    except InventoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    action = "verified" if args.check else "generated"
    print(
        f"{action} {len(inventory['features'])} requirements across "
        f"{len(inventory['groups'])} feature groups"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
