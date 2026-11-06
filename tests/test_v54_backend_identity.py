"""Offline regressions for complete provider releases and literal identities."""
import pytest
from downtify import spotify


def test_discography_without_total_pages_until_empty(monkeypatch):
    offsets = []
    def query(op, variables, *args):
        offsets.append(variables['offset'])
        batch = [{'uri': f'spotify:album:{variables["offset"]}', 'name': 'Same'}] if len(offsets) < 3 else []
        return {'artistUnion': {'discography': {'all': {'items': batch}}}}
    monkeypatch.setattr(spotify, '_partner_query', query)
    result = spotify._artist_full_discography('artist', 'token')
    assert offsets == [0, 1, 2]
    assert len(spotify._artist_releases(result, 'AC/DC')) == 2
    assert result['completeness']['complete'] is True


def test_partial_discography_survives_page_failure(monkeypatch):
    def query(op, variables, *args):
        if variables['offset']:
            raise ValueError('offline')
        return {'artistUnion': {'discography': {'all': {'items': [{'uri': 'spotify:album:A', 'name': 'Kept'}], 'totalCount': 3}}}}
    monkeypatch.setattr(spotify, '_partner_query', query)
    result = spotify._artist_full_discography('a', 't')
    assert result['all']['items'][0]['name'] == 'Kept'
    assert result['completeness']['reason'] == 'page_failure'
    assert result['completeness']['complete'] is False


def test_discography_page_cap_is_not_complete(monkeypatch):
    monkeypatch.setattr(spotify, '_DISCOGRAPHY_MAX_PAGES', 1)
    monkeypatch.setattr(spotify, '_partner_query', lambda *a: {'artistUnion': {'discography': {'all': {'items': [1], 'totalCount': 3}}}})
    assert spotify._artist_full_discography('a', 't')['completeness']['reason'] == 'page_cap'


def test_artist_page_reports_overview_quality_additively(monkeypatch):
    monkeypatch.setattr(spotify, '_artist_entity', lambda a: ({}, 'Name', 'cover', 't'))
    monkeypatch.setattr(spotify, '_artist_full_discography', lambda *a: (_ for _ in ()).throw(ValueError()))
    monkeypatch.setattr(spotify, '_artist_discography', lambda *a: {})
    quality = {}
    assert spotify.artist_page_from_id('a', metadata=quality) == ('Name', 'cover', [])
    assert quality == {'complete': False, 'reason': 'overview_fallback', 'source': 'overview'}


def test_track_and_graphql_rows_propagate_ordered_ids_without_fetches():
    credits = [{'name':'Tyler, The Creator', 'uri':'spotify:artist:'+'A'*22}, {'name':'Guest'}, {'name':'Third', 'id':'C'*22}]
    row = spotify._track_dict({'name':'Song', 'artists':credits, 'album':{'id':'L'*22}}, track_id='T'*22)
    assert row['artists'] == ['Tyler, The Creator','Guest','Third']
    assert row['artist_ids'] == ['A'*22, '', 'C'*22]
    assert row['album_id'] == 'L'*22
    gql = spotify._track_dict_from_graphql_item({'itemV2': {'__typename':'TrackResponseWrapper', 'data': {
        'uri':'spotify:track:'+'T'*22, 'artists':{'items':[{'uri':'spotify:artist:'+'A'*22, 'profile':{'name':'Tyler, The Creator'}}]},
        'albumOfTrack':{'uri':'spotify:album:'+'L'*22}}}})
    assert gql['artist_ids'] == ['A'*22]
    assert gql['album_id'] == 'L'*22


def test_release_rows_carry_own_structured_artist_ids():
    node = {'uri':'spotify:album:'+'L'*22, 'name':'Record', 'artists':{'items':[{'uri':'spotify:artist:'+'A'*22, 'profile':{'name':'AC/DC'}}]}}
    result = spotify._artist_releases({'all':{'items':[node]}}, 'AC/DC')[0]
    assert result['artists'] == ['AC/DC']
    assert result['artist_ids'] == ['A'*22]


def test_album_rows_keep_requested_release_id(monkeypatch):
    entity = {'name':'Record', 'releaseDate':'2020', 'artists':[{'name':'AC/DC', 'id':'A'*22}], 'trackList':[{'id':'T'*22, 'name':'Song'}]}
    monkeypatch.setattr(spotify, '_fetch_embed_json', lambda *a: {'props':{'pageProps':{'entity':entity}}})
    rows = spotify.album_tracks_from_id('L'*22)
    assert rows[0]['album_id'] == 'L'*22
    assert rows[0]['artist_ids'] == ['A'*22]


def test_opaque_subtitle_marked_not_structured():
    row = spotify._track_dict({'subtitle':'A, B'}, track_id='T'*22)
    assert row['artists'] == ['A, B']
    assert row['artists_structured'] is False
    structured = spotify._track_dict({'artists':[{'name':'Tyler, The Creator', 'id':'A'*22}]}, track_id='T'*22)
    assert structured['artists_structured'] is True


def test_enrichment_does_not_misalign_ids_with_kept_credits():
    row = spotify._merge_full_track_metadata({'artists':['Original']}, {'artists':['Other'], 'artist_ids':['A'*22]})
    assert row['artists'] == ['Original']
    assert not any(row.get('artist_ids') or [])


def test_album_subtitle_fallback_stays_opaque(monkeypatch):
    entity = {'name':'Record', 'releaseDate':'2020', 'subtitle':'A, B', 'trackList':[{'id':'T'*22, 'name':'Song'}]}
    monkeypatch.setattr(spotify, '_fetch_embed_json', lambda *a: {'props':{'pageProps':{'entity':entity}}})
    assert spotify.album_tracks_from_id('L'*22)[0]['artists_structured'] is False


def test_empty_page_before_reported_total_is_incomplete(monkeypatch):
    monkeypatch.setattr(spotify, '_partner_query', lambda *a: {'artistUnion':{'discography':{'all':{'items':[], 'totalCount':10}}}})
    result = spotify._artist_full_discography('a','t')
    assert result['completeness']['complete'] is False
    assert result['completeness']['reason'] == 'early_empty_page'


def test_artist_lookup_does_not_strip_punctuation(monkeypatch):
    monkeypatch.setattr(spotify, '_search_suggestion_items', lambda q: [])
    monkeypatch.setattr(spotify, 'search_results', lambda items: {'artists':[{'id':'A'*22, 'name':'AC/DC'}]})
    assert spotify.search_artist_by_name('ACDC') is None
    assert spotify.search_artist_by_name('ac/dc')['id'] == 'A'*22


def test_search_album_propagates_artist_ids():
    result = spotify.search_results([{'item':{'__typename':'AlbumResponseWrapper', 'data': {
        'uri':'spotify:album:'+'L'*22, 'name':'Record', 'artists':{'items':[{'uri':'spotify:artist:'+'A'*22, 'profile':{'name':'AC/DC'}}]}}}}])
    assert result['albums'][0]['artist_ids'] == ['A'*22]
