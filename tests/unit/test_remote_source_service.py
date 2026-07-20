"""Security and transport tests for remote source adapters."""

from __future__ import annotations

import datetime
import subprocess
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch
from urllib.error import URLError

import pytest

from src.core.models import HttpSource, RemoteSourcePolicy, S3Source, SshSource
from src.core.services.remote_source_service import (
    HttpRemoteSourceAdapter,
    S3RemoteSourceAdapter,
    SshRemoteSourceAdapter,
)


class _Response:
    def __init__(self, content: bytes, url: str, content_type: str = "text/csv") -> None:
        self._content = content
        self._url = url
        self.headers = {
            "Content-Length": str(len(content)),
            "Content-Type": content_type,
        }

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, limit: int) -> bytes:
        return self._content[:limit]

    def geturl(self) -> str:
        return self._url


class _Opener:
    def __init__(self, content: bytes, url: str, content_type: str = "text/csv") -> None:
        self.response = _Response(content, url, content_type)
        self.request: Any = None
        self.timeout: float | None = None

    def open(self, request: Any, timeout: float) -> _Response:
        self.request = request
        self.timeout = timeout
        return self.response


class _FailingOpener:
    def open(self, request: Any, timeout: float) -> _Response:
        raise URLError(request.full_url)


def _public_dns(*_args: object, **_kwargs: object) -> list[tuple[Any, ...]]:
    return [(2, 1, 6, "", ("93.184.216.34", 443))]


def test_http_ssh_and_s3_adapters_fetch_bounded_credential_safe_sources(
    tmp_path: Path,
) -> None:
    # [test->req~ring5.ingestion.remote-sources~1]
    policy = RemoteSourcePolicy(("data.example", "ssh.example", "objects.example"))
    content = b"benchmark,ipc\nalpha,1.25\n"

    http_opener = _Opener(content, "https://data.example/results.csv?download=1")
    http_source = HttpSource(
        "https://data.example/results.csv?token=url-secret",
        bearer_token="bearer-secret",
    )
    with patch("socket.getaddrinfo", side_effect=_public_dns):
        http = HttpRemoteSourceAdapter(cast(Any, http_opener)).fetch(http_source, policy)
    assert http.content == content
    assert http.display_uri == "https://data.example/results.csv"
    assert http_opener.request.get_header("Authorization") == "Bearer bearer-secret"
    assert "bearer-secret" not in repr(http_source)
    assert "url-secret" not in repr(http_source)
    assert "url-secret" not in repr(http)

    completed = subprocess.CompletedProcess([], 0, stdout=content, stderr=b"")
    ssh_source = SshSource("ssh.example", "/exports/results.csv", username="analyst")
    with (
        patch("socket.getaddrinfo", side_effect=_public_dns),
        patch("subprocess.run", return_value=completed) as run,
    ):
        ssh = SshRemoteSourceAdapter().fetch(ssh_source, policy)
    command = run.call_args.args[0]
    assert "BatchMode=yes" in command
    assert "StrictHostKeyChecking=yes" in command
    assert command[-1].startswith("head -c ")
    assert ssh.content == content
    assert ssh.display_uri == "ssh://ssh.example:22/exports/results.csv"

    s3_opener = _Opener(
        content,
        "https://objects.example/research/results.csv",
        "application/octet-stream",
    )
    s3_source = S3Source(
        endpoint="https://objects.example",
        bucket="research",
        key="results.csv",
        access_key="access-secret",
        secret_key="signing-secret",
        session_token="session-secret",
    )
    with patch("socket.getaddrinfo", side_effect=_public_dns):
        s3 = S3RemoteSourceAdapter(
            cast(Any, s3_opener),
            datetime.datetime(2026, 7, 20, tzinfo=datetime.timezone.utc),
        ).fetch(s3_source, policy)
    authorization = s3_opener.request.get_header("Authorization")
    assert authorization.startswith("AWS4-HMAC-SHA256 Credential=access-secret/")
    assert s3_opener.request.get_header("X-amz-security-token") == "session-secret"
    assert s3.display_uri == "s3://research/results.csv"
    assert "signing-secret" not in repr(s3_source)
    assert "session-secret" not in repr(s3_source)


def test_remote_policy_is_deny_by_default_and_blocks_private_or_credentialed_urls() -> None:
    source = HttpSource("https://localhost/results.csv?token=do-not-leak")
    with pytest.raises(ValueError, match="not authorized") as denied:
        HttpRemoteSourceAdapter(cast(Any, _Opener(b"a\n1\n", source.url))).fetch(
            source,
            RemoteSourcePolicy(()),
        )
    assert "do-not-leak" not in str(denied.value)

    with (
        patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]),
        pytest.raises(ValueError, match="non-public address"),
    ):
        HttpRemoteSourceAdapter(cast(Any, _Opener(b"a\n1\n", source.url))).fetch(
            source,
            RemoteSourcePolicy(("localhost",)),
        )

    credentialed = HttpSource("https://user:password@data.example/results.csv")
    with pytest.raises(ValueError, match="embedded credentials") as invalid:
        HttpRemoteSourceAdapter(cast(Any, _Opener(b"a\n1\n", credentialed.url))).fetch(
            credentialed,
            RemoteSourcePolicy(("data.example",)),
        )
    assert "password" not in str(invalid.value)

    with pytest.raises(ValueError, match="hostname is invalid"):
        SshRemoteSourceAdapter().fetch(
            SshSource("-oProxyCommand=unsafe", "/results.csv"),
            RemoteSourcePolicy(("-oproxycommand=unsafe",)),
        )


def test_remote_policy_reads_explicit_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RING5_ALLOWED_REMOTE_HOSTS", "data.example, *.lab.example")
    monkeypatch.setenv("RING5_ALLOW_PRIVATE_REMOTE_HOSTS", "1")
    monkeypatch.setenv("RING5_REQUIRE_REMOTE_TLS", "0")

    policy = RemoteSourcePolicy.from_environment()

    assert policy.allowed_hosts == ("data.example", "*.lab.example")
    assert policy.allow_private_hosts is True
    assert policy.require_tls is False


def test_http_adapter_stops_at_the_shared_download_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.core.services.remote_source_service as remote_module

    monkeypatch.setattr(remote_module, "MAX_BROWSER_UPLOAD_BYTES", 4)
    source = HttpSource("https://data.example/results.csv")
    opener = _Opener(b"12345", source.url)
    with (
        patch("socket.getaddrinfo", side_effect=_public_dns),
        pytest.raises(ValueError, match="download limit"),
    ):
        HttpRemoteSourceAdapter(cast(Any, opener)).fetch(
            source,
            RemoteSourcePolicy(("data.example",)),
        )


def test_http_transport_errors_drop_secret_bearing_causes() -> None:
    source = HttpSource(
        "https://data.example/results.csv?token=url-secret",
        bearer_token="bearer-secret",
    )
    with (
        patch("socket.getaddrinfo", side_effect=_public_dns),
        pytest.raises(ValueError, match="could not be reached") as failure,
    ):
        HttpRemoteSourceAdapter(cast(Any, _FailingOpener())).fetch(
            source,
            RemoteSourcePolicy(("data.example",)),
        )

    assert failure.value.__cause__ is None
    assert "url-secret" not in str(failure.value)
    assert "bearer-secret" not in str(failure.value)
