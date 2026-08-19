"""Command-line interface for R3TURN Public Signal Checker."""

from __future__ import annotations

import argparse
import json
import sys

from public_signal_checker.inspect import inspect_public_url
from public_signal_checker.models import SignalCheckerError, format_human

DESCRIPTION = (
    "Inspect selected public, machine-readable signals exposed by a website. "
    "This is not a R3TURN Brand Intelligence report."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="r3turn-signal",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "url",
        help="Public HTTP or HTTPS URL to inspect",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = inspect_public_url(args.url)
    except SignalCheckerError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_human(result), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
