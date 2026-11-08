
import subprocess

import pytest

from downtify.downloader import Downloader
from downtify.track_index import TrackIndex, resolve_existing_download


def _synthetic_audio(path, *, title='Song', artist='Artist'):
    subprocess.run([
        'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
        'sine=frequency=440:duration=0.2', '-metadata', f'title={title}',
        '-metadata', f'artist={artist}', '-q:a', '9', '-y', str(path),
    ], check=True)


def test_managed_destination_rejects_conflicting_stat_valid_source_before_register(tmp_path):
    """A real managed Downloader must not accept/claim another source's audio."""
    audio = tmp_path / 'Artist - Song.mp3'
    _synthetic_audio(audio, title='Different song')
    index = TrackIndex(tmp_path / 'index.sqlite')
    existing = {'song_id': 'A' * 22, 'name': 'Different song', 'artists': ['Artist']}
    requested = {'song_id': 'B' * 22, 'name': 'Song', 'artists': ['Artist']}
    index.register_source_copy(existing, audio.name, audio)
    assert index.validated_source_copy_ids(audio.name) == {existing['song_id']}

    downloader = Downloader(tmp_path, folder_structure=False)
    before = audio.read_bytes()
    try:
        downloader._validate_existing_copy(requested, audio.name)
    except RuntimeError:
        pass
    else:
        raise AssertionError('conflicting destination audio was accepted')

    assert audio.read_bytes() == before
    assert index.lookup(requested['song_id']) is None


def test_known_conflicting_stat_valid_source_copy_is_not_rebound(tmp_path, monkeypatch):
    audio = tmp_path / 'copy.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-metadata', 'title=Song', '-metadata', 'artist=Artist', '-q:a', '9', '-y', str(audio)], check=True)
    index = TrackIndex(tmp_path / 'index.sqlite')
    existing = {'song_id': 'A' * 22, 'name': 'Song', 'artists': ['Artist']}
    requested = {'song_id': 'B' * 22, 'name': 'Song', 'artists': ['Artist']}
    index.register_source_copy(existing, audio.name, audio)
    d = Downloader(tmp_path)
    monkeypatch.setattr(d, 'existing_filename_for', lambda *a, **k: audio.name)
    before = audio.read_bytes()
    assert resolve_existing_download(d, requested, track_index=index) is None
    assert audio.read_bytes() == before
    assert index.lookup('B' * 22) is None


def test_same_source_stat_valid_copy_is_reused(tmp_path, monkeypatch):
    audio = tmp_path / 'copy.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-metadata', 'title=Song', '-metadata', 'artist=Artist', '-q:a', '9', '-y', str(audio)], check=True)
    index = TrackIndex(tmp_path / 'index.sqlite')
    song = {'song_id': 'A' * 22, 'name': 'Song', 'artists': ['Artist']}
    index.register_source_copy(song, audio.name, audio)
    d = Downloader(tmp_path)
    monkeypatch.setattr(d, 'existing_filename_for', lambda *a, **k: audio.name)
    assert resolve_existing_download(d, song, track_index=index) == (audio.name, 'Already on disk')


def test_stale_source_stat_evidence_allows_reuse_without_registration(tmp_path, monkeypatch):
    audio = tmp_path / 'copy.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-metadata', 'title=Song', '-metadata', 'artist=Artist', '-q:a', '9', '-y', str(audio)], check=True)
    index = TrackIndex(tmp_path / 'index.sqlite')
    prior = {'song_id': 'A' * 22, 'name': 'Song', 'artists': ['Artist']}
    index.register_source_copy(prior, audio.name, audio)
    audio.write_bytes(audio.read_bytes() + b'changed stat')
    d = Downloader(tmp_path)
    monkeypatch.setattr(d, 'existing_filename_for', lambda *a, **k: audio.name)
    requested = {'song_id': 'B' * 22, 'name': 'Song', 'artists': ['Artist']}
    assert resolve_existing_download(d, requested, track_index=index) == (audio.name, 'Already on disk')
    assert index.lookup('B' * 22) is None


def test_canonical_indexed_copy_with_conflicting_source_id_is_not_reused(tmp_path, monkeypatch):
    audio = tmp_path / 'copy.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-metadata', 'title=Song', '-metadata', 'artist=Artist', '-q:a', '9', '-y', str(audio)], check=True)
    index = TrackIndex(tmp_path / 'index.sqlite')
    requested = {'song_id': 'B' * 22, 'name': 'Song', 'artists': ['Artist']}
    existing = {'song_id': 'A' * 22, 'name': 'Song', 'artists': ['Artist']}
    index.register(existing['song_id'], audio.name, full_path=audio)
    index.register_source_copy(existing, audio.name, audio)
    d = Downloader(tmp_path)
    monkeypatch.setattr(d, 'existing_filename_for', lambda *a, **k: None)
    assert resolve_existing_download(d, requested, track_index=index) is None
    assert index.lookup(requested['song_id']) is None


def test_source_identity_uses_resolved_path_not_requested_filename(tmp_path):
    audio = tmp_path / 'actual.mp3'
    _synthetic_audio(audio)
    index = TrackIndex(tmp_path / 'index.sqlite')
    prior = {'song_id': 'A' * 22}
    requested = {'song_id': 'B' * 22}
    index.register_source_copy(prior, 'stored-alias.mp3', audio)

    with pytest.raises(RuntimeError, match='different source track'):
        index.validate_source_identity(requested, 'requested-name.mp3', audio)


def test_source_identity_ignores_same_filename_at_different_physical_root(tmp_path):
    left = tmp_path / 'left'
    right = tmp_path / 'right'
    left.mkdir()
    right.mkdir()
    actual = left / 'copy.mp3'
    other = right / 'copy.mp3'
    _synthetic_audio(actual)
    _synthetic_audio(other)
    index = TrackIndex(tmp_path / 'index.sqlite')
    index.register_source_copy({'song_id': 'A' * 22}, 'copy.mp3', other)

    index.validate_source_identity({'song_id': 'B' * 22}, 'copy.mp3', actual)


def test_multiple_source_aliases_allow_only_requested_identity(tmp_path, monkeypatch):
    audio = tmp_path / 'copy.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-metadata', 'title=Song', '-metadata', 'artist=Artist', '-q:a', '9', '-y', str(audio)], check=True)
    index = TrackIndex(tmp_path / 'index.sqlite')
    first = {'song_id': 'A' * 22, 'name': 'Song', 'artists': ['Artist']}
    requested = {'song_id': 'B' * 22, 'name': 'Song', 'artists': ['Artist']}
    index.register_source_copy(first, 'first-alias.mp3', audio)
    index.register_source_copy(requested, 'second-alias.mp3', audio)
    d = Downloader(tmp_path)
    monkeypatch.setattr(d, 'existing_filename_for', lambda *a, **k: audio.name)
    assert resolve_existing_download(d, requested, track_index=index) == (audio.name, 'Already on disk')
    assert index.lookup(requested['song_id']) == audio.name
