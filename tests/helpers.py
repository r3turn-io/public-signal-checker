"""Shared test helpers. Tests never perform live network I/O."""

from __future__ import annotations

import socket

import httpx
import pytest

from public_signal_checker.fetch import TIMEOUT, USER_AGENT

PUBLIC_IPV4 = "8.8.8.8"


def mock_dns(monkeypatch: pytest.MonkeyPatch, hosts: dict[str, list[str]] | None = None) -> None:
    """Replace DNS lookup with a deterministic mapping. Unknown hosts fail closed."""
    mapping = {key.lower(): values for key, values in (hosts or {}).items()}

    def fake_getaddrinfo(host: str, port, *args, **kwargs):
        ips = mapping.get(str(host).lower())
        if not ips:
            raise socket.gaierror(socket.EAI_NONAME, "never connect")
        results = []
        for ip in ips:
            results.append(
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))
            )
        return results

    monkeypatch.setattr(
        "public_signal_checker.safety.socket.getaddrinfo", fake_getaddrinfo
    )


def mock_client(handler) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=False,
        trust_env=False,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
