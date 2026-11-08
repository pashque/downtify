"""Album-wide credits come from exact canonical entities, never commas."""
from __future__ import annotations

import base64
import json
from typing import Any

import httpx
import pytest

from downtify import spotify

ALBUM_ID = 'a' * 22
TRACK_ID = 't' * 22
NAMES = ['A$AP Rocky', 'Tyler, The Creator', 'Jozzy']
ARTIST_IDS = ['r' * 22, 'y' * 22, 'j' * 22]


def _track() -> dict[str, Any]:
    return {
        'uri': f'spotify:track:{TRACK_ID}',
        'name': 'Exact title',
        'artists': {'items': [
            {'profile': {'name': name}, 'uri': f'spotify:artist:{sid}'}
            for name, sid in zip(NAMES, ARTIST_IDS)
        ]},
    }


def _html(album: dict[str, Any]) -> str:
    state = {'entities': {'items': {f'spotify:album:{ALBUM_ID}': album}}}
    encoded = base64.b64encode(json.dumps(state).encode()).decode()
    return (
        '<meta name="music:release_date" content="2024-10-28"/>'
        f'<script id="initialState" type="text/plain">{encoded}</script>'
    )


def _resolve(
    monkeypatch: pytest.MonkeyPatch, html: str, status: int = 200,
) -> tuple[list, list]:
    embed = {
        'uri': f'spotify:album:{ALBUM_ID}', 'name': 'Exact album',
        'trackList': [
            {'uri': f'spotify:track:{TRACK_ID}', 'title': 'Exact title',
             'subtitle': ', '.join(NAMES),
             'audioPreview': {'url': 'https://p.scdn.co/mp3-preview/test'}},
            {'uri': 'spotify:track:' + 'u' * 22, 'title': 'Unlisted track',
             'subtitle': 'Earth, Wind & Fire'},
        ],
    }
    calls = []

    def fetch(kind: str, sid: str) -> dict[str, Any]:
        assert (kind, sid) == ('album', ALBUM_ID)
        return {'props': {'pageProps': {'entity': embed}}}

    def get(url: str, **kwargs: Any) -> httpx.Response:
        calls.append(url)
        assert url == f'https://open.spotify.com/album/{ALBUM_ID}'
        return httpx.Response(
            status, text=html, request=httpx.Request('GET', url)
        )

    monkeypatch.setattr(spotify, '_fetch_embed_json', fetch)
    monkeypatch.setattr(spotify.httpx, 'get', get)
    return spotify.album_tracks_from_id(ALBUM_ID), calls


@pytest.mark.parametrize('conflict', [
    'album_uri', 'album_name', 'track_uri', 'track_id', 'track_name',
    'credit_text', 'nested_album_uri', 'nested_album_name',
])
def test_conflicting_canonical_identity_never_replaces_embed_credits(
    monkeypatch: pytest.MonkeyPatch, conflict: str,
) -> None:
    track = _track()
    album = {'uri': f'spotify:album:{ALBUM_ID}', 'name': 'Exact album',
             'tracksV2': {'items': [{'track': track}]}}
    if conflict == 'album_uri':
        album['uri'] = 'spotify:album:' + 'b' * 22
    elif conflict == 'album_name':
        album['name'] = 'Exact album +'
    elif conflict == 'track_uri':
        track['uri'] = 'spotify:track:' + 'v' * 22
    elif conflict == 'track_id':
        track['id'] = 'v' * 22
    elif conflict == 'track_name':
        track['name'] = 'Exact title (Remix)'
    elif conflict == 'credit_text':
        track['artists']['items'].pop()
    else:
        track['albumOfTrack'] = {
            'uri': f'spotify:album:{ALBUM_ID}', 'name': 'Exact album',
        }
        field = 'uri' if conflict == 'nested_album_uri' else 'name'
        track['albumOfTrack'][field] = 'Different edition'
    rows, calls = _resolve(monkeypatch, _html(album))
    assert rows[0]['artists'] == [', '.join(NAMES)]
    assert rows[0]['artists_structured'] is False
    assert rows[0]['artist_ids'] == ['']
    assert len(rows) == 2
    assert len(calls) == 1


def test_structured_profile_names_ignore_malformed_values() -> None:
    assert spotify._artist_names({'artists': {'items': [
        {'profile': {'name': 'Earth, Wind & Fire'}},
        {'profile': 'not a profile'}, {'name': 42}, None,
    ]}}) == ['Earth, Wind & Fire']


@pytest.mark.parametrize('html', [
    '', '<script id="initialState">not-base64</script>',
    '<script id="initialState">bnVsbA==</script>',
])
def test_absent_or_malformed_state_preserves_all_rows(
    monkeypatch: pytest.MonkeyPatch, html: str,
) -> None:
    rows, calls = _resolve(monkeypatch, html)
    assert len(rows) == 2
    assert rows[0]['artists'] == [', '.join(NAMES)]
    assert rows[1]['artists'] == ['Earth, Wind & Fire']
    assert len(calls) == 1


def test_canonical_failure_keeps_rows_without_retrying_for_date(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows, calls = _resolve(monkeypatch, '', status=503)
    assert [row['song_id'] for row in rows] == [TRACK_ID, 'u' * 22]
    assert rows[0]['artists'] == [', '.join(NAMES)]
    assert rows[0]['artists_structured'] is False
    assert not rows[0]['release_date']
    assert rows[0]['preview_url'] == 'https://p.scdn.co/mp3-preview/test'
    assert len(calls) == 1


def test_album_recovers_ordered_structured_credits_with_one_page_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    album = {'uri': f'spotify:album:{ALBUM_ID}', 'name': 'Exact album',
             'tracksV2': {'items': [{'track': _track()}]}}
    rows, calls = _resolve(monkeypatch, _html(album))
    assert rows[0]['artists'] == NAMES
    assert rows[0]['artist_ids'] == ARTIST_IDS
    assert rows[0]['artists_structured'] is True
    assert rows[0]['artist'] == ', '.join(NAMES)
    assert calls == [f'https://open.spotify.com/album/{ALBUM_ID}']
    assert [row['song_id'] for row in rows] == [TRACK_ID, 'u' * 22]
    assert [row['track_number'] for row in rows] == [1, 2]
    assert all(row['album_id'] == ALBUM_ID for row in rows)
    assert all(row['release_date'] == '2024-10-28' for row in rows)
    assert rows[0]['preview_url'] == 'https://p.scdn.co/mp3-preview/test'
    assert rows[1]['artists'] == ['Earth, Wind & Fire']
    assert rows[1]['artists_structured'] is False
