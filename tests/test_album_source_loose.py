"""Best-effort fallback: every version Spotify search finds, fullest first."""
from downtify import spotify
from downtify.album_source import resolve_album_source
from downtify.track_index import TrackIndex


def _album(prefix, names, album='Nervous Energy', durs=None):
    return [dict(song_id=(prefix+str(i))*11, name=n, artists=['Mindy Meng Wang'], album_artist='Mindy Meng Wang',
                 album_name=album, release_date='2023-01-01', track_number=i,
                 duration=(durs or {}).get(n, 200), album_track_total=len(names))
            for i, n in enumerate(names, 1)]


def _local(**over):
    row = dict(file='m/03.mp3', title='Flow', artist='Mindy Meng Wang', album_artist='Mindy Meng Wang',
               album='Nervous Energy 一触即发', year='2021', track_number=3, duration=204.0)
    row.update(over)
    return [row]


def _patch(monkeypatch, albums, sources, queries=None):
    def search(q):
        if queries is not None:
            queries.append(q)
        return {'albums': albums(q) if callable(albums) else albums}
    monkeypatch.setattr(spotify, 'search', search)
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: sources[aid])


def test_album_found_only_via_track_query_expands(tmp_path, monkeypatch):
    full = _album('A', ['Intro', 'Run', 'Flow', 'Outro'])
    # Spotify names the album differently and only a track query finds it.
    _patch(monkeypatch, lambda q: [dict(id='A'*22, name='Nervous Energy', artists=['Mindy Meng Wang'], year='2023')]
           if 'Flow' in q else [], {'A'*22: full})
    title = 'Nervous Energy 一触即发'
    out = resolve_album_source(_local(), title, TrackIndex(tmp_path/'i.db'))
    assert out['status'] == 'resolved' and len(out['tracks']) == 4
    assert out['local_matches'] == {'A3'*11: ['m/03.mp3']}


def test_every_found_version_listed_fullest_first(tmp_path, monkeypatch):
    sources = {'S'*22: _album('S', ['Run', 'Flow'], 'Nervous Energy 一触即发'),
               'D'*22: _album('D', ['Run', 'Flow', 'Bonus 1', 'Bonus 2'], 'Nervous Energy 一触即发')}
    _patch(monkeypatch, [dict(id=k, name='Nervous Energy 一触即发', artists=['Mindy Meng Wang'], year='2019')
                         for k in sources], sources)
    out = resolve_album_source(_local(), 'Nervous Energy 一触即发', TrackIndex(tmp_path/'i.db'))
    assert [e['track_count'] for e in out['editions']] == [4, 2]
    assert out['edition'] == 'D'*22


def test_album_without_any_local_track_is_never_shown(tmp_path, monkeypatch):
    sources = {'A'*22: _album('A', ['Intro', 'Run']),
               'B'*22: _album('B', ['Flow'], durs={'Flow': 260})}  # same title, wrong length
    _patch(monkeypatch, [dict(id=k, name='Nervous Energy', artists=['Mindy Meng Wang'], year='2023') for k in sources],
           sources)
    out = resolve_album_source(_local(), 'Nervous Energy 一触即发', TrackIndex(tmp_path/'i.db'))
    assert out['status'] == 'unavailable'


def test_unrelated_artists_albums_are_not_candidates(tmp_path, monkeypatch):
    sources = {'A'*22: _album('A', ['Flow'])}
    _patch(monkeypatch, [dict(id='A'*22, name='Totally Different', artists=['Someone Else'], year='2023')], sources)
    assert resolve_album_source(_local(), 'Nervous Energy 一触即发', TrackIndex(tmp_path/'i.db'))['status'] == 'unavailable'


def test_fetches_are_bounded(tmp_path, monkeypatch):
    fetched = []
    albums = [dict(id=chr(65+i)*22, name='Nervous Energy 一触即发', artists=['Mindy Meng Wang'], year='2023') for i in range(10)]
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': albums})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: fetched.append(aid) or [])
    resolve_album_source(_local(), 'Nervous Energy 一触即发', TrackIndex(tmp_path/'i.db'))
    assert len(fetched) <= 6


def test_downloaded_album_also_offers_other_versions(tmp_path, monkeypatch):
    index = TrackIndex(tmp_path/'i.db')
    exact = _album('E', ['Run', 'Flow'], 'Nervous Energy')
    deluxe = _album('D', ['Run', 'Flow', 'Bonus'], 'Nervous Energy')
    local = _local(album='Nervous Energy', track_number=2)
    monkeypatch.setattr(index, 'spotify_id_for_filename', lambda f: 'E2'*11)
    monkeypatch.setattr(spotify, '_album_ref_from_open_track_page', lambda tid: ('E'*22, None))
    _patch(monkeypatch, [dict(id=k, name='Nervous Energy', artists=['Mindy Meng Wang'], year='2023')
                         for k in ('E'*22, 'D'*22)], {'E'*22: exact, 'D'*22: deluxe})
    out = resolve_album_source(local, 'Nervous Energy', index)
    assert [(e['id'], e['track_count']) for e in out['editions']] == [('D'*22, 3), ('E'*22, 2)]
    chosen = resolve_album_source(local, 'Nervous Energy', index, 'E'*22)
    assert chosen['edition'] == 'E'*22 and len(chosen['tracks']) == 2
