"""Year-by-year label loading and self-named artist exclusion."""

import pytest

from downtify import label_catalog, label_search
from tests.test_exact_label_releases import candidate


@pytest.fixture(autouse=True)
def clear():
    label_search._catalog_snapshot.cache_clear()
    label_search._year_snapshot.cache_clear()
    label_search._roster_label.cache_clear()
    yield
    label_search._catalog_snapshot.cache_clear()
    label_search._year_snapshot.cache_clear()
    label_search._roster_label.cache_clear()


def named(n, artist, year=2020):
    row = candidate(n)
    row['data']['artists']['items'] = [{'profile': {'name': artist}}]
    row['data']['date'] = {'year': year}
    return row


def setup(monkeypatch, by_year, labels):
    calls = []

    def fetch(name, offset, token, timeout, years=None):
        calls.append(years)
        items = by_year.get(years, [])
        return {
            'items': items,
            'totalCount': len(items),
            'pagingInfo': {'nextOffset': None},
        }

    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 't')
    monkeypatch.setattr(label_search, '_fetch_page', fetch)
    monkeypatch.setattr(
        label_catalog,
        'album_metadata',
        lambda i: {
            'album_id': i,
            'label': labels[int(i)],
            'release_date': f'20{int(i):02d}-01-01',
        },
    )
    return calls


def test_year_returns_only_that_years_exact_matches(monkeypatch):
    setup(
        monkeypatch,
        {'2020': [named(20, 'Frankov'), named(21, 'Other')]},
        {20: 'Frucht', 21: 'Fruchtfleisch LTD'},
    )
    result = label_search.year_releases('frucht', 2020)
    assert [x['album_id'][-2:] for x in result['releases']] == ['20']
    assert result['year'] == 2020
    assert result['complete'] is True
    assert result['excluded'] == 1


def test_empty_year_is_complete_and_empty(monkeypatch):
    setup(monkeypatch, {}, {})
    result = label_search.year_releases('frucht', 1999)
    assert result['releases'] == []
    assert result['complete'] is True


def test_artist_named_like_label_is_excluded_when_label_has_roster(
    monkeypatch,
):
    setup(
        monkeypatch,
        {
            None: [named(30, 'Frankov')],
            '2026': [named(26, 'Frucht', 2026), named(27, 'Frankov', 2026)],
        },
        {30: 'Frucht', 26: 'Frucht', 27: 'Frucht'},
    )
    result = label_search.year_releases('frucht', 2026)
    assert [x['album_id'][-2:] for x in result['releases']] == ['27']
    assert result['self_released'] == 1


def test_label_that_only_releases_under_its_own_name_keeps_them(
    monkeypatch,
):
    setup(
        monkeypatch,
        {None: [named(30, 'Solo')], '2026': [named(26, 'Solo', 2026)]},
        {30: 'Solo', 26: 'Solo'},
    )
    result = label_search.year_releases('solo', 2026)
    assert len(result['releases']) == 1
    assert result['self_released'] == 0


def test_year_with_capped_results_is_not_called_complete(monkeypatch):
    def fetch(name, offset, token, timeout, years=None):
        items = [named(i, 'A') for i in range(100)]
        return {
            'items': items[offset:offset + 50],
            'totalCount': 100,
            'pagingInfo': {'nextOffset': offset + 50 if offset == 0 else None},
        }

    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 't')
    monkeypatch.setattr(label_search, '_fetch_page', fetch)
    monkeypatch.setattr(
        label_catalog,
        'album_metadata',
        lambda i: {'album_id': i, 'label': 'Big', 'release_date': ''},
    )
    result = label_search.year_releases('Big', 2020)
    assert result['complete'] is False
    assert result['partial_reason'] == 'year_limit'


@pytest.mark.parametrize('year', [1899, 2200, 'x'])
def test_invalid_year_is_rejected(year):
    with pytest.raises(ValueError, match='year'):
        label_search.year_releases('frucht', year)


def test_label_branded_release_by_label_named_artist_is_kept(monkeypatch):
    branded = named(26, 'LuckyMe', 2020)
    branded['data']['name'] = 'LuckyMe Advent Calendar 20'
    setup(
        monkeypatch,
        {
            None: [named(30, 'Jacques Greene')],
            '2020': [branded, named(27, 'LuckyMe', 2020)],
        },
        {30: 'LuckyMe', 26: 'LuckyMe', 27: 'LuckyMe'},
    )
    result = label_search.year_releases('luckyme', 2020)
    assert [x['album_id'][-2:] for x in result['releases']] == ['26']
    assert result['self_released'] == 1
