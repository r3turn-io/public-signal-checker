"""Safe HTTP fetching with explicit redirects, timeouts, and size limits."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse, urlunparse

import httpx

from public_signal_checker.models import SignalCheckerError
from public_signal_checker.safety import authorize_url

MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 1_048_576
TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
USER_AGENT = "R3TURN-Public-Signal-Checker/0.1"
REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})


class FetchError(SignalCheckerError):
    """Raised when a remote resource cannot be fetched safely."""


@dataclass(frozen=True)
class FetchedResource:
    requested_url: str
    final_url: str
    status_code: int
    headers: httpx.Headers
    body: bytes


def create_client() -> httpx.Client:
    """Return an HTTP client with SSRF-relevant defaults applied."""
    return httpx.Client(
        follow_redirects=False,
        trust_env=False,
        timeout=TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )


def fetch_public(
    url: str,
    *,
    client: httpx.Client | None = None,
    max_bytes: int = MAX_RESPONSE_BYTES,
    max_redirects: int = MAX_REDIRECTS,
) -> FetchedResource:
    """Fetch *url* after authorizing each hop, without unrestricted redirects."""
    owns_client = client is None
    active = client if client is not None else create_client()
    try:
        return _fetch_with_client(
            url,
            client=active,
            max_bytes=max_bytes,
            max_redirects=max_redirects,
        )
    finally:
        if owns_client:
            active.close()


def origin_of(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme.lower()}://{parsed.netloc}"


def _fetch_with_client(
    url: str,
    *,
    client: httpx.Client,
    max_bytes: int,
    max_redirects: int,
) -> FetchedResource:
    current = _request_url(url)
    requested = current

    for _ in range(max_redirects + 1):
        authorize_url(current)
        status, headers, body, location = _send(client, current, max_bytes=max_bytes)

        if status in REDIRECT_STATUS_CODES:
            if not location:
                return FetchedResource(
                    requested_url=requested,
                    final_url=current,
                    status_code=status,
                    headers=headers,
                    body=body,
                )
            current = _absolute_location(current, location)
            continue

        return FetchedResource(
            requested_url=requested,
            final_url=current,
            status_code=status,
            headers=headers,
            body=body,
        )

    raise FetchError("Too many redirects.")


def _send(
    client: httpx.Client,
    url: str,
    *,
    max_bytes: int,
) -> tuple[int, httpx.Headers, bytes, str | None]:
    try:
        with client.stream("GET", url) as response:
            status = response.status_code
            headers = response.headers
            location = headers.get("location")
            if status in REDIRECT_STATUS_CODES:
                return status, headers, b"", location

            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise FetchError("The response exceeded the size limit.")
                chunks.append(chunk)
            return status, headers, b"".join(chunks), location
    except FetchError:
        raise
    except httpx.TimeoutException as exc:
        raise FetchError("The request timed out.") from exc
    except httpx.HTTPError as exc:
        raise FetchError("The request failed.") from exc


def _request_url(url: str) -> str:
    try:
        parsed = urlparse(url.strip())
    except ValueError as exc:
        raise FetchError("The request failed.") from exc
    path = parsed.path if parsed.path else "/"
    return urlunparse(
        (parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, "")
    )


def _absolute_location(current_url: str, location: str) -> str:
    try:
        joined = urljoin(current_url, location.strip())
        parsed = urlparse(joined)
    except ValueError as exc:
        raise FetchError("The request failed.") from exc
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise FetchError("The request failed.")
    return _request_url(joined)
