"""A flattened source subtitle must not hide verified local artist boundaries."""
from downtify.album_source import _with_editions


def test_flat_source_uses_matching_local_credit_boundaries_without_mutation():
    source = dict(song_id='x', name='St. Chroma', artists=['Tyler, The Creator, Daniel Caesar'],
                  album_name='CHROMAKOPIA', duration=197)
    local = dict(title='St. Chroma', artists=['Tyler, The Creator', 'Daniel Caesar'],
                 album='CHROMAKOPIA', duration=197.06)
    versions = [dict(id='edition', tracks=[source], local_matches={}, url='url')]
    result = _with_editions(versions, local_tracks=[local])
    assert result['tracks'][0]['artists'] == ['Tyler, The Creator', 'Daniel Caesar']
    assert source['artists'] == ['Tyler, The Creator, Daniel Caesar']


def test_ambiguous_or_different_local_credits_do_not_override_source():
    source = dict(song_id='x', name='Song', artists=['A, B'], album_name='Album', duration=197)
    versions = [dict(id='edition', tracks=[source], local_matches={}, url='url')]
    for local in [
        dict(title='Other', artists=['A', 'B'], album='Album', duration=197),
        dict(title='Song', artists=['A', 'B'], album='Other', duration=197),
        dict(title='Song', artists=['A', 'C'], album='Album', duration=197),
    ]:
        assert _with_editions(versions, local_tracks=[local])['tracks'][0]['artists'] == ['A, B']
    locals_ = [dict(title='Song', artists=names, album='Album', duration=197)
               for names in [['A', 'B'], ['A, B']]]
    assert _with_editions(versions, local_tracks=locals_)['tracks'][0]['artists'] == ['A, B']


def test_credit_boundaries_do_not_depend_on_downloaded_audio_length():
    source = dict(name='Darling, I', artists=['Tyler, The Creator, Teezo Touchdown'],
                  album_name='CHROMAKOPIA', duration=253)
    local = dict(title='Darling, I', artists=['Tyler, The Creator', 'Teezo Touchdown'],
                 album='CHROMAKOPIA', duration=288.55)
    versions = [dict(id='edition', tracks=[source], local_matches={}, url='url')]
    assert _with_editions(versions, local_tracks=[local])['tracks'][0]['artists'] == local['artists']
