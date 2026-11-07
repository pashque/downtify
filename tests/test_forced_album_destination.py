"""Forced album requests never mutate shared storage policy."""
from concurrent.futures import ThreadPoolExecutor
import subprocess
import pytest


def _make_audio(path):
    """Create a small, valid synthetic MP3 for tests that reuse audio files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        'ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
        'sine=frequency=440:duration=0.25', '-codec:a', 'libmp3lame',
        '-q:a', '9', '-y', str(path),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return path
from downtify.downloader import Downloader
from downtify.track_index import TrackIndex, resolve_existing_download
from downtify import api
from tests.test_download_modes import SONG, FULL

FORCED = dict(SONG, downtify_destination='album', downtify_download_mode='missing')
STEM = 'Drake/Drake - Dark Lane Demo Tapes (2020)/09. Future, Drake, Young Thug - D4L'

@pytest.mark.parametrize('structure', [False, True, None])
def test_forced_album_uses_canonical_structure_without_mutation(tmp_path, structure):
    d = Downloader(tmp_path, output_template='{title}', folder_structure=structure, playlist_use_library=False, organize_by_artist=True)
    before = vars(d).copy()
    assert d.expected_stem_for(FORCED, 'Playlist') == STEM
    assert vars(d) == before


def test_forced_status_is_separate_from_global_playable_rows(tmp_path, monkeypatch):
    import asyncio
    d = Downloader(tmp_path, folder_structure=False, playlist_use_library=True)
    playable = [{'file': 'Playlist/old.mp3'}]
    monkeypatch.setattr(api.state, 'downloader', d)
    monkeypatch.setattr(api, 'lookup_library_songs', lambda *a, **kw: playable)
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda request: None)
    monkeypatch.setattr(api, 'filter_paths_for_request', lambda paths, request: paths)
    class Request:
        async def json(self):
            return {'songs': [SONG], 'destination_status': True, 'destination': 'album', 'playlist_name': 'Playlist'}
    result = asyncio.run(api.library_lookup(Request()))
    assert result['tracks'] == playable
    assert result['destinations'][0]['stem'] == STEM
    assert result['destinations'][0]['exists'] is False
    assert 'downtify_destination' not in SONG


def test_legacy_forced_album_does_not_reuse_indexed_playlist(tmp_path):
    d = Downloader(tmp_path / 'audio', folder_structure=None)
    old = d.download_dir / 'Playlist' / 'old.mp3'
    old.parent.mkdir(parents=True)
    _make_audio(old)
    index = TrackIndex(tmp_path / 'index.db')
    index.register_song(SONG, 'Playlist/old.mp3', full_path=old)
    assert resolve_existing_download(d, FORCED, track_index=index) is None


def test_forced_album_copies_local_source_even_with_leave_in_place(tmp_path, monkeypatch):
    from downtify import downloader as module
    source = tmp_path / 'source.mp3'
    _make_audio(source)
    d = Downloader(tmp_path / 'downloads', folder_structure=False, slskd_settings={'leave_in_place': True})
    monkeypatch.setattr(module._MetadataLookups, 'collect', lambda self: None)
    monkeypatch.setattr(d, '_tag_file', lambda *a, **kw: None)
    stored = d._finalize_local_source(FORCED, source, 'slskd', None, 'Playlist')
    assert stored == STEM + '.mp3'
    assert (d.download_dir / stored).read_bytes() == source.read_bytes()


def test_parallel_forced_and_playlist_contexts_keep_distinct_targets(tmp_path, monkeypatch):
    import threading
    from downtify import downloader as module
    d = Downloader(tmp_path, folder_structure=False, playlist_use_library=True)
    before = (d.folder_structure, d.playlist_use_library, d.output_template, d.overwrite_existing_files)
    monkeypatch.setattr(module.spotify_mod, 'enrich_track_from_spotify_if_sparse', lambda song: song)
    monkeypatch.setattr(d, '_resolve_source', lambda *a: ('video', None, 'youtube', None))
    writes = []
    def fetch(song, video, progress, subdir, provider):
        target, prefix, name = d._target_location(song, subdir)
        writes.append(prefix + name)
        _make_audio(target / (name + '.mp3'))
        return prefix + name + '.mp3'
    monkeypatch.setattr(d, '_fetch_and_tag', fetch)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda song: d.download(song, subdir='Playlist'), [FORCED, FORCED, dict(SONG, downtify_download_mode='missing')]))
    assert results[:2] == [STEM + '.mp3'] * 2
    assert results[2] == 'Playlist/Future, Drake, Young Thug - D4L.mp3'
    assert writes.count(STEM) == 1
    assert before == (d.folder_structure, d.playlist_use_library, d.output_template, d.overwrite_existing_files)
    assert d._target_lock(FORCED, 'Playlist') is d._target_lock(FORCED, None)
    assert d._target_lock(FORCED, None) is not d._target_lock(SONG, 'Playlist')


def test_parallel_forced_local_downloads_share_target_lock(tmp_path, monkeypatch):
    import threading
    from downtify import downloader as module
    source = tmp_path / 'source.mp3'
    _make_audio(source)
    d = Downloader(tmp_path / 'downloads', folder_structure=False)
    barrier = threading.Barrier(2)
    monkeypatch.setattr(module.spotify_mod, 'enrich_track_from_spotify_if_sparse', lambda song: song)
    def resolve(*args):
        barrier.wait(timeout=5)
        return None, None, 'slskd', source
    monkeypatch.setattr(d, '_resolve_source', resolve)
    monkeypatch.setattr(module._MetadataLookups, 'collect', lambda self: None)
    tagged = []
    monkeypatch.setattr(d, '_tag_file', lambda *a, **kw: tagged.append(a[0]))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: d.download(FORCED), range(2)))
    assert results == [STEM + '.mp3'] * 2
    assert len(tagged) == 1


def test_batch_endpoint_retains_album_controls(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    from tests.test_artist_top_songs_url import _FakeRequest
    monkeypatch.setattr(api.state, 'downloader', object())
    submit = AsyncMock(return_value={'count': 1})
    monkeypatch.setattr(api, '_submit_playlist_batch', submit)
    result = asyncio.run(api.download_batch_endpoint(_FakeRequest({'songs': [FORCED], 'generate_m3u': False})))
    assert result['count'] == 1
    assert submit.await_args.args[0][0]['downtify_destination'] == 'album'
    assert submit.await_args.args[0][0]['downtify_download_mode'] == 'missing'


@pytest.mark.parametrize('source', ['spotify', 'deezer', 'text_search'])
def test_single_endpoint_retains_album_controls_for_all_sources(tmp_path, monkeypatch, source):
    import asyncio
    from unittest.mock import AsyncMock
    from tests.test_artist_top_songs_url import _FakeRequest
    monkeypatch.setattr(api.state, 'downloader', Downloader(tmp_path, folder_structure=False))
    monkeypatch.setattr(api.state, 'download_jobs', {})
    monkeypatch.setattr(api, '_song_for_download', lambda url: dict(SONG))
    run = AsyncMock(return_value=STEM + '.mp3')
    monkeypatch.setattr(api, '_run_download', run)
    result = asyncio.run(api.download_endpoint(_FakeRequest({}), url='url', client_id='', client_hints=dict(FORCED, source=source)))
    assert result == STEM + '.mp3'
    assert run.await_args.args[0]['downtify_destination'] == 'album'
    assert run.await_args.args[0]['downtify_download_mode'] == 'missing'


def test_forced_same_target_skips_without_network_or_global_mutation(tmp_path, monkeypatch):
    d = Downloader(tmp_path, folder_structure=False, overwrite_existing_files=True)
    target, prefix, name = d._target_location(FORCED, None)
    _make_audio(target / (name + '.mp3'))
    monkeypatch.setattr(d, '_resolve_source', lambda *a: pytest.fail('same destination must skip'))
    assert d.download(FORCED, subdir='Playlist') == STEM + '.mp3'
    assert d.folder_structure is False
    assert d.overwrite_existing_files is True


def test_single_url_retains_per_request_controls(monkeypatch):
    monkeypatch.setattr(api, '_song_for_download', lambda url: dict(SONG))
    song = api._song_from_download_request('url', FORCED)
    assert song['downtify_destination'] == 'album'
    assert song['downtify_download_mode'] == 'missing'
