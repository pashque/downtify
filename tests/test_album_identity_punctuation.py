"""Distinct album names and artists must never be merged by legacy recovery."""
from downtify.album_source import _album_key, _loose_versions
from downtify import spotify


def test_album_identity_keeps_every_meaningful_symbol_and_version():
    names=['CHROMAKOPIA','CHROMAKOPIA +','CHROMAKOPIA (Deluxe)','CHROMAKOPIA EP',
           '!!!','+++','|','||','A/B','A B','A&B','A.B']
    assert len({_album_key(n) for n in names})==len(names)
    assert _album_key('  Chromakopia  + ')==_album_key('CHROMAKOPIA +')


def test_same_album_title_never_recovers_a_different_artist(monkeypatch):
    local=[dict(file='x.mp3',title='Same Song',artist='|||',artists=['|||'],
                album_artist='|||',album='Same Album',duration=180)]
    monkeypatch.setattr(spotify,'search',lambda q:{'albums':[
        dict(id='X'*22,name='Same Album',artists=['Other Artist'])]})
    monkeypatch.setattr(spotify,'album_tracks_from_id',lambda aid:[
        dict(song_id='S'*22,name='Same Song',artists=['Other Artist'],duration=180)])
    assert _loose_versions(local,'Same Album')==[]
