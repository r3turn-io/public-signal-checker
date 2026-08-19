"""Factual extraction of selected public page signals."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin

from public_signal_checker.fetch import fetch_public, origin_of
from public_signal_checker.models import (
    HreflangEntry,
    InspectionResult,
    RobotsTxtObservation,
    SignalCheckerError,
)
from public_signal_checker.safety import UnsafeURLError

SITEMAP_PATH = "/sitemap.xml"


@dataclass
class HtmlSignals:
    title: str | None = None
    meta_description: str | None = None
    canonical: str | None = None
    hreflang: list[HreflangEntry] = field(default_factory=list)
    json_ld_blocks: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class JsonLdSignals:
    organization_jsonld: bool = False
    same_as: list[str] = field(default_factory=list)


class _PageParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self.signals = HtmlSignals()
        self._in_title = False
        self._title_parts: list[str] = []
        self._title_captured = False
        self._in_json_ld = False
        self._json_ld_parts: list[str] = []
        self._canonical_captured = False
        self._meta_captured = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        attr = _attr_map(attrs)

        if name == "title" and not self._title_captured:
            self._in_title = True
            return

        if name == "meta" and not self._meta_captured:
            meta_name = (attr.get("name") or "").strip().lower()
            if meta_name == "description":
                content = _clean_text(attr.get("content"))
                if content:
                    self.signals.meta_description = content
                    self._meta_captured = True
            return

        if name == "link":
            rel_tokens = set((attr.get("rel") or "").lower().split())
            href = (attr.get("href") or "").strip()
            if href and "canonical" in rel_tokens and not self._canonical_captured:
                self.signals.canonical = urljoin(self._base_url, href)
                self._canonical_captured = True
            hreflang = (attr.get("hreflang") or "").strip()
            if href and "alternate" in rel_tokens and hreflang:
                self.signals.hreflang.append(
                    HreflangEntry(hreflang=hreflang, href=urljoin(self._base_url, href))
                )
            return

        if name == "script":
            script_type = (attr.get("type") or "").strip().lower()
            if script_type == "application/ld+json":
                self._in_json_ld = True
                self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name == "title" and self._in_title:
            self._in_title = False
            title = _clean_text("".join(self._title_parts))
            if title:
                self.signals.title = title
                self._title_captured = True
            self._title_parts = []
        elif name == "script" and self._in_json_ld:
            self._in_json_ld = False
            block = "".join(self._json_ld_parts).strip()
            if block:
                self.signals.json_ld_blocks.append(block)
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        elif self._in_json_ld:
            self._json_ld_parts.append(data)


def inspect_public_url(url: str, *, client=None) -> InspectionResult:
    """Inspect selected public signals for *url*."""
    page = fetch_public(url, client=client)
    html = _decode_body(page.body)
    html_signals = extract_html_signals(html, base_url=page.final_url)
    jsonld = extract_jsonld_signals(html_signals.json_ld_blocks)

    robots = _observe_robots(page.final_url, client=client)
    sitemaps = _unique(list(robots.declared_sitemaps))
    conventional = _observe_conventional_sitemap(page.final_url, client=client)
    if conventional and conventional not in sitemaps:
        sitemaps.append(conventional)

    return InspectionResult(
        input_url=url.strip(),
        final_url=page.final_url,
        http_status=page.status_code,
        title=html_signals.title,
        meta_description=html_signals.meta_description,
        canonical=html_signals.canonical,
        robots_txt=RobotsTxtObservation(reachable=robots.reachable, url=robots.url),
        sitemaps=sitemaps,
        organization_jsonld=jsonld.organization_jsonld,
        same_as=jsonld.same_as,
        hreflang=html_signals.hreflang,
    )


def extract_html_signals(html: str, *, base_url: str) -> HtmlSignals:
    parser = _PageParser(base_url)
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return parser.signals
    return parser.signals


def extract_jsonld_signals(blocks: list[str]) -> JsonLdSignals:
    organization = False
    same_as: list[str] = []

    for block in blocks:
        payload = _parse_json_ld_block(block)
        if payload is None:
            continue
        found_org, found_same_as = _walk_jsonld(payload)
        if found_org:
            organization = True
        for item in found_same_as:
            if item not in same_as:
                same_as.append(item)

    return JsonLdSignals(organization_jsonld=organization, same_as=same_as)


def parse_robots_sitemaps(text: str) -> list[str]:
    found: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip().lower() != "sitemap":
            continue
        sitemap_url = value.strip()
        if sitemap_url and sitemap_url not in found:
            found.append(sitemap_url)
    return found


@dataclass
class _RobotsObservation:
    reachable: bool
    url: str
    declared_sitemaps: list[str]


def _observe_robots(final_url: str, *, client) -> _RobotsObservation:
    robots_url = origin_of(final_url) + "/robots.txt"
    try:
        fetched = fetch_public(robots_url, client=client)
    except SignalCheckerError:
        return _RobotsObservation(reachable=False, url=robots_url, declared_sitemaps=[])

    reachable = 200 <= fetched.status_code <= 299
    declared: list[str] = []
    if reachable:
        declared = parse_robots_sitemaps(_decode_body(fetched.body))
    return _RobotsObservation(
        reachable=reachable,
        url=fetched.final_url or robots_url,
        declared_sitemaps=declared,
    )


def _observe_conventional_sitemap(final_url: str, *, client) -> str | None:
    sitemap_url = origin_of(final_url) + SITEMAP_PATH
    try:
        fetched = fetch_public(sitemap_url, client=client)
    except (UnsafeURLError, SignalCheckerError):
        return None
    if 200 <= fetched.status_code <= 299:
        return fetched.final_url or sitemap_url
    return None


def _parse_json_ld_block(block: str) -> object | None:
    text = block.strip()
    if text.startswith("<!--") and text.endswith("-->"):
        text = text[4:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _walk_jsonld(node: object) -> tuple[bool, list[str]]:
    organization = False
    same_as: list[str] = []

    if isinstance(node, list):
        for item in node:
            found_org, found_same_as = _walk_jsonld(item)
            organization = organization or found_org
            for value in found_same_as:
                if value not in same_as:
                    same_as.append(value)
        return organization, same_as

    if not isinstance(node, dict):
        return False, []

    if _is_organization_type(node.get("@type")):
        organization = True
        for value in _same_as_values(node.get("sameAs")):
            if value not in same_as:
                same_as.append(value)

    graph = node.get("@graph")
    if graph is not None:
        found_org, found_same_as = _walk_jsonld(graph)
        organization = organization or found_org
        for value in found_same_as:
            if value not in same_as:
                same_as.append(value)

    for key, value in node.items():
        if key in {"@graph", "sameAs", "@type"}:
            continue
        found_org, found_same_as = _walk_jsonld(value)
        organization = organization or found_org
        for item in found_same_as:
            if item not in same_as:
                same_as.append(item)

    return organization, same_as


def _is_organization_type(value: object) -> bool:
    types: list[object]
    if isinstance(value, list):
        types = value
    else:
        types = [value]
    for item in types:
        if not isinstance(item, str):
            continue
        local = item.strip().rstrip("/").split("/")[-1]
        if local.lower() == "organization":
            return True
    return False


def _same_as_values(value: object) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    found: list[str] = []
    for item in items:
        if isinstance(item, str):
            cleaned = item.strip()
            if cleaned and cleaned not in found:
                found.append(cleaned)
        elif isinstance(item, dict):
            identifier = item.get("@id") or item.get("url")
            if isinstance(identifier, str):
                cleaned = identifier.strip()
                if cleaned and cleaned not in found:
                    found.append(cleaned)
    return found


def _decode_body(body: bytes) -> str:
    return body.decode("utf-8", errors="replace")


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _attr_map(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for key, value in attrs:
        if value is None:
            continue
        mapped[key.lower()] = value
    return mapped


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
