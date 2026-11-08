"""An opened Spotify release outranks local bindings without changing them."""
import asyncio

import pytest

from downtify import album_source, api, spotify
from downtify.auth import CLIENT, classify
from downtify.track_index import TrackIndex
from tests.test_library_visibility import _request

SELECTED = '53wStBoNAK1lhbfbuCJ2zd'
OWNED = '5ZscjYDLx3luVuDWPMkT3x'


@pytest.fixture
def source(monkeypatch):
    rows = [dict(file='owned.mp3', album_artist='+++', album='Album +')]
    tracks = [dict(song_id='S' * 22, name='One', artists=['+++'], album_artist='+++',
                   album_name='Album +', release_date='2021-10-22')]
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: tracks)
    monkeypatch.setattr(album_source, '_loose_versions', lambda *a, **k: [])
    return rows, tracks


def test_explicit_release_does_not_require_owned_ids_or_rebind_files(source):
    rows, tracks = source
    result = album_source.resolve_album_source(rows, 'Album +', None, SELECTED)
    assert result['status'] == 'resolved'
    assert result['edition'] == SELECTED
    assert result['tracks'] == tracks
    assert result['tracks'][0]['release_date'] == '2021-10-22'
    assert result['local_matches'] == {}
    assert rows == [dict(file='owned.mp3', album_artist='+++', album='Album +')]


@pytest.mark.parametrize('edition', ['bad', '', 'https://open.spotify.com/album/' + SELECTED])
def test_invalid_explicit_selection_is_unavailable(source, edition):
    rows, _ = source
    assert album_source.resolve_album_source(rows, 'Album +', None, edition) == {'status': 'unavailable', 'tracks': []}


@pytest.mark.parametrize('change', [{'album_name': 'Album'}, {'album_artist': 'Other'}, {'album_name': 'Other'}])
def test_mismatched_explicit_selection_is_unavailable(source, change):
    rows, tracks = source
    tracks[0].update(change)
    assert album_source.resolve_album_source(rows, 'Album +', None, SELECTED) == {'status': 'unavailable', 'tracks': []}


def test_unknown_menu_selection_never_defaults_to_owned():
    candidate = dict(id=OWNED, tracks=[dict(song_id='owned')], local_matches={}, url='owned')
    assert album_source._with_editions([candidate], SELECTED, owned_ids={'owned'}) == {'status': 'unavailable', 'tracks': []}


def test_preference_is_persistent_user_scoped_and_literal(tmp_path):
    path = tmp_path / 'index.db'
    index = TrackIndex(path)
    index.set_album_preference(5, '+++', 'Album +', SELECTED)
    again = TrackIndex(path)
    assert again.album_preference(5, '+++', 'Album +') == SELECTED
    assert again.album_preference(6, '+++', 'Album +') is None
    assert again.album_preference(5, '+++', 'Album') is None


def test_source_preference_api_honors_selection_without_rebinding(source, monkeypatch, tmp_path):

    rows, tracks = source
    index = TrackIndex(tmp_path / 'index.db')
    index.register('O' * 22, 'owned.mp3')
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(api, 'entries_for_request', lambda request: rows)
    body = {'artist': '+++', 'title': 'Album +', 'edition': SELECTED}
    result = asyncio.run(api.set_library_album_source_preference(_request(5, body=body)))
    assert result['edition'] == SELECTED
    assert api.library_album_source(_request(5), '+++', 'Album +')['edition'] == SELECTED
    assert index.spotify_id_for_filename('owned.mp3') == 'O' * 22
    assert classify('POST', '/api/library/album/source') == CLIENT
