from downtify import spotify
from downtify.downloader import Downloader

TRACK_ID = '5fHrHoJKfCgBd35zwIBmUK'
ALBUM_ID = '6OQ9gBfg5EXeNAEwGSs6jK'
TRACK = {'name': 'D4L', 'artists': [{'name': 'Future'}, {'name': 'Drake'}, {'name': 'Young Thug'}], 'releaseDate': {'isoString': '2020-05-01T00:00:00Z'}}
ALBUM = {'name': 'Dark Lane Demo Tapes', 'subtitle': 'Drake', 'releaseDate': {'isoString': '2020-05-01T00:00:00Z'}, 'trackList': [{'uri': 'spotify:track:' + TRACK_ID, 'title': 'D4L', 'subtitle': 'Future, Drake, Young Thug'}]}


def setup_source(monkeypatch):
    monkeypatch.setattr(spotify, '_fetch_embed_json', lambda kind, ident: {'props': {'pageProps': {'state': {'data': {'entity': TRACK if kind == 'track' else ALBUM}}}}})
    monkeypatch.setattr(spotify, '_album_ref_from_open_track_page', lambda ident: (ALBUM_ID, 9))


def test_individual_d4l_uses_album_artist_not_first_track_artist(monkeypatch):
    setup_source(monkeypatch)
    song = spotify.track_from_id(TRACK_ID, with_album=True)
    assert song.get('album_artist') == 'Drake'
    assert song['artists'] == ['Future', 'Drake', 'Young Thug']


def test_album_browse_preserves_album_credit(monkeypatch):
    setup_source(monkeypatch)
    song = spotify.album_tracks_from_id(ALBUM_ID)[0]
    assert song.get('album_artist') == 'Drake'
    # This fixture has only a flattened subtitle, not separate credits.
    assert song['artists'] == ['Future, Drake, Young Thug']


def test_complete_playlist_row_still_enriches_missing_album_artist(monkeypatch):
    setup_source(monkeypatch)
    song = dict(song_id=TRACK_ID, source='spotify', name='D4L', artists=['Future', 'Drake', 'Young Thug'], album_name='Dark Lane Demo Tapes', release_date='2020-05-01', track_number=9)
    enriched = spotify.enrich_track_from_spotify_if_sparse(song)
    assert enriched.get('album_artist') == 'Drake'


def test_track_with_nested_album_artist_uses_album_credit():
    entity = dict(TRACK, album={'name': 'Dark Lane Demo Tapes', 'artists': [{'name': 'Drake'}]})
    assert spotify._track_dict(entity, track_id=TRACK_ID).get('album_artist') == 'Drake'
