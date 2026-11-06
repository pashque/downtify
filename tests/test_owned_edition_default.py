"""Format availability belongs to the actual source edition, not a title alias."""
from downtify.album_source import _with_editions


def test_owned_source_ids_choose_default_without_reordering_edition_menu():
    def edition(id, ids):
        return dict(id=id, url='https://open.spotify.com/album/' + id,
                    local_matches={}, tracks=[dict(song_id=x, name=x, artists=['A']) for x in ids])
    fullest = edition('A' * 22, ['f1', 'f2', 'f3'])
    owned = edition('B' * 22, ['owned1', 'owned2'])
    ordered = [fullest, owned]
    result = _with_editions(ordered, owned_ids={'owned1', 'owned2'})
    assert result['edition'] == owned['id']
    assert [x['id'] for x in result['editions']] == [fullest['id'], owned['id']]
    explicit = _with_editions(ordered, edition=fullest['id'], owned_ids={'owned1', 'owned2'})
    assert explicit['edition'] == fullest['id']
    assert _with_editions(ordered)['edition'] == fullest['id']
