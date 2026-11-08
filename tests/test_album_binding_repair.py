import hashlib
from pathlib import Path

import pytest

from downtify.album_binding_repair import repair_bindings
from downtify.auth import ADMIN, classify
from downtify.library_catalog import LibraryContext
from downtify.track_index import TrackIndex


@pytest.fixture
def case(tmp_path):
    root = tmp_path / 'music'
    root.mkdir()
    file = root / 'one.mp3'
    file.write_bytes(b'original audio bytes')
    index = TrackIndex(tmp_path / 'index.db')
    row = dict(
        file='one.mp3',
        title='One',
        artists=['+++'],
        artist='+++',
        album='Album +',
        album_artist='+++',
        track_number=1,
        year='2021',
        duration=180,
    )
    song = dict(
        song_id='A' * 22,
        name='One',
        artists=['+++'],
        album_name='Album +',
        album_artist='+++',
        track_number=1,
        release_date='2021-10-22',
        duration=181,
    )
    plan = [
        dict(
            file='one.mp3',
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        )
    ]
    return (
        LibraryContext(download_dir=root, track_index=index),
        index,
        [row],
        [song],
        plan,
        file,
    )


def test_dry_run_and_atomic_alias_repair_preserve_audio_and_original_binding(
    case,
):
    ctx, index, rows, songs, plan, file = case
    index.register('B' * 22, 'one.mp3')
    before = file.read_bytes()
    dry = repair_bindings(ctx, index, rows, songs, plan)
    assert dry['candidates'] == 1
    assert not index.source_copies_for_song(
        songs[0]
    )
    out = repair_bindings(ctx, index, rows, songs, plan, dry_run=False)
    assert out['applied'] == 1
    assert index.source_copies_for_song(songs[0]) == [
        'one.mp3'
    ]
    assert index.lookup('B' * 22) == 'one.mp3'
    assert file.read_bytes() == before

    assert Path(out['backup']).is_file()


@pytest.mark.parametrize(
    'fault', ['hash', 'title', 'artist', 'duration', 'position', 'missing']
)
def test_invalid_manifest_or_fingerprint_cannot_write(case, fault):
    ctx, index, rows, songs, plan, file = case
    if fault == 'hash':
        plan[0]['sha256'] = '0' * 64
    if fault == 'title':
        songs[0]['name'] = 'One +'
    if fault == 'artist':
        songs[0]['artists'] = ['Other']
    if fault == 'duration':
        songs[0]['duration'] = 250
    if fault == 'position':
        songs[0]['track_number'] = 2
    if fault == 'missing':
        plan = []
    with pytest.raises(ValueError):
        repair_bindings(ctx, index, rows, songs, plan, dry_run=False)
    assert not index.source_copies_for_song(songs[0])


def test_valid_subset_does_not_claim_an_unchecked_track(case):
    ctx, index, rows, songs, plan, file = case
    other = dict(songs[0], song_id='C' * 22, name='Other', track_number=2)
    result = repair_bindings(
        ctx, index, rows, [*songs, other], plan, dry_run=False
    )
    assert result['applied'] == 1
    assert index.source_copies_for_song(other) == []


def test_repair_route_is_explicitly_admin_only():

    assert classify('POST', '/api/library/album/bindings/repair') == ADMIN
