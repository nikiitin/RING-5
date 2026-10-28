"""Contracts for the trusted dependency automation workflow and checked-in policy."""

from __future__ import annotations

import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


class WorkflowLoader(yaml.SafeLoader):
    """Keep YAML's ``on`` event key while resolving explicit booleans normally."""


WorkflowLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in values if tag != "tag:yaml.org,2002:bool"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE), list("tTfF")
)


def workflow(name: str) -> dict[str, Any]:
    """Read workflow data without PyYAML's legacy ``on``-as-boolean conversion."""
    result = yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=WorkflowLoader)
    assert isinstance(result, dict)
    return cast(dict[str, Any], result)


def configured_job_names(document: dict[str, Any]) -> set[str]:
    """Expand the checked-in ordinary and include-only job matrices."""
    names = []
    for identifier, job in document["jobs"].items():
        assert "if" not in job, f"Required PR job {identifier} must not be conditional"
        matrix = job.get("strategy", {}).get("matrix", {})
        if "include" in matrix:
            assert set(matrix) == {"include"}, "Review changed matrix semantics explicitly"
            combinations = matrix["include"]
        elif matrix:
            assert "exclude" not in matrix, "Review changed matrix semantics explicitly"
            combinations = [
                dict(zip(matrix, values)) for values in itertools.product(*matrix.values())
            ]
        else:
            combinations = [{}]
        for combination in combinations:
            name = re.sub(
                r"\$\{\{\s*matrix\.([\w-]+)\s*\}\}",
                lambda match: str(combination[match.group(1)]),
                job.get("name", identifier),
            )
            assert "${{" not in name, "Review dynamic job-name changes explicitly"
            names.append(name)
    assert len(names) == len(set(names)), "Required job names must be unambiguous"
    return set(names)


def test_required_workflow_contract_matches_every_pr_matrix_job() -> None:
    """An omitted wheel/Python/export job cannot silently weaken merge requirements."""
    config = json.loads((ROOT / ".github/dependency-automation.json").read_text())
    assert config["base_branch"] == "main"
    assert config["allow_major"] is False
    assert config["default_reviewer"] == "nikiitin"
    assert config["max_open_prs"] == 100
    expected = {"CI": ("ci.yml", 14), "CodeQL": ("codeql.yml", 1)}
    assert set(config["required_workflows"]) == set(expected)
    for display_name, (filename, count) in expected.items():
        definition = config["required_workflows"][display_name]
        source = workflow(filename)
        assert source["name"] == display_name
        assert "pull_request" in source["on"]
        assert definition["path"] == f".github/workflows/{filename}"
        assert len(definition["jobs"]) == len(set(definition["jobs"])) == count
        assert set(definition["jobs"]) == configured_job_names(source)
    assert config["dispatch_after_merge"] == ["ci.yml", "codeql.yml", "pages.yml"]
    for filename in config["dispatch_after_merge"]:
        assert "workflow_dispatch" in workflow(filename)["on"]


def test_privileged_workflow_runs_only_trusted_controller_code() -> None:
    """A privileged trigger cannot check out a PR or install/execute its payload."""
    document = workflow("dependency-automation.yml")
    events = document["on"]
    assert set(events) == {"pull_request_target", "workflow_run", "schedule", "workflow_dispatch"}
    assert events["pull_request_target"]["types"] == [
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
        "edited",
    ]
    assert events["workflow_run"] == {"workflows": ["CI", "CodeQL"], "types": ["completed"]}
    assert events["schedule"] == [{"cron": "17 * * * *"}]
    assert events["workflow_dispatch"]["inputs"]["dry_run"]["default"] is True
    assert document["permissions"] == {
        "actions": "write",
        "contents": "write",
        "issues": "write",
        "pull-requests": "write",
    }
    assert document["concurrency"] == {
        "group": "dependency-automation",
        "cancel-in-progress": False,
    }
    assert set(document["jobs"]) == {"review-and-merge"}
    job = document["jobs"]["review-and-merge"]
    assert job["if"] == "vars.DEPENDENCY_AUTOMATION_ENABLED == 'true'"
    steps = job["steps"]
    assert len(steps) == 3
    assert steps[0]["uses"] == workflow("ci.yml")["jobs"]["quality"]["steps"][0]["uses"]
    assert steps[0]["with"] == {
        "ref": "${{ github.event.repository.default_branch }}",
        "persist-credentials": False,
    }
    assert steps[1]["uses"].startswith("actions/setup-python@")
    assert re.fullmatch(r"actions/setup-python@[0-9a-f]{40}", steps[1]["uses"])
    assert steps[1]["with"]["python-version"] == "3.12"
    assert steps[2]["shell"] == "bash"
    assert steps[2]["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "DEPENDENCY_AUTOMATION_REVIEWER": "${{ vars.DEPENDENCY_AUTOMATION_REVIEWER }}",
        "PR_NUMBER": "${{ inputs.pr_number }}",
        "DRY_RUN": "${{ inputs.dry_run }}",
    }
    assert "${{" not in steps[2]["run"], "Put untrusted inputs in quoted environment arguments"
    assert 'python -m scripts.dependency_automation "${args[@]}"' in steps[2]["run"]


@pytest.mark.parametrize(
    ("event", "dry_run", "number", "apply"),
    [
        ("pull_request_target", "", "", True),
        ("workflow_run", "", "", True),
        ("schedule", "", "", True),
        ("workflow_dispatch", "true", "42", False),
        ("workflow_dispatch", "false", "42", True),
        ("workflow_dispatch", "", "42", False),
        ("workflow_dispatch", "true", "42; touch unexpected-command", False),
    ],
)
def test_controller_invocation_preserves_dry_run_and_literal_inputs(
    tmp_path: Path, event: str, dry_run: str, number: str, apply: bool
) -> None:
    """The real shell keeps manual dry runs inert and PR input as one argument."""
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is required to execute the hosted workflow shell contract")
    command_log = tmp_path / "arguments.json"
    python = tmp_path / "python"
    python.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['COMMAND_LOG']).write_text(json.dumps(sys.argv[1:]))\n"
    )
    python.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(tmp_path) + os.pathsep + os.environ.get("PATH", ""),
        "COMMAND_LOG": str(command_log),
        "GITHUB_EVENT_NAME": event,
        "PR_NUMBER": number,
        "DRY_RUN": dry_run,
    }
    script = workflow("dependency-automation.yml")["jobs"]["review-and-merge"]["steps"][2]["run"]
    result = subprocess.run(
        [bash, "-euo", "pipefail", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    expected = [
        "-m",
        "scripts.dependency_automation",
        "--config",
        ".github/dependency-automation.json",
    ]
    if number:
        expected += ["--pr", number]
    if apply:
        expected += ["--apply"]
    assert json.loads(command_log.read_text()) == expected
    assert not (tmp_path / "unexpected-command").exists()


def test_dependabot_does_not_request_a_human_on_every_update() -> None:
    """Human escalation belongs to the controller's substantive blocked result."""
    document = yaml.load((ROOT / ".github/dependabot.yml").read_text(), Loader=WorkflowLoader)
    assert all("reviewers" not in update for update in document["updates"])
    python = next(update for update in document["updates"] if update["package-ecosystem"] == "uv")
    assert all(group["update-types"] == ["minor", "patch"] for group in python["groups"].values())


def test_copilot_instructions_are_limited_to_dependency_review_surfaces() -> None:
    """Instructions cannot broaden approvals to executable automation or app code."""
    path = ROOT / ".github/instructions/dependency-review.instructions.md"
    frontmatter = path.read_text().split("---", 2)[1]
    patterns = yaml.safe_load(frontmatter)["applyTo"].split(",")
    assert patterns == [
        "pyproject.toml",
        "uv.lock",
        "Gemfile",
        "Gemfile.lock",
        ".github/workflows/*.yml",
    ]
