"""Monitor recovery uses physical catalog membership, not just watch history."""
import asyncio
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import pytest

from downtify import monitor
from downtify.downloader import Downloader
from downtify.monitor import LibraryStores, PlaylistMonitorDB
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

A = '4uLU6hMCjMI75M1A2tKUQC'
B = '7ouMYWpwJ422jRcDASZB7P'


def setup(tmp_path, monkeypatch, *, overwrite=True):
    db = PlaylistMonitorDB(tmp_path / 'watch.db')
    playlist = db.add_playlist('playlist', 'Road Trip', 'https://open.spotify.com/playlist/playlist')
    downloader = Downloader(tmp_path / 'music', folder_structure=True,
                            playlist_use_library=False, overwrite_existing_files=overwrite)
    library = LibraryStores(playlist_catalog=PlaylistCatalog(tmp_path / 'catalog.db'),
                            track_index=TrackIndex(tmp_path / 'index.db'))
    tracks = [dict(song_id=A, name='Alpha', artists=['Artist']),
              dict(song_id=B, name='Beta', artists=['Artist'])]
    monkeypatch.setattr(monitor.spotify, 'playlist_tracks_from_id', lambda _: tracks)
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _: {})
    monkeypatch.setattr(monitor, '_download_cover_for_watch', lambda *args: None)
    return db, playlist, downloader, library, tracks


def run(db, playlist, downloader, library):
    async def sweep():
        async def broadcast(_):
            pass
        return await monitor.check_playlist(playlist, db, downloader, broadcast,
                                            asyncio.get_running_loop(), {}, library)
    return asyncio.run(sweep())


@lru_cache(maxsize=None)
def _audio_bytes(suffix):
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg unavailable')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / ('fixture' + suffix)
        codec = {'mp3': ['-q:a', '9'], 'opus': ['-c:a', 'libopus', '-b:a', '32k'],
                 'm4a': ['-c:a', 'aac', '-b:a', '64k'], 'flac': ['-c:a', 'flac']}[suffix.lstrip('.')]
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                        'sine=frequency=440:duration=0.25', *codec, '-y', str(path)], check=True)
        return path.read_bytes()


def put(downloader, filename):
    path = downloader.download_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_audio_bytes(path.suffix))
    return path


def listed(downloader):
    path = downloader.download_dir / 'Road Trip/Road Trip.m3u'
    return [line for line in path.read_text().splitlines() if line and not line.startswith('#')]


def test_catalog_identity_seeds_watch_before_first_download(tmp_path, monkeypatch):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    # The catalog's source ID remains authoritative when filename metadata changed.
    old = 'Road Trip/Old Alpha spelling.opus'
    full = put(downloader, old)
    library.playlist_catalog.upsert_track(playlist.name, tracks[0], old, full)
    snapshots = []

    def download(song, cb, subdir=None):
        assert song['song_id'] == B, 'existing catalog track was reprocessed'
        filename = 'Road Trip/Artist - Beta.mp3'
        put(downloader, filename)
        return filename

    monkeypatch.setattr(downloader, 'download', download)
    original = monitor._regenerate_m3u

    def regenerate(*args, **kwargs):
        result = original(*args, **kwargs)
        snapshots.append(listed(downloader))
        return result
    monkeypatch.setattr(monitor, '_regenerate_m3u', regenerate)

    assert run(db, playlist, downloader, library) == 1
    assert db.get_track_filenames(playlist.id)[A] == old
    assert all(rows == ['Old Alpha spelling.opus', 'Artist - Beta.mp3'] for rows in snapshots)


@pytest.mark.parametrize('history', ['catalog', 'index', 'watch'])
def test_other_destination_does_not_satisfy_watch(tmp_path, monkeypatch, history):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch, overwrite=False)
    tracks[:] = tracks[:1]
    old = 'Other/Alpha.mp3'
    full = put(downloader, old)
    if history == 'catalog':
        library.playlist_catalog.upsert_track(playlist.name, tracks[0], old, full)
    elif history == 'index':
        library.track_index.register_song(tracks[0], old, full_path=full)
    else:
        db.mark_track_downloaded(playlist.id, A, old)
    calls = []

    def download(song, cb, subdir=None):
        calls.append(song['song_id'])
        put(downloader, 'Road Trip/Artist - Alpha.mp3')
        return 'Road Trip/Artist - Alpha.mp3'
    monkeypatch.setattr(downloader, 'download', download)
    assert run(db, playlist, downloader, library) == 1
    assert calls == [A]
    assert db.get_track_filenames(playlist.id)[A] == 'Road Trip/Artist - Alpha.mp3'
    assert full.is_file()


def test_incremental_snapshot_preserves_playable_existing_m3u_until_final(tmp_path, monkeypatch):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    put(downloader, 'Road Trip/Artist - Alpha.mp3')
    put(downloader, 'Road Trip/Artist - Beta.mp3')
    path = downloader.download_dir / 'Road Trip/Road Trip.m3u'
    path.write_text('#EXTM3U\nArtist - Alpha.mp3\nArtist - Beta.mp3\n')
    # An incomplete in-memory sweep must not replace the existing playable list.
    monitor._regenerate_m3u(playlist, tracks, downloader,
                            resolved={B: 'Road Trip/Artist - Beta.mp3'})
    assert set(listed(downloader)) == {'Artist - Alpha.mp3', 'Artist - Beta.mp3'}
    # Only an authoritative full-source final rewrite removes source departures.
    monitor._regenerate_m3u(playlist, tracks[1:], downloader,
                            known_tracks={B: 'Road Trip/Artist - Beta.mp3'})
    assert listed(downloader) == ['Artist - Beta.mp3']


@pytest.mark.parametrize(('structure', 'use_library'), [(True, True), (True, False),
                                                  (False, True), (False, False)])
def test_existing_destination_is_missing_only_even_with_overwrite_on(
        tmp_path, monkeypatch, structure, use_library):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    downloader.folder_structure = structure
    downloader.playlist_use_library = use_library
    tracks[:] = tracks[:1]
    tracks[0].update(album_name='Album', album_artist='Artist', year='2020', track_number=1)
    filename = downloader.expected_stem_for(tracks[0], 'Road Trip') + '.opus'
    put(downloader, filename)
    calls = []
    monkeypatch.setattr(downloader, 'download', lambda *a, **k: calls.append(a))
    assert run(db, playlist, downloader, library) == 0
    assert calls == []
    assert db.get_track_filenames(playlist.id) == {A: filename}


def test_missing_catalog_file_is_not_proof_of_presence(tmp_path, monkeypatch):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    tracks[:] = tracks[:1]
    filename = 'Road Trip/Artist - Alpha.mp3'
    full = put(downloader, filename)
    library.playlist_catalog.upsert_track(playlist.name, tracks[0], filename, full)
    full.unlink()
    calls = []

    def download(song, cb, subdir=None):
        calls.append(song['song_id'])
        put(downloader, filename)
        return filename
    monkeypatch.setattr(downloader, 'download', download)
    assert run(db, playlist, downloader, library) == 1
    assert calls == [A]


def test_804_catalog_files_recover_without_download_or_provider_enrichment(tmp_path, monkeypatch):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    tracks[:] = [dict(song_id=f'{i:022d}', name=f'Track {i}', artists=['Artist'])
                 for i in range(804)]
    rows = []
    for song in tracks:
        filename = f'Road Trip/old-name-{song["song_id"]}.opus'
        rows.append((song, filename, put(downloader, filename)))
    library.playlist_catalog.replace_playlist_tracks(playlist.name, rows)
    calls = []
    monkeypatch.setattr(downloader, 'download', lambda *a, **k: calls.append('download'))
    monkeypatch.setattr(monitor.spotify, 'track_from_id', lambda _: calls.append('enrich'))
    assert run(db, playlist, downloader, library) == 0
    assert calls == []
    assert len(db.get_track_filenames(playlist.id)) == 804
    assert len(listed(downloader)) == 804
    assert len(library.playlist_catalog.list_tracks(playlist.name)) == 804


def test_failed_missing_destination_does_not_restore_wrong_watch_copy_in_final(tmp_path, monkeypatch):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    put(downloader, 'Other/Alpha.mp3')
    db.mark_track_downloaded(playlist.id, A, 'Other/Alpha.mp3')
    filename = 'Road Trip/Artist - Beta.mp3'
    full = put(downloader, filename)
    library.playlist_catalog.upsert_track(playlist.name, tracks[1], filename, full)

    def fail(*args, **kwargs):
        raise RuntimeError('no match')
    monkeypatch.setattr(downloader, 'download', fail)
    assert run(db, playlist, downloader, library) == 0
    assert listed(downloader) == ['Artist - Beta.mp3']
    assert [row['track_spotify_id'] for row in library.playlist_catalog.list_tracks(playlist.name)] == [B]


def test_source_departure_is_removed_even_when_no_new_track_downloads(tmp_path, monkeypatch):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    for song in tracks:
        filename = f'Road Trip/Artist - {song["name"]}.mp3'
        full = put(downloader, filename)
        db.mark_track_downloaded(playlist.id, song['song_id'], filename)
        library.playlist_catalog.upsert_track(playlist.name, song, filename, full)
    path = downloader.download_dir / 'Road Trip/Road Trip.m3u'
    path.write_text('#EXTM3U\nArtist - Alpha.mp3\nArtist - Beta.mp3\n')
    tracks[:] = tracks[1:]
    calls = []
    monkeypatch.setattr(downloader, 'download', lambda *a, **kw: calls.append(a))
    assert run(db, playlist, downloader, library) == 0
    assert calls == []
    assert listed(downloader) == ['Artist - Beta.mp3']
    assert (downloader.download_dir / 'Road Trip/Artist - Alpha.mp3').is_file()


def test_monitor_marks_managed_download_missing_only_after_metadata_enrichment(tmp_path, monkeypatch):
    db, playlist, downloader, library, tracks = setup(tmp_path, monkeypatch)
    tracks[:] = tracks[:1]
    seen = []

    def download(song, cb, subdir=None):
        seen.append(song.get('downtify_download_mode'))
        filename = 'Road Trip/Artist - Alpha.mp3'
        put(downloader, filename)
        return filename
    monkeypatch.setattr(downloader, 'download', download)
    assert run(db, playlist, downloader, library) == 1
    assert seen == ['missing']
    assert 'downtify_download_mode' not in tracks[0]
