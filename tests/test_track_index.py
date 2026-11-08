"""Global Spotify track deduplication index."""

from __future__ import annotations

from downtify.downloader import Downloader
from downtify.library_paths import library_stored_path
from downtify.track_index import (
    TrackIndex,
    normalize_spotify_track_id,
    resolve_existing_download,
)

SPOTIFY_ID = '4uLU6hMCjMI75M1A2tKUQC'


def test_normalize_spotify_track_id_from_song_id():
    assert normalize_spotify_track_id({'song_id': SPOTIFY_ID}) == SPOTIFY_ID


def test_normalize_spotify_track_id_from_uri():
    assert (
        normalize_spotify_track_id({'song_id': f'spotify:track:{SPOTIFY_ID}'})
        == SPOTIFY_ID
    )


def test_normalize_ignores_youtube_ids():
    assert normalize_spotify_track_id({'song_id': 'dQw4w9WgXcQ'}) is None


def test_resolve_existing_prefers_global_library(tmp_path):
    import subprocess
    download_dir = tmp_path / 'music'
    download_dir.mkdir()
    slskd_dir = tmp_path / 'slskd'
    target = slskd_dir / 'Artist - Track.mp3'
    slskd_dir.mkdir(parents=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.2', '-metadata',
                    'title=Track', '-metadata', 'artist=Artist', '-q:a', '9',
                    '-y', str(target)], check=True)

    stored = library_stored_path(target, download_dir, slskd_dir)
    index = TrackIndex(tmp_path / 'library.db')
    index.register(SPOTIFY_ID, stored)

    d = Downloader(
        download_dir,
        audio_format='mp3',
        audio_providers=['youtube'],
        slskd_settings={'source_dir': str(slskd_dir)},
    )
    song = {
        'song_id': SPOTIFY_ID,
        'name': 'Track',
        'artists': ['Artist'],
    }
    hit = resolve_existing_download(
        d,
        song,
        subdir='Playlist B',
        track_index=index,
    )
    assert hit is not None
    assert hit[1] == 'Already in library'
    assert hit[0] == stored


def test_existing_invalid_exact_copy_conflicts_before_registration(tmp_path):
    import shutil
    import subprocess
    import pytest

    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg unavailable')
    download_dir = tmp_path / 'music'
    download_dir.mkdir()
    target = download_dir / 'Artist - Track.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.2', '-metadata',
                    'title=Different', '-metadata', 'artist=Artist', '-q:a', '9',
                    '-y', str(target)], check=True)
    original = target.read_bytes()
    index = TrackIndex(tmp_path / 'library.db')
    song = {'song_id': SPOTIFY_ID, 'name': 'Track', 'artists': ['Artist']}
    d = Downloader(download_dir)

    with pytest.raises(RuntimeError, match='existing file.*does not match'):
        resolve_existing_download(d, song, track_index=index)
    assert index.lookup(SPOTIFY_ID) is None
    assert target.read_bytes() == original


def test_existing_valid_exact_copy_is_reused_and_absence_is_none(tmp_path):
    import shutil
    import subprocess
    import pytest

    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg unavailable')
    download_dir = tmp_path / 'music'
    download_dir.mkdir()
    target = download_dir / 'Artist - Track.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.2', '-metadata',
                    'title=Track', '-metadata', 'artist=Artist', '-q:a', '9',
                    '-y', str(target)], check=True)
    index = TrackIndex(tmp_path / 'library.db')
    song = {'song_id': SPOTIFY_ID, 'name': 'Track', 'artists': ['Artist']}
    d = Downloader(download_dir)
    assert resolve_existing_download(d, song, track_index=index) == (
        target.name, 'Already on disk')
    assert index.lookup(SPOTIFY_ID) is None

    target.unlink()
    assert resolve_existing_download(d, song, track_index=index) is None


def test_reusing_unknown_import_does_not_register_source_from_tags(tmp_path):
    import subprocess
    download_dir = tmp_path / 'music'
    download_dir.mkdir()
    target = download_dir / 'Artist - Track.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.2', '-metadata',
                    'title=Track', '-metadata', 'artist=Artist', '-q:a', '9',
                    '-y', str(target)], check=True)
    index = TrackIndex(tmp_path / 'library.db')
    song = {'song_id': SPOTIFY_ID, 'name': 'Track', 'artists': ['Artist']}
    d = Downloader(download_dir)

    assert resolve_existing_download(d, song, track_index=index) == (
        target.name, 'Already on disk')
    assert index.lookup(SPOTIFY_ID) is None


def test_reusing_stat_validated_source_copy_preserves_source_registration(tmp_path):
    import subprocess
    download_dir = tmp_path / 'music'
    download_dir.mkdir()
    target = download_dir / 'Artist - Track.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.2', '-metadata',
                    'title=Track', '-metadata', 'artist=Artist', '-q:a', '9',
                    '-y', str(target)], check=True)
    index = TrackIndex(tmp_path / 'library.db')
    song = {'song_id': SPOTIFY_ID, 'name': 'Track', 'artists': ['Artist']}
    index.register_source_copy(song, target.name, target)
    d = Downloader(download_dir)

    assert resolve_existing_download(d, song, track_index=index) == (
        target.name, 'Already on disk')
    assert index.lookup(SPOTIFY_ID) == target.name
    assert index.source_copies_for_song(song) == [target.name]


def test_slskd_hit_validates_physical_file_and_external_symlink_fails(tmp_path):
    import subprocess
    import pytest

    music = tmp_path / 'music'
    root = tmp_path / 'slskd'
    music.mkdir()
    root.mkdir()
    target = root / 'Artist - Track.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.2', '-metadata',
                    'title=Track', '-metadata', 'artist=Artist', '-q:a', '9',
                    '-y', str(target)], check=True)
    index = TrackIndex(tmp_path / 'library.db')
    song = {'song_id': SPOTIFY_ID, 'name': 'Track', 'artists': ['Artist']}
    d = Downloader(music, slskd_settings={'source_dir': str(root)})
    stored = 'slskd/Artist - Track.mp3'
    index.register(SPOTIFY_ID, stored)
    assert resolve_existing_download(d, song, subdir='Other', track_index=index) == (
        stored, 'Already in library')

    outside = tmp_path / 'outside.mp3'
    outside.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(outside)
    with pytest.raises(RuntimeError, match='outside authorized roots'):
        resolve_existing_download(d, song, subdir='Other', track_index=index)


def test_real_hit_requires_validator(tmp_path, monkeypatch):
    import subprocess
    import pytest

    music = tmp_path / 'music'
    music.mkdir()
    target = music / 'Artist - Track.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.2', '-metadata',
                    'title=Track', '-metadata', 'artist=Artist', '-q:a', '9',
                    '-y', str(target)], check=True)
    d = Downloader(music)
    monkeypatch.setattr(d, '_validate_existing_copy', None)
    song = {'song_id': SPOTIFY_ID, 'name': 'Track', 'artists': ['Artist']}
    with pytest.raises(RuntimeError, match='validator'):
        resolve_existing_download(d, song)


def test_register_updates_path_for_same_track(tmp_path):
    index = TrackIndex(tmp_path / 'library.db')
    first = tmp_path / 'first' / 'Artist - Song.mp3'
    second = tmp_path / 'second' / 'Artist - Song.mp3'
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b'same')
    second.write_bytes(b'same')
    index.register(SPOTIFY_ID, 'first/path.mp3', full_path=first)
    index.register(SPOTIFY_ID, 'second/path.mp3', full_path=second)
    assert index.lookup(SPOTIFY_ID) == 'second/path.mp3'


def test_filenames_by_spotify_id_reads_the_whole_index(tmp_path):
    index = TrackIndex(tmp_path / 'lib.db')
    index.register('4uLU6hMCjMI75M1A2tKUQC', r'A\One.mp3')
    index.register('1x00000000000000000000', 'Two.flac')

    assert index.filenames_by_spotify_id() == {
        '4uLU6hMCjMI75M1A2tKUQC': 'A/One.mp3',
        '1x00000000000000000000': 'Two.flac',
    }
