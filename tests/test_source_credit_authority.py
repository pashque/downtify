"""Structured provider credits must not be replaced by weaker cached subtitles."""
from downtify.artist_credit_repair import source_credits
from downtify.playlist_spotify_cache import PlaylistSpotifyCache


def test_fresh_structured_credits_win_over_conflicting_cached_boundaries(tmp_path):
    cache = PlaylistSpotifyCache(tmp_path / 'cache.db')
    tid = 'T' * 22
    cache.store_track(tid, {
        'song_id': tid, 'name': 'Collaboration',
        'artists': ['Tyler', 'The Creator', 'Jozzy'],
        'artists_structured': False,
    })
    row = {
        'song_id': tid, 'name': 'Collaboration',
        'artists': ['Tyler, The Creator', 'Jozzy'],
        'artist_ids': ['A' * 22, 'B' * 22],
        'artists_structured': True,
    }
    assert source_credits([row], cache) == [row]


def test_opaque_cache_is_not_evidence_of_artist_boundaries(tmp_path):
    cache = PlaylistSpotifyCache(tmp_path / 'cache.db')
    tid = 'T' * 22
    cache.store_track(tid, {
        'song_id': tid, 'name': 'Collaboration',
        'artists': ['Tyler', 'The Creator', 'Jozzy'],
        'artists_structured': False,
    })
    row = {
        'song_id': tid, 'name': 'Collaboration',
        'artists': ['Tyler, The Creator, Jozzy'],
        'artists_structured': False,
    }
    assert source_credits([row], cache) == [row]
