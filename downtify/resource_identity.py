"""Exact fallback names when a provider-scoped resource ID is unavailable."""
from __future__ import annotations
import unicodedata


def exact_name_key(value: str) -> str:
    """Ignore casing/space only; punctuation and version text are identity."""
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).lower().split())
