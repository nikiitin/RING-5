"""Credential-safe configuration and results for authorized remote sources."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RemoteSourcePolicy:
    # [impl->req~ring5.ingestion.remote-sources~1]
    """Host and network boundary applied to every remote adapter."""

    allowed_hosts: tuple[str, ...]
    allow_private_hosts: bool = False
    require_tls: bool = True

    @classmethod
    def from_environment(cls) -> "RemoteSourcePolicy":
        """Build the deny-by-default policy configured for this process."""
        allowed = tuple(
            value.strip().lower()
            for value in os.environ.get("RING5_ALLOWED_REMOTE_HOSTS", "").split(",")
            if value.strip()
        )
        return cls(
            allowed_hosts=allowed,
            allow_private_hosts=os.environ.get("RING5_ALLOW_PRIVATE_REMOTE_HOSTS") == "1",
            require_tls=os.environ.get("RING5_REQUIRE_REMOTE_TLS", "1") != "0",
        )


@dataclass(frozen=True)
class HttpSource:
    """HTTPS dataset or portfolio source, optionally using a bearer token."""

    url: str = field(repr=False)
    file_name: str | None = None
    bearer_token: str | None = field(default=None, repr=False)

    @property
    def adapter(self) -> str:
        """Return the configured adapter identifier."""
        return "http"


@dataclass(frozen=True)
class SshSource:
    """Remote file fetched with system SSH key or agent authentication."""

    host: str
    path: str
    username: str | None = None
    port: int = 22
    identity_file: str | None = field(default=None, repr=False)
    file_name: str | None = None

    @property
    def adapter(self) -> str:
        """Return the configured adapter identifier."""
        return "ssh"


@dataclass(frozen=True)
class S3Source:
    """Path-style S3-compatible object source with optional SigV4 credentials."""

    endpoint: str
    bucket: str
    key: str
    region: str = "us-east-1"
    access_key: str | None = field(default=None, repr=False)
    secret_key: str | None = field(default=None, repr=False)
    session_token: str | None = field(default=None, repr=False)
    file_name: str | None = None

    @property
    def adapter(self) -> str:
        """Return the configured adapter identifier."""
        return "s3"


RemoteSource = HttpSource | SshSource | S3Source


@dataclass(frozen=True)
class RemoteDownload:
    """Bounded remote response passed directly into upload validation."""

    adapter: str
    display_uri: str
    file_name: str
    content_type: str
    content: bytes = field(repr=False)

    @property
    def size_bytes(self) -> int:
        """Return downloaded byte size."""
        return len(self.content)
