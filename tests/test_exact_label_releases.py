"""Broad label search must never leak similarly named labels into a page."""

import pytest

from downtify import label_catalog, label_search


def candidate(n):
    return {
        '__typename': 'AlbumResponseWrapper',
        'data': {
            'uri': f'spotify:album:{n:022d}', 'name': f'Release {n}',
            'date': {'year': 2026}, 'type': 'ALBUM',
            'artists': {'items': [{'profile': {'name': 'Artist'}}]},
        },
    }


@pytest.fixture(autouse=True)
def clear():
    label_search._catalog_snapshot.cache_clear()
    yield
    label_search._catalog_snapshot.cache_clear()


def setup_catalog(monkeypatch, metadata):
    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 'test')
    monkeypatch.setattr(label_search, '_fetch_page', lambda *a: {
        'items': [candidate(n) for n in metadata],
        'totalCount': len(metadata), 'pagingInfo': {'nextOffset': None},
    })

    def details(album_id):
        value = metadata[int(album_id)]
        if isinstance(value, Exception):
            raise value
        return {'album_id': album_id, **value}

    monkeypatch.setattr(label_catalog, 'album_metadata', details, raising=False)


def test_frucht_excludes_similar_label_names(monkeypatch):
    setup_catalog(monkeypatch, {
        1: {'label': 'Frucht', 'release_date': '2026-01-15'},
        2: {'label': 'Fruchtfleisch LTD', 'release_date': '2026-02-01'},
        3: {'label': 'Fruchtenhuber Music Group', 'release_date': '2026-03-01'},
        4: {'label': ' FRUCHT ', 'release_date': '2025-12-20'},
    })
    result = label_search.releases('frucht')
    assert [x['album_id'] for x in result['releases']] == [f'{1:022d}', f'{4:022d}']
    assert result['total'] == 2
    assert result['search_total'] == 4
    assert result['excluded'] == 2
    assert [x['release_date'] for x in result['releases']] == ['2026-01-15', '2025-12-20']
    assert all(x['label'].strip().lower() == 'frucht' for x in result['releases'])


def test_trademark_case_and_spacing_variants_are_same_label(monkeypatch):
    setup_catalog(monkeypatch, {
        1: {'label': 'LUCKYME®', 'release_date': '2026-01-01'},
        2: {'label': 'LuckyMe', 'release_date': '2026-02-01'},
        3: {'label': 'luckyme\u2122  ', 'release_date': '2026-03-01'},
        4: {'label': 'Lucky Me Records', 'release_date': '2026-04-01'},
        5: {'label': 'Lucky Me', 'release_date': '2026-05-01'},
    })
    for query in ('LUCKYME®', 'luckyme'):
        label_search._catalog_snapshot.cache_clear()
        result = label_search.releases(query)
        assert [x['album_id'][-1] for x in result['releases']] == ['3', '2', '1']
        assert result['excluded'] == 2


def test_label_key_only_strips_marks_case_and_whitespace():
    key = label_search.label_key
    assert key('LUCKYME®') == key(' luckyme ') == key('LuckyMe\u2122')
    assert key('Frucht') != key('Fruchtfleisch LTD')
    assert key('A & B') != key('A and B')


def test_capped_search_is_split_by_year_ranges(monkeypatch):
    """Spotify stops at 100 rows; wider labels need year partitions."""
    calls = []
    rows = {y: [y * 1000 + n for n in range(60)] for y in (2020, 2021, 2022)}

    def fetch(name, offset, token, timeout, years=None):
        calls.append(years)
        if years is None:
            ys = [2020, 2021, 2022]
        elif '-' in years:
            lo, hi = map(int, years.split('-'))
            ys = [y for y in rows if lo <= y <= hi]
        else:
            ys = [y for y in rows if y == int(years)]
        ids = [i for y in ys for i in rows[y]]
        items = [candidate(i) for i in ids[:100]] if years is None else [
            candidate(i) for i in ids
        ]
        total = 100 if years is None else len(ids)
        return {
            'items': items[offset:offset + 50],
            'totalCount': total,
            'pagingInfo': {
                'nextOffset': offset + 50 if offset + 50 < len(items) else None
            },
        }

    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 't')
    monkeypatch.setattr(label_search, '_fetch_page', fetch)
    monkeypatch.setattr(
        label_catalog, 'album_metadata',
        lambda i: {'album_id': i, 'label': 'Big', 'release_date': ''},
    )
    result = label_search.releases('Big')
    assert result['complete'] is True
    assert len(result['releases']) == 180
    assert any(c and '-' in c for c in calls)


def test_single_year_over_cap_is_reported_incomplete(monkeypatch):
    def fetch(name, offset, token, timeout, years=None):
        ids = list(range(100))
        return {
            'items': [candidate(i) for i in ids][offset:offset + 50],
            'totalCount': 100,
            'pagingInfo': {'nextOffset': offset + 50 if offset == 0 else None},
        }

    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 't')
    monkeypatch.setattr(label_search, '_fetch_page', fetch)
    monkeypatch.setattr(
        label_catalog, 'album_metadata',
        lambda i: {'album_id': i, 'label': 'Big', 'release_date': ''},
    )
    result = label_search.releases('Big')
    assert result['complete'] is False
    assert result['partial_reason'] == 'year_limit'
