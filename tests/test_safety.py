from __future__ import annotations

import pytest

from public_signal_checker.safety import UnsafeURLError, authorize_url
from tests.helpers import PUBLIC_IPV4, mock_dns


def test_http_url_allowed():
    authorize_url(f"http://{PUBLIC_IPV4}/")


def test_https_url_allowed():
    authorize_url(f"https://{PUBLIC_IPV4}/")


def test_http_hostname_allowed_when_dns_is_public(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})
    authorize_url("http://example.com/")


def test_https_hostname_allowed_when_dns_is_public(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})
    authorize_url("https://example.com/")


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/plain,hello",
        "ws://example.com/",
        "gopher://example.com/",
    ],
)
def test_unsupported_schemes_rejected(url):
    with pytest.raises(UnsafeURLError, match="Unsupported URL scheme"):
        authorize_url(url)


def test_localhost_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://localhost/")


def test_localhost_suffix_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://app.localhost/")


def test_127_0_0_1_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://127.0.0.1/")


@pytest.mark.parametrize(
    "url",
    [
        "http://10.0.0.8/",
        "http://192.168.1.20/",
        "http://172.16.0.5/",
        "http://172.31.255.1/",
        "http://100.64.0.1/",
    ],
)
def test_private_ipv4_rejected(url):
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://[fd00::1]/",
        "http://[fc00::1234]/",
        "http://[fe80::1]/",
        "http://[::1]/",
    ],
)
def test_private_ipv6_rejected(url):
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url(url)


def test_link_local_metadata_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://169.254.169.254/")


def test_multicast_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://224.0.0.1/")
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://[ff02::1]/")


def test_unspecified_addresses_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://0.0.0.0/")
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://[::]/")


def test_internal_hostname_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://intranet.corp/")


def test_url_embedded_credentials_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url(f"https://user:secret@{PUBLIC_IPV4}/")


def test_username_only_credentials_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url(f"https://user@{PUBLIC_IPV4}/")


def test_dns_resolving_to_private_ipv4_rejected(monkeypatch):
    mock_dns(monkeypatch, {"internal.example.com": ["10.0.0.8"]})
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://internal.example.com/")


def test_any_private_resolved_ip_rejects_the_host(monkeypatch):
    mock_dns(monkeypatch, {"dual.example.com": [PUBLIC_IPV4, "192.168.0.10"]})
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://dual.example.com/")


def test_ipv4_mapped_loopback_rejected():
    with pytest.raises(UnsafeURLError, match="not a permitted public"):
        authorize_url("http://[::ffff:127.0.0.1]/")


def test_blocked_url_error_does_not_leak_address():
    with pytest.raises(UnsafeURLError) as exc:
        authorize_url("http://10.1.2.3/")
    message = str(exc.value)
    assert "10.1.2.3" not in message
    assert "127.0.0.1" not in message


def test_unresolved_hostname_fails_closed(monkeypatch):
    mock_dns(monkeypatch, {})
    with pytest.raises(UnsafeURLError, match="could not be resolved"):
        authorize_url("http://missing.example.com/")


def test_empty_url_rejected():
    with pytest.raises(UnsafeURLError, match="invalid"):
        authorize_url("   ")
