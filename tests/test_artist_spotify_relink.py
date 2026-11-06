"""Artists left without a Spotify link are retried, by name and by their own tracks."""
import json
import os
from datetime import datetime, timedelta, timezone

from downtify import artist_profile as ap
from downtify import spotify


def _profile(tmp_path, name, **extra):
    data = ap._default_profile(name)
    data.update(extra)
    ap._save_profile(tmp_path, name, data)
    return ap._profile_path_for(tmp_path, name)


def _quiet(monkeypatch):
    monkeypatch.setattr(ap, '_spotify_id_from_name', lambda name: None)
    monkeypatch.setattr(ap, '_spotify_id_from_tracks', lambda *a, **k: None)


def test_existing_unlinked_profile_is_retried_and_saved(tmp_path, monkeypatch):
    path = _profile(tmp_path, 'Mindy')
    monkeypatch.setattr(ap, '_spotify_id_from_name', lambda name: 'S' * 22)
    out = ap.ensure_profile(tmp_path, 'Mindy', [], 'en')
    assert out['platforms_id']['spotify'] == 'S' * 22
    assert json.loads(path.read_text())['platforms_id']['spotify'] == 'S' * 22


def test_failed_retry_waits_a_day(tmp_path, monkeypatch):
    _profile(tmp_path, 'Mindy')
    calls = []
    monkeypatch.setattr(ap, '_spotify_id_from_name', lambda name: calls.append(name))
    monkeypatch.setattr(ap, '_spotify_id_from_tracks', lambda *a, **k: None)
    ap.ensure_profile(tmp_path, 'Mindy', [], 'en')
    ap.ensure_profile(tmp_path, 'Mindy', [], 'en')
    assert calls == ['Mindy']
    stale = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    data = ap.load_profile(tmp_path, 'Mindy'); data['spotify_lookup_at'] = stale
    ap._save_profile(tmp_path, 'Mindy', data)
    ap.ensure_profile(tmp_path, 'Mindy', [], 'en')
    assert calls == ['Mindy', 'Mindy']


def test_linked_profile_is_not_looked_up_again(tmp_path, monkeypatch):
    _profile(tmp_path, 'Drake', platforms_id={'spotify': 'D' * 22})
    monkeypatch.setattr(ap, '_spotify_id_from_name', lambda name: (_ for _ in ()).throw(AssertionError))
    assert ap.ensure_profile(tmp_path, 'Drake', [], 'en')['platforms_id']['spotify'] == 'D' * 22


def test_track_fallback_finds_artist_whose_name_search_fails(tmp_path, monkeypatch):
    _profile(tmp_path, 'Mindy Meng Wang')
    monkeypatch.setattr(ap, '_spotify_id_from_name', lambda name: None)
    monkeypatch.setattr(ap, '_local_track_facts', lambda d, f: {'title': 'Flow', 'duration': 204.2})
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [dict(id='A' * 22, name='X', artists=['Mindy Meng Wang 王萌'])]})
    monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid: [
        dict(song_id='T' * 22, name='Flow', duration=205, artists=['Mindy Meng Wang 王萌', 'Tim Shiel'])])
    monkeypatch.setattr(spotify, 'primary_artist_id_from_track_id', lambda tid: 'M' * 22 if tid == 'T' * 22 else None)
    out = ap.ensure_profile(tmp_path, 'Mindy Meng Wang', ['Mindy/Flow.mp3'], 'en')
    assert out['platforms_id']['spotify'] == 'M' * 22


def test_track_fallback_rejects_other_artists_and_wrong_lengths(tmp_path, monkeypatch):
    monkeypatch.setattr(ap, '_local_track_facts', lambda d, f: {'title': 'Flow', 'duration': 204.2})
    monkeypatch.setattr(spotify, 'search', lambda q: {'albums': [dict(id='A' * 22, name='X', artists=['Someone'])]})
    monkeypatch.setattr(spotify, 'primary_artist_id_from_track_id', lambda tid: 'X' * 22)
    for track in (dict(song_id='T' * 22, name='Flow', duration=205, artists=['Someone Else']),
                  dict(song_id='T' * 22, name='Flow', duration=260, artists=['Mindy Meng Wang'])):
        monkeypatch.setattr(spotify, 'album_tracks_from_id', lambda aid, t=track: [t])
        assert ap._spotify_id_from_tracks(tmp_path, 'Mindy Meng Wang', ['a.mp3']) is None


def test_profile_files_are_readable_by_the_host_user(tmp_path):
    path = _profile(tmp_path, 'Drake')
    assert os.stat(path).st_mode & 0o044 == 0o044
