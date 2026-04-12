"""
Basic academic humanizer for AI-generated section prose.

This module intentionally uses deterministic, light-touch rewriting so it can run
without external model calls while preserving factual meaning and citation markers.
"""

from __future__ import annotations

import re
from typing import Iterable, List


class BasicAcademicHumanizer:
    """Apply minimal stylistic rewrites to reduce robotic phrasing."""

    _PHRASE_REPLACEMENTS = (
        (r"\bIn conclusion,\s*", "Overall, "),
        (r"\bIt is important to note that\s+", ""),
        (r"\bIt can be observed that\s+", ""),
        (r"\bThis paper aims to\b", "This paper examines"),
        (r"\bThis study presents\b", "This study examines"),
        (r"\bIn this paper,\s+", "In this study, "),
        (r"\bAs shown in this study\b", "As shown in the analysis"),
    )

    _OPENER_VARIANTS = {
        "this section": "The discussion",
        "this study": "The study",
        "the paper": "This work",
    }

    def humanize(self, text: str) -> str:
        """Return a lightly humanized version of the input text."""
        if not text or not text.strip():
            return ""

        paragraphs = [p for p in re.split(r"\n\s*\n", text) if p and p.strip()]
        rewritten: List[str] = []

        for paragraph in paragraphs:
            p = self._normalize_whitespace(paragraph)
            p = self._replace_stock_phrases(p)
            p = self._dedupe_adjacent_sentences(p)
            p = self._vary_repeated_openers(p)
            rewritten.append(p)

        return "\n\n".join(rewritten).strip()

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _replace_stock_phrases(self, text: str) -> str:
        out = text
        for pattern, replacement in self._PHRASE_REPLACEMENTS:
            out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
        return out

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p and p.strip()]

    def _dedupe_adjacent_sentences(self, text: str) -> str:
        sentences = self._split_sentences(text)
        if not sentences:
            return text

        deduped: List[str] = []
        prev_norm = ""
        for sentence in sentences:
            norm = re.sub(r"\s+", " ", sentence).strip().lower()
            if norm == prev_norm:
                continue
            deduped.append(sentence)
            prev_norm = norm
        return " ".join(deduped)

    def _vary_repeated_openers(self, text: str) -> str:
        sentences = self._split_sentences(text)
        if len(sentences) < 2:
            return text

        adjusted: List[str] = []
        prev_opener = ""

        for sentence in sentences:
            words = sentence.split()
            opener = " ".join(words[:2]).lower() if len(words) >= 2 else (words[0].lower() if words else "")

            candidate = sentence
            if opener and opener == prev_opener:
                for phrase, replacement in self._OPENER_VARIANTS.items():
                    if sentence.lower().startswith(phrase):
                        candidate = replacement + sentence[len(phrase):]
                        break

            adjusted.append(candidate)
            prev_opener = opener

        return " ".join(adjusted)

    def humanize_sections(self, sections: Iterable[dict], content_key: str = "content") -> List[dict]:
        """Humanize section dictionaries while preserving non-content fields."""
        out: List[dict] = []
        for section in sections:
            clone = dict(section)
            body = str(clone.get(content_key, ""))
            clone[content_key] = self.humanize(body) if body else body
            out.append(clone)
        return out
