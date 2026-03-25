#!/usr/bin/env python3
"""CLI wrapper around the shared reference service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.references import DEFAULT_LIMIT, DEFAULT_STYLE, generate_references, pyzotero_capabilities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate references from DuckDuckGo + scholarly metadata.")
    parser.add_argument("query", nargs="?", default="", help="Research query")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Number of references")
    parser.add_argument("--style", default=DEFAULT_STYLE, help="IEEE/APA/MLA/Chicago/Harvard/Vancouver")
    parser.add_argument("--show-pyzotero-formats", action="store_true", help="Print pyzotero output formats and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.show_pyzotero_formats:
        info = pyzotero_capabilities()
        print("PyZotero available:", info["available"])
        print("PyZotero content formats:", ", ".join(info["formats"]))
        print(info["style_note"])
        return 0

    if not args.query.strip():
        print("Error: query is required unless --show-pyzotero-formats is used", file=sys.stderr)
        return 2

    try:
        result = generate_references(args.query, args.limit, args.style)
        print(f"Query: {result['query']}")
        print(f"References: {result['count']}")
        print(f"Style: {result['style_name']}")
        print("Domains:", ", ".join(result["source_domains"]))
        print("PyZotero available:", result["pyzotero"]["available"])
        print("PyZotero formats:", ", ".join(result["pyzotero"]["formats"]))
        print("=" * 80)
        print(result["formatted_references"])
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
