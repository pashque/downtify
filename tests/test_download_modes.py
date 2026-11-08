"""Missing-only and deliberate re-download are per-request, not global mutations."""

import asyncio
import subprocess
from unittest.mock import AsyncMock

import pytest

from downtify import api
from downtify.downloader import Downloader

SONG = dict(
    song_id='5fHrHoJKfCgBd35zwIBmUK',
    source='spotify',
    name='D4L',
    artists=['Future', 'Drake', 'Young Thug'],
    album_artist='Drake',
    album_name='Dark Lane Demo Tapes',
    release_date='2020-05-01',
    track_number=9,
)
FULL = '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'


def write_audio(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            'ffmpeg',
            '-nostdin',
            '-v',
            'error',
            '-f',
            'lavfi',
            '-i',
            'sine=frequency=440:duration=0.2',
            '-metadata',
            'title=D4L',
            '-metadata',
            'artist=Future, Drake, Young Thug',
            '-metadata',
            'album=Dark Lane Demo Tapes',
            '-metadata',
            'album_artist=Drake',
            '-codec:a',
            'libmp3lame',
            '-q:a',
            '9',
            '-y',
            str(path),
        ],
        check=True,
    )


@pytest.fixture
def existing(tmp_path):
    d = Downloader(
        tmp_path / 'downloads',
        output_template=FULL,
        folder_structure=True,
        playlist_use_library=True,
        overwrite_existing_files=True,
    )
    target, prefix, name = d._target_location(SONG, None)
    write_audio(target / (name + '.mp3'))
    return d, prefix + name + '.mp3'


def test_missing_mode_skips_shared_album_file_even_if_global_overwrite_on(
    existing, monkeypatch
):
    d, stored = existing
    monkeypatch.setattr(
        d,
        '_resolve_source',
        lambda *args: pytest.fail('must not fetch existing destination'),
    )
    assert (
        d.download(
            dict(SONG, downtify_download_mode='missing'), subdir='Playlist'
        )
        == stored
    )
    assert d.overwrite_existing_files is True


def test_redownload_mode_fetches_even_if_global_overwrite_off(
    existing, monkeypatch
):
    d, stored = existing
    d.overwrite_existing_files = False

    def fetch(*args):
        raise RuntimeError('source acquisition reached')

    monkeypatch.setattr(d, '_resolve_source', fetch)
    with pytest.raises(RuntimeError, match='source acquisition reached'):
        d.download(dict(SONG, downtify_download_mode='redownload'))
    assert d.overwrite_existing_files is False


def test_redownload_bypasses_completed_job(existing, monkeypatch):
    d, stored = existing
    monkeypatch.setattr(api.state, 'downloader', d)
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(
        api.state,
        'download_jobs',
        {
            SONG['song_id']: {
                'status': 'done',
                'filename': stored,
                'user_ids': set(),
            }
        },
    )
    run = AsyncMock(return_value='fresh.mp3')
    monkeypatch.setattr(api, '_run_download_locked', run)
    result = asyncio.run(
        api._run_download(
            dict(SONG, downtify_download_mode='redownload'), SONG['song_id']
        )
    )
    assert result == 'fresh.mp3'
    run.assert_awaited_once()


def test_api_missing_mode_skips_even_with_global_overwrite_on(
    existing, monkeypatch
):
    d, stored = existing
    monkeypatch.setattr(api.state, 'downloader', d)
    monkeypatch.setattr(api.state, 'track_index', None)
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(api, '_record_finished_download', AsyncMock())
    monkeypatch.setattr(
        d,
        'download',
        lambda *args, **kw: pytest.fail(
            'missing-only must skip before fetching'
        ),
    )
    result = asyncio.run(
        api._run_download(
            dict(SONG, downtify_download_mode='missing'), SONG['song_id']
        )
    )
    assert result == stored
    assert d.overwrite_existing_files is True
