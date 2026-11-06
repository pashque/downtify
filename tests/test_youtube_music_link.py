"""Open on YouTube Music resolves to the real track/album page, never a search."""
import pytest
from fastapi import HTTPException
from downtify import api, providers, auth


@pytest.fixture(autouse=True)
def _fresh_cache():
    api._YTM_LINK_CACHE.clear()


def test_track_resolves_to_watch_page(monkeypatch):
    seen = []
    monkeypatch.setattr(providers, 'find_match', lambda song: seen.append(song) or ('abcDEF12345', {}))
    out = api.youtube_music_link_endpoint('track', 'Drake, 21 Savage', 'Rich Flex', 239, artists=['Drake', '21 Savage'])
    assert out == {'url': 'https://music.youtube.com/watch?v=abcDEF12345'}
    assert seen[0]['artists'] == ['Drake', '21 Savage'] and seen[0]['duration'] == 239


def test_album_resolves_to_browse_page_with_matching_title_and_artist(monkeypatch):
    monkeypatch.setattr(providers, 'search_albums', lambda q, limit=10: [
        {'name': 'Her Loss (Remix)', 'artists': ['Drake'], 'url': 'https://music.youtube.com/browse/X'},
        {'name': 'Her Loss', 'artists': ['Someone'], 'url': 'https://music.youtube.com/browse/Y'},
        {'name': 'Her Loss', 'artists': ['Drake', '21 Savage'], 'url': 'https://music.youtube.com/browse/MPREb_ok'},
    ])
    assert api.youtube_music_link_endpoint('album', 'Drake', 'Her Loss', 0) == {'url': 'https://music.youtube.com/browse/MPREb_ok'}


@pytest.mark.parametrize('kind', ['track', 'album'])
def test_no_match_is_404_not_a_search_url(monkeypatch, kind):
    monkeypatch.setattr(providers, 'find_match', lambda song: (None, None))
    monkeypatch.setattr(providers, 'search_albums', lambda q, limit=10: [])
    with pytest.raises(HTTPException) as err:
        api.youtube_music_link_endpoint(kind, 'Drake', 'Nothing', 0)
    assert err.value.status_code == 404


def test_route_open_to_signed_in_clients():
    assert auth.rule_for('GET', '/api/youtube_music/link') == auth.CLIENT
    assert auth.rule_for('GET', '/api/spotify/link') == auth.CLIENT


def test_spotify_album_link_needs_exact_title_and_lead_artist(monkeypatch):
    from downtify import spotify
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        {'id': 'R' * 22, 'name': 'Her Loss (Remix)', 'artists': ['Drake']},
        {'id': 'O' * 22, 'name': 'Her Loss', 'artists': ['Other']},
        {'id': 'H' * 22, 'name': 'Her Loss', 'artists': ['Drake', '21 Savage']}]})
    assert api.spotify_link_endpoint('album', 'Drake, 21 Savage', 'Her Loss', artists=['Drake', '21 Savage']) == {'url': 'https://open.spotify.com/album/' + 'H' * 22}
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': []})
    with pytest.raises(HTTPException):
        api.spotify_link_endpoint('album', 'Nobody', 'Nothing')


def test_spotify_track_link_opens_the_track_page_of_its_album(monkeypatch):
    from downtify import spotify
    api._YTM_LINK_CACHE.clear()
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        {'id': 'A' * 22, 'name': "Don't Be Dumb", 'artists': ['A$AP Rocky']}]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda album_id: [
        {'song_id': 'X' * 22, 'name': 'SWAT TEAM (Remix)', 'url': 'https://open.spotify.com/track/' + 'X' * 22},
        {'song_id': 'T' * 22, 'name': 'SWAT TEAM', 'url': 'https://open.spotify.com/track/' + 'T' * 22},
    ])
    got = api.spotify_link_endpoint('track', 'A$AP Rocky', 'SWAT TEAM', "Don't Be Dumb")
    assert got == {'url': 'https://open.spotify.com/track/' + 'T' * 22}


def test_spotify_track_link_without_exact_track_is_404_not_a_search(monkeypatch):
    from downtify import spotify
    api._YTM_LINK_CACHE.clear()
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        {'id': 'A' * 22, 'name': 'Album', 'artists': ['Artist']}]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda album_id: [
        {'song_id': 'X' * 22, 'name': 'Other', 'url': 'https://open.spotify.com/track/' + 'X' * 22}])
    with pytest.raises(HTTPException) as err:
        api.spotify_link_endpoint('track', 'Artist', 'Missing', 'Album')
    assert err.value.status_code == 404
    with pytest.raises(HTTPException):
        api.spotify_link_endpoint('track', 'Artist', 'Missing', '')
