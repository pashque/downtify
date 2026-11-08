from downtify import deezer, discover, external_library


def test_discovery_preserves_symbol_artists_and_distinct_release_titles():
    assert discover.artist_key('AC/DC') != discover.artist_key('ACDC')
    assert discover.artist_key('|||') != discover.artist_key('||')
    assert discover.album_key('Artist', 'Album (Deluxe)') != discover.album_key('Artist', 'Album')
    assert discover.album_key('Artist', 'Album +') != discover.album_key('Artist', 'Album')


def test_external_identity_cannot_substitute_symbol_artist_or_version():
    def row(artist, title='Song'):
        return dict(artist=artist, artists=[artist], title=title)
    assert external_library.song_identity(row('!!!')) != external_library.song_identity(row('+++'))
    assert external_library.song_identity(row('A/B')) != external_library.song_identity(row('AB'))
    assert external_library.song_identity(row('Artist', 'Song (Live)')) != external_library.song_identity(row('Artist', 'Song'))
    assert external_library._primary_artist(row('Tyler, The Creator')) == 'Tyler, The Creator'


def test_preview_never_uses_another_punctuation_artist(monkeypatch):

    class Response:
        def raise_for_status(self): pass
        def json(self): return {'data': [{'title': 'Song', 'artist': {'name': 'ACDC'}, 'preview': 'https://cdns-preview-1.dzcdn.net/stream/clip.mp3', 'duration': 180}]}
    monkeypatch.setattr(deezer.httpx, 'get', lambda *args, **kwargs: Response())
    assert deezer.find_track_preview('AC/DC', 'Song', 180) == ''


def test_symbol_only_deezer_name_is_valid(monkeypatch):

    class Response:
        def raise_for_status(self): pass
        def json(self): return {'data': [{'id': 42, 'name': '|||', 'nb_fan': 100}]}
    monkeypatch.setattr(deezer.httpx, 'get', lambda *args, **kwargs: Response())
    assert deezer.resolve_artist_id('|||') == '42'
