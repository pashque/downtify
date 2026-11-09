"""Optional, exact-edition Spotify label metadata for release headers."""

from __future__ import annotations

import json
import re
import time
from datetime import date
from functools import lru_cache

import httpx

from . import spotify

# Public web-player getAlbum query, verified against the shipped web bundle.
_ALBUM_HASH = (
    '0b6ce3511e1b02e4a40fa95440f992acbe85080eb308af9194322d708fc1914f'
)


def album_label(album_id: str) -> str:
    """Return Spotify's label field; unknown stays unknown, never copyright."""
    return album_metadata(album_id)['label']


def album_metadata(album_id: str) -> dict[str, str]:
    """Exact-edition label/date; return a copy of bounded cached metadata."""
    if not re.fullmatch(r'[A-Za-z0-9]{22}', album_id):
        raise ValueError('Invalid Spotify album ID')
    return dict(_album_label_cached(album_id, int(time.time() // 3600)))


@lru_cache(maxsize=4096)
def _album_label_cached(album_id: str, hour: int) -> dict[str, str]:
    token = spotify._anonymous_token()
    if not token:
        raise ValueError('Spotify label metadata unavailable')
    try:
        result = httpx.get(
            spotify._PARTNER_API,
            params={
                'operationName': 'getAlbum',
                'variables': json.dumps({
                    'uri': f'spotify:album:{album_id}',
                    'offset': 0,
                    'limit': 1,
                    'locale': '',
                }),
                'extensions': json.dumps({
                    'persistedQuery': {
                        'version': 1,
                        'sha256Hash': _ALBUM_HASH,
                    }
                }),
            },
            headers={
                'Authorization': f'Bearer {token}',
                'User-Agent': spotify._USER_AGENT,
                'app-platform': 'WebPlayer',
            },
            timeout=15,
        )
        result.raise_for_status()
        payload = result.json()
        album = (payload.get('data') or {}).get('albumUnion')
        if payload.get('errors') or not isinstance(album, dict):
            raise ValueError('Unavailable Spotify album')
        if album.get('uri') != f'spotify:album:{album_id}':
            raise ValueError('Spotify album identity mismatch')
        label = album.get('label')
        release_date = ''
        info = album.get('date') or {}
        if isinstance(info, dict):
            iso = str(info.get('isoString') or '')[:10]
            try:
                date.fromisoformat(iso)
                length = {'DAY': 10, 'MONTH': 7, 'YEAR': 4}.get(
                    str(info.get('precision') or '')
                )
                release_date = iso[:length] if length else ''
            except ValueError:
                pass
        return {
            'album_id': album_id,
            'label': label.strip() if isinstance(label, str) else '',
            'release_date': release_date,
        }
    except (httpx.HTTPError, ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Spotify label metadata unavailable') from exc
