import os
from pathlib import Path

import pytest

from downtify.downloader import Downloader


@pytest.mark.parametrize('overwrite', [False, True])
def test_direct_missing_only_stages_and_does_not_clobber_racing_file(tmp_path, monkeypatch, overwrite):
    downloader = Downloader(tmp_path, overwrite_existing_files=overwrite)
    destination = tmp_path / 'Song.mp3'
    competitor = b'competitor bytes'

    def acquire(video_id, staging_dir, basename, **kwargs):
        staged = Path(staging_dir) / f'{basename}.mp3'
        assert staged.parent != tmp_path
        staged.write_bytes(b'acquired bytes')
        return staged

    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    real_link = os.link

    def race(src, dst, *args, **kwargs):
        Path(dst).write_bytes(competitor)
        return real_link(src, dst, *args, **kwargs)

    monkeypatch.setattr('downtify.downloader.os.link', race)
    with pytest.raises(FileExistsError):
        downloader.fetch_audio('video', tmp_path, 'Song', song={
            'song_id': 's', 'downtify_download_mode': 'missing'})
    assert destination.read_bytes() == competitor
    assert list(tmp_path.glob('.downtify-audio-*')) == []


def test_direct_explicit_redownload_still_writes_destination(tmp_path, monkeypatch):
    downloader = Downloader(tmp_path, overwrite_existing_files=False)
    destination = tmp_path / 'Song.mp3'

    def acquire(video_id, target_dir, basename, **kwargs):
        path = Path(target_dir) / f'{basename}.mp3'
        path.write_bytes(b'redownload')
        return path

    monkeypatch.setattr(downloader, '_fetch_audio', acquire)
    result = downloader.fetch_audio('video', tmp_path, 'Song', song={
        'song_id': 's', 'downtify_download_mode': 'redownload'})
    assert result == destination
    assert destination.read_bytes() == b'redownload'
