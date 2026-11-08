"""Spotify Web API tags call EP releases 'single'; search may say 'EP'."""

import json
from pathlib import Path
import pytest
from downtify import spotify
from downtify.album_source import resolve_album_source
from downtify.track_index import TrackIndex


@pytest.fixture(autouse=True)
def _strict_layer_only(monkeypatch):
    # These tests guard the exact-fingerprint layer; the best-effort search
    # fallback is covered by tests/test_album_source_loose.py.
    from downtify import album_source

    monkeypatch.setattr(album_source, '_loose_versions', lambda *a, **k: [])


@pytest.mark.parametrize(
    ('tag_type', 'provider_type', 'status'),
    [
        ('SINGLE', 'EP', 'resolved'),
        ('EP', 'SINGLE', 'resolved'),
        ('SINGLE', 'ALBUM', 'unavailable'),
        ('ALBUM', 'EP', 'unavailable'),
    ],
)
def test_actual_sampler_type_family(
    tmp_path, monkeypatch, tag_type, provider_type, status
):
    samples = json.loads(
        (
            Path(__file__).parent / 'fixtures/legacy_library_samples.json'
        ).read_text()
    )
    sample = next(s for s in samples if s['local']['album'] == '420 Sampler')
    local = [
        dict(r, file=r['filename'], album_type=tag_type, album_track_total=3)
        for r in sample['local']['rows']
    ]
    source = sample['sources'][0]
    monkeypatch.setattr(
        spotify,
        'search',
        lambda query: {'albums': [dict(source['album'], type=provider_type)]},
    )
    monkeypatch.setattr(
        spotify, 'album_tracks_from_id', lambda aid: source['tracks']
    )
    result = resolve_album_source(
        local, '420 Sampler', TrackIndex(tmp_path / 'index.db')
    )
    assert result['status'] == status
    if status == 'resolved':
        assert result['tracks'] == source['tracks']
