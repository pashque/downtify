from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from downtify import api
from downtify.downloader import DownloadResult


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        api.state.loop = loop
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def api_state():
    fields = ('downloader', 'loop', 'connections', 'track_index')
    previous = {name: getattr(api.state, name) for name in fields}
    previous_jobs = dict(api.state.download_jobs)
    api.state.connections = MagicMock()
    api.state.connections.broadcast_job = AsyncMock()
    api.state.download_jobs.clear()
    yield
    api.state.download_jobs.clear()
    api.state.download_jobs.update(previous_jobs)
    for name, value in previous.items():
        setattr(api.state, name, value)


def test_api_skip_marks_done_without_recording_ownership(api_state, tmp_path, monkeypatch):
    downloader = MagicMock()
    downloader.download.return_value = DownloadResult('Artist - Track.mp3', acquired=False)
    api.state.downloader = downloader
    api.state.track_index = None
    record = AsyncMock()
    monkeypatch.setattr(api, '_record_finished_download', record)
    song_id = api._register_job({'name': 'Track', 'artists': ['Artist']}, status='queued')

    filename = _run(api._run_download(api.state.download_jobs[song_id]['song'], song_id, user_id=17))

    assert filename == 'Artist - Track.mp3'
    assert api.state.download_jobs[song_id]['status'] == 'done'
    record.assert_not_awaited()
    # The API's public job filename stays a plain JSON string; provenance is internal.
    assert json.loads(json.dumps({'filename': filename})) == {'filename': 'Artist - Track.mp3'}
    assert not hasattr(filename, 'acquired')


def test_api_acquisition_records_finished_download(api_state, monkeypatch):
    downloader = MagicMock()
    downloader.download.return_value = DownloadResult('Artist - Track.mp3', acquired=True)
    api.state.downloader = downloader
    api.state.track_index = None
    record = AsyncMock()
    monkeypatch.setattr(api, '_record_finished_download', record)
    song = {'name': 'Track', 'artists': ['Artist']}
    song_id = api._register_job(song, status='queued')

    filename = _run(api._run_download(song, song_id, user_id=17))

    assert filename == 'Artist - Track.mp3'
    record.assert_awaited_once()
    assert record.await_args.args == (song, 'Artist - Track.mp3')
    assert record.await_args.kwargs['user_id'] == 17


def test_api_download_failure_preserves_error_contract(api_state):
    downloader = MagicMock()
    downloader.download.side_effect = OSError('provider failed')
    api.state.downloader = downloader
    song = {'name': 'Track', 'artists': ['Artist']}
    song_id = api._register_job(song, status='queued')

    with pytest.raises(OSError, match='provider failed'):
        _run(api._run_download(song, song_id))

    assert api.state.download_jobs[song_id]['status'] == 'error'
    assert api.state.download_jobs[song_id]['message'] == 'Error: provider failed'
