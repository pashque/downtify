"""Native Deezer album metadata propagation, using offline REST-shaped rows."""

from copy import deepcopy
from unittest.mock import patch

import pytest

from downtify import deezer


@pytest.mark.parametrize('resolver', [deezer.album_from_id, deezer.finder_album])
@pytest.mark.parametrize('album_artist', ['Album Artist', 'Simon & Garfunkel', 'Earth, Wind & Fire'])
def test_native_album_retains_album_credit_across_featured_and_paginated_tracks(
    resolver, album_artist
):
    first = {
        'id': 1,
        'title': 'First (feat. Guest)',
        'artist': {'name': 'Guest'},
        'contributors': [{'name': 'Guest'}, {'name': album_artist}],
    }
    second = {
        'id': 2,
        'title': 'Second',
        'artist': {'name': album_artist},
        'album': {'title': 'The Album', 'cover_xl': 'https://example.com/track.jpg'},
    }
    payload = {
        'id': 70,
        'title': 'The Album',
        'artist': {'name': album_artist},
        'cover_xl': 'https://example.com/album.jpg',
        'release_date': '2026-01-02',
        'tracks': {
            'data': [first],
            'next': 'https://api.deezer.com/album/70/tracks?index=1',
        },
    }
    original = deepcopy(payload)
    with patch.object(deezer, '_get_json', side_effect=[payload, {'data': [second]}]) as get:
        result = resolver('70')
    songs = result['tracks'] if isinstance(result, dict) else result
    assert [song.get('album_artist') for song in songs] == [album_artist, album_artist]
    assert [song['album_name'] for song in songs] == ['The Album', 'The Album']
    assert [song['cover_url'] for song in songs] == [
        'https://example.com/album.jpg', 'https://example.com/track.jpg'
    ]
    assert [song['artists'] for song in songs] == [['Guest', album_artist], [album_artist]]
    assert [song['name'] for song in songs] == ['First (feat. Guest)', 'Second']
    assert [song['track_number'] for song in songs] == [1, 2]
    assert all(song['album_track_total'] == 2 for song in songs)
    assert all(song['release_date'] == '2026-01-02' for song in songs)
    assert payload == original
    assert get.call_args_list == [
        (('https://api.deezer.com/album/70',), {}),
        (('https://api.deezer.com/album/70/tracks?index=1',), {}),
    ]


@pytest.mark.parametrize('resolver', [deezer.album_from_id, deezer.finder_album])
@pytest.mark.parametrize('artist', [None, {}, {'name': ''}, {'name': '   '}])
def test_missing_album_credit_is_not_guessed_from_track_or_contributors(resolver, artist):
    payload = {
        'title': 'Compilation',
        'artist': artist,
        'contributors': [{'name': 'Not An Album Credit'}],
        'tracks': {'data': [{
            'id': 1,
            'title': 'Track',
            'artist': {'name': 'Track Artist'},
            'contributors': [{'name': 'Guest'}],
        }]},
    }
    with patch.object(deezer, '_get_json', return_value=payload) as get:
        result = resolver('70')
    songs = result['tracks'] if isinstance(result, dict) else result
    assert not songs[0].get('album_artist')
    assert songs[0]['artists'] == ['Track Artist', 'Guest']
    get.assert_called_once_with('https://api.deezer.com/album/70')
