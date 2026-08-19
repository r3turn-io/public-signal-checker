from __future__ import annotations

import httpx
import pytest

from public_signal_checker.fetch import (
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    FetchError,
    fetch_public,
)
from public_signal_checker.safety import UnsafeURLError
from tests.helpers import PUBLIC_IPV4, mock_client, mock_dns


def test_redirect_to_private_target_rejected(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/"})
        raise AssertionError(f"unexpected request: {request.url}")

    with mock_client(handler) as client:
        with pytest.raises(UnsafeURLError, match="not a permitted public"):
            fetch_public("https://example.com/", client=client)


def test_public_redirect_accepted(monkeypatch):
    mock_dns(
        monkeypatch,
        {
            "example.com": [PUBLIC_IPV4],
            "www.example.com": [PUBLIC_IPV4],
        },
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "example.com" and request.url.path == "/":
            return httpx.Response(
                302, headers={"Location": "https://www.example.com/final"}
            )
        if request.url.host == "www.example.com" and request.url.path == "/final":
            return httpx.Response(200, text="<html><title>OK</title></html>")
        raise AssertionError(f"unexpected request: {request.url}")

    with mock_client(handler) as client:
        fetched = fetch_public("https://example.com/", client=client)

    assert fetched.status_code == 200
    assert fetched.final_url == "https://www.example.com/final"
    assert b"OK" in fetched.body


def test_relative_redirect_resolved_against_current_url(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/from":
            return httpx.Response(301, headers={"Location": "/to"})
        if request.url.path == "/to":
            return httpx.Response(200, text="arrived")
        raise AssertionError(f"unexpected request: {request.url}")

    with mock_client(handler) as client:
        fetched = fetch_public("https://example.com/from", client=client)

    assert fetched.status_code == 200
    assert fetched.final_url == "https://example.com/to"
    assert fetched.body == b"arrived"


def test_timeout_handled_safely():
    class TimeoutClient:
        def stream(self, *args, **kwargs):
            raise httpx.TimeoutException("simulated timeout")

        def close(self):
            return None

    with pytest.raises(FetchError, match="timed out"):
        fetch_public(f"http://{PUBLIC_IPV4}/", client=TimeoutClient())


def test_http_error_handled_safely():
    class FailingClient:
        def stream(self, *args, **kwargs):
            raise httpx.ConnectError("simulated failure")

        def close(self):
            return None

    with pytest.raises(FetchError, match="The request failed."):
        fetch_public(f"http://{PUBLIC_IPV4}/", client=FailingClient())


def test_timeout_error_does_not_leak_internal_details():
    class TimeoutClient:
        def stream(self, *args, **kwargs):
            raise httpx.TimeoutException("127.0.0.1 timed out connecting to 10.0.0.5")

        def close(self):
            return None

    with pytest.raises(FetchError) as exc:
        fetch_public(f"http://{PUBLIC_IPV4}/", client=TimeoutClient())
    message = str(exc.value)
    assert "127.0.0.1" not in message
    assert "10.0.0.5" not in message


def test_too_many_redirects_rejected(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "https://example.com/next"})

    with mock_client(handler) as client:
        with pytest.raises(FetchError, match="Too many redirects"):
            fetch_public(
                "https://example.com/",
                client=client,
                max_redirects=MAX_REDIRECTS,
            )


def test_response_size_limit(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (MAX_RESPONSE_BYTES + 1))

    with mock_client(handler) as client:
        with pytest.raises(FetchError, match="size limit"):
            fetch_public("https://example.com/", client=client)
