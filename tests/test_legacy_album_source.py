"""Legacy recovery must prove an edition, not infer it from search ranking."""

import asyncio
import copy
import json
from pathlib import Path

import pytest
from mutagen.id3 import ID3, TRCK, TXXX

from downtify import album_source, api, library_catalog, spotify
from downtify.album_source import enrich_legacy_edition, resolve_album_source
from downtify.download_destination import destination_status
from downtify.track_index import TrackIndex, resolve_existing_download
from tests.test_destination_dedupe import SONG, setup_playlist


@pytest.fixture(autouse=True)
def _strict_layer_only(monkeypatch):
    # These tests guard the exact-fingerprint layer; the best-effort search
    # fallback is covered by tests/test_album_source_loose.py.

    monkeypatch.setattr(album_source, '_loose_versions', lambda *a, **k: [])


@pytest.fixture
def legacy():
    local = [
        dict(
            file=f'Artist/Album/0{i}. Artist - Track {i}.mp3',
            title=f'Track {i}',
            artist='Artist',
            album_artist='Artist',
            album='Album',
            year='2019',
            track_number=i,
            duration=100 + i + 0.4,
        )
        for i in range(1, 4)
    ]
    source = [
        dict(
            song_id=str(i) * 22,
            name=f'Track {i}',
            artists=['Artist'],
            album_artist='Artist',
            album_name='Album',
            release_date='2019-01-01',
            track_number=i,
            duration=100 + i,
            album_track_total=3,
        )
        for i in range(1, 4)
    ]
    return local, source


def test_rich_legacy_recovery_preserves_source_metadata(
    legacy, tmp_path, monkeypatch
):
    local, source = legacy
    source[1]['name'] = 'Track 2 (feat. Guest)'
    source[1]['artists'] = ['Artist', 'Guest']
    local[1]['artist'] = 'Artist; Guest'
    before = copy.deepcopy((local, source))
    calls = []
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: (
            calls.append(query)
            or {
                'albums': [
                    dict(
                        id='A' * 22,
                        name='Album',
                        artists=['Artist'],
                        year='2019',
                    )
                ]
            }
        ),
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = resolve_album_source(
        local, 'Album', TrackIndex(tmp_path / 'index.db')
    )
    assert result['status'] == 'resolved'
    assert calls == ['Artist Album']
    assert result['tracks'] == source
    assert result['local_matches'] == {
        row['song_id']: [local[i]['file']] for i, row in enumerate(source)
    }
    assert (local, source) == before


@pytest.mark.parametrize(
    ('local_count', 'resource_type'), [(1, 'ALBUM'), (2, 'EP'), (1, 'SINGLE')]
)
def test_few_complete_fingerprints_expand_full_source(
    legacy, tmp_path, monkeypatch, local_count, resource_type
):
    local, source = legacy
    local = local[:local_count]
    before = copy.deepcopy((local, source))
    calls = []
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type=resource_type,
                )
            ]
        },
    )
    monkeypatch.setattr(
        spotify,
        'album_tracks_from_id',
        lambda aid: calls.append(aid) or source,
    )
    result = resolve_album_source(
        local, 'Album', TrackIndex(tmp_path / 'index.db')
    )
    assert result['status'] == 'resolved'
    assert result['tracks'] == source
    assert result['local_matches'] == {
        source[i]['song_id']: [row['file']] for i, row in enumerate(local)
    }
    assert calls == ['A' * 22]
    assert (local, source) == before


@pytest.mark.parametrize(
    'artists', [['Artist', 'Guest'], ['Earth, Wind & Fire']]
)
def test_candidate_artist_matches_provider_joined_album_credit(
    legacy, tmp_path, monkeypatch, artists
):
    local, source = legacy
    credit = ', '.join(artists)
    local = [dict(local[0], album_artist=credit)]
    source = [dict(row, album_artist=credit) for row in source]
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(id='A' * 22, name='Album', artists=artists, year='2019')
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    assert (
        resolve_album_source(
            local, 'Album', TrackIndex(tmp_path / 'index.db')
        )['status']
        == 'resolved'
    )


@pytest.mark.parametrize('candidate_count', [5, 6])
def test_legacy_candidate_expansion_is_bounded(
    legacy, tmp_path, monkeypatch, candidate_count
):
    local, source = legacy
    albums = [
        dict(
            id=chr(65 + i) * 22, name='Album', artists=['Artist'], year='2019'
        )
        for i in range(candidate_count)
    ]
    calls = []
    monkeypatch.setattr(spotify, 'search', lambda query: {'albums': albums})
    monkeypatch.setattr(
        spotify,
        'album_tracks_from_id',
        lambda aid: calls.append(aid) or source,
    )
    # Up to 5 verified versions are offered in the version selector; more stay offline.
    result = resolve_album_source(
        local[:1], 'Album', TrackIndex(tmp_path / 'i.db')
    )
    assert result['status'] == (
        'resolved' if candidate_count == 5 else 'unavailable'
    )
    if candidate_count == 5:
        assert len(result['editions']) == 5
    assert calls == (
        [row['id'] for row in albums] if candidate_count == 5 else []
    )


@pytest.mark.parametrize(
    'field',
    [
        'album_artist',
        'album',
        'year',
        'track_number',
        'artist',
        'duration',
        'title',
    ],
)
def test_single_legacy_file_requires_every_fingerprint_field(
    legacy, tmp_path, monkeypatch, field
):
    local, _ = legacy
    local = [dict(local[0])]
    local[0].pop(field)
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: pytest.fail('incomplete fingerprint must stay offline'),
    )
    assert (
        resolve_album_source(local, 'Album', TrackIndex(tmp_path / 'i.db'))[
            'status'
        ]
        == 'unavailable'
    )


@pytest.mark.parametrize('total', [1, 3, None, 'bad', '1/3'])
def test_trusted_local_total_disambiguates_single_from_ep(
    legacy, tmp_path, monkeypatch, total
):
    local, source = legacy
    local = [dict(local[0])]
    if total is not None:
        local[0]['album_track_total'] = total
    single = [dict(source[0], album_track_total=1)]
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type='SINGLE',
                ),
                dict(
                    id='B' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type='EP',
                ),
            ]
        },
    )
    monkeypatch.setattr(
        spotify,
        'album_tracks_from_id',
        lambda aid: single if aid == 'A' * 22 else source,
    )
    result = resolve_album_source(
        local, 'Album', TrackIndex(tmp_path / 'i.db')
    )
    if total in {1, 3, None}:
        # A file's total names its source version but never hides another one:
        # every verified version is offered, fullest first.
        assert result['status'] == 'resolved'
        assert [e['track_count'] for e in result['editions']] == [3, 1]
        assert len(result['tracks']) == 3
    else:
        assert result['status'] == 'unavailable'


@pytest.mark.parametrize('tag_number', ['1/1', '1/3', '1', '1/bad'])
def test_source_endpoint_reads_total_from_visible_file_not_cache(
    legacy, tmp_path, monkeypatch, tag_number
):

    local, source = legacy
    local = [dict(local[0], album_track_total=99)]
    before = copy.deepcopy(local)
    path = tmp_path / 'visible.mp3'
    tags = ID3()
    tags.add(TRCK(encoding=3, text=[tag_number]))
    tags.save(path)
    original_bytes = path.read_bytes()
    single = [dict(source[0], album_track_total=1)]
    monkeypatch.setattr(
        api.state, 'track_index', TrackIndex(tmp_path / 'i.db')
    )
    monkeypatch.setattr(api, 'entries_for_request', lambda req: local)
    monkeypatch.setattr(
        library_catalog, 'resolve_library_file', lambda file, ctx: path
    )
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type='SINGLE',
                ),
                dict(
                    id='B' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type='EP',
                ),
            ]
        },
    )
    monkeypatch.setattr(
        spotify,
        'album_tracks_from_id',
        lambda aid: single if aid == 'A' * 22 else source,
    )
    result = api.library_album_source(object(), 'Artist', 'Album')
    # Tags from the visible file are read but never hide a verified version.
    assert [e['track_count'] for e in result['editions']] == [3, 1]
    assert local == before
    assert path.read_bytes() == original_bytes


def test_single_tag_cannot_disambiguate_equal_length_ep_family(
    legacy, tmp_path, monkeypatch
):

    local, source = legacy
    path = tmp_path / 'visible.mp3'
    tags = ID3()
    tags.add(TRCK(encoding=3, text=['1/3']))
    tags.add(TXXX(encoding=3, desc='MusicBrainz Album Type', text=['single']))
    tags.save(path)
    enriched = enrich_legacy_edition(local[0], path)
    assert enriched['album_type'] == 'SINGLE'
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type='SINGLE',
                ),
                dict(
                    id='B' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type='EP',
                ),
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = resolve_album_source(
        [enriched], 'Album', TrackIndex(tmp_path / 'i.db')
    )
    # Spotify tags classify EPs as singles, so this is not edition evidence:
    # both verified versions are offered in the version selector.
    assert len(result['editions']) == 2


def test_real_three_playlist_files_recover_full_fifteen(tmp_path, monkeypatch):

    fixtures = Path(__file__).parent / 'fixtures'
    local = json.loads((fixtures / 'legacy_loyle_local.json').read_text())
    source = json.loads((fixtures / 'legacy_loyle_source.json').read_text())
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22,
                    name=local[0]['album'],
                    artists=[local[0]['album_artist']],
                    year='2019',
                )
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = resolve_album_source(
        local, local[0]['album'], TrackIndex(tmp_path / 'index.db')
    )
    assert result['status'] == 'resolved'
    assert len(result['tracks']) == 15
    assert len(result['local_matches']) == 3
    assert all(
        f.startswith('My Playlist #1/')
        for files in result['local_matches'].values()
        for f in files
    )


def test_verified_copies_are_parent_scoped_and_invalidate_on_change(tmp_path):

    d, index, old = setup_playlist(tmp_path)
    legacy = old.with_name('Old credit punctuation.mp3')
    old.rename(legacy)
    name = 'My Playlist/' + legacy.name
    index.register_source_copy(SONG, name, legacy)
    assert index.source_copies_for_song(SONG) == [name]
    assert (
        resolve_existing_download(
            d, SONG, subdir='My Playlist', track_index=index
        )[0]
        == name
    )
    assert resolve_existing_download(d, SONG, track_index=index) is None
    assert not destination_status(d, SONG, track_index=index)['exists']
    assert (
        destination_status(d, SONG, 'My Playlist', track_index=index)['file']
        == name
    )
    assert not destination_status(
        d, SONG, 'Another Playlist', track_index=index
    )['exists']
    legacy.write_bytes(b'replaced unrelated audio')
    assert index.source_copies_for_song(SONG) == []


def test_source_endpoint_ignores_stale_metadata_and_registers_only_visible_copies(
    legacy, tmp_path, monkeypatch
):

    local, source = legacy
    stale = dict(local[0], file='missing.mp3', title='Wrong stale title')
    index = TrackIndex(tmp_path / 'index.db')
    paths = {}
    for row in local:
        path = tmp_path / row['file']
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'audio')
        paths[row['file']] = path
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(
        api, 'entries_for_request', lambda req: local + [stale]
    )
    monkeypatch.setattr(
        library_catalog,
        'resolve_library_file',
        lambda file, ctx: paths.get(file),
    )
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22, name='Album', artists=['Artist'], year='2019'
                )
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = api.library_album_source(object(), 'Artist', 'Album')
    assert result['status'] == 'resolved'
    assert index.source_copies_for_song(source[0]) == [local[0]['file']]
    assert 'missing.mp3' not in str(result['local_matches'])


@pytest.mark.parametrize('local_count', [1, 2, 3])
@pytest.mark.parametrize(
    'change',
    [
        'year',
        'artist',
        'duration',
        'title',
        'total',
        'ambiguous',
        'incomplete',
        'number',
    ],
)
def test_legacy_rejects_weak_or_ambiguous_editions(
    legacy, tmp_path, monkeypatch, change, local_count
):
    local, source = legacy
    local = local[:local_count]
    albums = [dict(id='A' * 22, name='Album', artists=['Artist'], year='2019')]
    if change == 'year':
        albums[0]['year'] = '2020'
    if change == 'artist':
        source[0]['album_artist'] = 'Other'
    if change == 'duration':
        source[0]['duration'] += 6
    if change == 'title':
        source[0]['name'] += ' (Live)'
    if change == 'total':
        source[0]['album_track_total'] = 4
    if change == 'ambiguous':
        albums.append(dict(albums[0], id='B' * 22))
    if change == 'incomplete':
        local[0].pop('duration')
    # A renumbered (deluxe) file may match a unique fingerprint elsewhere;
    # a wrong number with no matching track anywhere must still fail.
    if change == 'number':
        local[0]['track_number'] = 99
        source[0]['name'] = 'Elsewhere'
    monkeypatch.setattr(spotify, 'search', lambda query: {'albums': albums})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = resolve_album_source(
        local, 'Album', TrackIndex(tmp_path / 'i.db')
    )
    if change == 'ambiguous':
        # Equally verified versions are listed for the user to choose.
        assert [e['id'] for e in result['editions']] == ['A' * 22, 'B' * 22]
    else:
        assert result['status'] == 'unavailable'


def test_lookup_uses_verified_visible_identity_not_client_file_hints(
    tmp_path, monkeypatch
):

    d, index, old = setup_playlist(tmp_path)
    name = 'My Playlist/' + old.name
    index.register_source_copy(SONG, name, old)
    monkeypatch.setattr(api.state, 'downloader', d)
    monkeypatch.setattr(api.state, 'track_index', index)
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda req: None)
    monkeypatch.setattr(api, 'lookup_library_songs', lambda *a, **kw: [])
    monkeypatch.setattr(
        api, 'filter_paths_for_request', lambda paths, req: paths
    )
    visible = [dict(file=name, title='Legacy title', artist='Legacy credit')]
    monkeypatch.setattr(api, 'entries_for_request', lambda req: visible)
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: pytest.fail('lookup must stay offline'),
    )

    class Request:
        @staticmethod
        async def json():
            return dict(
                songs=[dict(SONG, file='untrusted.mp3')],
                destination_status=True,
                destination='album',
            )

    result = asyncio.run(api.library_lookup(Request()))
    assert result['tracks'] == [dict(visible[0], song_id=SONG['song_id'])]
    assert not result['destinations'][0]['exists']
    visible.clear()
    assert asyncio.run(api.library_lookup(Request()))['tracks'] == []


@pytest.mark.parametrize('field', ['track_number', 'album_track_total'])
def test_provider_numeric_strings_preserve_exact_identity(
    legacy, tmp_path, monkeypatch, field
):
    local, source = legacy
    local = local[:1]
    for row in source:
        row[field] = str(row[field])
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22, name='Album', artists=['Artist'], year='2019'
                )
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = resolve_album_source(
        local, 'Album', TrackIndex(tmp_path / 'i.db')
    )
    assert result['status'] == 'resolved'
    assert result['tracks'] == source


def test_one_track_ep_accepts_case_variant_provider_type(
    legacy, tmp_path, monkeypatch
):
    local, source = legacy
    local = [dict(local[0], album_type='EP', album_track_total=1)]
    source = [dict(source[0], album_track_total=1)]
    before = copy.deepcopy((local, source))
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22,
                    name='Album',
                    artists=['Artist'],
                    year='2019',
                    type='ep',
                )
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = resolve_album_source(
        local, 'Album', TrackIndex(tmp_path / 'i.db')
    )
    assert result['status'] == 'resolved'
    assert result['tracks'] == source
    assert (local, source) == before


@pytest.mark.parametrize('local_count', [1, 2])
def test_actual_legacy_file_subset_recovers_full_source(
    tmp_path, monkeypatch, local_count
):

    fixtures = Path(__file__).parent / 'fixtures'
    local = json.loads((fixtures / 'legacy_loyle_local.json').read_text())[
        :local_count
    ]
    source = json.loads((fixtures / 'legacy_loyle_source.json').read_text())
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22,
                    name=local[0]['album'],
                    artists=[local[0]['album_artist']],
                    year='2019',
                )
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    result = resolve_album_source(
        local, local[0]['album'], TrackIndex(tmp_path / 'i.db')
    )
    assert result['status'] == 'resolved'
    assert result['tracks'] == source
    assert len(result['local_matches']) == local_count


@pytest.mark.parametrize('sample_index', [0, 1, 2])
def test_actual_library_samples_with_physical_tag_totals(
    tmp_path, monkeypatch, sample_index
):

    sample = json.loads(
        (
            Path(__file__).parent / 'fixtures' / 'legacy_library_samples.json'
        ).read_text()
    )[sample_index]
    local = [
        dict(row, file=row['filename']) for row in sample['local']['rows']
    ]
    before = copy.deepcopy(sample)
    total = [1, 7, 3][sample_index]
    paths = {}
    for row in local:
        path = tmp_path / row['file']
        path.parent.mkdir(parents=True, exist_ok=True)
        tags = ID3()
        tags.add(TRCK(encoding=3, text=[f'{row["track_number"]}/{total}']))
        tags.save(path)
        paths[row['file']] = path
    original = {key: path.read_bytes() for key, path in paths.items()}
    monkeypatch.setattr(
        api.state, 'track_index', TrackIndex(tmp_path / 'i.db')
    )
    monkeypatch.setattr(api, 'entries_for_request', lambda req: local)
    monkeypatch.setattr(
        library_catalog,
        'resolve_library_file',
        lambda file, ctx: paths.get(file),
    )
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {'albums': [s['album'] for s in sample['sources']]},
    )
    monkeypatch.setattr(
        spotify,
        'album_tracks_from_id',
        lambda aid: next(
            s['tracks'] for s in sample['sources'] if s['album']['id'] == aid
        ),
    )
    result = api.library_album_source(
        object(), sample['local']['artist'], sample['local']['album']
    )
    assert result['status'] == 'resolved'
    # The file's own version is always offered; the fullest version opens first.
    assert total in [e['track_count'] for e in result['editions']]
    assert len(result['tracks']) == max(
        e['track_count'] for e in result['editions']
    )
    fullest = max(
        (
            s
            for s in sample['sources']
            if s['album']['id'] in {e['id'] for e in result['editions']}
        ),
        key=lambda s: len(s['tracks']),
    )
    assert result['tracks'] == fullest['tracks']
    assert len(result['local_matches']) == len(local)
    assert sample == before
    assert {key: path.read_bytes() for key, path in paths.items()} == original


def test_string_track_numbers_remain_valid_fingerprints(
    legacy, tmp_path, monkeypatch
):
    local, source = legacy
    for row in local:
        row['track_number'] = str(row['track_number'])
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {
            'albums': [
                dict(
                    id='A' * 22, name='Album', artists=['Artist'], year='2019'
                )
            ]
        },
    )
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    assert (
        resolve_album_source(local, 'Album', TrackIndex(tmp_path / 'i.db'))[
            'status'
        ]
        == 'resolved'
    )
