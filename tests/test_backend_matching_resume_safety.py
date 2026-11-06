"""Offline edge cases for the resumed matching/identity lane."""
import pytest
from downtify import library_catalog as catalog, providers


@pytest.mark.parametrize('name', ['|', '||', '!!!'])
def test_catalog_track_ids_precede_alias_metadata(monkeypatch, name):
    row = {'file': 'right.mp3', 'song_id': 'A' * 22, 'artists': ['Alias'], 'title': 'Old Title'}
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: [row])
    found = catalog.lookup_library_songs(None, [{'song_id': 'A' * 22, 'artists': [name], 'title': 'Same Song'}])
    assert [r['file'] for r in found] == ['right.mp3']


def test_catalog_id_only_request_is_not_title_only(monkeypatch):
    row = {'file': 'right.mp3', 'song_id': 'A' * 22, 'artists': ['|||'], 'title': 'Song'}
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: [row])
    assert [r['file'] for r in catalog.lookup_library_songs(None, [{'song_id': 'A' * 22}])] == ['right.mp3']
    assert catalog.lookup_library_songs(None, [{'title': 'Song'}]) == []


def test_catalog_artist_ids_do_not_cross_provider_namespaces(monkeypatch):
    row = {'file': 'right.mp3', 'source': 'spotify', 'artist_ids': ['spotifyArtist'], 'artists': ['|||'], 'title': 'Song'}
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: [row])
    found = catalog.lookup_library_songs(None, [{'source': 'youtube', 'artist_ids': ['UCyoutube'], 'artists': ['|||'], 'title': 'Song'}])
    assert [r['file'] for r in found] == ['right.mp3']


def test_spotify_structured_artist_ids_are_not_youtube_ids():
    artists = providers._matching_artists({'source': 'spotify', 'artists': [{'name': '|||', 'id': 'spotifyArtist'}]})
    assert providers._artists_overlap(artists, {'artists': [{'name': '|||', 'id': 'UCyoutube'}]})


def test_upload_inferred_credit_cannot_inherit_uploader_id():
    row = {'videoId': 'rightvideo1', 'title': '||| - Song', 'artists': [{'name': 'Uploader', 'id': 'UCuploader'}], 'videoType': 'MUSIC_VIDEO_TYPE_OMV'}
    song = providers._playlist_track_song(row)
    assert song['artists'] == ['|||']
    assert not any(song.get('artist_ids') or [])


@pytest.mark.parametrize('artist', [[], [''], ['  ', 'Guest']])
def test_album_matching_never_accepts_no_primary_artist(monkeypatch, artist):
    monkeypatch.setattr(providers, '_album_browse_id_from_search', lambda *a: 'album')
    monkeypatch.setattr(providers, '_cached_album_tracks_and_count', lambda *a: ([{'videoId': 'wrongvideo1', 'title': 'Song', 'artists': [{'name': 'Guest'}]}], 1))
    assert providers._find_match_via_album({'artists': artist, 'name': 'Song', 'album_name': 'Album'}) == (None, None)


@pytest.mark.parametrize('artists', [[], [''], ['  ']])
def test_official_audio_swap_without_artist_keeps_original(monkeypatch, artists):
    monkeypatch.setattr(providers, '_ytm', lambda: type('Ytm', (), {'search': lambda *a, **kw: [{'videoId': 'wrongvideo1', 'title': 'Song', 'artists': [{'name': 'Other'}], 'videoType': 'MUSIC_VIDEO_TYPE_ATV'}]})())
    providers._omv_preference_cache.clear()
    assert providers._prefer_official_audio_track('original', 180, 'Song', artists, 'MUSIC_VIDEO_TYPE_OMV') == ('original', 180)


def test_official_audio_swap_does_not_revive_negative_variant(monkeypatch):
    monkeypatch.setattr(providers, '_ytm', lambda: type('Ytm', (), {'search': lambda *a, **kw: [{'videoId': 'wrongvideo1', 'title': 'Song (Nightcore)', 'artists': [{'name': '|||'}], 'videoType': 'MUSIC_VIDEO_TYPE_ATV'}]})())
    providers._omv_preference_cache.clear()
    assert providers._prefer_official_audio_track('original', 180, 'Song', ['|||'], 'MUSIC_VIDEO_TYPE_OMV') == ('original', 180)


def test_mobile_structured_object_credits_keep_boundaries():
    from downtify import library_sync
    row = library_sync.public_row({'artist': 'Flattened, Guest', 'artists': [{'name': 'Earth, Wind & Fire', 'id': 'a'}, {'name': 'Guest'}]})
    assert row['artists'] == ['Earth, Wind & Fire', 'Guest']
    assert row['album_artist'] == 'Earth, Wind & Fire'
