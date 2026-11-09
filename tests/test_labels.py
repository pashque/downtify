"""Bounded label discovery must never masquerade as a full discography."""

import httpx
import pytest

from downtify import spotify


@pytest.mark.parametrize(
    'payload',
    [
        {'errors': [{'message': 'PersistedQueryNotFound'}]},
        {},
        {'data': {'searchV2': None}},
    ],
)
def test_label_search_rejects_graphql_failures(monkeypatch, payload):
    monkeypatch.setattr(spotify, '_anonymous_token', lambda: 'anonymous-test')
    monkeypatch.setattr(
        spotify.httpx,
        'get',
        lambda *a, **k: httpx.Response(
            200,
            json=payload,
            request=httpx.Request('GET', 'https://example.test'),
        ),
    )
    with pytest.raises(ValueError, match='Spotify search failed'):
        spotify.label_releases('LuckyMe')


def test_label_releases_use_label_filter_and_native_release_shape(monkeypatch):
    queries = []

    def search(query):
        queries.append(query)
        return {
            'albums': [
                {
                    'id': '0eyTz4axCv1nyRSCHxDNY0',
                    'name': 'jg',
                    'artists': ['Jacques Greene'],
                    'year': '2026',
                    'cover_url': 'https://i.scdn.co/image/test',
                    'type': 'ALBUM',
                },
                {
                    'id': '4K8ggbbaVkoq9rRLeV593t',
                    'name': 'Blue Spring',
                    'artists': ['Nathan Micay'],
                    'year': '2019',
                    'type': 'ALBUM',
                },
            ]
        }

    monkeypatch.setattr(spotify, 'search', search)
    result = spotify.label_releases(' LuckyMe ')
    assert queries == ['label:"LuckyMe"']
    assert result['label'] == 'LuckyMe'
    assert result['complete'] is False
    assert 'not a complete catalog' in result['notice']
    assert [r['name'] for r in result['releases']] == ['jg', 'Blue Spring']
    release = result['releases'][0]
    assert release['album_id'] == '0eyTz4axCv1nyRSCHxDNY0'
    assert release['url'] == (
        'https://open.spotify.com/album/0eyTz4axCv1nyRSCHxDNY0'
    )
    assert release['source'] == 'spotify'
    assert release['artists'] == ['Jacques Greene']


def test_label_releases_deduplicate_exact_ids_not_editions(monkeypatch):
    first = {'id': '0eyTz4axCv1nyRSCHxDNY0', 'name': 'jg', 'year': '2026'}
    other = {**first, 'id': '4K8ggbbaVkoq9rRLeV593t'}
    monkeypatch.setattr(
        spotify,
        'search',
        lambda _: {
            'albums': [first, first, other, {'id': '../bad', 'name': 'bad'}],
        },
    )
    result = spotify.label_releases('LuckyMe')
    assert len(result['releases']) == 2


@pytest.mark.parametrize(
    'label', ['', '  ', 'x' * 201, 'LuckyMe" OR artist:x', 'x\ny']
)
def test_label_releases_reject_query_injection_before_search(
    monkeypatch, label
):
    def unexpected(_):
        pytest.fail('Invalid label must not reach Spotify')

    monkeypatch.setattr(spotify, 'search', unexpected)
    with pytest.raises(ValueError, match='label'):
        spotify.label_releases(label)


def test_label_releases_does_not_hide_provider_failure(monkeypatch):
    def fail(_):
        raise ValueError('Spotify search failed')

    monkeypatch.setattr(spotify, 'search', fail)
    with pytest.raises(ValueError, match='Spotify search failed'):
        spotify.label_releases('LuckyMe')


def test_label_releases_empty_is_still_incomplete(monkeypatch):
    monkeypatch.setattr(spotify, 'search', lambda _: {'albums': []})
    result = spotify.label_releases('LuckyMe')
    assert result['releases'] == []
    assert result['complete'] is False
