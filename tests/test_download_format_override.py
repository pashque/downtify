"""Per-request output formats never change the shared downloader settings."""
import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from downtify import api
from downtify.downloader import Downloader

SONG = dict(song_id='format-test', source='deezer', name='Song', artists=['Artist'],
            album_artist='Artist', album_name='Album', track_number=1,
            release_date='2020', youtube_id='video', cover_url='cover', genre='Rock')


@pytest.mark.parametrize('fmt', ['mp3', 'flac', 'ogg', 'opus', 'm4a'])
def test_request_format_hint_is_private_and_preserves_input(fmt):
    hints = dict(SONG, audioFormat=fmt)
    result = api._song_from_download_request('unused', hints)
    assert result['downtify_audio_format'] == fmt
    assert 'downtify_audio_format' not in hints


@pytest.mark.parametrize('fmt', ['FLAC', '', 'wav', '../flac', None, 42, ['flac']])
def test_invalid_request_formats_are_rejected(fmt):
    with pytest.raises(HTTPException) as exc:
        api._song_from_download_request('unused', dict(SONG, audioFormat=fmt))
    assert exc.value.status_code == 400


def test_resolved_url_receives_format_override(monkeypatch):
    monkeypatch.setattr(api, '_song_for_download', lambda _: dict(SONG))
    assert api._song_from_download_request('url', {'audioFormat': 'flac'})['downtify_audio_format'] == 'flac'


@pytest.mark.parametrize('mode,overwrite', [('missing', True), ('missing', False), ('redownload', False)])
def test_override_acquires_separate_format_without_deleting_mp3(tmp_path, monkeypatch, mode, overwrite):
    d = Downloader(tmp_path, folder_structure=False, overwrite_existing_files=overwrite,
                   download_cover_art=False)
    mp3 = tmp_path / 'Artist - Song.mp3'
    mp3.write_bytes(b'original MP3')
    calls = []

    class YDL:
        def __init__(self, opts):
            assert 'downtify_audio_format' not in opts
            self.opts = self.params = opts
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def add_post_processor(self, pp, **kwargs):
            calls.append(pp.mapping)
        def download(self, urls):
            from pathlib import Path
            Path(self.opts['outtmpl'].replace('%(ext)s', calls[-1])).write_bytes(b'new audio')

    monkeypatch.setattr('downtify.downloader.yt_dlp.YoutubeDL', YDL)
    monkeypatch.setattr(d, '_tag_file', lambda *a, **kw: None)
    result = d.download(dict(SONG, downtify_audio_format='flac', downtify_download_mode=mode))
    assert result == 'Artist - Song.flac'
    assert (tmp_path / result).read_bytes() == b'new audio'
    assert calls == ['flac']
    assert mp3.read_bytes() == b'original MP3'
    assert d.audio_format == 'mp3'
    assert d.overwrite_existing_files is overwrite


def test_missing_override_skips_only_requested_format_at_destination(tmp_path, monkeypatch):
    d = Downloader(tmp_path, folder_structure=False, overwrite_existing_files=True)
    song = dict(SONG, downtify_audio_format='flac', downtify_download_mode='missing')
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'mp3')
    assert d.existing_filename_for(song) is None
    (tmp_path / 'Artist - Song.flac').write_bytes(b'flac')
    monkeypatch.setattr(d, '_fetch_and_tag', lambda *a: pytest.fail('already present'))
    assert d.download(song) == 'Artist - Song.flac'


def test_override_does_not_use_legacy_cross_destination_scan(tmp_path):
    d = Downloader(tmp_path, overwrite_existing_files=False)
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'Artist - Song.flac').write_bytes(b'flac')
    assert d.find_existing_download(dict(SONG, downtify_audio_format='flac')) is None


@pytest.mark.parametrize('completed', [False, True])
def test_api_does_not_reuse_wrong_format_destination(tmp_path, monkeypatch, completed):
    d = Downloader(tmp_path, folder_structure=False, overwrite_existing_files=False)
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'mp3')
    monkeypatch.setattr(api.state, 'downloader', d)
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(api.state, 'track_index', None)
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(api.state, 'download_jobs', {
        SONG['song_id']: {'status': 'done' if completed else 'queued',
                         'filename': 'Artist - Song.mp3', 'user_ids': set()}})
    monkeypatch.setattr(api, '_record_finished_download', AsyncMock())
    download = lambda *a, **kw: 'Artist - Song.flac'
    monkeypatch.setattr(d, 'download', download)
    assert asyncio.run(api._run_download(dict(SONG, downtify_audio_format='flac'), SONG['song_id'])) == 'Artist - Song.flac'


def test_override_stages_away_from_existing_audio(tmp_path, monkeypatch):
    d = Downloader(tmp_path)
    original = tmp_path / 'Artist - Song.mp3'
    original.write_bytes(b'original')
    def opts(template, hook):
        from pathlib import Path
        assert Path(template).parent != tmp_path
        raise RuntimeError('isolated staging reached')
    monkeypatch.setattr(d, '_ydl_options', opts)
    with pytest.raises(RuntimeError, match='isolated staging reached'):
        d.fetch_audio('video', tmp_path, 'Artist - Song', song=dict(SONG, downtify_audio_format='flac'))
    assert original.read_bytes() == b'original'


def test_batch_applies_top_level_format_to_all_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', Downloader(tmp_path))
    monkeypatch.setattr(api, 'log_activity', AsyncMock())
    submit = AsyncMock(return_value={'count': 1})
    monkeypatch.setattr(api, '_submit_playlist_batch', submit)
    class Request:
        scope = {'state': {}}
        async def json(self): return {'songs': [dict(SONG)], 'audioFormat': 'flac'}
    asyncio.run(api.download_batch_endpoint(Request()))
    assert submit.call_args.args[0][0]['downtify_audio_format'] == 'flac'


def test_api_indexed_mp3_cannot_satisfy_flac_request(tmp_path, monkeypatch):
    from unittest.mock import Mock
    d = Downloader(tmp_path, folder_structure=True, overwrite_existing_files=False)
    song = dict(SONG, downtify_audio_format='flac')
    directory, _, stem = d._target_location(song, None)
    stored = str((directory / (stem + '.mp3')).relative_to(tmp_path))
    (tmp_path / stored).write_bytes(b'mp3')
    index = Mock()
    index.source_copies_for_song.return_value = [stored]
    monkeypatch.setattr(api.state, 'downloader', d)
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(api.state, 'download_semaphore', None)
    monkeypatch.setattr(api, '_record_finished_download', AsyncMock())
    monkeypatch.setattr(d, 'download', lambda *a, **kw: 'fresh.flac')
    assert asyncio.run(api._run_download(song, 'format-test')) == 'fresh.flac'


def test_album_endpoint_applies_audio_format(tmp_path, monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', Downloader(tmp_path))
    monkeypatch.setattr(api, '_songs_for_album_download', lambda _: [dict(SONG)])
    monkeypatch.setattr(api, 'log_activity', AsyncMock())
    monkeypatch.setattr(api, '_register_job', lambda *a, **kw: 'format-test')
    run = AsyncMock(return_value='fresh.flac')
    monkeypatch.setattr(api, '_run_download', run)
    class Request:
        scope = {'state': {}}
        headers = {'content-length': '22'}
        async def json(self): return {'audioFormat': 'flac'}
    asyncio.run(api.download_album_endpoint(Request(), 'album-url'))
    assert run.call_args.args[0]['downtify_audio_format'] == 'flac'


def test_private_yt_option_is_consumed_before_ytdlp(tmp_path, monkeypatch):
    d = Downloader(tmp_path)
    def opts(template, hook):
        return {'outtmpl': template, 'downtify_audio_format': 'flac'}, False
    monkeypatch.setattr(d, '_ydl_options', opts)
    class YDL:
        def __init__(self, options):
            assert 'downtify_audio_format' not in options
            raise RuntimeError('private option consumed')
    monkeypatch.setattr('downtify.downloader.yt_dlp.YoutubeDL', YDL)
    with pytest.raises(RuntimeError, match='private option consumed'):
        d.fetch_audio('video', tmp_path, 'Song', song=SONG)


def test_completed_format_job_elsewhere_does_not_skip_destination(tmp_path, monkeypatch):
    d = Downloader(tmp_path, overwrite_existing_files=False)
    (tmp_path / 'other').mkdir()
    (tmp_path / 'other/Artist - Song.flac').write_bytes(b'flac')
    monkeypatch.setattr(api.state, 'downloader', d)
    monkeypatch.setattr(api.state, 'loop', None)
    monkeypatch.setattr(api.state, 'download_jobs', {'format-test': {
        'status': 'done', 'filename': 'other/Artist - Song.flac', 'user_ids': set()}})
    run = AsyncMock(return_value='Artist - Song.flac')
    monkeypatch.setattr(api, '_run_download_locked', run)
    assert asyncio.run(api._run_download(dict(SONG, downtify_audio_format='flac'), 'format-test')) == 'Artist - Song.flac'
    run.assert_awaited_once()


def test_existing_override_matches_uppercase_extension(tmp_path):
    d = Downloader(tmp_path)
    (tmp_path / 'Artist - Song.FLAC').write_bytes(b'flac')
    assert d.existing_filename_for(dict(SONG, downtify_audio_format='flac')) == 'Artist - Song.FLAC'


@pytest.mark.parametrize('fmt', ['../flac', 'FLAC', ['flac']])
def test_forged_private_format_hint_is_rejected(fmt):
    with pytest.raises(HTTPException) as exc:
        api._song_from_download_request('unused', dict(SONG, downtify_audio_format=fmt))
    assert exc.value.status_code == 400


def test_restarted_job_retains_new_request_format(monkeypatch):
    monkeypatch.setattr(api.state, 'download_jobs', {'format-test': {
        'status': 'done', 'song': dict(SONG), 'user_ids': set()}})
    api._register_job(dict(SONG, downtify_audio_format='flac'))
    assert api.state.download_jobs['format-test']['song']['downtify_audio_format'] == 'flac'


@pytest.mark.parametrize('payload', [
    {'audioFormat': 'FLAC', 'songs': [SONG]},
    {'songs': [dict(SONG, downtify_audio_format='../flac')]},
])
def test_batch_validates_formats_before_queueing(tmp_path, monkeypatch, payload):
    monkeypatch.setattr(api.state, 'downloader', Downloader(tmp_path))
    monkeypatch.setattr(api, 'log_activity', AsyncMock())
    submit = AsyncMock()
    monkeypatch.setattr(api, '_submit_playlist_batch', submit)
    class Request:
        scope = {'state': {}}
        async def json(self): return payload
    with pytest.raises(HTTPException) as exc:
        asyncio.run(api.download_batch_endpoint(Request()))
    assert exc.value.status_code == 400
    submit.assert_not_awaited()


def test_real_ffmpeg_conversion_keeps_existing_mp3(tmp_path, monkeypatch):
    """Offline lossy-source conversion: a FLAC container does not restore fidelity."""
    import json
    import shutil
    import subprocess
    import yt_dlp
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('ffmpeg and ffprobe required')
    original = tmp_path / 'Artist - Song.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.1', str(original)], check=True)
    original_bytes = original.read_bytes()
    real_ydl = yt_dlp.YoutubeDL
    class OfflineYDL(real_ydl):
        def download(self, urls):
            from pathlib import Path
            source = Path(self.params['outtmpl']['default'].replace('%(ext)s', 'mp3'))
            shutil.copyfile(original, source)
            info = {'filepath': str(source), 'ext': 'mp3', 'vcodec': 'none'}
            for pp in self._pps['post_process']:
                removals, info = pp.run(info)
                for filename in removals:
                    Path(filename).unlink()
    monkeypatch.setattr('downtify.downloader.yt_dlp.YoutubeDL', OfflineYDL)
    d = Downloader(tmp_path, download_cover_art=False, folder_structure=False)
    monkeypatch.setattr(d, '_tag_file', lambda *a, **kw: None)
    stored = d.download(dict(SONG, downtify_audio_format='flac'))
    assert stored == 'Artist - Song.flac'
    output = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                             'stream=codec_name', '-of', 'json', str(tmp_path / stored)],
                            check=True, capture_output=True, text=True)
    assert json.loads(output.stdout)['streams'][0]['codec_name'] == 'flac'
    assert original.read_bytes() == original_bytes
    assert not list(tmp_path.glob('.downtify-audio-*'))


def test_local_provider_format_override_copies_and_converts_without_touching_source(tmp_path, monkeypatch):
    import shutil
    import subprocess
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg required')
    source = tmp_path / 'incoming.mp3'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'sine=frequency=440:duration=0.1', str(source)], check=True)
    original = source.read_bytes()
    d = Downloader(tmp_path / 'library', folder_structure=False, download_cover_art=False,
                   slskd_settings={'leave_in_place': True})
    monkeypatch.setattr(d, '_tag_file', lambda *a, **kw: None)
    stored = d._finalize_local_source(dict(SONG, downtify_audio_format='flac'),
                                     source, 'slskd', None, None)
    assert stored == 'Artist - Song.flac'
    assert (d.download_dir / stored).read_bytes().startswith(b'fLaC')
    assert source.read_bytes() == original
    assert d.audio_format == 'mp3'
