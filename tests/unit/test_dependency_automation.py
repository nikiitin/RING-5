"""Exercise the privileged controller without network access or real PR writes."""

from __future__ import annotations

import base64
import copy
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import dependency_automation as controller
from scripts.dependency_update_policy import PolicyDecision, VersionChange

HEAD = "a" * 40
BASE = "b" * 40
OTHER = "c" * 40
REPOSITORY = "owner/project"
ROOT = f"/repos/{REPOSITORY}"
NOW = datetime(2026, 10, 24, 12, tzinfo=UTC)


def reviewer_actor(login: str = "Copilot", **fields: Any) -> dict[str, Any]:
    """Represent the same immutable native bot under either API login spelling."""
    return {
        "login": login,
        "type": "Bot",
        "id": controller.COPILOT_USER_ID,
        "node_id": controller.COPILOT_NODE_ID,
        **fields,
    }


@pytest.fixture
def config() -> dict[str, Any]:
    return {
        "base_branch": "main",
        "allow_major": False,
        "default_reviewer": "",
        "max_open_prs": 100,
        "required_workflows": {
            "CI": {"path": ".github/workflows/ci.yml", "jobs": ["unit"]},
            "CodeQL": {"path": ".github/workflows/codeql.yml", "jobs": ["scan"]},
        },
        "dispatch_after_merge": ["ci.yml", "codeql.yml", "pages.yml"],
    }


class FakeClient(controller.GitHubClient):
    """Model API state and retain every attempted mutation."""

    def __init__(self) -> None:
        super().__init__("fake")
        self.identity_response = reviewer_actor()
        self.identity_reads = 0
        self.server_time = NOW
        self.receipt_error = False
        self.receipt_update_error = False
        self.native_response_error = False
        self.intent_response_error = False
        self.pr: dict[str, Any] = {
            "number": 1,
            "state": "open",
            "draft": False,
            "user": {"login": controller.DEPENDABOT, "type": "Bot"},
            "base": {"ref": "main", "sha": BASE, "repo": {"full_name": REPOSITORY}},
            "head": {
                "sha": HEAD,
                "ref": "dependabot/uv/example-1.2.3",
                "repo": {"full_name": REPOSITORY},
            },
            "changed_files": 1,
            "mergeable_state": "clean",
            "requested_reviewers": [],
        }
        self.commits: list[dict[str, Any]] = [
            {
                "author": {"login": controller.DEPENDABOT},
                "commit": {"verification": {"verified": True}},
            }
        ]
        self.files: list[dict[str, Any]] = [{"filename": "uv.lock", "status": "modified"}]
        self.reviews: list[dict[str, Any]] = [
            {
                "id": 1,
                "user": reviewer_actor(controller.COPILOT_REQUEST_LOGIN),
                "commit_id": HEAD,
                "state": "APPROVED",
            }
        ]
        self.rules: list[dict[str, Any]] = [
            {
                "type": "required_status_checks",
                "parameters": {
                    "strict_required_status_checks_policy": True,
                    "required_status_checks": [{"context": "unit"}, {"context": "scan"}],
                },
            },
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "dismiss_stale_reviews_on_push": True,
                },
            },
        ]
        self.runs: dict[str, list[dict[str, Any]]] = {
            name: [self.run(name, number)] for name, number in [("ci", 11), ("codeql", 12)]
        }
        self.jobs: dict[int, list[dict[str, Any]]] = {
            11: [{"name": "unit", "conclusion": "success"}],
            12: [{"name": "scan", "conclusion": "success"}],
        }
        self.threads: list[dict[str, Any]] = []
        self.review_decision = "APPROVED"
        self.graphql_errors = False
        self.behind = False
        self.comments: list[dict[str, Any]] = []
        self.writes: list[tuple[str, str, Any]] = []
        self.reads = 0
        self.branch_reads = 0
        self.new_head_on_final_read = False
        self.retarget_on_final_read = False
        self.new_base_on_final_read = False
        self.request_error = False
        self.maintainer_error_once = False
        self.dispatch_error = False
        self.merge_succeeds = True
        self.lost_merge_response = False
        self.closed_without_merge = False
        self.tag_type = "commit"
        self.tag_sha = OTHER

    @staticmethod
    def run(name: str, number: int) -> dict[str, Any]:
        return {
            "id": number,
            "run_attempt": 1,
            "head_sha": HEAD,
            "head_repository": {"full_name": REPOSITORY},
            "event": "pull_request",
            "path": f".github/workflows/{name}.yml",
            "pull_requests": [{"number": 1, "head": {"sha": HEAD}, "base": {"sha": BASE}}],
            "status": "completed",
            "conclusion": "success",
            "html_url": f"https://github.com/{REPOSITORY}/actions/runs/{number}",
        }

    def paginate(self, path: str, key: str | None = None) -> list[dict[str, Any]]:
        if path.endswith("/commits"):
            return copy.deepcopy(self.commits)
        if path.endswith("/files"):
            return copy.deepcopy(self.files)
        if path.endswith("/reviews"):
            return copy.deepcopy(self.reviews)
        if path.endswith("/comments"):
            return copy.deepcopy(self.comments)
        if "/workflows/" in path:
            name = path.split("/workflows/")[1].split(".")[0]
            return copy.deepcopy(self.runs[name])
        if "/jobs?" in path:
            return copy.deepcopy(self.jobs[int(path.split("/runs/")[1].split("/")[0])])
        raise AssertionError(path)

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if path == "/graphql":
            if self.graphql_errors:
                return {"errors": [{"message": "query denied"}]}
            return {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "headRefOid": self.pr["head"]["sha"],
                            "reviewDecision": self.review_decision,
                            "reviewThreads": {
                                "nodes": self.threads,
                                "pageInfo": {"hasNextPage": False, "endCursor": None},
                            },
                        }
                    }
                }
            }
        if method == "GET":
            if path.startswith("/users/"):
                self.identity_reads += 1
                return copy.deepcopy(self.identity_response)
            if path == ROOT + "/pulls/1":
                self.reads += 1
                result = copy.deepcopy(self.pr)
                if self.new_head_on_final_read and self.reads >= 2:
                    result["head"]["sha"] = OTHER
                if self.retarget_on_final_read and self.reads >= 2:
                    result["base"]["ref"] = "unprotected"
                return result
            if "/contents/" in path:
                return {
                    "type": "file",
                    "encoding": "base64",
                    "size": 5,
                    "content": base64.b64encode(b"data\n").decode(),
                }
            if path.endswith("/rules/branches/main"):
                return self.rules
            if path.endswith("/branches/main"):
                self.branch_reads += 1
                return {
                    "commit": {
                        "sha": (
                            OTHER
                            if self.new_base_on_final_read and self.branch_reads >= 2
                            else BASE
                        )
                    }
                }
            if "/compare/" in path:
                return {
                    "behind_by": int(self.behind),
                    "status": "diverged" if self.behind else "ahead",
                }
            if "/git/ref/tags/" in path:
                return {"object": {"type": self.tag_type, "sha": self.tag_sha}}
            if "/git/tags/" in path:
                return {"object": {"type": "commit", "sha": OTHER}}
            raise AssertionError(path)
        assert payload is not None
        self.writes.append((method, path, payload))
        if path.endswith("/requested_reviewers"):
            if self.request_error and controller.COPILOT_REQUEST_LOGIN in payload["reviewers"]:
                raise controller.ApiError("GitHub request failed with HTTP 403")
            if self.maintainer_error_once and payload["reviewers"] == ["owner"]:
                self.maintainer_error_once = False
                raise controller.ApiError("Temporary review-request failure")
            self.pr["requested_reviewers"] += [
                (
                    reviewer_actor(name)
                    if name == controller.COPILOT_REQUEST_LOGIN
                    else {"login": name}
                )
                for name in payload["reviewers"]
            ]
            if (
                self.native_response_error
                and controller.COPILOT_REQUEST_LOGIN in payload["reviewers"]
            ):
                raise controller.ApiError("Native request response lost")
        if method == "PATCH" and "/issues/comments/" in path:
            if self.receipt_update_error and "ring5-native-review-request:" in payload["body"]:
                raise controller.ApiError("Receipt update failed")
            comment = next(
                item for item in self.comments if item["id"] == int(path.rsplit("/", 1)[1])
            )
            comment["body"] = payload["body"]
            return copy.deepcopy(comment)
        if path.endswith("/comments"):
            if self.receipt_error and "ring5-native-review-request:" in payload["body"]:
                raise controller.ApiError("Receipt persistence failed")
            self.comments.append(
                {
                    "id": len(self.comments) + 1,
                    "user": {"login": "github-actions[bot]", "type": "Bot"},
                    "body": payload["body"],
                    "created_at": self.server_time.isoformat(),
                }
            )
            if self.intent_response_error and "State: intent" in payload["body"]:
                raise controller.ApiError("Intent response lost")
            return copy.deepcopy(self.comments[-1])
        if path.endswith("/merge"):
            if self.lost_merge_response:
                self.pr["state"] = "closed"
                self.pr["merged"] = not self.closed_without_merge
                raise controller.ApiError("Merge response connection lost")
            return {"merged": self.merge_succeeds}
        if path.endswith("/dispatches") and self.dispatch_error:
            raise controller.ApiError("Dispatch failed")
        return None


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    monkeypatch.setattr(
        controller, "assess_changes", lambda changes, **kwargs: PolicyDecision(True, (), ())
    )
    return FakeClient()


def assess(
    client: FakeClient, config: dict[str, Any], *, apply: bool = False, now: datetime = NOW
) -> controller.Outcome:
    return controller.evaluate_pr(client, REPOSITORY, 1, config, apply=apply, now=now)


def test_dry_run_never_mutates_even_when_ready(client: FakeClient, config: dict[str, Any]) -> None:
    assert assess(client, config).state == "ready"
    assert client.writes == []


def test_ref_qualified_workflow_path_is_supported(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.runs["ci"][0]["path"] += "@refs/pull/1/merge"
    assert assess(client, config).state == "ready"
    client.runs["ci"][0]["path"] = ".github/workflows/different.yml@refs/pull/1/merge"
    assert assess(client, config).state == "waiting_checks"


def test_merge_is_bound_to_reviewed_sha_and_dispatches_main(
    client: FakeClient, config: dict[str, Any]
) -> None:
    assert assess(client, config, apply=True).state == "merged"
    assert client.writes[0] == (
        "PUT",
        ROOT + "/pulls/1/merge",
        {"sha": HEAD, "merge_method": "squash"},
    )
    assert [entry[1].split("/")[-2] for entry in client.writes[1:]] == [
        "ci.yml",
        "codeql.yml",
        "pages.yml",
    ]
    assert all(entry[2] == {"ref": "main"} for entry in client.writes[1:])


@pytest.mark.parametrize("change", ["author", "fork", "base", "draft", "closed", "branch"])
def test_non_dependabot_scope_is_ignored(
    client: FakeClient, config: dict[str, Any], change: str
) -> None:
    if change == "author":
        client.pr["user"]["login"] = "human"
    if change == "fork":
        client.pr["head"]["repo"]["full_name"] = "attacker/project"
    if change == "base":
        client.pr["base"]["ref"] = "develop"
    if change == "draft":
        client.pr["draft"] = True
    if change == "closed":
        client.pr["state"] = "closed"
    if change == "branch":
        client.pr["head"]["ref"] = "feature"
    assert assess(client, config, apply=True).state == "ignored"
    assert client.writes == []


@pytest.mark.parametrize(
    "change", ["unsigned", "human_commit", "extra_file", "added", "renamed", "outside_scope"]
)
def test_provenance_and_diff_scope_cannot_authorize_merge(
    client: FakeClient, config: dict[str, Any], change: str
) -> None:
    if change == "unsigned":
        client.commits[0]["commit"]["verification"]["verified"] = False
    if change == "human_commit":
        client.commits[0]["author"]["login"] = "human"
    if change == "extra_file":
        client.pr["changed_files"] = 2
    if change == "added":
        client.files[0]["status"] = "added"
    if change == "renamed":
        client.files[0]["previous_filename"] = "elsewhere"
    if change == "outside_scope":
        client.files[0]["filename"] = ".github/instructions/dependency-review.instructions.md"
    assert assess(client, config, apply=True).state == "needs_review"
    assert not any(entry[1].endswith("/merge") for entry in client.writes)


@pytest.mark.parametrize("change", ["no_strict", "missing_context", "stale_reviews", "no_approval"])
def test_missing_native_protection_blocks(
    client: FakeClient, config: dict[str, Any], change: str
) -> None:
    if change == "no_strict":
        client.rules[0]["parameters"]["strict_required_status_checks_policy"] = False
    if change == "missing_context":
        client.rules[0]["parameters"]["required_status_checks"].pop()
    if change == "stale_reviews":
        client.rules[1]["parameters"]["dismiss_stale_reviews_on_push"] = False
    if change == "no_approval":
        client.rules[1]["parameters"]["required_approving_review_count"] = 0
    assert assess(client, config).state == "needs_review"


@pytest.mark.parametrize(
    "change", ["no_run", "wrong_head", "wrong_base", "wrong_repo", "wrong_event"]
)
def test_unrelated_or_stale_ci_cannot_satisfy_gate(
    client: FakeClient, config: dict[str, Any], change: str
) -> None:
    run = client.runs["ci"][0]
    if change == "no_run":
        client.runs["ci"] = []
    if change == "wrong_head":
        run["head_sha"] = OTHER
    if change == "wrong_base":
        run["pull_requests"][0]["base"]["sha"] = OTHER
    if change == "wrong_repo":
        run["head_repository"]["full_name"] = "fork/project"
    if change == "wrong_event":
        run["event"] = "workflow_dispatch"
    assert assess(client, config).state == "waiting_checks"


@pytest.mark.parametrize(
    "change", ["failed", "cancelled", "missing_job", "skipped_job", "newer_failed_attempt"]
)
def test_all_actual_jobs_and_latest_attempt_must_pass(
    client: FakeClient, config: dict[str, Any], change: str
) -> None:
    if change in {"failed", "cancelled"}:
        client.runs["ci"][0]["conclusion"] = change
    if change == "missing_job":
        client.jobs[11] = []
    if change == "skipped_job":
        client.jobs[11][0]["conclusion"] = "skipped"
    if change == "newer_failed_attempt":
        run = FakeClient.run("ci", 13)
        run["conclusion"] = "failure"
        client.runs["ci"].append(run)
    assert assess(client, config).state == "needs_review"


def test_stale_copilot_approval_waits_for_new_review(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews[0]["commit_id"] = OTHER
    assert assess(client, config, apply=True).state == "waiting_copilot"
    assert client.writes[1:2] == [
        (
            "POST",
            ROOT + "/pulls/1/requested_reviewers",
            {"reviewers": [controller.COPILOT_REQUEST_LOGIN]},
        )
    ]
    assert len(client.comments) == 1
    assert "request accepted" in client.comments[0]["body"]


@pytest.mark.parametrize(
    "change", ["comment", "dismissed", "human_rejection", "thread", "not_counted"]
)
def test_comments_and_unresolved_findings_are_not_approval(
    client: FakeClient, config: dict[str, Any], change: str
) -> None:
    if change == "comment":
        client.reviews[0]["state"] = "COMMENTED"
    if change == "dismissed":
        client.reviews[0]["state"] = "DISMISSED"
    if change == "human_rejection":
        client.reviews.append(
            {"id": 2, "user": {"login": "human"}, "state": "CHANGES_REQUESTED", "commit_id": HEAD}
        )
    if change == "thread":
        client.threads = [{"isResolved": False}]
    if change == "not_counted":
        client.review_decision = "REVIEW_REQUIRED"
    assert assess(client, config).state == "needs_review"


def test_review_api_failure_never_merges(client: FakeClient, config: dict[str, Any]) -> None:
    client.graphql_errors = True
    with pytest.raises(controller.ApiError):
        assess(client, config, apply=True)
    assert not any(entry[1].endswith("/merge") for entry in client.writes)


@pytest.mark.parametrize("change", ["head", "main"])
def test_concurrent_push_forces_fresh_evaluation(
    client: FakeClient, config: dict[str, Any], change: str
) -> None:
    client.new_head_on_final_read = change == "head"
    client.new_base_on_final_read = change == "main"
    assert assess(client, config, apply=True).state == "waiting"
    assert client.writes == []


def test_retargeted_pr_is_not_merged(client: FakeClient, config: dict[str, Any]) -> None:
    client.retarget_on_final_read = True
    assert assess(client, config, apply=True).state == "waiting"
    assert client.writes == []


def test_outdated_branch_waits_without_pinging_maintainer(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.behind = True
    assert assess(client, config, apply=True).state == "waiting_update"
    assert client.writes == []


def test_escalation_is_once_per_head_and_survives_copilot_failure(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews[0]["state"] = "COMMENTED"
    client.request_error = True
    assert assess(client, config, apply=True).state == "needs_review"
    first = list(client.writes)
    assert any(entry[1].endswith("/comments") and "@owner" in entry[2]["body"] for entry in first)
    assert any(entry[2] == {"reviewers": ["owner"]} for entry in first)
    assert assess(client, config, apply=True).state == "needs_review"
    assert client.writes == first


def test_post_merge_failure_does_not_request_review_on_closed_pr(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.dispatch_error = True
    assert assess(client, config, apply=True).state == "merged_dispatch_failed"
    assert not any(entry[1].endswith("/requested_reviewers") for entry in client.writes)
    assert "merge succeeded" in client.comments[0]["body"]


def test_failed_maintainer_request_is_retried_without_duplicate_comment(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews[0]["state"] = "COMMENTED"
    client.maintainer_error_once = True
    assert assess(client, config, apply=True).state == "needs_review"
    assert len(client.comments) == 1
    assert assess(client, config, apply=True).state == "needs_review"
    assert len(client.comments) == 1
    assert len([entry for entry in client.writes if entry[2] == {"reviewers": ["owner"]}]) == 2


def test_configuration_inspection_cannot_apply(
    client: FakeClient,
    config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GH_TOKEN", "secret-not-printed")
    monkeypatch.setattr(controller, "GitHubClient", lambda token: client)
    monkeypatch.setattr(
        "sys.argv", ["controller", "--config", str(path), "--check-configuration", "--apply"]
    )
    assert controller.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mutations_performed"] is False
    assert client.writes == []
    client.rules[0]["parameters"]["strict_required_status_checks_policy"] = False
    assert controller.main() == 1
    assert client.writes == []


def test_unavailable_review_api_escalates_and_fails_cli(
    client: FakeClient,
    config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(config))
    client.graphql_errors = True
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GH_TOKEN", "not-printed")
    monkeypatch.setattr(controller, "GitHubClient", lambda token: client)
    monkeypatch.setattr("sys.argv", ["controller", "--config", str(path), "--pr", "1", "--apply"])
    assert controller.main() == 1
    assert len(client.comments) == 1
    assert "@owner" in client.comments[0]["body"]
    assert not any(entry[1].endswith("/merge") for entry in client.writes)


def test_credentials_cannot_follow_redirect_or_absolute_api_path() -> None:
    client = controller.GitHubClient("secret")
    with pytest.raises(controller.ApiError, match="path"):
        client.request("GET", "//attacker.example/collect")
    with pytest.raises(controller.ApiError, match="redirects"):
        controller._NoRedirect().redirect_request(
            controller.Request("https://api.github.com/test"),
            None,
            302,
            "redirect",
            {},
            "https://attacker.example/collect",
        )


@pytest.mark.parametrize("event_type", ["pull_request", "workflow_dispatch"])
def test_completed_workflow_only_evaluates_its_associated_pr(
    client: FakeClient,
    config: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    event_type: str,
) -> None:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(config))
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps({"workflow_run": {"event": event_type, "pull_requests": [{"number": 1}]}})
    )
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GH_TOKEN", "not-printed")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_run")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    monkeypatch.setattr(controller, "GitHubClient", lambda token: client)
    monkeypatch.setattr("sys.argv", ["controller", "--config", str(path)])
    assert controller.main() == 0
    results = json.loads(capsys.readouterr().out)["outcomes"]
    assert len(results) == (1 if event_type == "pull_request" else 0)
    assert client.writes == []


def test_server_merge_refusal_is_not_bypassed(client: FakeClient, config: dict[str, Any]) -> None:
    client.merge_succeeds = False
    assert assess(client, config, apply=True).state == "needs_review"
    attempts = [entry for entry in client.writes if entry[1].endswith("/merge")]
    assert len(attempts) == 1
    assert attempts[0][2] == {"sha": HEAD, "merge_method": "squash"}


def test_lost_success_response_still_dispatches_main_workflows(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.lost_merge_response = True
    assert assess(client, config, apply=True).state == "merged"
    assert len([entry for entry in client.writes if entry[1].endswith("/merge")]) == 1
    assert len([entry for entry in client.writes if entry[1].endswith("/dispatches")]) == 3


def test_closed_without_merge_does_not_dispatch_workflows(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.lost_merge_response = True
    client.closed_without_merge = True
    with pytest.raises(controller.ApiError, match="connection lost"):
        assess(client, config, apply=True)
    assert not any(entry[1].endswith("/dispatches") for entry in client.writes)


def test_truncated_collection_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = controller.GitHubClient("secret")
    monkeypatch.setattr(client, "request", lambda *args: [{} for _ in range(100)])
    with pytest.raises(controller.ApiError, match="pagination"):
        client.paginate("/repos/owner/project/pulls")


def test_action_release_tag_must_resolve_to_pin(client: FakeClient) -> None:
    update = VersionChange(
        "github-actions",
        "owner/action/init",
        "1.0.0",
        "1.1.0",
        "owner/action",
        HEAD,
        OTHER,
        "v1.0.0",
        "v1.1.0",
    )
    controller._action_provenance(client, [update])
    client.tag_type = "tag"
    controller._action_provenance(client, [update])
    client.tag_type = "commit"
    client.tag_sha = BASE
    with pytest.raises(controller.ApiError, match="does not match"):
        controller._action_provenance(client, [update])


@pytest.mark.parametrize("login", ["Copilot", controller.COPILOT_REQUEST_LOGIN])
def test_native_approval_matches_verified_identity_under_both_logins(
    client: FakeClient, config: dict[str, Any], login: str
) -> None:
    client.reviews[0]["user"] = reviewer_actor(login)
    assert assess(client, config).state == "ready"
    assert assess(client, config).state == "ready"
    assert client.identity_reads == 1
    assert client.writes == []


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "User"},
        {"id": controller.COPILOT_USER_ID + 1},
        {"node_id": "BOT_unrelated"},
        {"id": None},
        {"node_id": None},
    ],
)
@pytest.mark.parametrize("login", ["Copilot", controller.COPILOT_REQUEST_LOGIN])
def test_display_name_and_bot_alias_cannot_spoof_approval(
    client: FakeClient, config: dict[str, Any], fields: dict[str, Any], login: str
) -> None:
    client.reviews[0]["user"] = reviewer_actor(login, **fields)
    assert assess(client, config).state == "waiting_copilot"
    assert client.writes == []


@pytest.mark.parametrize("fields", [{"type": "User"}, {"id": 1}, {"node_id": "BOT_other"}])
def test_unverified_alias_resolution_cannot_authorize_requests_or_merges(
    client: FakeClient, config: dict[str, Any], fields: dict[str, Any]
) -> None:
    client.identity_response.update(fields)
    with pytest.raises(controller.ApiError, match="pinned bot"):
        assess(client, config, apply=True)
    assert client.writes == []


@pytest.mark.parametrize("latest_state", ["APPROVED", "COMMENTED", "DISMISSED"])
def test_latest_native_review_uses_identity_across_login_spellings(
    client: FakeClient, config: dict[str, Any], latest_state: str
) -> None:
    client.reviews[0]["state"] = "CHANGES_REQUESTED"
    client.reviews.append(
        {
            "id": 2,
            "user": reviewer_actor(),
            "commit_id": HEAD,
            "state": latest_state,
        }
    )
    expected = "ready" if latest_state == "APPROVED" else "needs_review"
    assert assess(client, config).state == expected
    assert client.writes == []


def test_completed_canonical_review_is_not_requested_again_during_escalation(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews[0]["user"] = reviewer_actor()
    client.reviews[0]["state"] = "COMMENTED"
    assert assess(client, config, apply=True).state == "needs_review"
    assert not any(
        payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
        for _, _, payload in client.writes
    )


def test_acceptance_receipt_suppresses_repeated_paid_requests_across_runs(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews = []
    assert assess(client, config, apply=True).state == "waiting_copilot"
    assert len(client.comments) == 1
    receipt = client.comments[0]
    assert "request accepted" in receipt["body"]
    assert "does not indicate" in receipt["body"]
    assert "@" not in receipt["body"]
    client.pr["requested_reviewers"] = []
    before = copy.deepcopy(client.writes)
    assert assess(client, config, apply=True).state == "waiting_copilot"
    client._copilot_receipts.clear()
    assert assess(client, config, apply=True).state == "waiting_copilot"
    assert client.writes == before
    assert client.identity_reads == 1


@pytest.mark.parametrize("login", ["Copilot", controller.COPILOT_REQUEST_LOGIN])
def test_existing_pending_actor_gets_observation_receipt_without_paid_request(
    client: FakeClient, config: dict[str, Any], login: str
) -> None:
    client.reviews = []
    client.pr["requested_reviewers"] = [reviewer_actor(login)]
    assert assess(client, config, apply=True).state == "waiting_copilot"
    assert len(client.comments) == 1
    assert "pending native review request was observed" in client.comments[0]["body"]
    assert not any(path.endswith("/requested_reviewers") for _, path, _ in client.writes)


@pytest.mark.parametrize("fields", [{"type": "User"}, {"id": 1}, {"node_id": "BOT_other"}])
def test_spoofed_pending_actor_cannot_suppress_the_verified_native_request(
    client: FakeClient, config: dict[str, Any], fields: dict[str, Any]
) -> None:
    client.reviews = []
    client.pr["requested_reviewers"] = [reviewer_actor(**fields)]
    assert assess(client, config, apply=True).state == "waiting_copilot"
    assert any(
        payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
        for _, _, payload in client.writes
    )
    assert "request accepted" in client.comments[0]["body"]


def test_receipt_timeout_escalates_once_without_another_native_request(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews = []
    assert assess(client, config, apply=True).state == "waiting_copilot"
    assert (
        assess(client, config, apply=True, now=NOW + timedelta(hours=24, seconds=-1)).state
        == "waiting_copilot"
    )
    result = assess(client, config, apply=True, now=NOW + timedelta(hours=24))
    assert result.state == "needs_review"
    assert "24 hours" in result.reasons[0]
    assert len(client.comments) == 2
    assert "@owner" in client.comments[1]["body"]
    before = copy.deepcopy(client.writes)
    assert assess(client, config, apply=True, now=NOW + timedelta(hours=25)).state == "needs_review"
    assert client.writes == before
    assert (
        sum(
            payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
            for _, _, payload in client.writes
        )
        == 1
    )


def test_late_current_head_approval_supersedes_the_receipt_timeout(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews = []
    assert assess(client, config, apply=True).state == "waiting_copilot"
    later = NOW + timedelta(hours=25)
    assert assess(client, config, apply=True, now=later).state == "needs_review"
    client.reviews = [{"id": 1, "user": reviewer_actor(), "commit_id": HEAD, "state": "APPROVED"}]
    client.writes.clear()
    assert assess(client, config, now=later).state == "ready"
    assert client.writes == []


def test_new_head_with_stale_pending_actor_and_old_approval_gets_its_own_deadline(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews = []
    assert assess(client, config, apply=True).state == "waiting_copilot"
    client.pr["head"]["sha"] = OTHER
    client.server_time = NOW + timedelta(hours=1)
    client.reviews = [{"id": 1, "user": reviewer_actor(), "commit_id": HEAD, "state": "APPROVED"}]
    for runs in client.runs.values():
        for run in runs:
            run["head_sha"] = OTHER
            run["pull_requests"][0]["head"]["sha"] = OTHER
    assert assess(client, config, apply=True, now=client.server_time).state == "waiting_copilot"
    assert len(client.comments) == 2
    assert controller._receipt_marker(OTHER) in client.comments[1]["body"]
    assert "observed" in client.comments[1]["body"]
    assert (
        assess(client, config, apply=True, now=NOW + timedelta(hours=24, minutes=30)).state
        == "waiting_copilot"
    )
    assert assess(client, config, apply=True, now=NOW + timedelta(hours=25)).state == "needs_review"
    assert not any(path.endswith("/merge") for _, path, _ in client.writes)


@pytest.mark.parametrize("pending", [False, True])
def test_dry_run_does_not_create_a_request_or_observation_receipt(
    client: FakeClient, config: dict[str, Any], pending: bool
) -> None:
    client.reviews = []
    client.pr["requested_reviewers"] = [reviewer_actor()] if pending else []
    assert assess(client, config).state == "waiting_copilot"
    assert client.writes == []


@pytest.mark.parametrize(
    ("author", "head"),
    [
        ({"login": "github-actions[bot]", "type": "User"}, HEAD),
        ({"login": "unrelated[bot]", "type": "Bot"}, HEAD),
        ({"login": "github-actions[bot]", "type": "Bot"}, OTHER),
    ],
)
def test_forged_or_stale_receipt_cannot_suppress_a_new_request(
    client: FakeClient, config: dict[str, Any], author: dict[str, str], head: str
) -> None:
    client.reviews = []
    client.comments = [
        {
            "id": 1,
            "user": author,
            "body": controller._receipt_marker(head) + "\nforged or stale",
            "created_at": (NOW - timedelta(days=7)).isoformat(),
        }
    ]
    assert assess(client, config, apply=True).state == "waiting_copilot"
    assert any(
        payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
        for _, _, payload in client.writes
    )
    assert len(client.comments) == 2


def test_intent_persistence_failure_cannot_make_a_paid_request(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews = []
    client.receipt_error = True
    result = assess(client, config, apply=True)
    assert result.state == "needs_review"
    assert "receipt could not be verified" in result.reasons[0]
    assert len(client.comments) == 1
    assert "@owner" in client.comments[0]["body"]
    client._copilot_receipts.clear()
    assert assess(client, config, apply=True).state == "needs_review"
    assert (
        sum(
            payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
            for _, _, payload in client.writes
        )
        == 0
    )
    assert not any(path.endswith("/merge") for _, path, _ in client.writes)


@pytest.mark.parametrize(
    ("failure", "paid_attempts"),
    [
        ("receipt_update_error", 1),
        ("native_response_error", 1),
        ("request_error", 1),
        ("intent_response_error", 0),
    ],
)
def test_unconfirmed_intent_never_retries_after_restart_and_missing_pending_actor(
    client: FakeClient, config: dict[str, Any], failure: str, paid_attempts: int
) -> None:
    client.reviews = []
    setattr(client, failure, True)
    assert assess(client, config, apply=True).state == "needs_review"
    assert "State: intent" in client.comments[0]["body"]
    restarted = FakeClient()
    restarted.pr = copy.deepcopy(client.pr)
    restarted.pr["requested_reviewers"] = [
        actor
        for actor in restarted.pr["requested_reviewers"]
        if actor["login"] != controller.COPILOT_REQUEST_LOGIN
    ]
    restarted.reviews = []
    restarted.comments = copy.deepcopy(client.comments)
    result = assess(restarted, config, apply=True)
    assert result.state == "needs_review"
    assert "unconfirmed completion" in result.reasons[0]
    assert len(restarted.comments) == 2
    assert not any(
        payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
        for _, _, payload in restarted.writes
    )
    assert (
        sum(
            payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
            for _, _, payload in client.writes
        )
        == paid_attempts
    )
    restarted.reviews = [
        {"id": 1, "user": reviewer_actor(), "commit_id": HEAD, "state": "APPROVED"}
    ]
    restarted.writes.clear()
    assert assess(restarted, config).state == "ready"
    assert restarted.writes == []


@pytest.mark.parametrize("timestamp", [None, "invalid", "2026-10-24T12:00:00"])
def test_unusable_trusted_receipt_timestamp_is_visible_and_cannot_trigger_another_request(
    client: FakeClient, config: dict[str, Any], timestamp: str | None
) -> None:
    client.reviews = []
    client.comments = [
        {
            "id": 1,
            "user": {"login": "github-actions[bot]", "type": "Bot"},
            "body": controller._receipt_marker(HEAD) + "\naccepted",
            "created_at": timestamp,
        }
    ]
    result = assess(client, config, apply=True)
    assert result.state == "needs_review"
    assert "receipt could not be verified" in result.reasons[0]
    assert len(client.comments) == 2
    assert "@owner" in client.comments[1]["body"]
    assert not any(
        payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
        for _, _, payload in client.writes
    )


def test_expired_receipt_dry_run_only_reports_needed_escalation(
    client: FakeClient, config: dict[str, Any]
) -> None:
    client.reviews = []
    assert assess(client, config, apply=True).state == "waiting_copilot"
    client.writes.clear()
    assert assess(client, config, now=NOW + timedelta(days=1)).state == "needs_review"
    assert client.writes == []


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        ("", "needs_review"),
        ("\n", "needs_review"),
        ("\r\nState: intent\r\nIntent recorded", "needs_review"),
        ("\r\nState: accepted\r\nRequest accepted", "waiting_copilot"),
        ("\nState: unknown\nUnrecognized state", "needs_review"),
    ],
)
def test_trusted_exact_head_receipt_header_is_never_ignored_to_make_a_paid_request(
    client: FakeClient, config: dict[str, Any], suffix: str, expected: str
) -> None:
    client.reviews = []
    client.comments = [
        {
            "id": 1,
            "user": {"login": "github-actions[bot]", "type": "Bot"},
            "body": controller._receipt_marker(HEAD) + suffix,
            "created_at": NOW.isoformat(),
        }
    ]
    assert assess(client, config, apply=True).state == expected
    assert not any(
        payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
        for _, _, payload in client.writes
    )


@pytest.mark.parametrize("padding", [False, True])
def test_lock_only_update_escalates_without_requesting_excluded_native_review(
    client: FakeClient, config: dict[str, Any], monkeypatch: pytest.MonkeyPatch, padding: bool
) -> None:
    from scripts.dependency_update_policy import assess_changes

    before = (Path(__file__).resolve().parents[2] / "uv.lock").read_text()
    after = before.replace('version = "1.17.0"', 'version = "1.17.1"').replace(
        "six-1.17.0", "six-1.17.1"
    )
    assert before != after
    monkeypatch.setattr(controller, "assess_changes", assess_changes)
    project = (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()
    if padding:
        client.files.append({"filename": "pyproject.toml", "status": "modified"})
        client.pr["changed_files"] = 2

    def content(_client: Any, _root: str, path: str, ref: str) -> str:
        if path == "uv.lock":
            return before if ref == BASE else after
        return project if ref == BASE else project + "\n# formatting only\n"

    monkeypatch.setattr(controller, "_content", content)
    result = assess(client, config, apply=True)
    assert result.state == "needs_review"
    assert any("Lock-only" in reason for reason in result.reasons)
    assert len(client.comments) == 1
    assert "@owner" in client.comments[0]["body"]
    assert not any(
        payload == {"reviewers": [controller.COPILOT_REQUEST_LOGIN]}
        for _, _, payload in client.writes
    )
    assert not any(path.endswith("/merge") for _, path, _ in client.writes)
