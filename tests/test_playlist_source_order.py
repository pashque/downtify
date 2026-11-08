"""Source position is not an album track number or a downloaded-row index."""
from types import SimpleNamespace

from downtify import monitor
from downtify.playlist_catalog import PlaylistCatalog


def test_monitor_catalog_retains_source_gaps_and_source_removals(tmp_path):
    catalog = PlaylistCatalog(tmp_path / 'library.db')
    songs = [{'song_id': c * 22, 'name': c, 'track_number': n}
             for c, n in [('a', 9), ('b', 1), ('c', 3), ('d', 2)]]
    for song in songs:
        (tmp_path / (song['name'] + '.mp3')).touch()
    catalog.replace_playlist_tracks('P', [(s, s['name'] + '.mp3', tmp_path / (s['name'] + '.mp3')) for s in songs])
    watch = SimpleNamespace(name='P', source=monitor.SOURCE_SPOTIFY, spotify_id='p' * 22, user_id=0)
    dl = SimpleNamespace(download_dir=tmp_path)
    stores = monitor.LibraryStores(playlist_catalog=catalog)
    # Source removed b; c exists in source but its download has not succeeded.
    monitor._sync_library_playlist(watch, [songs[3], songs[2], songs[0]], dl,
                                   {'a' * 22: 'a.mp3', 'd' * 22: 'd.mp3'}, stores, {})
    assert [(r['track_spotify_id'], r['track_order']) for r in catalog.list_tracks('P')] == [('d' * 22, 0), ('a' * 22, 2)]


def test_incremental_m3u_inserts_recovery_in_source_order_without_losing_members(tmp_path):
    from downtify import m3u
    for name in ['first', 'missing', 'last', 'departed']:
        (tmp_path / (name + '.mp3')).touch()
    path, _ = m3u.write_m3u(tmp_path, 'P', [{'filename': n + '.mp3'} for n in ['last', 'first', 'departed']])
    m3u.write_m3u(tmp_path, 'P', [{'filename': 'missing.mp3'}],
                  preserve_existing=True,
                  source_order=['first.mp3', 'missing.mp3', 'last.mp3', 'last.mp3'])
    # Incremental publication is not permission to drop old playable members.
    assert m3u.read_m3u_tracks(path, tmp_path) == ['first.mp3', 'missing.mp3', 'last.mp3', 'last.mp3', 'departed.mp3']


def test_partial_spotify_batch_publishes_existing_and_recovered_files_in_source_order(tmp_path, monkeypatch):
    import asyncio
    from downtify import api, m3u
    folder = tmp_path / 'P'
    folder.mkdir()
    songs = [{'song_id': c * 22, 'name': c, 'artists': ['Artist']} for c in 'abcd']
    catalog = PlaylistCatalog(tmp_path / 'library.db')
    for index in [0, 3]:
        song = songs[index]
        name = 'P/' + song['name'] + '.mp3'
        (tmp_path / name).touch()
        catalog.upsert_track('P', song, name, tmp_path / name, track_order=index)
    path, _ = m3u.write_m3u(tmp_path, 'P', [{'filename': 'P/a.mp3'}, {'filename': 'P/d.mp3'}], playlist_subdir='P')
    monkeypatch.setattr(api.state, 'downloader', SimpleNamespace(download_dir=tmp_path))
    monkeypatch.setattr(api.state, 'playlist_catalog', catalog)
    monkeypatch.setattr(api.state, 'playlist_spotify_cache', None)
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(api, '_organize_enabled', lambda: False)
    monkeypatch.setattr(api, 'slskd_dir_from_downloader', lambda dl: None)
    monkeypatch.setattr(api, '_fetch_playlist_for_batch', lambda *args: ('P', songs))

    async def noop(*args, **kwargs):
        pass
    monkeypatch.setattr(api, '_fetch_playlist_cover', noop)
    monkeypatch.setattr(api, '_finish_playlist_batch', noop)
    positions = []

    async def recover(song, *args, **kwargs):
        positions.append(kwargs['track_order'])
        if song['name'] == 'c':
            return None
        (folder / 'b.mp3').touch()
        return 'P/b.mp3'
    monkeypatch.setattr(api, '_run_download', recover)
    asyncio.run(api._process_batch(songs[1:3], ['b', 'c'], 'https://open.spotify.com/playlist/' + 'p' * 22, True))
    assert m3u.read_m3u_tracks(path, tmp_path) == ['P/a.mp3', 'P/b.mp3', 'P/d.mp3']
    assert positions == [1, 2]


def test_monitor_incremental_publication_uses_source_order_before_final_sync(tmp_path):
    from downtify import m3u
    folder = tmp_path / 'P'
    folder.mkdir()
    songs = [{'song_id': c * 22, 'name': c, 'artists': ['Artist']} for c in 'abc']
    for c in 'abc':
        (folder / (c + '.mp3')).touch()
    path, _ = m3u.write_m3u(tmp_path, 'P', [{'filename': 'P/c.mp3'}, {'filename': 'P/a.mp3'}], playlist_subdir='P')
    watch = SimpleNamespace(name='P')
    dl = SimpleNamespace(download_dir=tmp_path, organize_by_artist_album=False)
    monitor._regenerate_m3u(watch, songs, dl, {c * 22: 'P/' + c + '.mp3' for c in 'abc'})
    assert m3u.read_m3u_tracks(path, tmp_path) == ['P/a.mp3', 'P/b.mp3', 'P/c.mp3']
