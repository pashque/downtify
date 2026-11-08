"""Only exact visible library provenance may expand a source album."""
import pytest
from fastapi import HTTPException

from downtify import api
from downtify.track_index import TrackIndex
from tests.test_download_modes import SONG
from tests.test_library_visibility import _request
from tests.test_library_visibility import library as library


@pytest.fixture(autouse=True)
def _no_live_version_search(monkeypatch):
    # Extra-version search must never reach the network in tests.
    from downtify import album_source
    monkeypatch.setattr(album_source, '_loose_versions', lambda *a, **k: [])


@pytest.mark.parametrize('indexed', [False, True])
def test_source_endpoint_enforces_real_hidden_album_rules(library, monkeypatch, tmp_path, indexed):
    index = TrackIndex(tmp_path / 'source-index.db')
    if indexed:
        index.register('A' * 22, 'Ana/Sun/Ana - One.mp3')
    monkeypatch.setattr(api.state, 'track_index', index)
    from downtify.library_visibility import album_key
    api.state.library_visibility.hide('album', album_key('Ana', 'Sun'))
    monkeypatch.setattr(api.spotify, 'search', lambda query: pytest.fail('hidden album search'))
    monkeypatch.setattr(api.spotify, '_album_ref_from_open_track_page', lambda tid: pytest.fail('hidden provenance'))
    with pytest.raises(HTTPException) as exc:
        api.library_album_source(_request(5), 'Ana', 'Sun')
    assert exc.value.status_code == 404


def test_source_route_allows_authenticated_library_clients():
    from downtify.auth import CLIENT, classify
    assert classify('GET', '/api/library/album/source') == CLIENT


def test_source_endpoint_expands_only_visible_owned_tracks(monkeypatch, tmp_path):
    index = TrackIndex(tmp_path / 'index.db')
    index.register_song(SONG, 'visible.mp3')
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(api, 'entries_for_request', lambda request: [dict(file='visible.mp3', album_artist='Drake', album=SONG['album_name'])])
    monkeypatch.setattr(api.spotify, '_album_ref_from_open_track_page', lambda tid: ('A' * 22, ''))
    monkeypatch.setattr(api.spotify, 'album_tracks_from_id', lambda aid: [SONG, dict(SONG, song_id='B' * 22, name='Second')])
    result = api.library_album_source(object(), 'Drake', SONG['album_name'])
    assert result['status'] == 'resolved'
    assert len(result['tracks']) == 2
    assert result['url'] == 'https://open.spotify.com/album/' + 'A' * 22


@pytest.mark.parametrize('album_id', ['bad', 'https://open.spotify.com/album/' + 'A' * 22])
def test_malformed_album_identity_is_never_normalized(monkeypatch, tmp_path, album_id):
    from downtify.album_source import resolve_album_source
    index = TrackIndex(tmp_path / 'index.db')
    index.register_song(SONG, 'local.mp3')
    monkeypatch.setattr(api.spotify, '_album_ref_from_open_track_page', lambda tid: (album_id, ''))
    monkeypatch.setattr(api.spotify, 'album_tracks_from_id', lambda aid: [SONG])
    assert resolve_album_source([{'file': 'local.mp3'}], SONG['album_name'], index) == {'status': 'unavailable', 'tracks': []}


@pytest.mark.parametrize('source_tracks', [[], [dict(SONG, album_name='Dark Lane Demo Tapes (Deluxe)')], [dict(SONG, song_id='C' * 22)]])
def test_different_edition_or_missing_known_identity_is_unavailable(monkeypatch, tmp_path, source_tracks):
    from downtify.album_source import resolve_album_source
    index = TrackIndex(tmp_path / 'index.db')
    index.register_song(SONG, 'local.mp3')
    monkeypatch.setattr(api.spotify, '_album_ref_from_open_track_page', lambda tid: ('A' * 22, ''))
    monkeypatch.setattr(api.spotify, 'album_tracks_from_id', lambda aid: source_tracks)
    assert resolve_album_source([{'file': 'local.mp3'}], SONG['album_name'], index) == {'status': 'unavailable', 'tracks': []}


def test_unknown_provenance_never_searches_network(monkeypatch, tmp_path):
    from downtify.album_source import resolve_album_source
    monkeypatch.setattr(api.spotify, 'search', lambda query: pytest.fail('insufficient metadata search'))
    monkeypatch.setattr(api.spotify, '_album_ref_from_open_track_page', lambda tid: pytest.fail('no known identity'))
    assert resolve_album_source([{'file': 'unknown.mp3'}], SONG['album_name'], TrackIndex(tmp_path / 'index.db'))['status'] == 'unavailable'


def test_invisible_album_cannot_trigger_source_network(monkeypatch):
    monkeypatch.setattr(api, 'entries_for_request', lambda request: [])
    monkeypatch.setattr(api.spotify, '_album_ref_from_open_track_page', lambda tid: pytest.fail('private provenance leaked'))
    with pytest.raises(HTTPException) as exc:
        api.library_album_source(object(), 'Drake', SONG['album_name'])
    assert exc.value.status_code == 404
