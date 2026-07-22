"""Authorized, bounded HTTP, SSH, and S3-compatible source adapters."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import ipaddress
import mimetypes
import re
import socket
import subprocess
from collections.abc import Mapping
from http.client import HTTPMessage
from pathlib import Path, PurePosixPath
from typing import IO, Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, OpenerDirector, Request, build_opener

from src.core.common.security_limits import (
    MAX_BROWSER_UPLOAD_BYTES,
    MAX_BROWSER_UPLOAD_NAME_LENGTH,
    REMOTE_CONNECT_TIMEOUT_SECONDS,
    REMOTE_TRANSFER_TIMEOUT_SECONDS,
)
from src.core.models.remote_source_models import (
    HttpSource,
    RemoteDownload,
    RemoteSource,
    RemoteSourcePolicy,
    S3Source,
    SshSource,
)

_SAFE_SSH_COMPONENT = re.compile(r"^[A-Za-z0-9._@%+=:,/~-]+$")
_SAFE_SSH_USER = re.compile(r"^[A-Za-z0-9._-]+$")
_SAFE_S3_BUCKET = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
_DNS_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _normalized_host(host: str | None) -> str:
    if not host:
        raise ValueError("Remote source must include a hostname.")
    try:
        normalized = host.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise ValueError("Remote source hostname is invalid.") from exc
    try:
        ipaddress.ip_address(normalized.split("%", 1)[0])
    except ValueError:
        labels = normalized.split(".")
        if len(normalized) > 253 or any(_DNS_LABEL.fullmatch(label) is None for label in labels):
            raise ValueError("Remote source hostname is invalid.")
    return normalized


def _matches_allowed_host(host: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        normalized = pattern.rstrip(".")
        if normalized.startswith("*."):
            suffix = normalized[1:]
            if host.endswith(suffix) and host != normalized[2:]:
                return True
        elif host == normalized:
            return True
    return False


def _public_address(address: str) -> bool:
    parsed = ipaddress.ip_address(address.split("%", 1)[0])
    return not (
        parsed.is_private
        or parsed.is_loopback
        or parsed.is_link_local
        or parsed.is_multicast
        or parsed.is_reserved
        or parsed.is_unspecified
    )


def _authorize_url(
    url: str,
    policy: RemoteSourcePolicy,
    schemes: frozenset[str],
) -> tuple[str, str]:
    """Authorize scheme, host, port, and every currently resolved address."""
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    if scheme not in schemes:
        raise ValueError(f"Remote adapter does not allow {scheme or 'missing'} URL scheme.")
    if policy.require_tls and scheme == "http":
        raise ValueError("Remote HTTP sources require TLS (https).")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Remote URLs must not contain embedded credentials.")
    host = _normalized_host(parsed.hostname)
    if not policy.allowed_hosts or not _matches_allowed_host(host, policy.allowed_hosts):
        raise ValueError(f"Remote host {host!r} is not authorized by RING5_ALLOWED_REMOTE_HOSTS.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Remote source port is invalid.") from exc
    try:
        addresses = {
            cast(str, item[4][0])
            for item in socket.getaddrinfo(
                host,
                port,
                type=socket.SOCK_STREAM,
            )
        }
    except socket.gaierror as exc:
        raise ValueError(f"Authorized remote host {host!r} could not be resolved.") from exc
    if not addresses:
        raise ValueError(f"Authorized remote host {host!r} did not resolve to an address.")
    if not policy.allow_private_hosts and any(not _public_address(item) for item in addresses):
        raise ValueError(f"Remote host {host!r} resolves to a non-public address.")
    display = urlunsplit((scheme, parsed.netloc, parsed.path, "", ""))
    return host, display


def _safe_file_name(selected: str | None, fallback: str) -> str:
    name = selected or fallback
    if (
        not name
        or Path(name).name != name
        or "\x00" in name
        or any(ord(character) < 32 for character in name)
        or len(name) > MAX_BROWSER_UPLOAD_NAME_LENGTH
        or Path(name).suffix.lower() not in {".csv", ".json", ".xlsx"}
    ):
        raise ValueError("Remote source filename must safely end in .csv, .json, or .xlsx.")
    return name


def _response_content_type(headers: Any, file_name: str) -> str:
    value = ""
    if hasattr(headers, "get"):
        value = str(headers.get("Content-Type", ""))
    detected = value.partition(";")[0].strip().lower()
    return detected or mimetypes.guess_type(file_name)[0] or "application/octet-stream"


class _PolicyRedirectHandler(HTTPRedirectHandler):
    """Re-authorize every HTTP redirect before urllib follows it."""

    def __init__(self, policy: RemoteSourcePolicy) -> None:
        super().__init__()
        self._policy = policy

    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> Request | None:
        """Authorize a non-credentialed redirect before constructing its request."""
        absolute = urljoin(req.full_url, newurl)
        _authorize_url(absolute, self._policy, frozenset({"http", "https"}))
        if req.has_header("Authorization") or req.has_header("X-amz-security-token"):
            raise ValueError("Credentialed remote requests do not follow redirects.")
        return super().redirect_request(req, fp, code, msg, headers, absolute)


def _read_http(
    request: Request,
    policy: RemoteSourcePolicy,
    *,
    opener: OpenerDirector | None = None,
) -> tuple[bytes, object, str]:
    """Read at most the upload byte limit and sanitize transport failures."""
    host, _display = _authorize_url(
        request.full_url,
        policy,
        frozenset({"http", "https"}),
    )
    selected_opener = opener or build_opener(_PolicyRedirectHandler(policy))
    try:
        with selected_opener.open(request, timeout=REMOTE_TRANSFER_TIMEOUT_SECONDS) as response:
            final_url = str(response.geturl())
            _authorize_url(final_url, policy, frozenset({"http", "https"}))
            length = response.headers.get("Content-Length")
            if length is not None:
                try:
                    declared_length = int(length)
                except (TypeError, ValueError) as exc:
                    raise ValueError("Remote source returned an invalid Content-Length.") from exc
                if declared_length < 0:
                    raise ValueError("Remote source returned an invalid Content-Length.")
                if declared_length > MAX_BROWSER_UPLOAD_BYTES:
                    raise ValueError("Remote source exceeds the 64 MiB download limit.")
            content = cast(bytes, response.read(MAX_BROWSER_UPLOAD_BYTES + 1))
            if len(content) > MAX_BROWSER_UPLOAD_BYTES:
                raise ValueError("Remote source exceeds the 64 MiB download limit.")
            if not content:
                raise ValueError("Remote source returned an empty file.")
            return content, response.headers, final_url
    except HTTPError as exc:
        raise ValueError(f"Authorized remote host {host!r} returned HTTP {exc.code}.") from None
    except (TimeoutError, URLError):
        raise ValueError(f"Authorized remote host {host!r} could not be reached.") from None


class RemoteSourceAdapter(Protocol):
    """Adapter contract for one remote-source transport."""

    def fetch(self, source: RemoteSource, policy: RemoteSourcePolicy) -> RemoteDownload:
        """Fetch one authorized and bounded remote object."""


class HttpRemoteSourceAdapter:
    """Fetch HTTPS sources without retaining URL queries or bearer tokens."""

    def __init__(self, opener: OpenerDirector | None = None) -> None:
        self._opener = opener

    def fetch(self, source: RemoteSource, policy: RemoteSourcePolicy) -> RemoteDownload:
        # [impl->req~ring5.ingestion.remote-sources~1]
        """Fetch one authorized HTTPS file."""
        if not isinstance(source, HttpSource):
            raise TypeError("HTTP adapter requires HttpSource configuration.")
        _host, display = _authorize_url(
            source.url,
            policy,
            frozenset({"http", "https"}),
        )
        parsed = urlsplit(source.url)
        file_name = _safe_file_name(source.file_name, PurePosixPath(parsed.path).name)
        headers = {"Accept": "text/csv, application/json, application/octet-stream"}
        if source.bearer_token:
            if "\r" in source.bearer_token or "\n" in source.bearer_token:
                raise ValueError("Bearer token contains invalid control characters.")
            headers["Authorization"] = f"Bearer {source.bearer_token}"
        content, response_headers, final_url = _read_http(
            Request(source.url, headers=headers, method="GET"),
            policy,
            opener=self._opener,
        )
        _final_host, final_display = _authorize_url(
            final_url,
            policy,
            frozenset({"http", "https"}),
        )
        return RemoteDownload(
            adapter="http",
            display_uri=final_display or display,
            file_name=file_name,
            content_type=_response_content_type(response_headers, file_name),
            content=content,
        )


class SshRemoteSourceAdapter:
    """Fetch remote files through OpenSSH with strict host verification."""

    def fetch(self, source: RemoteSource, policy: RemoteSourcePolicy) -> RemoteDownload:
        # [impl->req~ring5.ingestion.remote-sources~1]
        """Fetch one authorized file through the system SSH client."""
        if not isinstance(source, SshSource):
            raise TypeError("SSH adapter requires SshSource configuration.")
        if not 1 <= source.port <= 65_535:
            raise ValueError("SSH port must be from 1 through 65535.")
        if source.username and _SAFE_SSH_USER.fullmatch(source.username) is None:
            raise ValueError("SSH username contains unsupported characters.")
        if not source.path.startswith("/") or _SAFE_SSH_COMPONENT.fullmatch(source.path) is None:
            raise ValueError("SSH source path must be absolute and contain only safe characters.")
        host = _normalized_host(source.host)
        uri_host = f"[{host}]" if ":" in host else host
        uri = f"ssh://{uri_host}:{source.port}{source.path}"
        _authorized, display = _authorize_url(uri, policy, frozenset({"ssh"}))
        target = f"{source.username}@{host}" if source.username else host
        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"ConnectTimeout={int(REMOTE_CONNECT_TIMEOUT_SECONDS)}",
            "-p",
            str(source.port),
        ]
        if source.identity_file:
            identity = Path(source.identity_file).resolve()
            if not identity.is_file():
                raise ValueError("SSH identity file does not exist or is not a file.")
            if identity.stat().st_mode & 0o077:
                raise ValueError(
                    "SSH identity file permissions must exclude group and other users."
                )
            command.extend(["-i", str(identity)])
        command.extend(
            [
                target,
                f"head -c {MAX_BROWSER_UPLOAD_BYTES + 1} -- {source.path}",
            ]
        )
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                timeout=REMOTE_TRANSFER_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(
                f"SSH source on authorized host {host!r} could not be fetched."
            ) from exc
        if completed.returncode != 0:
            raise ValueError(
                f"SSH source on authorized host {host!r} failed with status "
                f"{completed.returncode}."
            )
        if not completed.stdout:
            raise ValueError("SSH source returned an empty file.")
        if len(completed.stdout) > MAX_BROWSER_UPLOAD_BYTES:
            raise ValueError("SSH source exceeds the 64 MiB download limit.")
        file_name = _safe_file_name(source.file_name, PurePosixPath(source.path).name)
        return RemoteDownload(
            adapter="ssh",
            display_uri=display,
            file_name=file_name,
            content_type=mimetypes.guess_type(file_name)[0] or "application/octet-stream",
            content=completed.stdout,
        )


def _signing_key(secret: str, date: str, region: str) -> bytes:
    initial = hmac.new(f"AWS4{secret}".encode(), date.encode(), hashlib.sha256).digest()
    regional = hmac.new(initial, region.encode(), hashlib.sha256).digest()
    service = hmac.new(regional, b"s3", hashlib.sha256).digest()
    return hmac.new(service, b"aws4_request", hashlib.sha256).digest()


class S3RemoteSourceAdapter:
    """Fetch path-style S3-compatible objects with optional SigV4 authentication."""

    def __init__(
        self,
        opener: OpenerDirector | None = None,
        now: datetime.datetime | None = None,
    ) -> None:
        self._opener = opener
        self._now = now

    def fetch(self, source: RemoteSource, policy: RemoteSourcePolicy) -> RemoteDownload:
        # [impl->req~ring5.ingestion.remote-sources~1]
        """Fetch one authorized S3-compatible object."""
        if not isinstance(source, S3Source):
            raise TypeError("S3 adapter requires S3Source configuration.")
        if _SAFE_S3_BUCKET.fullmatch(source.bucket) is None:
            raise ValueError("S3 bucket name is invalid.")
        if not source.key or source.key.startswith("/") or ".." in PurePosixPath(source.key).parts:
            raise ValueError("S3 object key must be a non-traversing relative path.")
        if not source.region or _SAFE_SSH_USER.fullmatch(source.region) is None:
            raise ValueError("S3 region is invalid.")
        if bool(source.access_key) != bool(source.secret_key):
            raise ValueError("S3 access key and secret key must be provided together.")
        if source.session_token and not source.access_key:
            raise ValueError("S3 session token requires access and secret keys.")
        if any(
            value and ("\r" in value or "\n" in value)
            for value in (source.access_key, source.session_token)
        ):
            raise ValueError("S3 credentials contain invalid control characters.")
        endpoint = source.endpoint.rstrip("/")
        parsed_endpoint = urlsplit(endpoint)
        if parsed_endpoint.query or parsed_endpoint.fragment or parsed_endpoint.username:
            raise ValueError("S3 endpoint must not contain query, fragment, or credentials.")
        _authorize_url(
            endpoint,
            policy,
            frozenset({"http", "https"}),
        )
        object_path = "/".join([quote(source.bucket, safe="-._~"), quote(source.key, safe="/-._~")])
        url = f"{endpoint}/{object_path}"
        headers: dict[str, str] = {"Accept": "application/octet-stream"}
        if source.access_key and source.secret_key:
            current = self._now or datetime.datetime.now(datetime.timezone.utc)
            amz_date = current.strftime("%Y%m%dT%H%M%SZ")
            date = current.strftime("%Y%m%d")
            payload_hash = "UNSIGNED-PAYLOAD"
            canonical_uri = urlsplit(url).path
            canonical_host = parsed_endpoint.netloc.lower()
            canonical_headers = (
                f"host:{canonical_host}\n"
                f"x-amz-content-sha256:{payload_hash}\n"
                f"x-amz-date:{amz_date}\n"
            )
            signed_headers = "host;x-amz-content-sha256;x-amz-date"
            if source.session_token:
                canonical_headers += f"x-amz-security-token:{source.session_token}\n"
                signed_headers += ";x-amz-security-token"
                headers["X-Amz-Security-Token"] = source.session_token
            canonical_request = "\n".join(
                ["GET", canonical_uri, "", canonical_headers, signed_headers, payload_hash]
            )
            scope = f"{date}/{source.region}/s3/aws4_request"
            string_to_sign = "\n".join(
                [
                    "AWS4-HMAC-SHA256",
                    amz_date,
                    scope,
                    hashlib.sha256(canonical_request.encode()).hexdigest(),
                ]
            )
            signature = hmac.new(
                _signing_key(source.secret_key, date, source.region),
                string_to_sign.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers.update(
                {
                    "Authorization": (
                        "AWS4-HMAC-SHA256 "
                        f"Credential={source.access_key}/{scope}, "
                        f"SignedHeaders={signed_headers}, Signature={signature}"
                    ),
                    "X-Amz-Content-SHA256": payload_hash,
                    "X-Amz-Date": amz_date,
                }
            )
        file_name = _safe_file_name(source.file_name, PurePosixPath(source.key).name)
        content, response_headers, _final_url = _read_http(
            Request(url, headers=headers, method="GET"),
            policy,
            opener=self._opener,
        )
        return RemoteDownload(
            adapter="s3",
            display_uri=f"s3://{source.bucket}/{source.key}",
            file_name=file_name,
            content_type=_response_content_type(response_headers, file_name),
            content=content,
        )


class RemoteSourceService:
    """Dispatch configured remote sources through transport-specific adapters."""

    def __init__(self, adapters: Mapping[str, RemoteSourceAdapter] | None = None) -> None:
        self._adapters: dict[str, RemoteSourceAdapter] = dict(
            adapters
            or {
                "http": HttpRemoteSourceAdapter(),
                "ssh": SshRemoteSourceAdapter(),
                "s3": S3RemoteSourceAdapter(),
            }
        )

    def fetch(
        self,
        source: RemoteSource,
        policy: RemoteSourcePolicy | None = None,
    ) -> RemoteDownload:
        # [impl->req~ring5.ingestion.remote-sources~1]
        """Fetch with the named adapter under an explicit or environment policy."""
        selected_policy = policy or RemoteSourcePolicy.from_environment()
        adapter = self._adapters.get(source.adapter)
        if adapter is None:
            raise ValueError(f"Remote source adapter {source.adapter!r} is not configured.")
        return adapter.fetch(source, selected_policy)
