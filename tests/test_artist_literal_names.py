"""Artist identity survives tag reads, listing and cache without rewriting music."""
from unittest.mock import patch

import pytest
from mutagen.id3 import ID3, TALB, TIT2, TPE1, TPE2, TXXX

from downtify.library_metadata import read_audio_metadata
from downtify.library_catalog import LibraryContext, list_library_entries
from downtify.library_metadata_cache import LibraryMetadataCache


def _track(tmp_path, artist='Tyler, The Creator', artists=None, album_artist=''):
    path = tmp_path / 'track.mp3'
    tags = ID3()
    tags.add(TIT2(encoding=3, text=['EARFQUAKE']))
    tags.add(TALB(encoding=3, text=['IGOR']))
    tags.add(TPE1(encoding=3, text=[artist]))
    if album_artist:
        tags.add(TPE2(encoding=3, text=[album_artist]))
    if artists is not None:
        tags.add(TXXX(encoding=3, desc='ARTISTS', text=artists))
    tags.save(path, v2_version=4)
    return path


@pytest.mark.parametrize('artist,expected', [
    ('Tyler, The Creator', ['Tyler, The Creator']),
    ('AC/DC', ['AC/DC']),
    (r'A\B', [r'A\B']),
    ('Earth, Wind & Fire; Guest/Name', ['Earth, Wind & Fire', 'Guest/Name']),
])
def test_unstructured_artist_only_splits_legacy_semicolons(tmp_path, artist, expected):
    path = _track(tmp_path, artist=artist)
    before = path.read_bytes()
    assert read_audio_metadata(path)['artists'] == expected
    assert path.read_bytes() == before


@pytest.mark.parametrize('credits,album_artist,expected', [
    (['Tyler', 'The Creator'], 'Tyler, The Creator', ['Tyler, The Creator']),
    (['Tyler', 'The Creator', 'Daniel Caesar'], 'Tyler, The Creator',
     ['Tyler, The Creator', 'Daniel Caesar']),
    (['Guest', 'Tyler', 'The Creator'], 'Tyler, The Creator',
     ['Guest', 'Tyler, The Creator']),
    (['Tyler, The Creator', 'Frank Ocean'], 'Tyler, The Creator',
     ['Tyler, The Creator', 'Frank Ocean']),
    (['Tyler', 'The Creator'], 'A$AP Rocky', ['Tyler', 'The Creator']),
    (['Tyler', 'The Creator'], 'tyler, the creator', ['Tyler', 'The Creator']),
])
def test_reconcile_only_exact_adjacent_album_artist(tmp_path, credits, album_artist, expected):
    path = _track(tmp_path, artists=credits, album_artist=album_artist)
    before = path.read_bytes()
    assert read_audio_metadata(path)['artists'] == expected
    assert path.read_bytes() == before


@pytest.mark.parametrize('credits', [None, ['Tyler, The Creator', 'Frank Ocean'], ['A; B', 'Guest']])
def test_listing_cold_and_warm_cache_keeps_exact_credits(tmp_path, credits):
    path = _track(tmp_path, artists=credits)
    expected = credits or ['Tyler, The Creator']
    before = path.read_bytes()
    for cache in (None, LibraryMetadataCache(tmp_path / 'metadata.db')):
        ctx = LibraryContext(download_dir=tmp_path, metadata_cache=cache)
        assert list_library_entries(ctx)[0]['artists'] == expected
        if cache:
            with patch('downtify.library_metadata_cache.library_entry_for_file',
                       side_effect=AssertionError('cache hit must not read tags')):
                assert list_library_entries(ctx)[0]['artists'] == expected
    assert path.read_bytes() == before


def test_v6_cache_rereads_even_when_stat_unchanged(tmp_path):
    path = _track(tmp_path, artists=['Tyler', 'The Creator', 'Daniel Caesar'],
                  album_artist='Tyler, The Creator')
    cache = LibraryMetadataCache(tmp_path / 'metadata.db')
    cache.get_entry(path.name, path)
    with cache._connect() as conn:
        conn.execute("UPDATE library_metadata SET meta_version=6, artist='Tyler; The Creator; Daniel Caesar'")
    from downtify.library_metadata import library_entry_for_file
    with patch('downtify.library_metadata_cache.library_entry_for_file',
               wraps=library_entry_for_file) as read:
        entry = cache.get_entry(path.name, path)
        assert read.call_count == 1
    assert entry['artist'] == 'Tyler, The Creator; Daniel Caesar'
    assert entry['artists'] == ['Tyler, The Creator', 'Daniel Caesar']


@pytest.mark.parametrize('subtitle', ['Tyler, The Creator', 'Earth, Wind & Fire', 'A，B'])
def test_spotify_flat_subtitle_is_opaque(tmp_path, subtitle):
    from downtify import spotify
    row = spotify._track_dict({'title': 'Song', 'subtitle': subtitle}, track_id='track')
    assert row['artists'] == [subtitle]


def test_spotify_wrapper_structured_credits_beat_flat_subtitle():
    from downtify import spotify
    credits = ['Tyler, The Creator', 'Frank Ocean']
    row = spotify._embed_row_track({
        'track': {'id': 'track', 'title': 'She', 'subtitle': 'Tyler, The Creator, Frank Ocean'},
        'artists': [{'name': name} for name in credits],
    })
    assert spotify._track_dict(row, track_id='track')['artists'] == credits


def test_spotify_inner_structured_credits_still_win():
    from downtify import spotify
    row = spotify._embed_row_track({
        'track': {'id': 'track', 'artists': [{'name': 'Tyler, The Creator'}, {'name': 'Frank Ocean'}]},
        'artists': [{'name': 'Wrong Artist'}], 'subtitle': 'Wrong, Subtitle',
    })
    assert spotify._track_dict(row, track_id='track')['artists'] == ['Tyler, The Creator', 'Frank Ocean']


def test_catalog_song_key_does_not_truncate_literal_name():
    from downtify.library_catalog import song_key
    assert song_key('Tyler, The Creator', 'She') != song_key('Tyler', 'She')
    assert song_key('Earth, Wind & Fire; Guest', 'September') == song_key('Earth, Wind & Fire', 'September')
    assert song_key('Simon & Garfunkel', 'Sound') != song_key('Simon', 'Sound')


def test_catalog_grouping_prefers_structured_lead_artist():
    from downtify.library_catalog import album_artist_of
    assert album_artist_of({'artist': 'A; B; Guest', 'artists': ['A; B', 'Guest']}) == 'A; B'


def test_catalog_lookup_prefers_structured_credits_over_display(tmp_path):
    from downtify.library_catalog import lookup_library_songs
    path = _track(tmp_path, artists=['Tyler, The Creator', 'Frank Ocean'])
    ctx = LibraryContext(download_dir=tmp_path)
    songs = [{'name': 'EARFQUAKE', 'artist': 'Tyler, The Creator, Frank Ocean',
              'artists': ['Tyler, The Creator', 'Frank Ocean']}]
    assert [entry['file'] for entry in lookup_library_songs(ctx, songs)] == [path.name]


