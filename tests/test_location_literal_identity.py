"""Location fingerprints retain the same literal identity as library lookup."""
from downtify.library_locations import _fingerprint


def test_location_fingerprint_uses_structured_local_credits():
    local = dict(title='One', artist='Tyler, The Creator, Guest',
                 artists=['Tyler, The Creator', 'Guest'], album_artist='Tyler, The Creator',
                 album='Sun +', year='2020', track_number=1, duration=180)
    source = dict(name='One', artists=['Tyler, The Creator', 'Guest'],
                  album_artist='Tyler, The Creator', album_name='Sun +',
                  release_date='2020', track_number=1, duration=180)
    assert _fingerprint(local, local=True) == _fingerprint(source)


def test_location_fingerprint_preserves_literal_names_but_normalizes_nfkc():
    source = dict(name='One', artists=['Straße'], album_artist='Straße',
                  album_name='Sun +', release_date='2020', track_number=1, duration=180)
    assert _fingerprint(source) != _fingerprint(dict(source, artists=['Strasse'], album_artist='Strasse'))
    assert _fingerprint(dict(source, name='Ｏｎｅ')) == _fingerprint(source)
