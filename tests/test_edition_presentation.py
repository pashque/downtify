"""Edition menu evidence must not change the selected release identity."""
from downtify import album_source, spotify
from downtify.album_source import _with_editions


def test_link_discovery_works_without_local_files_and_preserves_opened_id(monkeypatch):
    def tracks(aid):
        title = 'Album (Deluxe)' if aid == 'D' * 22 else 'Album'
        rows = [dict(song_id='T' * 22, name='One', artists=['A'], album_artist='A',
                     album_name=title, duration=200, explicit=aid != 'C' * 22)]
        if aid == 'D' * 22:
            rows.append(dict(rows[0], song_id='B' * 22, name='Bonus'))
        return rows
    monkeypatch.setattr(spotify, 'album_tracks_from_id', tracks)
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [
        dict(id=i * 22, name=n, artists=[a], type='ALBUM') for i, n, a in
        [('S', 'Album', 'A'), ('D', 'Album (Deluxe)', 'A'), ('C', 'Album', 'A'),
         ('W', 'Album', 'Wrong'), ('P', 'Album +', 'A')]]})
    discover = getattr(album_source, 'discover_album_editions', lambda aid: {})
    result = discover('S' * 22)
    assert result.get('edition') == 'S' * 22
    assert {e['id'] for e in result['editions']} == {'S' * 22, 'D' * 22, 'C' * 22}
    assert result['tracks'] == tracks('S' * 22)
    assert result['local_matches'] == {}


def test_menu_carries_complete_recording_evidence_and_selected_id():
    tracks = [dict(song_id='a' * 22, name='One +', artists=['A', 'B'],
                   album_name='Album (Deluxe)', duration=201.123, explicit=False,
                   track_number=1, disc_number=2, release_date='2024-01-02')]
    candidate = dict(id='b' * 22, tracks=tracks, url='exact-url', local_matches={})
    result = _with_editions([candidate], 'b' * 22)
    entry = result['editions'][0]
    assert entry['title'] == 'Album (Deluxe)'
    assert entry['release_date'] == '2024-01-02'
    assert entry['tracks'] == [dict(name='One +', artists=['A', 'B'], duration=201.123,
                                   explicit=False, track_number=1, disc_number=2)]
    assert result['edition'] == 'b' * 22
    assert result['tracks'] == tracks
    assert 'song_id' not in entry['tracks'][0]
