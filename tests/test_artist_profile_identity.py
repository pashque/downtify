"""Profile/art ownership regressions; all fixtures are isolated sidecars."""
import json

import pytest

from downtify import artist_profile as ap


@pytest.mark.parametrize('kind', [ap.KIND_PHOTO, ap.KIND_BANNER])
def test_new_art_paths_do_not_collapse_punctuation(tmp_path, kind):
    assert ap.image_path_for(tmp_path, 'AC/DC', kind) != ap.image_path_for(tmp_path, 'ACDC', kind)


@pytest.mark.parametrize('stored_name', ['AC/DC', 'ACDC', None])
@pytest.mark.parametrize('kind', [ap.KIND_PHOTO, ap.KIND_BANNER])
def test_legacy_art_requires_profile_name_attestation(tmp_path, kind, stored_name):
    legacy = tmp_path / ap._DIRNAMES[kind] / ('ACDC' + ap._SUFFIXES[kind])
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b'custom art')
    profile = tmp_path / ap._PROFILE_DIRNAME / 'ACDC.json'
    profile.parent.mkdir(parents=True)
    profile.write_text(json.dumps({'name': stored_name, 'bio': 'custom'}))
    owner = stored_name
    other = 'ACDC' if owner == 'AC/DC' else 'AC/DC'
    if owner:
        assert ap.image_path_for(tmp_path, owner, kind) == legacy
        assert ap.image_url_for(tmp_path, owner, kind) is not None
    assert ap.image_url_for(tmp_path, other, kind) is None
    assert ap.image_version_for(tmp_path, other, kind) is None
    assert not ap.delete_image(tmp_path, other, kind)
    assert legacy.read_bytes() == b'custom art'


def test_seed_lock_key_is_stable_when_verified_legacy_path_changes(tmp_path):
    before = ap._seed_key(tmp_path, 'AC/DC')
    legacy = tmp_path / ap._PROFILE_DIRNAME / 'ACDC.json'
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({'name': 'AC/DC'}))
    assert ap._seed_key(tmp_path, 'AC/DC') == before
    assert ap._seed_key(tmp_path, 'ac/dc') == before
    assert ap._seed_key(tmp_path, 'ACDC') != before


@pytest.mark.parametrize('stored_name', ['ACDC', None])
def test_hashed_profile_still_requires_matching_stored_name(tmp_path, stored_name):
    path = ap._profile_path_for(tmp_path, 'AC/DC')
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'name': stored_name, 'bio': 'not theirs'}))
    assert ap.load_profile(tmp_path, 'AC/DC')['bio'] == ''


@pytest.mark.parametrize('stored_name', ['ACDC', None])
def test_hashed_top_cache_still_requires_matching_stored_name(tmp_path, stored_name):
    path = ap.profile_top_songs_path_for(tmp_path, 'AC/DC')
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'name': stored_name, 'songs': []}))
    assert ap.profile_top_songs_load(tmp_path, 'AC/DC') is None
