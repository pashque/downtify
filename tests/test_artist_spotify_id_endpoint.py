"""Clickable link-page artists resolve to a Spotify artist id by exact name."""
import pytest
from fastapi import HTTPException
from downtify import api, spotify


def test_returns_exact_spotify_artist(monkeypatch):
    monkeypatch.setattr(spotify, 'search_artist_by_name', lambda n: {'id': 'D' * 22, 'name': 'Drake'})
    assert api.artist_spotify_id_endpoint(' Drake ') == {'id': 'D' * 22, 'name': 'Drake'}


@pytest.mark.parametrize('found', [None, {'id': 'bad'}, RuntimeError('down')])
def test_unknown_or_failing_lookup_is_404(monkeypatch, found):
    def lookup(name):
        if isinstance(found, Exception):
            raise found
        return found
    monkeypatch.setattr(spotify, 'search_artist_by_name', lookup)
    with pytest.raises(HTTPException) as err:
        api.artist_spotify_id_endpoint('Nobody')
    assert err.value.status_code == 404


def test_route_is_open_to_signed_in_clients():
    from downtify import auth
    assert auth.rule_for('GET', '/api/artists/spotify_id') == auth.CLIENT
