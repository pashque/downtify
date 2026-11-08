"""Offline regressions for artist identity at library and audio boundaries."""
import pytest

from downtify import library_catalog as catalog
from downtify import library_sync as sync
from downtify import providers
from downtify.track_index import TrackIndex


@pytest.mark.parametrize('artist', ['!!!', '+++', '|', 'A/B', 'A&B', 'A B', '東京', 'Straße', 'Strasse'])
def test_song_key_keeps_artist_identity(artist):
    assert catalog.song_key(artist, 'Same Song').rsplit('|', 1)[0] == artist.lower()


def test_song_key_nfkc_whitespace_only():
    assert catalog.song_key('  Ａ/Ｂ\t Band ', 'Song') == catalog.song_key('a/b band', 'Song')
    assert catalog.song_key('Beyoncé', 'Song') != catalog.song_key('Beyonce', 'Song')


def test_lookup_prefers_structured_stored_artist(monkeypatch):
    entries = [
        {'file': 'wrong.mp3', 'title': 'Same Song', 'artist': '+++', 'artists': ['+++']},
        {'file': 'right.mp3', 'title': 'Same Song', 'artist': 'flattened, guest', 'artists': ['|||', 'Guest']},
    ]
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: entries)
    assert catalog.lookup_library_songs(None, [{'title': 'Same Song', 'artists': ['|||']}]) == [entries[1]]


def test_lookup_rejects_missing_artist(monkeypatch):
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: [
        {'file': 'unknown.mp3', 'title': 'Same Song', 'artist': ''},
    ])
    assert catalog.lookup_library_songs(None, [{'title': 'Same Song'}]) == []


@pytest.mark.parametrize('name', ['Earth, Wind & Fire', 'A / B', '|||', '+++'])
def test_mobile_sync_keeps_whole_legacy_names(name):
    assert sync.public_row({'artist': name, 'album': 'Album'})['artists'] == [name]


def test_mobile_sync_uses_structured_credit_for_grouping():
    row = sync.public_row({'artist': 'Wrong, Guest', 'artists': ['|||', 'Guest'], 'album': 'Album'})
    assert row['artists'] == ['|||', 'Guest']
    assert row['album_artist'] == '|||'
    assert row['artist_id'] == sync.grouping_keys({'artist': '|||'})['artist_id']
    assert sync.split_artists('Earth, Wind & Fire; Guest') == ['Earth, Wind & Fire', 'Guest']


def _hit(artist, video='rightvideo01', artist_id=None):
    credit = {'name': artist}
    if artist_id:
        credit['id'] = artist_id
    return {'videoId': video, 'title': 'Same Song', 'artists': [credit], 'duration_seconds': 180, 'resultType': 'song'}


@pytest.mark.parametrize('artist', ['|', '||', '|||', '!!!', '+++', '東京'])
def test_find_match_never_substitutes_symbol_artist(monkeypatch, artist):
    class FakeYtm:
        def search(self, *args, **kwargs):
            return [_hit('Unrelated Artist', 'wrongvideo1'), _hit(artist)]
    monkeypatch.setattr(providers, '_ytm', lambda: FakeYtm())
    monkeypatch.setattr(providers, '_youtube_search', lambda *a: [])
    assert providers.find_match({'artists': [artist], 'name': 'Same Song', 'duration': 180})[0] == 'rightvideo01'


def test_find_match_album_fallback_never_title_only(monkeypatch):
    class FakeYtm:
        def search(self, *args, **kwargs):
            return []
    monkeypatch.setattr(providers, '_ytm', lambda: FakeYtm())
    monkeypatch.setattr(providers, '_youtube_search', lambda *a: [])
    monkeypatch.setattr(providers, '_album_browse_id_from_search', lambda *a: 'album')
    monkeypatch.setattr(providers, '_cached_album_tracks_and_count', lambda *a: ([_hit('Unrelated Artist')], 1))
    assert providers.find_match({'artists': ['|||'], 'name': 'Same Song', 'album_name': 'Album'}) == (None, None)


@pytest.mark.parametrize(('target', 'candidate'), [('A', 'A&B'), ('B', 'A&B'), ('+', '+++'), ('Straße', 'Strasse'), ('|||', 'Normal')])
def test_provider_credit_tokens_do_not_invent_identity(target, candidate):
    assert not providers._artists_overlap([target], _hit(candidate))


def test_provider_blank_artist_not_title_only():
    assert not providers._artists_overlap(['  '], _hit('Anyone'))


def test_provider_ids_authoritative_and_contradictions_rejected():
    assert not providers._artists_overlap([{'name': '|||', 'id': 'UCknown'}], _hit('|||', artist_id='UCwrong'))
    assert providers._artists_overlap([{'name': '|||', 'id': 'UCknown'}], _hit('Alias', artist_id='UCknown'))


def test_provider_features_keep_primary_not_shared_guest():
    assert not providers._artists_overlap(['|||', 'Guest'], {'artists': [{'name': 'Other'}, {'name': 'Guest'}]})
    assert providers._artists_overlap(['|||', 'Guest'], _hit('||| feat. Guest'))


@pytest.mark.parametrize(('left', 'right'), [('Song', 'Song+'), ('+', '!!!'), ('|', '||'), ('Song', 'Song (Live)'), ('Song', 'Song (Remix)')])
def test_song_key_preserves_recording_versions(left, right):
    assert catalog.song_key('Artist', left) != catalog.song_key('Artist', right)


def test_lookup_uses_batch_source_ids_and_rejects_other_recording(monkeypatch, tmp_path):
    index = TrackIndex(tmp_path / 'index.db')
    # Real canonical and stat-validated recovered identities; no provider calls.
    path = tmp_path / 'right.mp3'
    path.write_bytes(b'offline fixture')
    index.register_source_copy({'song_id': 'A' * 22}, 'right.mp3', path)
    other = tmp_path / 'wrong.mp3'
    other.write_bytes(b'offline fixture wrong')
    index.register_source_copy({'song_id': 'B' * 22}, 'wrong.mp3', other)
    entries = [{'file': p, 'artist': '|||', 'artists': ['|||'], 'title': 'Same Song'} for p in ['wrong.mp3', 'right.mp3']]
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: entries)
    calls = []
    original = index.identities_for_files

    def batch(files):
        calls.append(files)
        return original(files)
    monkeypatch.setattr(index, 'identities_for_files', batch)
    ctx = catalog.LibraryContext(tmp_path, track_index=index)
    rows = catalog.lookup_library_songs(ctx, [{'song_id': 'A' * 22, 'artists': ['|||'], 'title': 'Same Song'}])
    assert [r['file'] for r in rows] == ['right.mp3']
    assert rows[0]['spotify_track_ids'] == ['A' * 22]
    assert rows[0]['song_id'] == 'A' * 22
    assert len(calls) == 1
    assert catalog.lookup_library_songs(ctx, [{'song_id': 'C' * 22, 'artists': ['|||'], 'title': 'Same Song'}]) == []


def test_lookup_unindexed_ambiguous_album_is_not_recording_identity(monkeypatch):
    entries = [{'file': f'{album}.mp3', 'artist': '|||', 'title': 'Same Song', 'album': album} for album in ['First', 'Second']]
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: entries)
    assert catalog.lookup_library_songs(None, [{'artists': ['|||'], 'title': 'Same Song'}]) == []
    rows = catalog.lookup_library_songs(None, [{'artists': ['|||'], 'title': 'Same Song', 'album_name': 'Second'}])
    assert [r['file'] for r in rows] == ['Second.mp3']


def test_find_match_structured_symbol_ids(monkeypatch):
    class FakeYtm:
        def search(self, *a, **kw):
            return [_hit('|||', 'wrongvideo1', 'UCwrong'), _hit('Alias', 'rightvideo01', 'UCknown')]
    monkeypatch.setattr(providers, '_ytm', lambda: FakeYtm())
    monkeypatch.setattr(providers, '_youtube_search', lambda *a: [])
    assert providers.find_match({'artists': [{'name': '|||', 'id': 'UCknown'}], 'name': 'Same Song', 'duration': 180})[0] == 'rightvideo01'
    assert providers.find_match({'artists': ['|||'], 'artist_ids': ['UCknown'], 'source': 'youtube', 'name': 'Same Song', 'duration': 180})[0] == 'rightvideo01'


@pytest.mark.parametrize('artists', [[], [''], ['  ']])
def test_find_match_without_artist_safely_unmatched(monkeypatch, artists):
    class FakeYtm:
        def search(self, *a, **kw):
            return [_hit('Unrelated')]
    monkeypatch.setattr(providers, '_ytm', lambda: FakeYtm())
    monkeypatch.setattr(providers, '_youtube_search', lambda *a: [])
    assert providers.find_match({'artists': artists, 'name': 'Same Song'}) == (None, None)


def test_youtube_title_is_not_artist_evidence(monkeypatch):
    monkeypatch.setattr(providers, '_youtube_search', lambda *a: [
        {'id': 'wrongvideo1', 'title': 'Other Artist - |||', 'channel': 'Other Artist', 'duration': 180},
    ])
    assert providers.find_match_youtube_only({'artists': ['|||'], 'name': '|||', 'duration': 180}) is None


def test_provider_symbol_combined_credit_keeps_symbol_length():
    assert not providers._artists_overlap(['|'], _hit('||| feat. Guest'))
    assert providers._artists_overlap(['|||'], _hit('||| feat. Guest'))


def test_youtube_literal_comma_artist_is_not_split():
    result = providers._youtube_entry_to_result({'id': 'wrongvideo1', 'title': 'Earth, Wind & Fire - Same Song'})
    assert not providers._artists_overlap(['Earth'], result)
    assert providers._artists_overlap(['Earth, Wind & Fire'], result)


def test_lookup_rejects_known_artist_id_contradiction(monkeypatch):
    monkeypatch.setattr(catalog, 'listing_for_request', lambda *a, **kw: [
        {'file': 'wrong.mp3', 'artist': '|||', 'artists': ['|||'], 'artist_ids': ['wrong'], 'title': 'Same Song'},
    ])
    assert catalog.lookup_library_songs(None, [{'artists': ['|||'], 'artist_ids': ['right'], 'title': 'Same Song'}]) == []


@pytest.mark.parametrize(('left', 'right'), [('Song', 'Song+'), ('Song', 'Songbird'), ('+', '!!!'), ('|', '||'), ('Song', 'Song (Live)'), ('Song', 'Song (Remix)')])
def test_provider_titles_keep_distinct_recordings(left, right):
    assert not providers._titles_match(left, right)


def test_provider_search_song_preserves_authoritative_symbol_artist_id():
    song = providers._result_to_song(_hit('|||', artist_id='UCknown'))
    assert song['artists'] == ['|||']
    assert song['artist_ids'] == ['UCknown']
    assert song['source'] == 'youtube'


@pytest.mark.parametrize('album_name', ['', 'Album'])
def test_provider_never_revives_rejected_audio_variant(monkeypatch, album_name):
    row = _hit('|||')
    row['title'] = 'Same Song (Nightcore)'

    class FakeYtm:
        def search(self, *a, **kw):
            return [row]
    monkeypatch.setattr(providers, '_ytm', lambda: FakeYtm())
    monkeypatch.setattr(providers, '_youtube_search', lambda *a: [])
    monkeypatch.setattr(providers, '_album_browse_id_from_search', lambda *a: 'album')
    monkeypatch.setattr(providers, '_cached_album_tracks_and_count', lambda *a: ([row], 1))
    assert providers.find_match({'artists': ['|||'], 'name': 'Same Song', 'album_name': album_name}) == (None, None)
