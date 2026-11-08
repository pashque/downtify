"""Backend storage-toggle settings and shared playlist routing."""
import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from downtify import api, monitor
from downtify.downloader import Downloader
from downtify.folder_settings import settings_use_shared_playlists
from downtify.library_delete import delete_playlist_from_library
from downtify.library_reconcile import refresh_playlists_after_moves
from downtify.playlist_catalog import PlaylistCatalog
from downtify.track_index import TrackIndex

FULL = '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'
FLAT = '{artists} - {title}.{output-ext}'


class Request:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


@pytest.fixture
def settings_state(monkeypatch, tmp_path):
    monkeypatch.setattr(api.state, 'settings', dict(api.DEFAULT_SETTINGS))
    monkeypatch.setattr(api.state, 'settings_path', tmp_path / 'settings.json')
    downloader = Downloader(tmp_path, organize_by_artist=True, organize_by_album=True)
    downloader.output_template = 'custom'
    downloader.folder_structure = None
    downloader.playlist_use_library = True
    monkeypatch.setattr(api.state, 'downloader', downloader)
    return api.state


def save(payload):
    return asyncio.run(api.update_settings_endpoint(Request(payload), client_id=''))


@pytest.mark.parametrize(('structured', 'shared'), [(True, True), (True, False), (False, True), (False, False)])
def test_toggle_update_resets_template_and_hot_updates(settings_state, structured, shared):
    result = save({'folder_structure': structured, 'playlist_use_library': shared, 'output': 'stale'})
    expected = FULL if structured else FLAT
    assert result['output'] == expected
    assert settings_state.downloader.output_template == expected.replace('.{output-ext}', '')
    assert settings_state.downloader.folder_structure is structured
    assert settings_state.downloader.playlist_use_library is shared
    assert result['organize_by_artist'] is False
    assert result['organize_by_album'] is False
    assert settings_state.downloader.organize_by_artist is False
    assert settings_state.downloader.organize_by_album is False
    assert api._load_settings(settings_state.settings_path)['folder_structure'] is structured
    # Full frontend payloads with unchanged toggles must not erase manual edits.
    result = save({**result, 'output': 'manual/{title}.{output-ext}'})
    assert result['output'] == 'manual/{title}.{output-ext}'
    assert settings_state.downloader.output_template == 'manual/{title}'
    result = save({'playlist_use_library': not shared})
    assert result['output'] == expected


@pytest.mark.parametrize(('key', 'value'), [('folder_structure', 'false'), ('folder_structure', 1), ('playlist_use_library', None), ('playlist_use_library', 'true'), ('playlist_use_library', 0)])
def test_toggle_validation_is_atomic(settings_state, key, value):
    before = dict(settings_state.settings)
    with pytest.raises(HTTPException) as error:
        save({'output': 'must not change', key: value})
    assert error.value.status_code == 400
    assert settings_state.settings == before
    assert settings_state.downloader.output_template == 'custom'
    assert not settings_state.settings_path.exists()


@pytest.mark.parametrize(('routing', 'expected'), [((True, True), True), ((True, False), False), ((False, True), False), ((False, False), True)])
def test_shared_playlist_routing(settings_state, routing, expected, monkeypatch, tmp_path):
    structured, shared = routing
    settings_state.settings.update(folder_structure=structured, playlist_use_library=shared,
                                   organize_by_artist=False, organize_by_album=False)
    d = settings_state.downloader
    d.folder_structure = structured
    d.playlist_use_library = shared
    d.organize_by_artist = d.organize_by_album = False
    assert api._organize_enabled() is expected
    assert api._playlist_subdir_for_name('Mix') == (None if expected else 'Mix')
    assert settings_use_shared_playlists(settings_state.settings) is expected
    song = {'song_id': 'id', 'name': 'Song', 'artists': ['Artist']}
    (tmp_path / 'song.mp3').write_bytes(b'audio')
    asyncio.run(api._write_batch_m3u([song], {0: 'song.mp3'}, 'Mix', 'Mix'))
    target = tmp_path / ('Playlists' if expected else 'Mix') / 'Mix.m3u'
    assert target.exists()
    playlist = SimpleNamespace(name='Mix', source='spotify', spotify_id='pid')
    assert monitor._regenerate_m3u(playlist, [song], d, resolved={'id': 'song.mp3'}) == target
    covers = []
    monkeypatch.setattr(monitor, 'download_playlist_cover', lambda source, pid, path, settings: covers.append(path))
    monitor._download_cover_for_watch(playlist, d, settings_state.settings)
    assert covers == [target]


def test_mock_legacy_downloader_does_not_invent_new_flags(settings_state, monkeypatch):
    d = MagicMock()
    d.organize_by_artist = d.organize_by_album = False
    monkeypatch.setattr(api.state, 'downloader', d)
    assert api._organize_enabled() is False


def test_property_overrides_legacy_flags(settings_state, monkeypatch):
    monkeypatch.setattr(api.state, 'downloader', SimpleNamespace(
        uses_shared_playlist_storage=False, organize_by_artist=True, organize_by_album=True))
    assert api._organize_enabled() is False


@pytest.mark.parametrize(('structured', 'shared', 'expected_subdir'), [(None, True, 'Mix'), (True, True, None), (True, False, 'Mix'), (False, True, 'Mix'), (False, False, None)])
def test_batch_only_passes_own_folder_in_separate_mode(settings_state, monkeypatch, structured, shared, expected_subdir):
    d = settings_state.downloader
    d.folder_structure, d.playlist_use_library = structured, shared
    d.organize_by_artist = d.organize_by_album = structured is None
    seen = []

    async def download(song, song_id, subdir=None, **kwargs):
        seen.append(subdir)
    monkeypatch.setattr(api, '_run_download', download)
    asyncio.run(api._process_batch([{'song_id': 'id', 'name': 'Song'}], ['job'], '', False, playlist_name='Mix'))
    assert seen == [expected_subdir]


def test_main_passes_storage_settings_to_downloader():
    tree = ast.parse((Path(__file__).parents[1] / 'main.py').read_text())
    constructors = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name) and node.func.id == 'Downloader']
    assert len(constructors) == 1
    assert {'folder_structure', 'playlist_use_library'} <= {kw.arg for kw in constructors[0].keywords}


@pytest.mark.parametrize(('structured', 'shared', 'expected'), [(True, True, True), (True, False, False), (False, True, False), (False, False, True)])
def test_library_delete_only_scans_owned_playlist_folder(tmp_path, structured, shared, expected):
    download_dir = tmp_path / 'downloads'
    folder = download_dir / 'Mix'
    folder.mkdir(parents=True)
    unrelated = folder / 'unrelated.mp3'
    unrelated.write_bytes(b'audio')
    catalog = PlaylistCatalog(tmp_path / 'library.db')
    catalog.ensure_playlist('Mix')
    state = SimpleNamespace(playlist_catalog=catalog, track_index=TrackIndex(tmp_path / 'library.db'),
                            cover_cache=None, metadata_cache=None, navidrome_index=None)
    settings = {'folder_structure': structured, 'playlist_use_library': shared,
                'organize_by_artist': False, 'organize_by_album': False}
    result = delete_playlist_from_library('Mix', download_dir, settings, state)
    assert result['ok']
    assert unrelated.exists() is expected


@pytest.mark.parametrize(('structured', 'shared', 'expected'), [(True, True, True), (True, False, False), (False, True, False), (False, False, True)])
def test_library_reconcile_m3u_uses_storage_policy(settings_state, tmp_path, structured, shared, expected):
    audio = tmp_path / 'song.mp3'
    audio.write_bytes(b'audio')
    catalog = PlaylistCatalog(tmp_path / 'library.db')
    catalog.replace_playlist_tracks('Mix', [({'song_id': '4uLU6hMCjMI75M1A2tKUQC', 'name': 'Song', 'artists': ['Artist']}, 'song.mp3', audio)])
    settings = {'folder_structure': structured, 'playlist_use_library': shared,
                'organize_by_artist': False, 'organize_by_album': False, 'generate_m3u': True}
    refresh_playlists_after_moves({'Mix'}, settings=settings, downloader=settings_state.downloader,
                                  playlist_catalog=catalog, delete_tag_mismatches=False)
    assert (tmp_path / ('Playlists' if expected else 'Mix') / 'Mix.m3u').exists()


def test_legacy_defaults_and_disk_roundtrip(tmp_path):
    fresh = api._load_settings(tmp_path / 'missing.json')
    assert fresh.get('folder_structure', 'missing') is None
    assert fresh['playlist_use_library'] is True
    path = tmp_path / 'old.json'
    path.write_text(json.dumps({'output': 'custom', 'organize_by_album': True}))
    loaded = api._load_settings(path)
    assert loaded['folder_structure'] is None
    assert loaded['output'] == 'custom'
    assert loaded['organize_by_album'] is True
    loaded.update(folder_structure=False, playlist_use_library=False)
    api._save_settings(path, loaded)
    assert api._load_settings(path) == loaded
