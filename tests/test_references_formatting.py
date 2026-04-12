"""Tests for reference text formatting styles."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.utils.references import DEFAULT_LIMIT, ReferenceItem, format_references


def test_default_reference_limit_is_30():
    assert DEFAULT_LIMIT == 30


def _sample_items():
    return [
        ReferenceItem(
            title="A Survey on Federated Learning",
            url="https://example.org/paper1",
            source="IEEE Access",
            authors=["Jane Doe", "John Smith"],
            year="2021",
            doi="10.1000/test.1",
        ),
        ReferenceItem(
            title="Privacy in Clinical AI",
            url="https://example.org/paper2",
            source="Nature Medicine",
            authors=["Alice Brown"],
            year="2023",
        ),
    ]


def test_format_references_ieee_text():
    text = format_references(_sample_items(), "IEEE")

    assert "[1]" in text
    assert '"A Survey on Federated Learning,"' in text
    assert "doi: 10.1000/test.1" in text
    assert "URL: https://example.org/paper2" in text
    assert "https://example.org/paper1" not in text


def test_format_references_harvard_text():
    text = format_references(_sample_items(), "HARVARD")

    assert "[1] Jane Doe, John Smith (2021) 'A Survey on Federated Learning', IEEE Access." in text
    assert "[2] Alice Brown (2023) 'Privacy in Clinical AI', Nature Medicine." in text
