from pathlib import Path

import pytest

from downtify.downloader import Downloader


@pytest.mark.parametrize('overwrite', [False, True])
def test_missing_only_publish_does_not_overwrite_competitor(tmp_path, monkeypatch, overwrite):
    downloader = Downloader(tmp_path, overwrite_existing_files=overwrite)
    destination = tmp_path / 'Song.mp3'
    staged_bytes = b'acquired bytes'
    competitor_bytes = b'competitor bytes'

    def acquire(video_id, staging_dir, basename, **kwargs):
        staged = Path(staging_dir) / f'{basename}.mp3'
        staged.write_bytes(staged_bytes)
        return staged

    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    real_link = __import__('os').link

    def competitor_at_publish(src, dst, *args, **kwargs):
        Path(dst).write_bytes(competitor_bytes)
        return real_link(src, dst, *args, **kwargs)

    monkeypatch.setattr('downtify.downloader.os.link', competitor_at_publish)
    with pytest.raises(FileExistsError):
        downloader.fetch_audio('video', tmp_path, 'Song', song={'song_id': 's', 'downtify_download_mode': 'missing', 'downtify_audio_format': 'mp3'})
    assert destination.read_bytes() == competitor_bytes
    assert list(tmp_path.glob('.downtify-audio-*')) == []


@pytest.mark.parametrize('overwrite', [False, True])
def test_default_mode_stages_unknown_audio_and_does_not_overwrite_competitor(tmp_path, monkeypatch, overwrite):
    downloader = Downloader(tmp_path, overwrite_existing_files=overwrite)
    destination = tmp_path / 'Song.mp3'
    competitor = b'competitor bytes'

    def acquire(video_id, staging_dir, basename, **kwargs):
        staged = Path(staging_dir) / f'{basename}.mp3'
        staged.write_bytes(b'acquired bytes')
        return staged

    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    real_link = __import__('os').link

    def competitor_at_publish(src, dst, *args, **kwargs):
        Path(dst).write_bytes(competitor)
        return real_link(src, dst, *args, **kwargs)

    monkeypatch.setattr('downtify.downloader.os.link', competitor_at_publish)
    if overwrite:
        result = downloader.fetch_audio('video', tmp_path, 'Song', song={'song_id': 's'})
        assert result == destination
        assert destination.read_bytes() == b'acquired bytes'
    else:
        with pytest.raises(FileExistsError):
            downloader.fetch_audio('video', tmp_path, 'Song', song={'song_id': 's'})
        assert destination.read_bytes() == competitor


def test_redownload_started_absent_does_not_overwrite_competitor(tmp_path, monkeypatch):
    downloader = Downloader(tmp_path, overwrite_existing_files=False)
    destination = tmp_path / 'Song.mp3'
    competitor = b'competitor bytes'

    def acquire(video_id, staging_dir, basename, **kwargs):
        staged = Path(staging_dir) / f'{basename}.mp3'
        staged.write_bytes(b'acquired bytes')
        destination.write_bytes(competitor)
        return staged

    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    with pytest.raises(FileExistsError):
        downloader.fetch_audio('video', tmp_path, 'Song', song={
            'song_id': 's', 'downtify_download_mode': 'redownload',
            'downtify_audio_format': 'mp3'})
    assert destination.read_bytes() == competitor


def test_redownload_replaced_original_during_acquisition_preserves_competitor(tmp_path, monkeypatch):
    downloader = Downloader(tmp_path, overwrite_existing_files=False)
    destination = tmp_path / 'Song.mp3'
    destination.write_bytes(b'authorized original')

    def acquire(video_id, staging_dir, basename, **kwargs):
        staged = Path(staging_dir) / f'{basename}.mp3'
        staged.write_bytes(b'acquired bytes')
        replacement = tmp_path / 'competitor.tmp'
        replacement.write_bytes(b'competitor replacement')
        replacement.replace(destination)
        return staged

    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    with pytest.raises(RuntimeError, match='changed during redownload'):
        downloader.fetch_audio('video', tmp_path, 'Song', song={
            'song_id': 's', 'downtify_download_mode': 'redownload',
            'downtify_audio_format': 'mp3'})
    assert destination.read_bytes() == b'competitor replacement'


def test_redownload_detects_in_place_destination_rewrite(tmp_path, monkeypatch):
    downloader = Downloader(tmp_path, overwrite_existing_files=False)
    destination = tmp_path / 'Song.mp3'
    destination.write_bytes(b'original')

    def acquire(video_id, staging_dir, basename, **kwargs):
        staged = Path(staging_dir) / f'{basename}.mp3'
        staged.write_bytes(b'acquired')
        destination.write_bytes(b'competitor rewrite with changed size')
        return staged

    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    with pytest.raises(RuntimeError, match='changed during redownload'):
        downloader.fetch_audio('video', tmp_path, 'Song', song={
            'song_id': 's', 'downtify_download_mode': 'redownload',
            'downtify_audio_format': 'mp3'})
    assert destination.read_bytes() == b'competitor rewrite with changed size'


def test_redownload_replaces_stable_original(tmp_path, monkeypatch):
    downloader = Downloader(tmp_path, overwrite_existing_files=False)
    destination = tmp_path / 'Song.mp3'
    destination.write_bytes(b'authorized original')
    def acquire(video_id, staging_dir, basename, **kwargs):
        staged = Path(staging_dir) / f'{basename}.mp3'
        staged.write_bytes(b'fresh bytes')
        return staged
    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    result = downloader.fetch_audio('video', tmp_path, 'Song', song={
        'song_id': 's', 'downtify_download_mode': 'redownload',
        'downtify_audio_format': 'mp3'})
    assert result == destination
    assert destination.read_bytes() == b'fresh bytes'
