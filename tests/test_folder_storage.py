"""The exact storage matrix approved by the user, without network calls."""

import pytest

from downtify.downloader import Downloader

FULL = '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'
FLAT = '{artists} - {title}.{output-ext}'
SONG = dict(name='D4L', artists=['Future', 'Drake', 'Young Thug'], album_artist='Drake', album_name='Dark Lane Demo Tapes', release_date='2020-05-01', track_number=9, source='spotify', song_id='5fHrHoJKfCgBd35zwIBmUK')


@pytest.mark.parametrize(('structure', 'playlists'), [(True, True), (True, False), (False, True), (False, False)])
def test_individual_tracks_use_global_structure(tmp_path, structure, playlists):
    d = Downloader(tmp_path, output_template=FULL if structure else FLAT, folder_structure=structure, playlist_use_library=playlists)
    target, prefix, basename = d._expected_location(SONG, None)
    if structure:
        assert target == tmp_path / 'Drake' / 'Drake - Dark Lane Demo Tapes (2020)'
        assert basename == '09. Future, Drake, Young Thug - D4L'
    else:
        assert target == tmp_path
        assert basename == 'Future, Drake, Young Thug - D4L'


@pytest.mark.parametrize(('structure', 'playlists', 'folder'), [(True, True, 'Drake/Drake - Dark Lane Demo Tapes (2020)'), (True, False, 'My Playlist'), (False, True, 'My Playlist'), (False, False, '')])
def test_playlist_routing_matrix(tmp_path, structure, playlists, folder):
    d = Downloader(tmp_path, output_template=FULL if structure else FLAT, folder_structure=structure, playlist_use_library=playlists)
    target, prefix, basename = d._expected_location(SONG, 'My Playlist')
    assert target == tmp_path / folder
    assert prefix == (folder + '/' if folder else '')
    assert basename == ('09. ' if structure and playlists else '') + 'Future, Drake, Young Thug - D4L'
    assert d.uses_shared_playlist_storage is (structure == playlists)


def test_flat_setting_does_not_allow_stale_hierarchy_template(tmp_path):
    d = Downloader(tmp_path, output_template=FULL, folder_structure=False, playlist_use_library=False)
    target, _, basename = d._expected_location(SONG, 'My Playlist')
    assert target == tmp_path
    assert basename == 'Future, Drake, Young Thug - D4L'


def test_playlist_and_album_copies_have_distinct_existing_file_paths(tmp_path):
    d = Downloader(tmp_path, output_template=FULL, folder_structure=True, playlist_use_library=False)
    pl_dir, _, pl_name = d._target_location(SONG, 'My Playlist')
    (pl_dir / (pl_name + '.mp3')).write_bytes(b'test-fixture-not-audio')
    assert d.existing_filename_for(SONG, 'My Playlist') == 'My Playlist/Future, Drake, Young Thug - D4L.mp3'
    assert d.existing_filename_for(SONG) is None


def test_structured_missing_albumartist_cannot_skip_early(tmp_path):
    d = Downloader(tmp_path, output_template=FULL, folder_structure=True)
    incomplete = {k: v for k, v in SONG.items() if k != 'album_artist'}
    assert not d._can_resolve_path_early(incomplete)


def test_toggle_hot_update_changes_paths_without_restart(tmp_path):
    d = Downloader(tmp_path, output_template=FULL, folder_structure=True, playlist_use_library=True)
    d.playlist_use_library = False
    assert d._expected_location(SONG, 'My Playlist')[0] == tmp_path / 'My Playlist'
    d.folder_structure = False
    assert d._expected_location(SONG, 'My Playlist')[0] == tmp_path
    assert d._expected_location(SONG, None)[0] == tmp_path
