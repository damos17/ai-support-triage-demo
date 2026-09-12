from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter


TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


class SimilarityEngine(ABC):
    """Boundary for incident-description similarity.

    The demo defaults to a local lexical engine so it remains reproducible and
    dependency-light. A semantic embeddings implementation can be plugged in
    later without changing incident orchestration.
    """

    name: str = "unknown"

    @abstractmethod
    def score(self, left: str, right: str) -> float:
        raise NotImplementedError


class TokenCosineSimilarity(SimilarityEngine):
    """Local cosine similarity over normalized token-frequency vectors."""

    name = "token_cosine"

    def __init__(self, stopwords: set[str] | None = None):
        self.stopwords = stopwords or {
            "the", "a", "an", "our", "is", "are", "has", "have", "with", "since", "this", "and", "for",
            "we", "us", "too", "to", "of", "in", "on", "from", "it", "that", "but", "or",
            "у", "и", "в", "во", "на", "с", "со", "из", "для", "по", "что", "это", "не", "мы", "наш", "наша",
        }

    def score(self, left: str, right: str) -> float:
        a = self._vector(left)
        b = self._vector(right)
        if not a or not b:
            return 0.0
        shared = set(a) & set(b)
        dot = sum(a[token] * b[token] for token in shared)
        norm_a = math.sqrt(sum(value * value for value in a.values()))
        norm_b = math.sqrt(sum(value * value for value in b.values()))
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)

    def _vector(self, text: str) -> Counter[str]:
        tokens = []
        for raw in TOKEN_RE.findall(text.lower()):
            token = self._normalize(raw)
            if len(token) > 2 and token not in self.stopwords:
                tokens.append(token)
        return Counter(tokens)

    @staticmethod
    def _normalize(token: str) -> str:
        # Lightweight normalization keeps the demo dependency-free while
        # reducing trivial English/Russian inflection differences.
        suffixes = (
            "ing", "ed", "es", "s",
            "ами", "ями", "ого", "ему", "ому", "ов", "ев", "ам", "ям", "ах", "ях", "ы", "и", "а", "я",
        )
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                return token[: -len(suffix)]
        return token
