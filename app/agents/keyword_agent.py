"""Keyword extraction agent used by writing flows.

This agent deterministically derives concise paper keywords from abstract text,
with optional user-provided overrides.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable, List, Sequence


class KeywordAgent:
    """Derive 3-4 publication keywords from abstract/title content."""

    name = "KeywordAgent"

    _STOPWORDS = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into",
        "is", "it", "of", "on", "or", "that", "the", "their", "this", "to", "using",
        "use", "with", "via", "we", "our", "can", "also", "shows", "show", "study",
        "research", "analysis", "approach", "method", "methods", "paper", "work", "results",
        "result", "proposed", "based", "framework", "model", "models", "system", "systems",
    }

    _FALLBACK = ["Technical Analysis", "Evidence Synthesis", "Academic Writing"]

    def extract_keywords(
        self,
        title: str,
        abstract: str,
        provided: Sequence[Any] | None = None,
        limit: int = 4,
    ) -> List[str]:
        """Return up to ``limit`` keywords.

        Priority order:
        1. Explicit keywords if provided.
        2. Acronyms and phrases from abstract/title.
        3. High-signal single terms.
        4. Safe fallback terms.
        """
        cleaned_provided = self._clean_keywords(provided or [])
        if cleaned_provided:
            return cleaned_provided[: max(1, limit)]

        source_title = str(title or "").strip()
        source_abstract = str(abstract or "").strip()
        combined = f"{source_title} {source_abstract}".strip()

        selected: List[str] = []
        seen = set()

        for acronym in self._extract_acronyms(combined):
            self._append_unique(selected, seen, acronym, limit)
            if len(selected) >= limit:
                return selected

        for phrase in self._extract_phrases(source_abstract or combined):
            self._append_unique(selected, seen, phrase, limit)
            if len(selected) >= limit:
                return selected

        for term in self._extract_terms(source_title, source_abstract):
            self._append_unique(selected, seen, term, limit)
            if len(selected) >= limit:
                return selected

        for fallback in self._FALLBACK:
            self._append_unique(selected, seen, fallback, limit)
            if len(selected) >= limit:
                break

        return selected[:limit]

    def _clean_keywords(self, keywords: Sequence[Any]) -> List[str]:
        out: List[str] = []
        seen = set()
        for raw in keywords:
            term = str(raw or "").strip()
            if not term:
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(term)
        return out

    def _extract_acronyms(self, text: str) -> Iterable[str]:
        if not text:
            return []
        acronyms = re.findall(r"\b[A-Z]{2,}\b", text)
        # Keep order, dedupe
        ordered: List[str] = []
        seen = set()
        for acronym in acronyms:
            if acronym in seen:
                continue
            seen.add(acronym)
            ordered.append(acronym)
        return ordered

    def _extract_phrases(self, text: str) -> Iterable[str]:
        if not text:
            return []

        words = re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", text.lower())
        if len(words) < 2:
            return []

        phrase_counts: Counter[str] = Counter()
        for idx in range(len(words) - 1):
            w1, w2 = words[idx], words[idx + 1]
            if w1 in self._STOPWORDS or w2 in self._STOPWORDS:
                continue
            phrase_counts[f"{w1} {w2}"] += 1

        ranked = sorted(
            phrase_counts.items(),
            key=lambda item: (item[1], len(item[0])),
            reverse=True,
        )
        return [self._title_case_phrase(phrase) for phrase, _ in ranked[:8]]

    def _extract_terms(self, title: str, abstract: str) -> Iterable[str]:
        title_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", title.lower())
        abs_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+-]{2,}", abstract.lower())

        scores: Counter[str] = Counter()
        for token in abs_tokens:
            if token in self._STOPWORDS:
                continue
            scores[token] += 1

        # Title terms get extra weight to preserve topic intent.
        for token in title_tokens:
            if token in self._STOPWORDS:
                continue
            scores[token] += 2

        ranked = sorted(scores.items(), key=lambda item: (item[1], len(item[0])), reverse=True)
        return [token.upper() if token.isupper() else token.title() for token, _ in ranked[:10]]

    @staticmethod
    def _title_case_phrase(phrase: str) -> str:
        parts = phrase.split()
        cased = [p.upper() if p.isupper() else p.title() for p in parts]
        return " ".join(cased)

    @staticmethod
    def _append_unique(target: List[str], seen: set, value: str, limit: int) -> None:
        clean = str(value or "").strip()
        if not clean:
            return
        key = clean.lower()
        if key in seen:
            return
        seen.add(key)
        if len(target) < limit:
            target.append(clean)