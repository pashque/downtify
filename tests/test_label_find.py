"""Finding label candidates from loose or misspelled text."""

import httpx
import pytest

from downtify import label_catalog, label_find, label_search
from tests.test_label_years import named


@pytest.fixture(autouse=True)
def clear():
    label_find._find_snapshot.cache_clear()
    yield
    label_find._find_snapshot.cache_clear()


def setup(monkeypatch, searches, labels, musicbrainz=None, dates=None):
    dates = dates or {}
    """searches: search term -> list of (album number, artist)."""
    calls = []
    monkeypatch.setattr(label_search.spotify, '_anonymous_token', lambda: 't')

    def fetch(name, offset, token, timeout, years=None):
        calls.append(name)
        items = []
        for n, artist in searches.get(name, []):
            row = named(n, artist)
            row['data']['coverArt'] = {
                'sources': [{'url': f'https://img/{n}', 'width': 300}]
            }
            items.append(row)
        return {
            'items': items,
            'totalCount': len(items),
            'pagingInfo': {'nextOffset': None},
        }

    monkeypatch.setattr(label_search, '_fetch_page', fetch)
    monkeypatch.setattr(
        label_catalog,
        'album_metadata',
        lambda i: {
            'album_id': i,
            'label': labels[int(i)],
            'release_date': dates.get(int(i), '2020-01-01'),
        },
    )
    monkeypatch.setattr(
        label_find, '_musicbrainz_names', lambda q: list(musicbrainz or [])
    )
    return calls


def names(result):
    return [x['name'] for x in result['labels']]


def test_lists_each_exact_label_separately_with_example_artists(monkeypatch):
    setup(
        monkeypatch,
        {'draft': [(1, 'Ana'), (2, 'Ana'), (3, 'Bo'), (4, 'Cy'), (5, 'Di')]},
        {1: 'Draft', 2: 'DRAFT', 3: 'Draft LTD', 4: 'Draft LTD', 5: 'Crafty'},
    )
    result = label_find.find('draft')
    assert names(result) == ['Draft', 'Draft LTD']
    draft, ltd = result['labels']
    assert draft['releases'] == 2
    assert draft['artists'] == ['Ana']
    assert ltd['releases'] == 2
    assert ltd['artists'] == ['Bo', 'Cy']


def test_rectangular_and_rectangular_records_are_different(monkeypatch):
    setup(
        monkeypatch,
        {'rectangular': [(1, 'Bonab'), (2, 'Manu Ritchie')]},
        {1: 'Rectangular', 2: 'Rectangular Records'},
    )
    assert names(label_find.find('rectangular')) == [
        'Rectangular',
        'Rectangular Records',
    ]


def test_most_common_spelling_is_shown(monkeypatch):
    setup(
        monkeypatch,
        {'luckyme': [(1, 'A'), (2, 'B'), (3, 'C')]},
        {1: 'LUCKYME®', 2: 'LuckyMe', 3: 'LuckyMe'},
    )
    result = label_find.find('luckyme')
    assert names(result) == ['LuckyMe']
    assert result['labels'][0]['releases'] == 3


def test_misspelling_uses_musicbrainz_and_finds_the_spotify_spelling(
    monkeypatch,
):
    calls = setup(
        monkeypatch,
        {'recangular': [], 'RectAngular': [(1, 'Bonab')]},
        {1: 'Rectangular'},
        musicbrainz=['RectAngular'],
    )
    result = label_find.find('recangular')
    assert names(result) == ['Rectangular']
    assert result['fuzzy'] is True
    assert 'RectAngular' in calls


def test_musicbrainz_is_not_asked_when_spotify_already_matches(monkeypatch):
    setup(
        monkeypatch,
        {'draft': [(1, 'Ana')]},
        {1: 'Draft'},
    )

    def fail(q):
        raise AssertionError('MusicBrainz must not be called')

    monkeypatch.setattr(label_find, '_musicbrainz_names', fail)
    assert names(label_find.find('draft')) == ['Draft']


def test_musicbrainz_failure_is_not_an_error(monkeypatch):
    setup(monkeypatch, {'recangular': []}, {})

    def down(q):
        raise ValueError('503')

    monkeypatch.setattr(label_find, '_musicbrainz_names', down)
    assert label_find.find('recangular')['labels'] == []


def test_unrelated_labels_from_a_loose_search_are_left_out(monkeypatch):
    setup(
        monkeypatch,
        {'draft': [(1, 'A'), (2, 'B')]},
        {1: 'Draft', 2: 'Warner Records'},
    )
    assert names(label_find.find('draft')) == ['Draft']


def test_word_missing_still_finds_the_label(monkeypatch):
    setup(
        monkeypatch,
        {'ninja': [(1, 'A'), (2, 'B')]},
        {1: 'Ninja Tune', 2: 'Ninja Tune'},
    )
    assert names(label_find.find('ninja')) == ['Ninja Tune']


@pytest.mark.parametrize('query', ['', ' ', 'x', 'a"b', 'x' * 201])
def test_invalid_query_is_rejected(query):
    with pytest.raises(ValueError, match='query'):
        label_find.find(query)


def test_musicbrainz_is_retried_once_after_a_rate_limit(monkeypatch):
    answers = [
        httpx.Response(503, request=httpx.Request('GET', 'https://mb')),
        httpx.Response(
            200,
            json={'labels': [{'name': 'Frucht', 'score': 52}]},
            request=httpx.Request('GET', 'https://mb'),
        ),
    ]
    monkeypatch.setattr(label_find.time, 'sleep', lambda s: None)
    monkeypatch.setattr(
        label_find.httpx, 'get', lambda *a, **k: answers.pop(0)
    )
    assert label_find._musicbrainz_names('fruchtt') == ['Frucht']


def test_whole_first_word_match_outranks_a_longer_word(monkeypatch):
    setup(
        monkeypatch,
        {'draft': [(1, 'A'), (2, 'B')]},
        {1: 'Drafty', 2: 'Draft LTD'},
    )
    assert names(label_find.find('draft')) == ['Draft LTD', 'Drafty']


def test_quick_mode_never_asks_musicbrainz(monkeypatch):
    setup(monkeypatch, {'zzzz': []}, {})

    def fail(q):
        raise AssertionError('MusicBrainz must not be called')

    monkeypatch.setattr(label_find, '_musicbrainz_names', fail)
    assert label_find.find('zzzz', fuzzy=False)['labels'] == []


def test_quick_mode_reads_fewer_albums(monkeypatch):
    rows = [(n, f'A{n}') for n in range(80)]
    setup(
        monkeypatch,
        {'draft': rows},
        {n: 'Draft' for n in range(80)},
    )
    full = label_find.find('draft')
    label_find._find_snapshot.cache_clear()
    quick = label_find.find('draft', fuzzy=False)
    assert full['labels'][0]['releases'] == 80
    assert quick['labels'][0]['releases'] == label_find._QUICK_ALBUMS
    assert label_find._QUICK_ALBUMS < 80


def test_quick_and_full_results_are_cached_separately(monkeypatch):
    calls = setup(monkeypatch, {'draft': [(1, 'A')]}, {1: 'Draft'})
    label_find.find('draft', fuzzy=False)
    label_find.find('draft', fuzzy=True)
    assert calls.count('draft') == 2


def test_labels_carry_no_image(monkeypatch):
    setup(monkeypatch, {'draft': [(1, 'A')]}, {1: 'Draft'})
    assert 'image' not in label_find.find('draft')['labels'][0]
