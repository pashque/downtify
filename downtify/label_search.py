"""Page Spotify's label search; completeness is scoped to exposed results."""

from __future__ import annotations

import copy
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Any

import httpx

from . import label_catalog, spotify

_SEARCH_HASH = (
    '202cb3305e31e5a0767ba7925f28bd728cf8f8b0217e6da43909056071cd70e9'
)
_PAGE_SIZE = 50
_MAX_PAGES = 20
_SEARCH_CAP = 100
_FIRST_YEAR = 1950
_BUDGET_SECONDS = 45
_VERIFY_SECONDS = 180


_MARKS = dict.fromkeys(map(ord, '®™©℗'))


def _plain(name: str) -> str:
    text = unicodedata.normalize('NFKC', name.translate(_MARKS))
    return ' '.join(text.split())


def label_key(name: str) -> str:
    """Identity key: ignores trademark marks, case and spacing only."""
    return _plain(name).casefold()


class _PartialCatalog(ValueError):
    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__('Partial Spotify label search')
        self.data = data


def releases(label: str) -> dict[str, Any]:
    """All exposed pages, with explicit partial state and bounded caching."""
    raw = label.strip()
    name = _plain(raw)
    if (
        not name
        or len(raw) > 200
        or any(ord(c) < 32 or c in '\\"' for c in raw)
    ):
        raise ValueError('Invalid label name')
    try:
        result = _catalog_snapshot(name, int(time.time() // 1800))
    except _PartialCatalog as exc:
        result = exc.data
    return copy.deepcopy(result)


def _fetch_page(
    name: str,
    offset: int,
    token: str,
    timeout: float,
    years: str | None = None,
) -> dict[str, Any]:
    try:
        response = httpx.get(
            spotify._PARTNER_API,
            params={
                'operationName': 'searchAlbums',
                'variables': json.dumps({
                    'searchTerm': f'label:"{name}"'
                    + (f' year:{years}' if years else ''),
                    'offset': offset,
                    'limit': _PAGE_SIZE,
                    'numberOfTopResults': 20,
                    'includePreReleases': False,
                    'includeAlbumPreReleases': False,
                    'includeAudiobooks': True,
                    'includeAuthors': False,
                    'includeEpisodeContentRatingsV2': True,
                }),
                'extensions': json.dumps({
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': _SEARCH_HASH,
                    }
                }),
            },
            headers={
                'Authorization': f'Bearer {token}',
                'User-Agent': spotify._USER_AGENT,
                'app-platform': 'WebPlayer',
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        data = ((payload.get('data') or {}).get('searchV2') or {}).get(
            'albumsV2'
        )
        if payload.get('errors') or not isinstance(data, dict):
            raise ValueError('Invalid search response')
        if not isinstance(data.get('items'), list):
            raise ValueError('Invalid search items')
        paging = data.get('pagingInfo')
        if not isinstance(paging, dict) or 'nextOffset' not in paging:
            raise ValueError('Missing search pagination')
        return data
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Spotify label search unavailable') from exc


def _merge_page(found: dict[str, dict[str, Any]], items: list[Any]) -> bool:
    """Keep exact IDs and signal duplicates/opaque provider rows."""
    albums = spotify.search_results([{'item': item} for item in items])[
        'albums'
    ]
    unstable = False
    valid = 0
    for album in albums:
        album_id = str(album.get('id') or '')
        if not re.fullmatch(r'[A-Za-z0-9]{22}', album_id):
            continue
        valid += 1
        if album_id in found:
            unstable = True
        found[album_id] = {
            **album,
            'album_id': album_id,
            'source': 'spotify',
            'url': f'https://open.spotify.com/album/{album_id}',
        }
    return unstable or valid != len(items)


def _verify_labels(
    name: str, found: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], int, int]:
    """Search names are candidates, never proof of exact label membership."""
    matches = []
    excluded = 0
    unverified = 0
    deadline = time.monotonic() + _VERIFY_SECONDS
    candidates = list(found.values())
    with ThreadPoolExecutor(max_workers=8) as pool:
        for start in range(0, len(candidates), 8):
            if time.monotonic() >= deadline:
                unverified += len(candidates) - start
                break
            batch = candidates[start:start + 8]
            futures = [
                pool.submit(label_catalog.album_metadata, row['album_id'])
                for row in batch
            ]
            for row, future in zip(batch, futures):
                try:
                    metadata = future.result()
                except ValueError:
                    unverified += 1
                    continue
                actual = metadata.get('label', '').strip()
                if not actual:
                    unverified += 1
                elif label_key(actual) != label_key(name):
                    excluded += 1
                else:
                    matches.append({**row, **metadata})
    return matches, excluded, unverified


def _crawl(
    name: str, years: str | None, token: str, deadline: float
) -> tuple[dict[str, dict[str, Any]], int | None, bool, str]:
    """Page one search; returns found rows, reported total, done, reason."""
    offset = 0
    total = None
    found: dict[str, dict[str, Any]] = {}
    reason = 'page_limit'
    unstable = False
    for page_number in range(_MAX_PAGES):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return found, total, False, 'time_limit'
        try:
            page = _fetch_page(name, offset, token, min(15, remaining), years)
        except ValueError:
            if page_number == 0 and years is None:
                raise
            return found, total, False, 'provider_error'
        reported = page.get('totalCount')
        if (
            isinstance(reported, int)
            and not isinstance(reported, bool)
            and reported >= 0
        ):
            if total is not None and reported != total:
                unstable = True
            total = reported
        items = page['items']
        unstable = _merge_page(found, items) or unstable
        next_offset = page['pagingInfo']['nextOffset']
        if next_offset is None:
            if unstable or (total is not None and len(found) > total):
                return found, total, False, 'unstable_results'
            if total is not None and len(found) < total:
                return found, total, False, 'early_end'
            return found, total, True, ''
        if (
            not items
            or not isinstance(next_offset, int)
            or isinstance(next_offset, bool)
            or next_offset != offset + len(items)
            or next_offset <= offset
        ):
            return found, total, False, 'pagination_gap'
        offset = next_offset
    return found, total, False, reason


def _split_years(
    name: str,
    low: int,
    high: int,
    token: str,
    deadline: float,
    found: dict[str, dict[str, Any]],
) -> tuple[int, bool, str]:
    """Spotify caps a search at 100 rows; bisect release years under it."""
    years = str(low) if low == high else f'{low}-{high}'
    part, total, done, reason = _crawl(name, years, token, deadline)
    found.update(part)
    seen = total or 0
    if done and seen < _SEARCH_CAP:
        return seen, True, ''
    if not done and reason != 'unstable_results' or low == high:
        return seen, False, reason or 'year_limit'
    middle = (low + high) // 2
    first = _split_years(name, low, middle, token, deadline, found)
    second = _split_years(name, middle + 1, high, token, deadline, found)
    return (
        first[0] + second[0],
        first[1] and second[1],
        first[2] or second[2],
    )


@lru_cache(maxsize=32)
def _catalog_snapshot(name: str, half_hour: int) -> dict[str, Any]:
    token = spotify._anonymous_token()
    if not token:
        raise ValueError('Spotify label search unavailable')
    deadline = time.monotonic() + _BUDGET_SECONDS
    found, total, complete, reason = _crawl(name, None, token, deadline)
    if complete and total is not None and total >= _SEARCH_CAP:
        found = {}
        total, complete, reason = _split_years(
            name, _FIRST_YEAR, time.gmtime().tm_year + 1, token, deadline,
            found,
        )
    return _finish(name, found, total, complete, reason)


def _finish(
    name: str,
    found: dict[str, dict[str, Any]],
    total: int | None,
    complete: bool,
    reason: str,
) -> dict[str, Any]:
    matches, excluded, unverified = _verify_labels(name, found)
    self_released = 0
    if any(_self_released(row, name) for row in matches) and _roster_label(
        name, int(time.time() // 1800)
    ):
        kept = [row for row in matches if not _self_released(row, name)]
        self_released = len(matches) - len(kept)
        matches = kept
    if unverified:
        complete = False
        reason = reason or 'metadata_unavailable'
    result = {
        'self_released': self_released,
        'label': name,
        'releases': sorted(
            matches,
            key=lambda row: str(
                row.get('release_date') or row.get('year') or ''
            ),
            reverse=True,
        ),
        'total': len(matches) if complete and total is not None else None,
        'search_total': total,
        'excluded': excluded,
        'unverified': unverified,
        'complete': complete,
        'partial_reason': reason,
        'scope': 'exact_spotify_label',
        'notice': (
            'Exact album-label matches only; Spotify search can omit '
            'releases.'
        ),
    }
    if not complete:
        raise _PartialCatalog(result)
    return result


def _own_name(row: dict[str, Any], name: str) -> bool:
    """True when every credited artist is named exactly like the label."""
    artists = row.get('artists') or []
    return bool(artists) and all(
        isinstance(a, str) and label_key(a) == label_key(name)
        for a in artists
    )


def _self_released(row: dict[str, Any], name: str) -> bool:
    """Artist named like the label and a title that is not label-branded.

    Distributors often copy the artist name into Spotify's label field, so
    an unrelated artist called "Frucht" looks like the label Frucht. A
    release titled after the label (``LuckyMe Advent Calendar``) is kept.
    """
    return _own_name(row, name) and label_key(name) not in label_key(
        str(row.get('name') or '')
    )


@lru_cache(maxsize=64)
def _roster_label(name: str, half_hour: int) -> bool:
    """Whether the label releases other artists, not only its own name."""
    token = spotify._anonymous_token()
    if not token:
        raise ValueError('Spotify label search unavailable')
    found, _total, _done, _reason = _crawl(
        name, None, token, time.monotonic() + 20
    )
    others = [
        row for row in found.values() if not _own_name(row, name)
    ][:25]
    for row in others:
        try:
            meta = label_catalog.album_metadata(row['album_id'])
        except ValueError:
            continue
        if label_key(meta.get('label', '')) == label_key(name):
            return True
    return False


def _clean_label(label: str) -> str:
    raw = label.strip()
    name = _plain(raw)
    if (
        not name
        or len(raw) > 200
        or any(ord(c) < 32 or c in '\\"' for c in raw)
    ):
        raise ValueError('Invalid label name')
    return name


@lru_cache(maxsize=512)
def _year_snapshot(name: str, year: int, half_hour: int) -> dict[str, Any]:
    token = spotify._anonymous_token()
    if not token:
        raise ValueError('Spotify label search unavailable')
    found, total, done, reason = _crawl(
        name, str(year), token, time.monotonic() + _BUDGET_SECONDS
    )
    if done and total is not None and total >= _SEARCH_CAP:
        done, reason = False, 'year_limit'
    matches, excluded, unverified = _verify_labels(name, found)
    self_released = 0
    if matches and any(_self_released(row, name) for row in matches):
        if _roster_label(name, half_hour):
            kept = [row for row in matches if not _self_released(row, name)]
            self_released = len(matches) - len(kept)
            matches = kept
    if unverified:
        done, reason = False, reason or 'metadata_unavailable'
    result = {
        'label': name,
        'year': year,
        'releases': sorted(
            matches,
            key=lambda row: str(row.get('release_date') or ''),
            reverse=True,
        ),
        'complete': done,
        'partial_reason': reason,
        'search_total': total,
        'excluded': excluded,
        'self_released': self_released,
        'unverified': unverified,
        'scope': 'exact_spotify_label',
    }
    if not done:
        raise _PartialCatalog(result)
    return result


def year_releases(label: str, year: Any) -> dict[str, Any]:
    """Exact-label releases of one release year, for progressive loading."""
    name = _clean_label(label)
    if (
        not isinstance(year, int)
        or isinstance(year, bool)
        or not _FIRST_YEAR <= year <= time.gmtime().tm_year + 1
    ):
        raise ValueError('Invalid year')
    try:
        result = _year_snapshot(name, year, int(time.time() // 1800))
    except _PartialCatalog as exc:
        result = exc.data
    return copy.deepcopy(result)
