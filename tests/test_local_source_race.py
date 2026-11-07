"""Local-provider publication must not clobber a concurrent destination."""

import hashlib
import os
import subprocess
from pathlib import Path

import pytest

from downtify import downloader as downloader_module
from downtify.downloader import Downloader


class _NoLookups:
    def __init__(self, *_args):
        pass

    def collect(self):
        return downloader_module._LookupResults(None, None, None)

    def cancel(self):
        pass


@pytest.fixture
def synthetic_mp3(tmp_path):
    source = tmp_path / 'provider-source.mp3'
    subprocess.run(
        ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'lavfi',
         '-i', 'sine=frequency=440:duration=0.2', '-q:a', '9', '-y', str(source)],
        check=True,
    )
    return source


@pytest.mark.parametrize('overwrite', [False, True])
def test_local_missing_only_does_not_overwrite_file_appearing_at_copy(
    tmp_path, monkeypatch, synthetic_mp3, overwrite
):
    downloader = Downloader(tmp_path, overwrite_existing_files=overwrite)
    destination_dir = tmp_path / 'library'
    destination_dir.mkdir()
    destination = destination_dir / 'Song.mp3'
    competitor = b'concurrent provider download'
    song = {
        'song_id': 'song', 'title': 'Song', 'downtify_download_mode': 'missing',
        'downtify_destination': 'album',
    }

    monkeypatch.setattr(downloader_module, '_MetadataLookups', _NoLookups)
    monkeypatch.setattr(downloader, '_target_location',
                        lambda *_args: (destination_dir, '', 'Song'))
    source_hash = hashlib.sha256(synthetic_mp3.read_bytes()).hexdigest()
    monkeypatch.setattr(downloader_module, '_MetadataLookups', _NoLookups)
    monkeypatch.setattr(downloader, '_target_location',
                        lambda *_args: (destination_dir, '', 'Song'))
    real_link, real_replace = os.link, os.replace

    def inject_then_link(src, dst, *args, **kwargs):
        if Path(dst) == destination:
            destination.write_bytes(competitor)
        return real_link(src, dst, *args, **kwargs)

    def inject_then_replace(src, dst, *args, **kwargs):
        if Path(dst) == destination:
            destination.write_bytes(competitor)
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(downloader_module.os, 'link', inject_then_link)
    monkeypatch.setattr(downloader_module.os, 'replace', inject_then_replace)
    with pytest.raises(FileExistsError):
        downloader._finalize_local_source(song, synthetic_mp3, 'slskd', None, None)
    assert destination.read_bytes() == competitor
    assert hashlib.sha256(synthetic_mp3.read_bytes()).hexdigest() == source_hash
