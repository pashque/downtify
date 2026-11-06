"""Authoritative offline, physical multi-copy track availability."""
import asyncio
import json

import pytest
from starlette.requests import Request

from downtify import api
from downtify.auth import CLIENT, Principal, classify
from downtify.downloader import Downloader
from downtify.library_catalog import LibraryContext, list_library_entries
from downtify.library_paths_cache import invalidate_library_paths_cache, set_listing_refresh_fn
from downtify.track_index import TrackIndex
from tests.test_library_visibility import _write_track

SONG = dict(song_id='5fHrHoJKfCgBd35zwIBmUK', name='One', artists=['Ana'],
            album_artist='Ana', album_name='Sun', release_date='2020',
            track_number=1, duration=180)


def request(songs):
    async def receive():
        return {'type': 'http.request', 'body': json.dumps({'songs': songs}).encode()}
    return Request({'type': 'http', 'headers': [], 'state': {
        'principal': Principal('device', 'client', '', 1, 'admin', 'admin')}}, receive)


def locations(songs):
    return asyncio.run(api.library_locations(request(songs)))['locations']


@pytest.fixture
def env(tmp_path, monkeypatch):
    root = tmp_path / 'downloads'
    root.mkdir()
    index = TrackIndex(tmp_path / 'index.db')
    downloader = Downloader(root, folder_structure=True, playlist_use_library=False)
    ctx = LibraryContext(download_dir=root, track_index=index)
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(api.state, 'downloader', downloader)
    monkeypatch.setattr(api.state, 'library_visibility', None)
    monkeypatch.setattr(api.state, 'playlist_catalog', None)
    invalidate_library_paths_cache()
    set_listing_refresh_fn(lambda: list_library_entries(ctx))
    yield root, index, downloader
    set_listing_refresh_fn(lambda: None)
    invalidate_library_paths_cache()


def test_equivalent_provider_editions_show_actual_formats_without_rebinding(env, monkeypatch):
    from downtify.recording_equivalence import RecordingEquivalenceRegistry
    from downtify import recording_equivalence
    from tests.test_recording_equivalence import sequence, A, B
    root, index, downloader = env
    first, second = sequence('a'), sequence('b')
    registry = RecordingEquivalenceRegistry()
    registry.add(A, first); registry.add(B, second)
    monkeypatch.setattr(recording_equivalence, 'registry', registry)
    rel = 'Mix/one.mp3'
    _write_track(root, rel, 'First', 'Artist', 'Title')
    index.register_song(first[0], rel, full_path=root / rel)
    assert locations([second[0]])[0]['formats'] == ['mp3']
    from downtify.library_catalog import lookup_library_songs
    assert lookup_library_songs(api.library_context(), [second[0]])[0]['song_id'] == second[0]['song_id']
    assert index.spotify_id_for_filename(rel) == first[0]['song_id']
    (root / rel).unlink()
    assert locations([second[0]])[0]['formats'] == []


def test_source_id_preserves_album_and_playlist_formats(env, monkeypatch):
    root, index, downloader = env
    from pathlib import PurePosixPath
    from mutagen.id3 import ID3, TDRC, TRCK
    album = downloader.expected_stem_for(dict(SONG, downtify_destination='album')) + '.mp3'
    playlist = 'Mix/Ana - One.flac'
    _write_track(root, album, 'One', 'Ana', 'Sun')
    tags = ID3(root / album)
    tags.add(TDRC(encoding=3, text='2020'))
    tags.add(TRCK(encoding=3, text='1'))
    tags.save(root / album)
    (root / 'Mix').mkdir()
    (root / playlist).write_bytes(b'flac fixture')
    index.register_song(SONG, album, full_path=root / album)
    index.register_source_copy(SONG, playlist, root / playlist)
    monkeypatch.setattr(api, 'playlists_for_request', lambda request: [dict(name='Mix', files=[playlist])])
    result = locations([SONG, SONG, dict(song_id='0' * 22)])
    assert len(result) == 3
    assert result[0] == result[1] == dict(key=SONG['song_id'], downloaded=True,
        formats=['flac', 'mp3'], album_formats=['mp3'], albums=[dict(artist='Ana', title='Sun')], playlists=[dict(name='Mix')])
    assert result[2]['downloaded'] is False
    assert str(root) not in json.dumps(result)


def test_local_binding_finds_other_proven_copies_ignoring_client_identity(env):
    root, index, downloader = env
    first, second = 'Mix/one.mp3', 'Other/two.mp3'
    for rel in (first, second):
        _write_track(root, rel, 'One', 'Ana', 'Sun')
        index.register_source_copy(SONG, rel, root / rel)
    # If the reverse binding is ignored the second copy's playlist disappears.
    from downtify.library_locations import track_locations
    rows = list_library_entries(api.library_context())
    result = track_locations(api.library_context(), [dict(file=first, song_id='0' * 22)],
        rows, downloader, index, [dict(name='Other', files=[second])])
    assert result[0]['playlists'] == [dict(name='Other')]
    assert result[0]['key'] == '0' * 22


@pytest.mark.parametrize('source', [True, False])
def test_complete_fingerprint_joins_unindexed_copies_but_not_name_only(env, monkeypatch, source):
    root, index, downloader = env
    from downtify.library_locations import track_locations
    rows = []
    for rel in ('Mix/one.mp3', 'Other/one.flac', 'Unrelated/one.mp3'):
        path = root / rel
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b'fixture')
        rows.append(dict(file=rel, title='One', artist='Ana', album_artist='Ana',
                         album='Sun', year='2020', track_number=1, duration=180))
    rows[-1]['album'] = 'Another edition'
    query = SONG if source else dict(file=rows[0]['file'], title='forged')
    result = track_locations(api.library_context(), [query], rows, downloader, index,
        [dict(name='Other', files=[rows[1]['file']]), dict(name='Wrong', files=[rows[-1]['file']])])
    assert result[0]['formats'] == ['flac', 'mp3']
    assert result[0]['playlists'] == [dict(name='Other')]


def test_locations_is_client_authorized_and_validates_batch(env):
    from fastapi import HTTPException
    assert classify('POST', '/api/library/locations') == CLIENT
    for bad in (None, {}, 'songs', [None], [SONG] * 201, [dict(file=[])]):
        with pytest.raises(HTTPException) as error:
            locations(bad)
        assert error.value.status_code == 400
    assert locations([]) == []
    assert len(locations([{}] * 200)) == 200


def test_real_catalog_membership_without_m3u_respects_collection_owner(env, monkeypatch):
    from downtify.playlist_catalog import PlaylistCatalog
    from tests.test_library_visibility import _request
    root, index, downloader = env
    rel = 'My Playlist#1/Ana - One.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    catalog = PlaylistCatalog(root.parent / 'catalog.db')
    catalog.replace_playlist_tracks('My Playlist#1', [(SONG, rel, root / rel)], user_id=5)
    catalog.replace_playlist_tracks('Private', [(SONG, rel, root / rel)], user_id=7)
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    result = asyncio.run(api.library_locations(_request(5, body={'songs': [{'file': rel}]})))
    assert result['locations'][0]['playlists'] == [dict(name='My Playlist#1')]
    assert locations([{'file': rel}])[0]['playlists'] == [dict(name='My Playlist#1'), dict(name='Private')]


@pytest.mark.parametrize('kind', ['deleted', 'hidden', 'outside', 'symlink', 'forged'])
def test_unavailable_files_never_claim_collections(env, monkeypatch, kind):
    from downtify.library_locations import track_locations
    root, index, downloader = env
    rel = 'Mix/one.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    index.register_song(SONG, rel, full_path=root / rel)
    row = dict(file=rel, title='One', artist='Ana', album='Sun', album_artist='Ana')
    rows, query = [row], SONG
    if kind == 'deleted':
        (root / rel).unlink()
    elif kind == 'hidden':
        rows = []
    elif kind in ('outside', 'symlink'):
        outside = root.parent / 'outside.mp3'
        outside.write_bytes(b'private')
        if kind == 'outside':
            row['file'] = str(outside)
            query = dict(file=str(outside), **SONG)
        else:
            (root / rel).unlink()
            (root / rel).symlink_to(outside)
    else:
        query = dict(SONG, file='does-not-exist.mp3')
    result = track_locations(api.library_context(), [query], rows, downloader, index,
        [dict(name='Mix', files=[rel])])[0]
    assert not result['downloaded']
    assert result['albums'] == result['playlists'] == result['formats'] == []


def test_changed_recovered_copy_loses_source_identity(env):
    root, index, downloader = env
    rel = 'Mix/one.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    index.register_source_copy(SONG, rel, root / rel)
    assert locations([SONG])[0]['downloaded']
    with (root / rel).open('ab') as file:
        file.write(b'changed')
    assert not locations([SONG])[0]['downloaded']


def test_deleted_file_after_cached_snapshot_is_not_downloaded(env):
    root, index, downloader = env
    rel = 'Mix/one.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    index.register_song(SONG, rel, full_path=root / rel)
    assert locations([SONG])[0]['downloaded']
    (root / rel).unlink()
    assert not locations([SONG])[0]['downloaded']


def test_source_lookup_never_calls_provider(env, monkeypatch):
    from downtify import spotify, deezer
    def forbidden(*args, **kwargs):
        raise AssertionError('provider network used during availability rendering')
    for module in (spotify, deezer):
        for name in ('search', 'album_tracks_from_id', 'song_from_url'):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, forbidden)
    assert not locations([SONG, {}])[0]['downloaded']


def test_actual_hidden_rule_applies_to_locations(env, monkeypatch):
    from downtify.library_visibility import LibraryVisibility, KIND_TRACK
    from tests.test_library_visibility import _request
    root, index, downloader = env
    rel = 'Mix/one.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    index.register_song(SONG, rel, full_path=root / rel)
    rules = LibraryVisibility(root.parent / 'hidden.db')
    rules.hide(KIND_TRACK, 'track', path=rel)
    monkeypatch.setattr(api.state, 'library_visibility', rules)
    result = asyncio.run(api.library_locations(_request(5, body={'songs': [SONG, dict(file=rel)]})))
    assert [r['downloaded'] for r in result['locations']] == [False, False]
    assert locations([SONG])[0]['downloaded']  # native admin bypass


def test_disc_number_conflict_is_not_complete_fingerprint(env):
    from downtify.library_locations import track_locations
    root, index, downloader = env
    rel = 'Other/one.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    row = dict(file=rel, title='One', artist='Ana', album_artist='Ana', album='Sun',
               year='2020', track_number=1, duration=180, disc_number=2)
    result = track_locations(api.library_context(), [dict(SONG, disc_number=1)], [row], downloader, index)
    assert not result[0]['downloaded']


def test_album_only_and_shared_manual_playlists_use_same_physical_album_file(env):
    from downtify.manual_playlists import create_manual_playlist, edit_manual_playlist
    from mutagen.id3 import ID3, TDRC
    root, index, downloader = env
    rel = downloader.expected_stem_for(dict(SONG, downtify_destination='album')) + '.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    tags = ID3(root / rel)
    tags.add(TDRC(encoding=3, text='2020'))
    tags.save(root / rel)
    index.register_song(SONG, rel, full_path=root / rel)
    assert locations([SONG])[0]['albums'] == [dict(artist='Ana', title='Sun')]
    assert locations([SONG])[0]['playlists'] == []
    ctx = api.library_context()
    for name in ('Shared One', 'Shared Two'):
        create_manual_playlist(ctx, name)
        edit_manual_playlist(ctx, name, add=[rel])
    result = locations([SONG, {'file': rel}])
    for row in result:
        assert row['albums'] == [dict(artist='Ana', title='Sun')]
        assert row['playlists'] == [dict(name='Shared One'), dict(name='Shared Two')]
    assert len(list(root.rglob('*.mp3'))) == 1


def test_compilation_destination_uses_tagged_album_credit_but_library_route_artist(env):
    root, index, downloader = env
    from mutagen.id3 import ID3, TPE2, TDRC
    compilation = dict(SONG, album_artist='Various Artists')
    rel = downloader.expected_stem_for(dict(compilation, downtify_destination='album')) + '.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    tags = ID3(root / rel)
    tags.add(TPE2(encoding=3, text='Various Artists'))
    tags.add(TDRC(encoding=3, text='2020'))
    tags.save(root / rel)
    index.register_song(compilation, rel, full_path=root / rel)
    assert locations([compilation])[0]['albums'] == [dict(artist='Ana', title='Sun')]


def test_local_playlist_tags_do_not_claim_album_copy(env):
    root, index, downloader = env
    rel = 'Mix/Ana - One.mp3'
    _write_track(root, rel, 'One', 'Ana', 'Sun')
    index.register_song(SONG, rel, full_path=root / rel)
    assert locations([{'file': rel}]) == [dict(key=rel, downloaded=True,
        formats=['mp3'], album_formats=[], albums=[], playlists=[])]
