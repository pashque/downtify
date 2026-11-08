import json
import pytest
from downtify import artist_profile as ap


@pytest.mark.parametrize('a,b', [('AC/DC', 'ACDC'), ('/', '?'), ('?', '*'), ('A+B', 'AB')])
def test_profile_and_top_cache_paths_do_not_collapse(a, b, tmp_path):
    assert ap._profile_path_for(tmp_path, a) != ap._profile_path_for(tmp_path, b)
    assert ap.profile_top_songs_path_for(tmp_path, a) != ap.profile_top_songs_path_for(tmp_path, b)
    ap._save_profile(tmp_path, a, {**ap._default_profile(a), 'bio': 'one'})
    assert ap.load_profile(tmp_path, b)['bio'] == ''


def test_verified_legacy_profile_is_read_without_moving_art(tmp_path):
    path = tmp_path / ap._PROFILE_DIRNAME / 'ACDC.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'name': 'AC/DC', 'bio': 'custom'}))
    art = tmp_path / ap._DIRNAMES[ap.KIND_PHOTO] / 'ACDC.jpg'
    art.parent.mkdir(parents=True)
    art.write_bytes(b'custom image')
    assert ap.load_profile(tmp_path, 'AC/DC')['bio'] == 'custom'
    assert ap.load_profile(tmp_path, 'ACDC')['bio'] == ''
    ap._save_profile(tmp_path, 'ACDC', ap._default_profile('ACDC'))
    assert json.loads(path.read_text())['bio'] == 'custom'
    assert art.read_bytes() == b'custom image'


def test_legacy_cache_is_only_used_for_matching_artist(tmp_path):
    p = tmp_path / ap._TOP_SONGS_DIRNAME / 'ACDC.topsongs.json'
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'name': 'AC/DC', 'songs': []}))
    assert ap.profile_top_songs_load(tmp_path, 'AC/DC')['songs'] == []
    assert ap.profile_top_songs_load(tmp_path, 'ACDC') is None


def test_profile_identity_normalizes_case_width_and_whitespace(tmp_path):
    assert ap._profile_path_for(tmp_path, 'ＡＣ/DC') == ap._profile_path_for(tmp_path, 'ac/dc')
    assert ap._profile_path_for(tmp_path, ' Artist   Name ') == ap._profile_path_for(tmp_path, 'artist name')


def test_song_profile_uses_authoritative_credit_id_without_network(monkeypatch):
    monkeypatch.setattr(ap.spotify, 'primary_artist_id_from_track_id', lambda *a: pytest.fail('ID already known'))
    monkeypatch.setattr(ap.spotify, 'search_artist_by_name', lambda *a: None)
    song = {'source': 'spotify', 'song_id': 'T' * 22, 'artists': ['AC/DC'], 'artist_ids': ['A' * 22], 'artists_structured': True}
    assert ap._spotify_artist_id_for_song(song, 'AC/DC') == 'A' * 22
    assert ap._spotify_artist_id_for_song(song, 'ACDC') is None


def test_opaque_credit_cannot_seed_canonical_artist(monkeypatch):
    monkeypatch.setattr(ap.spotify, 'primary_artist_id_from_track_id', lambda *a: pytest.fail('opaque credit'))
    monkeypatch.setattr(ap.spotify, 'search_artist_by_name', lambda *a: pytest.fail('opaque credit'))
    song = {'source': 'spotify', 'song_id': 'T' * 22, 'artists': ['A, B'], 'artists_structured': False}
    assert ap._spotify_artist_id_for_song(song, 'A, B') is None
