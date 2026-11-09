"""A finished Spotify search is not the label's historical discography."""

import json

import httpx
import pytest

from downtify import label_search


def album(n, name='Release', year=2026):
    return {
        '__typename': 'AlbumResponseWrapper',
        'data': {
            'uri': f'spotify:album:{n:022d}',
            'name': name,
            'date': {'year': year},
            'type': 'ALBUM',
            'artists': {'items': [{'profile': {'name': 'Artist'}}]},
        },
    }


def page(items, total, next_offset):
    return {
        'data': {
            'searchV2': {
                'albumsV2': {
                    'items': items,
                    'totalCount': total,
                    'pagingInfo': {'nextOffset': next_offset},
                }
            }
        }
    }


@pytest.fixture(autouse=True)
def cache():
    label_search._catalog_snapshot.cache_clear()
    yield
    label_search._catalog_snapshot.cache_clear()


def mock_pages(monkeypatch, pages):
    calls = []
    monkeypatch.setattr(
        label_search.label_catalog, 'album_metadata',
        lambda album_id: {
            'album_id': album_id, 'label': 'LuckyMe', 'release_date': '',
        },
    )
    monkeypatch.setattr(
        label_search.spotify, '_anonymous_token', lambda: 'anon'
    )

    def get(url, **kwargs):
        variables = json.loads(kwargs['params']['variables'])
        calls.append(variables)
        payload = pages[variables['offset']]
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(
            200, json=payload, request=httpx.Request('GET', url)
        )

    monkeypatch.setattr(label_search.httpx, 'get', get)
    return calls


def test_follows_all_pages_and_keeps_exact_editions(monkeypatch):
    calls = mock_pages(
        monkeypatch,
        {
            0: page([album(1, year=2019)], 3, 1),
            1: page([album(2), album(3)], 3, None),
        },
    )
    result = label_search.releases(' LuckyMe ')
    assert [x['offset'] for x in calls] == [0, 1]
    assert calls[0]['searchTerm'] == 'label:"LuckyMe"'
    assert result['complete'] is True
    assert result['total'] == 3
    assert result['scope'] == 'exact_spotify_label'
    assert len(result['releases']) == 3
    assert result['releases'][0]['year'] == '2026'
    assert result['releases'][0]['album_id'] == f'{2:022d}'


def test_later_failure_keeps_successful_page_and_is_not_cached(monkeypatch):
    calls = mock_pages(
        monkeypatch,
        {
            0: page([album(1)], 3, 1),
            1: httpx.ConnectError('unavailable'),
        },
    )
    for _ in range(2):
        result = label_search.releases('LuckyMe')
        assert len(result['releases']) == 1
        assert result['complete'] is False
        assert result['partial_reason'] == 'provider_error'
    assert len(calls) == 4


def test_completed_catalog_is_cached_without_mutable_shared_results(
    monkeypatch,
):
    calls = mock_pages(monkeypatch, {0: page([album(1)], 1, None)})
    first = label_search.releases('LuckyMe')
    first['releases'].clear()
    assert len(label_search.releases('LuckyMe')['releases']) == 1
    assert len(calls) == 1


@pytest.mark.parametrize(
    ('data', 'reason'),
    [
        (page([album(1)], 8, None), 'early_end'),
        (page([album(1)], 8, 0), 'pagination_gap'),
        (page([album(1), album(1)], 2, None), 'unstable_results'),
        (page([album(1), album(2)], 1, None), 'unstable_results'),
    ],
)
def test_never_claims_complete_on_missing_repeated_or_looping_results(
    monkeypatch, data, reason
):
    mock_pages(monkeypatch, {0: data})
    result = label_search.releases('LuckyMe')
    assert result['complete'] is False
    assert result['partial_reason'] == reason
    assert len(result['releases']) == len({
        row['data']['uri']
        for row in data['data']['searchV2']['albumsV2']['items']
    })


def test_page_limit_is_explicit_not_silent(monkeypatch):
    monkeypatch.setattr(label_search, '_MAX_PAGES', 1)
    mock_pages(monkeypatch, {0: page([album(1)], 100, 1)})
    result = label_search.releases('LuckyMe')
    assert result['complete'] is False
    assert result['partial_reason'] == 'page_limit'


def test_missing_total_is_not_zero_and_valid_empty_is_complete(monkeypatch):
    mock_pages(monkeypatch, {0: page([], None, None)})
    result = label_search.releases('LuckyMe')
    assert result['complete'] is True
    assert result['total'] is None
    assert result['releases'] == []


@pytest.mark.parametrize(
    'payload', [{}, {'errors': [{'message': 'bad query'}]}]
)
def test_first_page_provider_error_raises_not_empty_success(
    monkeypatch, payload
):
    mock_pages(monkeypatch, {0: payload})
    with pytest.raises(ValueError, match='Spotify'):
        label_search.releases('LuckyMe')


@pytest.mark.parametrize('name', ['', 'x" OR artist:y', 'x\ny', 'x' * 201])
def test_invalid_label_is_rejected_before_requests(monkeypatch, name):
    def fail(*args, **kwargs):
        pytest.fail('Invalid input must not reach network')

    monkeypatch.setattr(label_search.httpx, 'get', fail)
    with pytest.raises(ValueError, match='label'):
        label_search.releases(name)
