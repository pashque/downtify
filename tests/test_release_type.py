"""Album pages say what a release really is: album, single, EP or compilation."""
from downtify import api, spotify
from downtify.album_source import _release_type, resolve_album_source
from downtify.track_index import TrackIndex
from tests.test_album_source_loose import _album, _local, _patch


def test_release_type_is_normalised_and_never_guessed():
    assert _release_type('EP') == 'ep'
    assert _release_type('SINGLE') == 'single'
    assert _release_type('Album') == 'album'
    assert _release_type('COMPILATION') == 'compilation'
    assert _release_type('') == ''
    assert _release_type('MIXTAPE?') == ''


def test_each_found_version_carries_spotify_release_type(tmp_path, monkeypatch):
    sources = {'S' * 22: _album('S', ['Run', 'Flow'], 'Nervous Energy 一触即发'),
               'D' * 22: _album('D', ['Run', 'Flow', 'Bonus 1', 'Bonus 2'], 'Nervous Energy 一触即发')}
    kinds = {'S' * 22: 'EP', 'D' * 22: 'ALBUM'}
    _patch(monkeypatch, [dict(id=k, name='Nervous Energy 一触即发', artists=['Mindy Meng Wang'], year='2019', type=kinds[k])
                         for k in sources], sources)
    out = resolve_album_source(_local(), 'Nervous Energy 一触即发', TrackIndex(tmp_path / 'i.db'))
    assert [(e['track_count'], e['release_type']) for e in out['editions']] == [(4, 'album'), (2, 'ep')]
    assert out['release_type'] == 'album'
    picked = resolve_album_source(_local(), 'Nervous Energy 一触即发', TrackIndex(tmp_path / 'i.db'),
                                  edition='S' * 22)
    assert picked['release_type'] == 'ep'


def test_indexed_album_takes_its_type_from_the_search_results(tmp_path, monkeypatch):
    index = TrackIndex(tmp_path / 'i.db')
    index.register('S1' * 11, 'm/03.mp3')
    single = _album('S', ['Flow'], 'Flow')
    monkeypatch.setattr(spotify, '_album_ref_from_open_track_page', lambda tid: ('S' * 22, None))
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: single)
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id='S' * 22, name='Flow', artists=['Mindy Meng Wang'], year='2023', type='SINGLE')]})
    out = resolve_album_source(_local(album='Flow'), 'Flow', index)
    assert out['status'] == 'resolved'
    assert out['release_type'] == 'single'


def test_unknown_type_stays_empty(tmp_path, monkeypatch):
    sources = {'D' * 22: _album('D', ['Run', 'Flow'], 'Nervous Energy 一触即发')}
    _patch(monkeypatch, [dict(id='D' * 22, name='Nervous Energy 一触即发', artists=['Mindy Meng Wang'], year='2019')], sources)
    out = resolve_album_source(_local(), 'Nervous Energy 一触即发', TrackIndex(tmp_path / 'i.db'))
    assert out['release_type'] == '' and out['editions'][0]['release_type'] == ''


def test_spotify_album_link_reports_its_release_type(monkeypatch):
    rows = [dict(song_id='T' * 22, name='Blood Bank', album_name='Blood Bank', artists=['Bon Iver'],
                 cover_url='', year='2009')]
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: rows)
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id='O' * 22, name='Blood Bank', artists=['Bon Iver'], type='ALBUM'),
        dict(id='B' * 22, name='Blood Bank', artists=['Bon Iver'], type='EP')]})
    api._RELEASE_TYPE_CACHE.clear()
    assert api._spotify_details('album', 'B' * 22)['release_type'] == 'ep'
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': []})
    api._RELEASE_TYPE_CACHE.clear()
    assert api._spotify_details('album', 'B' * 22)['release_type'] == ''


def test_provider_rows_with_a_release_type_keep_it():
    rows = [dict(name='x', album_name='Royals', release_type='Single', artists=['Lorde'])]
    assert api._collection_details('album', rows)['release_type'] == 'single'
    assert 'release_type' not in api._collection_details('playlist', rows)
