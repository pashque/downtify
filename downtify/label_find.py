"""Find label candidates from loose text: wrong spelling, missing words.

Spotify has no label list. Its ``label:`` search matches word starts, so the
albums it returns are read for their own exact ``label`` field; each distinct
label string is one candidate. Spotify's search does not forgive a typo, so
when nothing close is found MusicBrainz's fuzzy label search suggests names
that are then looked up on Spotify the same way.
"""

from __future__ import annotations

import copy
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Any

import httpx

from . import label_catalog, label_search, spotify

_MIN_SCORE = 0.75
_STRONG_SCORE = 0.9
_MAX_LABELS = 12
_MAX_ALBUMS = 100
_QUICK_ALBUMS = 40
_BUDGET_SECONDS = 25
_MB_URL = 'https://musicbrainz.org/ws/2/label/'
_MB_AGENT = 'Downtify/3 (label search; https://github.com/pashque/downtify)'


def _clean_query(query: str) -> str:
    raw = query.strip()
    text = label_search._plain(raw)
    if (
        len(text) < 2
        or len(raw) > 200
        or any(ord(c) < 32 or c in '\\"' for c in raw)
    ):
        raise ValueError('Invalid query')
    return text


def _score(query: str, name: str) -> float:
    """0..1 similarity; a name containing every query word counts as close."""
    q, n = label_search.label_key(query), label_search.label_key(name)
    if not q or not n:
        return 0.0
    score = SequenceMatcher(None, q, n).ratio()
    words = label_search._plain(name).casefold().split()
    wanted = label_search._plain(query).casefold().split()
    if words and words[0] == label_search._plain(query).casefold():
        score = max(score, 0.95)
    elif n.startswith(q) or q in n:
        score = max(score, 0.9)
    elif wanted and all(
        any(word.startswith(w) for word in words) for w in wanted
    ):
        score = max(score, 0.9)
    return score


def _musicbrainz_names(query: str) -> list[str]:
    """Fuzzy label names from MusicBrainz; empty when it is unavailable."""
    labels: list[Any] = []
    for attempt in range(2):
        try:
            response = httpx.get(
                _MB_URL,
                params={'fmt': 'json', 'limit': 6, 'query': f'{query}~'},
                headers={'User-Agent': _MB_AGENT},
                timeout=8,
            )
            response.raise_for_status()
            labels = response.json().get('labels') or []
            break
        except (httpx.HTTPError, ValueError) as exc:
            if attempt:
                raise ValueError('MusicBrainz unavailable') from exc
            time.sleep(1.3)  # its limit is one request per second
    return [
        str(item['name'])
        for item in labels
        if isinstance(item, dict)
        and item.get('name')
        and int(item.get('score') or 0) >= 50
    ][:5]


def _sample(
    term: str,
    token: str,
    deadline: float,
    found: dict[str, dict[str, Any]],
    limit: int = _MAX_ALBUMS,
) -> None:
    """Add the exact labels of albums one Spotify label search returns."""
    rows, _total, _done, _reason = label_search._crawl(
        term, None, token, deadline
    )
    albums = list(rows.values())[:limit]

    def read(row: dict[str, Any]) -> tuple[dict[str, Any], str]:
        try:
            meta = label_catalog.album_metadata(row['album_id'])
        except ValueError:
            return row, ''
        return row, meta.get('label', '').strip()

    with ThreadPoolExecutor(max_workers=8) as pool:
        for row, label in pool.map(read, albums):
            if time.monotonic() > deadline or not label:
                continue
            key = label_search.label_key(label)
            entry = found.setdefault(
                key,
                {
                    'names': Counter(),
                    'artists': Counter(),
                    'n': 0,
                },
            )
            entry['names'][label] += 1
            entry['n'] += 1
            for artist in row.get('artists') or []:
                entry['artists'][artist] += 1


def _rank(
    query: str, found: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    labels = []
    for entry in found.values():
        names = entry['names']
        # Most common spelling; an all-capitals variant only wins alone.
        name = sorted(names, key=lambda n: (-names[n], n.isupper(), n))[0]
        score = _score(query, name)
        if score < _MIN_SCORE:
            continue
        artists = sorted(
            entry['artists'], key=lambda a: (-entry['artists'][a], a)
        )
        labels.append({
            'name': name,
            'releases': entry['n'],
            'artists': artists[:3],
            'score': round(score, 2),
        })
    labels.sort(key=lambda x: (-x['score'], -x['releases'], x['name']))
    return labels[:_MAX_LABELS]


@lru_cache(maxsize=128)
def _find_snapshot(query: str, half_hour: int, fuzzy: bool) -> dict[str, Any]:
    token = spotify._anonymous_token()
    if not token:
        raise ValueError('Spotify label search unavailable')
    deadline = time.monotonic() + _BUDGET_SECONDS
    found: dict[str, dict[str, Any]] = {}
    limit = _MAX_ALBUMS if fuzzy else _QUICK_ALBUMS
    _sample(query, token, deadline, found, limit)
    labels = _rank(query, found)
    corrected = False
    if fuzzy and not any(x['score'] >= _STRONG_SCORE for x in labels):
        try:
            suggestions = _musicbrainz_names(query)
        except ValueError:
            suggestions = []
        for name in suggestions:
            if time.monotonic() > deadline:
                break
            try:
                _sample(
                    label_search._plain(name), token, deadline, found, limit
                )
            except ValueError:
                continue
        ranked = _rank(query, found)
        corrected = bool(ranked) and ranked != labels
        labels = ranked
    return {'query': query, 'labels': labels, 'fuzzy': corrected}


def find(query: str, fuzzy: bool = True) -> dict[str, Any]:
    """Label candidates for loose text, best match first.

    ``fuzzy=False`` is the light mode for ordinary searches: fewer albums
    are read and MusicBrainz is never asked.
    """
    text = _clean_query(query)
    return copy.deepcopy(
        _find_snapshot(text, int(time.time() // 1800), bool(fuzzy))
    )
