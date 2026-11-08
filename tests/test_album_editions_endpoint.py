"""Exact-source edition discovery is read-only and available to signed-in clients."""
import pytest
from fastapi import HTTPException

from downtify import album_source, api, auth


def test_exact_album_editions_endpoint(monkeypatch):
    calls = []
    result = {'status': 'resolved', 'edition': 'A' * 22, 'editions': []}

    def discover(album_id):
        calls.append(album_id)
        return result
    monkeypatch.setattr(album_source, 'discover_album_editions', discover)
    endpoint = getattr(api, 'spotify_album_editions_endpoint', None)
    assert callable(endpoint), 'edition discovery route is missing'
    assert endpoint('A' * 22) == result
    assert calls == ['A' * 22]
    for invalid in ['', 'A' * 21, 'A' * 23, '!' * 22, ' ' + 'A' * 22]:
        with pytest.raises(HTTPException) as err:
            endpoint(invalid)
        assert err.value.status_code == 400
    assert calls == ['A' * 22]
    assert any(route.path == '/api/spotify/album/editions' for route in api.router.routes)
    assert auth.rule_for('GET', '/api/spotify/album/editions') == auth.CLIENT
    assert auth.rule_for('POST', '/api/spotify/album/editions') != auth.CLIENT
