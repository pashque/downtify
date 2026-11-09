import pytest
from fastapi import HTTPException

from downtify import api, label_search, spotify


def test_endpoint_uses_paginated_catalog_not_suggestions(monkeypatch):
    payload = {
        'label': 'LuckyMe',
        'releases': [],
        'complete': True,
        'total': 0,
    }
    monkeypatch.setattr(label_search, 'releases', lambda _: payload)

    def no_suggestions(_):
        pytest.fail('Label route must use paginated search')

    monkeypatch.setattr(spotify, 'label_releases', no_suggestions)
    assert api.label_releases_endpoint(label='LuckyMe') == payload


def test_endpoint_reports_first_page_failure(monkeypatch):
    def fail(_):
        raise ValueError('Spotify unavailable')

    monkeypatch.setattr(label_search, 'releases', fail)
    monkeypatch.setattr(spotify, 'label_releases', fail)
    with pytest.raises(HTTPException) as exc:
        api.label_releases_endpoint(label='LuckyMe')
    assert exc.value.status_code == 502


def test_endpoint_loads_one_year(monkeypatch):
    monkeypatch.setattr(
        label_search,
        'year_releases',
        lambda label, year: {'label': label, 'year': year, 'releases': []},
    )
    assert api.label_releases_endpoint(label='Frucht', year=2020)['year'] == 2020


@pytest.mark.parametrize('year', [1800, 3000])
def test_endpoint_rejects_invalid_year(year):
    with pytest.raises(HTTPException) as exc:
        api.label_releases_endpoint(label='Frucht', year=year)
    assert exc.value.status_code == 422
