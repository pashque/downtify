"""Real-library cases that previously stayed local-only (Her Loss, EP suffixes, deluxe order)."""
import pytest

from downtify import album_source, spotify
from downtify.album_source import resolve_album_source
from downtify.track_index import TrackIndex


@pytest.fixture(autouse=True)
def _strict_layer_only(monkeypatch):
    # Exact layer only; the search fallback is in test_album_source_loose.py.
    monkeypatch.setattr(album_source, '_loose_versions', lambda *a, **k: [])


def _source(album, explicit, prefix):
    return [dict(song_id=(prefix + str(i)) * 11, name=f'Track {i}', artists=['Drake', '21 Savage'],
                 album_artist='Drake', album_name=album, release_date='2022-11-04',
                 track_number=i, duration=200 + i, album_track_total=4, explicit=explicit)
            for i in range(1, 5)]


def _local(album, explicit=None, n=2):
    row = dict(file=f'x/0{n}.mp3', title=f'Track {n}', artist='Drake; 21 Savage',
               album_artist='Drake', album=album, year='2022', track_number=n, duration=200 + n + .3)
    if explicit is not None:
        row['explicit'] = explicit
    return [row]


# Untagged files read as explicit=False, so that is not evidence: explicit opens first.
@pytest.mark.parametrize(('local_explicit', 'expected'), [(True, 'E'), (False, 'E'), (None, 'E')])
def test_explicit_and_clean_twins_resolve_instead_of_failing(tmp_path, monkeypatch, local_explicit, expected):
    sources = {'E' * 22: _source('Her Loss', True, 'E'), 'C' * 22: _source('Her Loss', False, 'C')}
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id=k, name='Her Loss', artists=['Drake', '21 Savage'], year='2022', type='ALBUM') for k in sources]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: sources[aid])
    out = resolve_album_source(_local('Her Loss', local_explicit), 'Her Loss', TrackIndex(tmp_path / 'i.db'))
    assert out['status'] == 'resolved'
    assert len(out['tracks']) == 4
    assert out['url'].endswith(expected * 22)


def test_all_verified_versions_listed_fullest_first_and_selectable(tmp_path, monkeypatch):
    standard = _source('Her Loss', True, 'S')
    deluxe = _source('Her Loss', True, 'D') + [dict(_source('Her Loss', True, 'D')[0], song_id='X' * 22,
                                                    name='Bonus', track_number=5)]
    for t in deluxe:
        t['album_track_total'] = 5
    sources = {'S' * 22: standard, 'D' * 22: deluxe}
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id=k, name='Her Loss', artists=['Drake'], year='2022') for k in sources]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: sources[aid])
    out = resolve_album_source(_local('Her Loss'), 'Her Loss', TrackIndex(tmp_path / 'i.db'))
    assert out['edition'] == 'D' * 22
    assert len(out['tracks']) == 5
    assert [(e['id'], e['track_count']) for e in out['editions']] == [('D' * 22, 5), ('S' * 22, 4)]
    picked = resolve_album_source(_local('Her Loss'), 'Her Loss', TrackIndex(tmp_path / 'i.db'), 'S' * 22)
    assert picked['edition'] == 'S' * 22
    assert len(picked['tracks']) == 4
    # Explicit source selection must not silently rebind existing files.
    assert picked['local_matches'] == {}
    # An unknown edition id cannot select anything outside the verified set.
    other = resolve_album_source(_local('Her Loss'), 'Her Loss', TrackIndex(tmp_path / 'i.db'), 'Z' * 22)
    assert other == {'status': 'unavailable', 'tracks': []}


def test_version_missing_a_local_file_is_not_offered(tmp_path, monkeypatch):
    a, b = _source('Her Loss', True, 'E'), _source('Her Loss', True, 'C')
    b[1]['name'] = 'Something else'
    sources = {'E' * 22: a, 'C' * 22: b}
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id=k, name='Her Loss', artists=['Drake'], year='2022') for k in sources]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: sources[aid])
    out = resolve_album_source(_local('Her Loss'), 'Her Loss', TrackIndex(tmp_path / 'i.db'))
    assert [e['id'] for e in out['editions']] == ['E' * 22]


@pytest.mark.parametrize(('local_title', 'remote_title'), [
    ('Sad But Ambitious EP', 'Sad But Ambitious'),
    ('WORSHIP FRIENDSHIP (COMPILATION)', 'WORSHIP FRIENDSHIP'),
    ('Fourfit EP05', 'Fourfit EP 05'),
    ('Night Drive - EP', 'Night Drive'),
])
def test_strict_identity_keeps_release_type_suffix_and_spacing(tmp_path, monkeypatch, local_title, remote_title):
    source = _source(remote_title, True, 'E')
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id='E' * 22, name=remote_title, artists=['Drake'], year='2022')]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    out = resolve_album_source(_local(local_title), local_title, TrackIndex(tmp_path / 'i.db'))
    assert out['status'] == 'unavailable'


def test_suffixed_title_retries_search_without_suffix(tmp_path, monkeypatch):
    source = _source('WORSHIP FRIENDSHIP', True, 'E')
    queries = []

    def search(q):
        queries.append(q)
        return {'albums': [dict(id='E' * 22, name='WORSHIP FRIENDSHIP', artists=['Drake'], year='2022')]
                if 'COMPILATION' not in q else [dict(id='Z' * 22, name='Share', artists=['Other'], year='2015')]}
    monkeypatch.setattr(spotify, 'search', search)
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    title = 'WORSHIP FRIENDSHIP (COMPILATION)'
    out = resolve_album_source(_local(title), title, TrackIndex(tmp_path / 'i.db'))
    assert out['status'] == 'unavailable'
    assert queries == [f'Drake {title}', 'Drake WORSHIP FRIENDSHIP']


def test_one_unreadable_version_does_not_hide_the_others(tmp_path, monkeypatch):
    source = _source('Her Loss', True, 'E')

    def tracks(aid):
        if aid == 'B' * 22:
            raise ValueError('Spotify entity not found in embed payload')
        return source
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id=k, name='Her Loss', artists=['Drake'], year='2022') for k in ('B' * 22, 'E' * 22)]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', tracks)
    out = resolve_album_source(_local('Her Loss'), 'Her Loss', TrackIndex(tmp_path / 'i.db'))
    assert [e['id'] for e in out['editions']] == ['E' * 22]


def test_different_words_are_still_different_albums(tmp_path, monkeypatch):
    source = _source('Her Loss Remix', True, 'E')
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id='E' * 22, name='Her Loss Remix', artists=['Drake'], year='2022')]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    assert resolve_album_source(_local('Her Loss'), 'Her Loss', TrackIndex(tmp_path / 'i.db'))['status'] == 'unavailable'


def test_deluxe_track_found_by_unique_title_when_numbering_differs(tmp_path, monkeypatch):
    album = 'The Melodic Blue (Deluxe)'
    source = [dict(song_id=str(i) * 22, name=n, artists=a, album_artist='Baby Keem', album_name=album,
                   release_date='2022-10-28', track_number=i, duration=d, album_track_total=3)
              for i, (n, a, d) in enumerate([('trademark usa', ['Baby Keem'], 250),
                                             ('lost souls', ['Baby Keem', 'Brent Faiyaz'], 270),
                                             ('cocoa', ['Baby Keem', 'Don Toliver'], 180)], 1)]
    local = [dict(file='k/01.mp3', title='lost souls (with Brent Faiyaz)', artist='Baby Keem; Brent Faiyaz',
                  album_artist='Baby Keem', album=album, year='2022', track_number=1, duration=269.76)]
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [dict(id='K' * 22, name=album, artists=['Baby Keem'], year='2022')]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    out = resolve_album_source(local, album, TrackIndex(tmp_path / 'i.db'))
    assert out['status'] == 'resolved'
    assert out['local_matches'] == {'2' * 22: ['k/01.mp3']}


def test_title_fallback_requires_duration_and_uniqueness(tmp_path, monkeypatch):
    album = 'Deluxe'
    source = [dict(song_id=str(i) * 22, name='Same', artists=['A'], album_artist='A', album_name=album,
                   release_date='2022-01-01', track_number=i, duration=200, album_track_total=2) for i in (1, 2)]
    local = [dict(file='a.mp3', title='Same', artist='A', album_artist='A', album=album, year='2022',
                  track_number=5, duration=200)]
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [dict(id='K' * 22, name=album, artists=['A'], year='2022')]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: source)
    assert resolve_album_source(local, album, TrackIndex(tmp_path / 'i.db'))['status'] == 'unavailable'
    local[0].update(title='Other')
    assert resolve_album_source(local, album, TrackIndex(tmp_path / 'i.db'))['status'] == 'unavailable'
