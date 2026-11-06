from downtify.playlist_spotify_cache import PlaylistSpotifyCache


def test_source_identity_survives_persistent_track_cache(tmp_path):
    cache=PlaylistSpotifyCache(tmp_path/'cache.sqlite')
    row=dict(song_id='T'*22,name='Song',artists=['|||'],artist_ids=['A'*22],
             album_id='R'*22,album_name='Album +',source='spotify')
    cache.store_track(row['song_id'],row)
    cached=cache.get_cached_track(row['song_id'])
    assert cached['artist_ids']==row['artist_ids']
    assert cached['album_id']==row['album_id']
    assert cached['source']=='spotify'
