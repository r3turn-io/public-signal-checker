"""Observation-only result models for Public Signal Checker."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


class SignalCheckerError(Exception):
    """Error whose message is safe to print on a public CLI."""


@dataclass(frozen=True)
class HreflangEntry:
    hreflang: str
    href: str

    def to_dict(self) -> dict[str, str]:
        return {"hreflang": self.hreflang, "href": self.href}


@dataclass(frozen=True)
class RobotsTxtObservation:
    reachable: bool
    url: str | None

    def to_dict(self) -> dict[str, Any]:
        return {"reachable": self.reachable, "url": self.url}


@dataclass(frozen=True)
class InspectionResult:
    """Factual public-surface observations for a single URL."""

    input_url: str
    final_url: str | None
    http_status: int | None
    title: str | None
    meta_description: str | None
    canonical: str | None
    robots_txt: RobotsTxtObservation
    sitemaps: list[str] = field(default_factory=list)
    organization_jsonld: bool = False
    same_as: list[str] = field(default_factory=list)
    hreflang: list[HreflangEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_url": self.input_url,
            "final_url": self.final_url,
            "http_status": self.http_status,
            "title": self.title,
            "meta_description": self.meta_description,
            "canonical": self.canonical,
            "robots_txt": self.robots_txt.to_dict(),
            "sitemaps": list(self.sitemaps),
            "organization_jsonld": self.organization_jsonld,
            "same_as": list(self.same_as),
            "hreflang": [entry.to_dict() for entry in self.hreflang],
        }


def format_human(result: InspectionResult) -> str:
    """Render inspection observations as interpretation-free text.

    Values may originate from an untrusted remote page. They are sanitized
    for terminal display here, at the presentation boundary only; the
    underlying observation model and JSON output are unaffected.
    """
    lines = [
        "R3TURN Public Signal Checker v0.1",
        "",
        "This is not a R3TURN Brand Intelligence report.",
        "",
        f"input_url: {_sanitize_for_terminal(result.input_url)}",
        f"final_url: {_display(result.final_url)}",
        f"http_status: {_display(result.http_status)}",
        f"title: {_display(result.title)}",
        f"meta_description: {_display(result.meta_description)}",
        f"canonical: {_display(result.canonical)}",
        f"robots.txt reachable: {_yes_no(result.robots_txt.reachable)}",
        f"robots.txt url: {_display(result.robots_txt.url)}",
        _list_block("sitemaps", result.sitemaps),
        f"Organization JSON-LD detected: {_yes_no(result.organization_jsonld)}",
        _list_block("sameAs", result.same_as),
        _hreflang_block(result.hreflang),
    ]
    return "\n".join(lines) + "\n"


def _sanitize_for_terminal(value: str) -> str:
    """Neutralize ASCII control characters (0x00-0x1F, 0x7F) for terminal display.

    Untrusted remote text may contain raw control or ANSI escape bytes.
    JSON output already escapes these through standard JSON encoding; this
    helper protects only the human-readable rendering path.
    """
    return _CONTROL_CHARS_RE.sub(" ", value)


def _display(value: object | None) -> str:
    if value is None or value == "":
        return "(not detected)"
    if isinstance(value, str):
        return _sanitize_for_terminal(value)
    return str(value)


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _list_block(label: str, values: list[str]) -> str:
    if not values:
        return f"{label}: (none detected)"
    inner = "\n".join(f"  - {_sanitize_for_terminal(item)}" for item in values)
    return f"{label}:\n{inner}"


def _hreflang_block(entries: list[HreflangEntry]) -> str:
    if not entries:
        return "hreflang: (none detected)"
    inner = "\n".join(
        f"  - hreflang={_sanitize_for_terminal(entry.hreflang)}"
        f" href={_sanitize_for_terminal(entry.href)}"
        for entry in entries
    )
    return f"hreflang:\n{inner}"
