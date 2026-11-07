"""End-to-end slskd leave-in-place preservation across API and monitor."""
from __future__ import annotations

import asyncio
import hashlib
import os
import subprocess

import pytest

from downtify import api, monitor
from downtify.downloader import Downloader
from downtify.library_paths import locate_library_file
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

TRACK_ID = '4uLU6hMCjMI75M1A2tKUQC'
PLAYLIST_ID = '37i9dQZF1DXcBWIGoYBM5M'


def _audio(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
        'sine=frequency=440:duration=0.4', '-metadata', 'title=Track',
        '-metadata', 'artist=Artist', '-codec:a', 'libmp3lame', '-q:a', '9',
        '-y', str(path),
    ], check=True)
    stat = path.stat()
    return hashlib.sha256(path.read_bytes()).hexdigest(), stat.st_mtime_ns


def _downloader(tmp_path, source):
    d = Downloader(
        tmp_path / 'downloads', audio_providers=['slskd'],
        slskd_settings={'enabled': True, 'leave_in_place': True,
                        'source_dir': str(source.parent.parent)},
    )
    d._resolve_source = lambda song, cb: (None, None, 'slskd', source)
    return d


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        api.state.loop = loop
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _stable(path, before):
    stat = path.stat()
    assert (hashlib.sha256(path.read_bytes()).hexdigest(), stat.st_mtime_ns) == before


def test_real_downloader_result_through_api_preserves_slskd_file(tmp_path, monkeypatch):
    source = tmp_path / 'slskd' / 'peer' / 'Track.mp3'
    before = _audio(source)
    d = _downloader(tmp_path, source)
    old_downloader, old_loop = api.state.downloader, api.state.loop
    old_index, old_connections = api.state.track_index, api.state.connections
    old_jobs = dict(api.state.download_jobs)
    api.state.downloader = d
    api.state.track_index = TrackIndex(tmp_path / 'library.db')
    api.state.connections = type('Connections', (), {'broadcast_job': _noop})()
    api.state.download_jobs.clear()
    recorded = []
    monkeypatch.setattr(api, '_record_finished_download', lambda *a, **k: _record(recorded, a, k))
    try:
        song = {'song_id': TRACK_ID, 'name': 'Track', 'artists': ['Artist']}
        job_id = api._register_job(song, status='queued')
        result = _run(api._run_download(song, job_id, user_id=7))
        assert result == 'slskd/peer/Track.mp3'
        assert api.state.download_jobs[job_id]['status'] == 'done'
        assert api.state.download_jobs[job_id]['message'] == 'Reused'
        assert not recorded
        assert api.state.track_index.lookup(TRACK_ID) is None
        assert locate_library_file(result, d.download_dir, source.parent.parent) == source
        _stable(source, before)
    finally:
        api.state.download_jobs.clear()
        api.state.download_jobs.update(old_jobs)
        api.state.downloader, api.state.loop = old_downloader, old_loop
        api.state.track_index, api.state.connections = old_index, old_connections


async def _noop(*args, **kwargs):
    return None


def _record(bucket, args, kwargs):
    bucket.append((args, kwargs))


def test_real_downloader_result_through_monitor_preserves_file_and_manifest(tmp_path, monkeypatch):
    source = tmp_path / 'slskd' / 'peer' / 'Track.mp3'
    before = _audio(source)
    d = _downloader(tmp_path, source)
    db_path = tmp_path / 'library.db'
    index, catalog = TrackIndex(db_path), PlaylistCatalog(db_path)
    stores = LibraryStores(track_index=index, playlist_catalog=catalog)
    song = {'song_id': TRACK_ID, 'name': 'Track', 'artists': ['Artist']}
    monkeypatch.setattr(monitor.spotify, 'playlist_tracks_from_id', lambda _id: [song])
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _id: {})
    db = PlaylistMonitorDB(tmp_path / 'monitor.db')
    watch = db.add_playlist(PLAYLIST_ID, 'Road Trip', f'https://open.spotify.com/playlist/{PLAYLIST_ID}')
    loop = asyncio.new_event_loop()
    try:
        count = loop.run_until_complete(monitor.check_playlist(
            watch, db, d, lambda _msg: asyncio.sleep(0), loop,
            {'generate_m3u': False}, stores,
        ))
    finally:
        loop.close()
    assert count == 1
    manifest = db.get_track_filenames(watch.id)
    assert manifest[TRACK_ID] == 'slskd/peer/Track.mp3'
    rows = catalog.list_tracks('Road Trip')
    assert [(row['filename'], row['track_order']) for row in rows] == [
        ('slskd/peer/Track.mp3', 0)
    ]
    assert index.lookup(TRACK_ID) is None
    assert locate_library_file(manifest[TRACK_ID], d.download_dir, source.parent.parent) == source
    _stable(source, before)
