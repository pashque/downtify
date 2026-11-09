"""Read exact Spotify album labels, never infer them from copyright."""

import httpx
import pytest

from downtify import label_catalog, spotify

ID = '0eyTz4axCv1nyRSCHxDNY0'


@pytest.fixture(autouse=True)
def clear_cache():
    label_catalog._album_label_cached.cache_clear()
    yield
    label_catalog._album_label_cached.cache_clear()


def response(monkeypatch, album, errors=None):
    calls = []
    monkeypatch.setattr(spotify, '_anonymous_token', lambda: 'anonymous-test')

    def get(url, **kwargs):
        calls.append(kwargs)
        return httpx.Response(
            200,
            request=httpx.Request('GET', url),
            json={
                'data': {'albumUnion': album},
                **({'errors': errors} if errors else {}),
            },
        )

    monkeypatch.setattr(label_catalog.httpx, 'get', get)
    return calls


def test_reads_authoritative_label_not_copyright(monkeypatch):
    calls = response(
        monkeypatch,
        {
            'uri': f'spotify:album:{ID}',
            'name': 'jg',
            'label': 'LUCKYME®',
            'copyright': {'items': [{'text': 'Other company'}]},
        },
    )
    assert label_catalog.album_label(ID) == 'LUCKYME®'
    assert label_catalog.album_label(ID) == 'LUCKYME®'
    assert len(calls) == 1
    assert calls[0]['params']['operationName'] == 'getAlbum'


def test_album_metadata_preserves_full_release_date(monkeypatch):
    response(monkeypatch, {
        'uri': f'spotify:album:{ID}', 'label': 'Frucht',
        'date': {'isoString': '2026-01-15T00:00:00Z', 'precision': 'DAY'},
    })
    assert label_catalog.album_metadata(ID) == {
        'album_id': ID, 'label': 'Frucht', 'release_date': '2026-01-15',
    }


def test_does_not_guess_from_copyright(monkeypatch):
    response(
        monkeypatch,
        {
            'uri': f'spotify:album:{ID}',
            'name': 'jg',
            'copyright': {'items': [{'text': '2026 LUCKYME®'}]},
        },
    )
    assert not label_catalog.album_label(ID)


@pytest.mark.parametrize(
    'album', [None, {}, {'uri': 'spotify:album:wrong', 'label': 'Wrong'}]
)
def test_rejects_different_or_unavailable_album(monkeypatch, album):
    response(monkeypatch, album)
    with pytest.raises(ValueError, match='Spotify'):
        label_catalog.album_label(ID)


def test_provider_error_is_not_a_missing_label(monkeypatch):
    calls = response(monkeypatch, None, [{'message': 'query failed'}])
    for _ in range(2):
        with pytest.raises(ValueError, match='Spotify'):
            label_catalog.album_label(ID)
    assert len(calls) == 2


@pytest.mark.parametrize('album_id', ['bad', '../etc', ''])
def test_invalid_id_never_contacts_provider(monkeypatch, album_id):
    def fail(*a, **k):
        pytest.fail('No remote requests')

    monkeypatch.setattr(label_catalog.httpx, 'get', fail)
    with pytest.raises(ValueError, match='Spotify'):
        label_catalog.album_label(album_id)
