"""Known release types work even for unowned, search-unlisted editions."""
import pytest
from tests.test_spotify_album_credit_entities import _html, _resolve, ALBUM_ID


@pytest.mark.parametrize('kind', ['ALBUM', 'SINGLE', 'EP', 'COMPILATION'])
def test_unowned_release_type_from_exact_canonical_entity(monkeypatch, kind):
    rows, calls = _resolve(monkeypatch, _html(dict(uri=f'spotify:album:{ALBUM_ID}',
                       name='Exact album', type=kind, tracksV2={'items': []})))
    assert {row.get('release_type') for row in rows} == {kind.lower()}
    assert len(calls) == 1


@pytest.mark.parametrize('conflict', ['uri', 'name', 'type'])
def test_unknown_or_conflicting_release_type_is_not_guessed(monkeypatch, conflict):
    album = dict(uri=f'spotify:album:{ALBUM_ID}', name='Exact album', type='SINGLE', tracksV2={'items': []})
    album[conflict] = 'wrong'
    rows, calls = _resolve(monkeypatch, _html(album))
    assert not any(row.get('release_type') for row in rows)
