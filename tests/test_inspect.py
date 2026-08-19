from __future__ import annotations

import json

import httpx

from public_signal_checker.inspect import (
    extract_html_signals,
    extract_jsonld_signals,
    inspect_public_url,
    parse_robots_sitemaps,
)
from public_signal_checker.models import InspectionResult, RobotsTxtObservation, format_human
from tests.helpers import PUBLIC_IPV4, mock_client, mock_dns

SAMPLE_HTML = """<!doctype html>
<html>
<head>
  <title>  Example Domain  </title>
  <meta name="description" content="An example public page.">
  <link rel="canonical" href="https://example.com/">
  <link rel="alternate" hreflang="en" href="https://example.com/">
  <link rel="alternate" hreflang="tr" href="/tr/">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Example Org",
    "sameAs": [
      "https://twitter.com/example",
      "https://www.linkedin.com/company/example"
    ]
  }
  </script>
</head>
<body><h1>Example</h1></body>
</html>
"""


def test_title_extraction():
    signals = extract_html_signals(SAMPLE_HTML, base_url="https://example.com/")
    assert signals.title == "Example Domain"


def test_meta_description_extraction():
    signals = extract_html_signals(SAMPLE_HTML, base_url="https://example.com/")
    assert signals.meta_description == "An example public page."


def test_canonical_extraction():
    signals = extract_html_signals(SAMPLE_HTML, base_url="https://example.com/page")
    assert signals.canonical == "https://example.com/"


def test_canonical_relative_url_resolved():
    html = '<link rel="canonical" href="/canonical-page">'
    signals = extract_html_signals(html, base_url="https://example.com/dir/")
    assert signals.canonical == "https://example.com/canonical-page"


def test_hreflang_extraction():
    signals = extract_html_signals(SAMPLE_HTML, base_url="https://example.com/")
    pairs = [(entry.hreflang, entry.href) for entry in signals.hreflang]
    assert ("en", "https://example.com/") in pairs
    assert ("tr", "https://example.com/tr/") in pairs


def test_organization_jsonld_detection():
    signals = extract_html_signals(SAMPLE_HTML, base_url="https://example.com/")
    jsonld = extract_jsonld_signals(signals.json_ld_blocks)
    assert jsonld.organization_jsonld is True


def test_same_as_extraction():
    signals = extract_html_signals(SAMPLE_HTML, base_url="https://example.com/")
    jsonld = extract_jsonld_signals(signals.json_ld_blocks)
    assert jsonld.same_as == [
        "https://twitter.com/example",
        "https://www.linkedin.com/company/example",
    ]


def test_organization_jsonld_from_graph_and_schema_url():
    block = json.dumps(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "https://schema.org/Organization",
                    "sameAs": "https://github.com/example",
                }
            ],
        }
    )
    jsonld = extract_jsonld_signals([block])
    assert jsonld.organization_jsonld is True
    assert jsonld.same_as == ["https://github.com/example"]


def test_malformed_jsonld_handled_without_crash():
    html = """<html><head>
    <title>Still parsed</title>
    <script type="application/ld+json">{not-valid-json</script>
    <script type="application/ld+json">{"@type": "Organization"}</script>
    </head></html>"""
    signals = extract_html_signals(html, base_url="https://example.com/")
    jsonld = extract_jsonld_signals(signals.json_ld_blocks)
    assert signals.title == "Still parsed"
    assert jsonld.organization_jsonld is True


def test_malformed_jsonld_only_does_not_claim_organization():
    jsonld = extract_jsonld_signals(["{broken", "null", "[1,2,3]"])
    assert jsonld.organization_jsonld is False
    assert jsonld.same_as == []


def test_robots_sitemap_declaration_parsing():
    text = """
User-agent: *
Allow: /
# Sitemap: https://example.com/ignored-comment.xml
Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/news.xml
"""
    assert parse_robots_sitemaps(text) == [
        "https://example.com/sitemap.xml",
        "https://example.com/news.xml",
    ]


def test_robots_and_sitemap_discovery(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/robots.txt":
            return httpx.Response(
                200,
                text="User-agent: *\nSitemap: https://example.com/declared.xml\n",
            )
        if path == "/sitemap.xml":
            return httpx.Response(200, text="<urlset></urlset>")
        if path in {"/", ""}:
            return httpx.Response(200, text="<title>Home</title>")
        return httpx.Response(404)

    with mock_client(handler) as client:
        result = inspect_public_url("https://example.com/", client=client)

    assert result.robots_txt.reachable is True
    assert result.robots_txt.url == "https://example.com/robots.txt"
    assert "https://example.com/declared.xml" in result.sitemaps
    assert "https://example.com/sitemap.xml" in result.sitemaps


def test_robots_unreachable_is_observed_not_interpreted(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404, text="missing")
        if request.url.path == "/sitemap.xml":
            return httpx.Response(404, text="missing")
        return httpx.Response(200, text="<title>Home</title>")

    with mock_client(handler) as client:
        result = inspect_public_url("https://example.com/", client=client)

    assert result.robots_txt.reachable is False
    assert result.sitemaps == []
    assert result.title == "Home"


def test_json_output_serialization():
    result = InspectionResult(
        input_url="https://example.com/",
        final_url="https://example.com/",
        http_status=200,
        title="Example Domain",
        meta_description=None,
        canonical="https://example.com/",
        robots_txt=RobotsTxtObservation(
            reachable=True, url="https://example.com/robots.txt"
        ),
        sitemaps=[],
        organization_jsonld=False,
        same_as=[],
        hreflang=[],
    )
    payload = result.to_dict()
    encoded = json.dumps(payload)
    decoded = json.loads(encoded)

    assert decoded["input_url"] == "https://example.com/"
    assert decoded["final_url"] == "https://example.com/"
    assert decoded["http_status"] == 200
    assert decoded["title"] == "Example Domain"
    assert decoded["meta_description"] is None
    assert decoded["canonical"] == "https://example.com/"
    assert decoded["robots_txt"] == {
        "reachable": True,
        "url": "https://example.com/robots.txt",
    }
    assert decoded["sitemaps"] == []
    assert decoded["organization_jsonld"] is False
    assert decoded["same_as"] == []
    assert decoded["hreflang"] == []


def test_human_output_is_factual_not_diagnostic():
    result = InspectionResult(
        input_url="https://example.com/",
        final_url="https://example.com/",
        http_status=200,
        title=None,
        meta_description=None,
        canonical=None,
        robots_txt=RobotsTxtObservation(reachable=False, url="https://example.com/robots.txt"),
        organization_jsonld=False,
    )
    text = format_human(result)
    assert "Organization JSON-LD detected: NO" in text
    assert "This is not a R3TURN Brand Intelligence report." in text
    assert "weak" not in text.lower()
    assert "score" not in text.lower()
    assert "grade" not in text.lower()
    assert "entity visibility" not in text.lower()


def test_full_inspection_extracts_page_signals(monkeypatch):
    mock_dns(monkeypatch, {"example.com": [PUBLIC_IPV4]})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\n")
        if request.url.path == "/sitemap.xml":
            return httpx.Response(404)
        return httpx.Response(200, text=SAMPLE_HTML)

    with mock_client(handler) as client:
        result = inspect_public_url("https://example.com/", client=client)

    assert result.http_status == 200
    assert result.title == "Example Domain"
    assert result.meta_description == "An example public page."
    assert result.canonical == "https://example.com/"
    assert result.organization_jsonld is True
    assert "https://twitter.com/example" in result.same_as
    assert any(entry.hreflang == "en" for entry in result.hreflang)
