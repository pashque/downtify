"""A label's year outline lets the page skip gaps without guessing."""

import pytest

from downtify import label_search
from tests.test_label_years import named


@pytest.fixture(autouse=True)
def clear():
    label_search._outline_snapshot.cache_clear()
    yield
    label_search._outline_snapshot.cache_clear()


def fake(monkeypatch, items, total=None):
    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 't')
    monkeypatch.setattr(
        label_search,
        '_fetch_page',
        lambda name, offset, token, timeout, years=None: {
            'items': items,
            'totalCount': len(items) if total is None else total,
            'pagingInfo': {'nextOffset': None},
        },
    )


def test_outline_lists_distinct_years_newest_first_and_is_not_capped(
    monkeypatch,
):
    fake(
        monkeypatch,
        [named(1, 'A', 2024), named(2, 'B', 2015), named(3, 'C', 2015)],
    )
    result = label_search.outline('Rectangular')
    assert result['years'] == [2024, 2015]
    assert result['capped'] is False


def test_outline_of_a_capped_search_says_so(monkeypatch):
    items = [named(i, 'A', 2010 + i % 5) for i in range(100)]
    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 't')

    def fetch(name, offset, token, timeout, years=None):
        return {
            'items': items[offset : offset + 50],
            'totalCount': 100,
            'pagingInfo': {'nextOffset': offset + 50 if offset == 0 else None},
        }

    monkeypatch.setattr(label_search, '_fetch_page', fetch)
    result = label_search.outline('Big')
    assert result['capped'] is True
    assert result['years'] == [2014, 2013, 2012, 2011, 2010]


def test_empty_outline_has_no_years(monkeypatch):
    fake(monkeypatch, [])
    assert label_search.outline('Nothing') == {
        'label': 'Nothing',
        'years': [],
        'capped': False,
        'total': 0,
    }
