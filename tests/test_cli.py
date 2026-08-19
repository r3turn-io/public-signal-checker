from __future__ import annotations

import json

import pytest

from public_signal_checker.cli import main
from public_signal_checker.models import (
    HreflangEntry,
    InspectionResult,
    RobotsTxtObservation,
)


def test_help_exits_zero():
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_nonzero_for_blocked_localhost(capsys):
    code = main(["http://localhost/"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "not a permitted public" in captured.err
    assert "127.0.0.1" not in captured.err


def test_cli_nonzero_for_127_0_0_1(capsys):
    code = main(["http://127.0.0.1/"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err.strip() != ""
    assert "10.0.0." not in captured.err


def test_cli_nonzero_for_malformed_bracket_url(capsys):
    code = main(["http://[invalid"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert captured.err.strip() != ""
    assert "Traceback" not in captured.err
    assert "public_signal_checker" not in captured.err.lower()
    assert ".py" not in captured.err


def test_cli_nonzero_for_unsupported_scheme(capsys):
    code = main(["ftp://example.com/"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Unsupported URL scheme" in captured.err


def test_cli_json_output(monkeypatch, capsys):
    result = InspectionResult(
        input_url="https://example.com/",
        final_url="https://www.example.com/",
        http_status=200,
        title="Example Domain",
        meta_description="An example public page.",
        canonical="https://example.com/",
        robots_txt=RobotsTxtObservation(
            reachable=True, url="https://www.example.com/robots.txt"
        ),
        sitemaps=["https://www.example.com/sitemap.xml"],
        organization_jsonld=True,
        same_as=["https://twitter.com/example"],
        hreflang=[HreflangEntry(hreflang="en", href="https://example.com/")],
    )
    monkeypatch.setattr(
        "public_signal_checker.cli.inspect_public_url", lambda url: result
    )

    code = main(["https://example.com/", "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["input_url"] == "https://example.com/"
    assert payload["final_url"] == "https://www.example.com/"
    assert payload["http_status"] == 200
    assert payload["organization_jsonld"] is True
    assert payload["same_as"] == ["https://twitter.com/example"]
    assert payload["hreflang"] == [{"hreflang": "en", "href": "https://example.com/"}]
    assert captured.err == ""


def test_cli_human_output_is_factual(monkeypatch, capsys):
    result = InspectionResult(
        input_url="https://example.com/",
        final_url="https://example.com/",
        http_status=200,
        title="Example Domain",
        meta_description=None,
        canonical=None,
        robots_txt=RobotsTxtObservation(
            reachable=False, url="https://example.com/robots.txt"
        ),
        organization_jsonld=False,
    )
    monkeypatch.setattr(
        "public_signal_checker.cli.inspect_public_url", lambda url: result
    )

    code = main(["https://example.com/"])
    captured = capsys.readouterr()

    assert code == 0
    assert "Organization JSON-LD detected: NO" in captured.out
    assert "This is not a R3TURN Brand Intelligence report." in captured.out
    assert "weak entity" not in captured.out.lower()
    assert "score" not in captured.out.lower()
    assert "grade" not in captured.out.lower()
