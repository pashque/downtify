"""Monitor must not claim provenance for downloader skips."""
from __future__ import annotations

import asyncio

from downtify import monitor
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

TRACK_A = '4uLU6hMCjMI75M1A2tKUQC'
PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'


class DownloadResult(str):
    def __new__(cls, filename, *, acquired):
        value = super().__new__(cls, filename)
        value.acquired = acquired
        return value


class Downloader:
    organize_by_artist = False
    organize_by_album = False
    slskd_settings = {}
    overwrite_existing_files = False

    def __init__(self, root, *, acquired):
        self.download_dir = root
        self.acquired = acquired
        self.calls = 0

    def download(self, song, cb, subdir=None):
        self.calls += 1
        name = f'{subdir}/{song["name"]}.mp3'
        path = self.download_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'preserved-existing-bytes' if not self.acquired else b'new-audio')
        return DownloadResult(name, acquired=self.acquired)

    @staticmethod
    def existing_filename_for(song, subdir=None):
        return None


def test_skipped_filename_keeps_monitor_manifest_but_does_not_register_provenance(monkeypatch, tmp_path):
    root = tmp_path / 'downloads'
    library_db = tmp_path / 'library.db'
    index = TrackIndex(library_db)
    catalog = PlaylistCatalog(library_db)
    library = LibraryStores(track_index=index, playlist_catalog=catalog)
    downloader = Downloader(root, acquired=False)
    song = {'song_id': TRACK_A, 'name': 'Alpha', 'artists': ['Artist']}
    monkeypatch.setattr(monitor.spotify, 'playlist_tracks_from_id', lambda _id: [song])
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(PLAYLIST_ID, 'Road Trip', f'https://open.spotify.com/playlist/{PLAYLIST_ID}')
    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(monitor.check_playlist(
            watch, db, downloader, lambda _msg: asyncio.sleep(0), loop,
            {'generate_m3u': False}, library,
        ))
    finally:
        loop.close()

    assert count == 1
    assert downloader.calls == 1
    assert (root / 'Road Trip' / 'Alpha.mp3').read_bytes() == b'preserved-existing-bytes'
    assert db.get_track_filenames(watch.id)[TRACK_A] == 'Road Trip/Alpha.mp3'
    assert index.lookup(TRACK_A) is None
    # The playlist catalog/M3U mirror the monitor's known manifest; the
    # source-copy index is the speculative provenance that must stay empty.
    assert catalog.list_tracks('Road Trip')


def test_acquired_filename_registers_index_and_catalog(monkeypatch, tmp_path):
    root = tmp_path / 'downloads'
    library_db = tmp_path / 'library.db'
    index = TrackIndex(library_db)
    catalog = PlaylistCatalog(library_db)
    library = LibraryStores(track_index=index, playlist_catalog=catalog)
    downloader = Downloader(root, acquired=True)
    song = {'song_id': TRACK_A, 'name': 'Alpha', 'artists': ['Artist']}
    monkeypatch.setattr(monitor.spotify, 'playlist_tracks_from_id', lambda _id: [song])
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(PLAYLIST_ID, 'Road Trip', f'https://open.spotify.com/playlist/{PLAYLIST_ID}')
    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(monitor.check_playlist(
            watch, db, downloader, lambda _msg: asyncio.sleep(0), loop,
            {'generate_m3u': False}, library,
        ))
    finally:
        loop.close()

    assert count == 1
    assert index.lookup(TRACK_A) == 'Road Trip/Alpha.mp3'
    assert [(row['filename'], row['track_order']) for row in catalog.list_tracks('Road Trip')] == [
        ('Road Trip/Alpha.mp3', 0)
    ]


class Owners:
    def __init__(self):
        self.calls = []

    def add(self, *args):
        self.calls.append(args)


def test_skipped_artist_copy_does_not_register_owner(monkeypatch, tmp_path):
    root = tmp_path / 'downloads'
    owners = Owners()
    library = LibraryStores(track_owners=owners)
    downloader = Downloader(root, acquired=False)
    song = {'song_id': TRACK_A, 'name': 'Alpha', 'artists': ['Artist']}
    monkeypatch.setattr(monitor.providers, 'artist_albums_from_channel_id',
                        lambda _id: [{'album_id': 'album1', 'name': 'Album', 'type': 'album'}])
    monkeypatch.setattr(monitor.providers, 'album_tracks_from_browse_id',
                        lambda _id: [song])
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist('channel', 'Artist', 'https://example.test', kind=monitor.KIND_ARTIST)
    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(monitor.check_artist(
            watch, db, downloader, lambda _msg: asyncio.sleep(0), loop, {}, library,
        ))
    finally:
        loop.close()

    assert count == 1
    assert db.get_track_filenames(watch.id)[TRACK_A] == 'None/Alpha.mp3'
    assert owners.calls == []
