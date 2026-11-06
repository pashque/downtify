import pytest
from fastapi import HTTPException
from downtify import api, spotify, providers

@pytest.fixture(autouse=True)
def clear():
    api._YTM_LINK_CACHE.clear()

@pytest.mark.parametrize('name', ['Tyler, The Creator', 'Earth, Wind & Fire', 'AC/DC'])
def test_literal_album_artist(name, monkeypatch):
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [{'id': 'A'*22, 'name': 'Record', 'artists': [name]}]})
    assert api.spotify_link_endpoint('album', name, 'Record')['url'].endswith('A'*22)
    monkeypatch.setattr(providers, 'search_albums', lambda *a, **kw: [{'name': 'Record', 'artists': [name], 'url': 'https://music.youtube.com/browse/MPRE_ok'}])
    assert api.youtube_music_link_endpoint('album', name, 'Record', 0)['url'].endswith('MPRE_ok')

def test_track_never_guesses_comma_boundaries(monkeypatch):
    seen = []
    monkeypatch.setattr(providers, 'find_match', lambda song: seen.append(song) or ('abcDEF12345', {}))
    api.youtube_music_link_endpoint('track', 'Earth, Wind & Fire', 'Song', 2)
    assert seen[0]['artists'] == ['Earth, Wind & Fire']

def test_structured_credits_and_exact_ids(monkeypatch):
    monkeypatch.setattr(spotify, 'search', lambda *a: pytest.fail('exact id must not search'))
    assert api.spotify_link_endpoint('track', '', 'Title', source_id='T'*22)['url'].endswith('T'*22)
    assert api.youtube_music_link_endpoint('track', '', 'Title', 0, source_id='abcDEF12345')['url'].endswith('abcDEF12345')
    seen = []
    monkeypatch.setattr(providers, 'find_match', lambda song: seen.append(song) or ('abcDEF12345', {}))
    api.youtube_music_link_endpoint('track', 'ignored', 'Title', 0, artists=['Tyler, The Creator', 'Guest'])
    assert seen[0]['artists'] == ['Tyler, The Creator', 'Guest']


def test_structured_album_query_uses_credit_names(monkeypatch):
    queries = []
    monkeypatch.setattr(spotify, 'search', lambda q: queries.append(q) or {'albums':[{'id':'A'*22, 'name':'Record', 'artists':['Tyler, The Creator']}]})
    api.spotify_link_endpoint('album', '', 'Record', artists=['Tyler, The Creator'])
    assert queries == ['Tyler, The Creator Record']
