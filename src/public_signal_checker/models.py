"""Observation-only result models for Public Signal Checker."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    """Render inspection observations as interpretation-free text."""
    lines = [
        "R3TURN Public Signal Checker v0.1",
        "",
        "This is not a R3TURN Brand Intelligence report.",
        "",
        f"input_url: {result.input_url}",
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


def _display(value: object | None) -> str:
    if value is None or value == "":
        return "(not detected)"
    return str(value)


def _yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def _list_block(label: str, values: list[str]) -> str:
    if not values:
        return f"{label}: (none detected)"
    inner = "\n".join(f"  - {item}" for item in values)
    return f"{label}:\n{inner}"


def _hreflang_block(entries: list[HreflangEntry]) -> str:
    if not entries:
        return "hreflang: (none detected)"
    inner = "\n".join(
        f"  - hreflang={entry.hreflang} href={entry.href}" for entry in entries
    )
    return f"hreflang:\n{inner}"
