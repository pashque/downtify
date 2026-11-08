from pathlib import Path
from downtify import m3u


def test_playlist_publication_is_atomic(tmp_path, monkeypatch):
    (tmp_path / 'a.mp3').touch()
    (tmp_path / 'b.mp3').touch()
    target, _ = m3u.write_m3u(tmp_path, 'P', [{'filename': 'a.mp3'}])
    assert target is not None
    before = target.read_text()
    replace = Path.replace
    publications = []

    def publish(staged, destination):
        assert Path(destination).read_text() == before
        assert staged != destination and 'b.mp3' in staged.read_text()
        publications.append(destination)
        return replace(staged, destination)
    monkeypatch.setattr(Path, 'replace', publish)
    m3u.write_m3u(tmp_path, 'P', [{'filename': 'b.mp3'}], preserve_existing=True)
    assert publications == [target]


def test_partial_batch_preserves_existing_playlist_and_metadata(tmp_path):
    for name in ('one.mp3', 'two.mp3', 'new.mp3'):
        (tmp_path / name).touch()
    path, _ = m3u.write_m3u(tmp_path, 'P', [
        {'filename': 'one.mp3', 'artist': 'Owner', 'title': 'First', 'duration': 12},
        {'filename': 'two.mp3', 'artist': 'Guest', 'title': 'Second', 'duration': 13},
    ])
    original = path.read_text()
    path, count = m3u.write_m3u(tmp_path, 'P', [
        {'filename': 'new.mp3', 'title': 'New', 'duration': 20},
    ], preserve_existing=True)
    assert count == 3
    assert m3u.read_m3u_tracks(path, tmp_path) == ['one.mp3', 'two.mp3', 'new.mp3']
    for line in original.splitlines():
        assert line in path.read_text().splitlines()


def test_partial_batch_deduplicates_and_excludes_deleted_or_unsafe_paths(tmp_path):
    (tmp_path / 'kept.mp3').touch()
    path, _ = m3u.write_m3u(tmp_path, 'P', [{'filename': 'kept.mp3'}])
    path.write_text(path.read_text() + '../missing.mp3\n../../../outside.mp3\n')
    _, count = m3u.write_m3u(tmp_path, 'P', [{'filename': 'kept.mp3', 'title': 'Updated'}], preserve_existing=True)
    assert count == 1
    assert m3u.read_m3u_tracks(path, tmp_path) == ['kept.mp3']


def test_incremental_write_keeps_existing_repeated_source_occurrences(tmp_path):
    (tmp_path / 'same.mp3').touch()
    (tmp_path / 'new.mp3').touch()
    path, _ = m3u.write_m3u(tmp_path, 'P', [{'filename': 'same.mp3'}, {'filename': 'same.mp3'}])
    assert path is not None
    _, kept = m3u.write_m3u(tmp_path, 'P', [{'filename': 'new.mp3'}], preserve_existing=True)
    assert kept == 3
    assert m3u.read_m3u_tracks(path, tmp_path) == ['same.mp3', 'same.mp3', 'new.mp3']


def test_missing_batch_preserves_large_playlist_with_real_m3u(tmp_path, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from downtify import api
    folder = tmp_path / 'P'
    folder.mkdir()
    existing = []
    for i in range(804):
        name = f'P/old-{i}.mp3'
        (tmp_path / name).touch()
        existing.append({'filename': name})
    path, _ = m3u.write_m3u(tmp_path, 'P', existing, playlist_subdir='P')
    monkeypatch.setattr(api.state, 'downloader', SimpleNamespace(download_dir=tmp_path))
    monkeypatch.setattr(api.state, 'playlist_catalog', None)
    monkeypatch.setattr(api.state, 'settings', {})
    monkeypatch.setattr(api, '_organize_enabled', lambda: False)
    monkeypatch.setattr(api, 'slskd_dir_from_downloader', lambda dl: None)

    async def acquire(song, *args, **kwargs):
        if song['name'] == 'failed':
            return None
        (folder / 'new.mp3').touch()
        return 'P/new.mp3'
    monkeypatch.setattr(api, '_run_download', acquire)
    asyncio.run(api._process_batch([{'name': 'new'}, {'name': 'failed'}], ['a', 'b'], '', True, playlist_name='P'))
    assert path is not None
    assert len(m3u.read_m3u_tracks(path, tmp_path)) == 805
    assert m3u.read_m3u_tracks(path, tmp_path)[:804] == [x['filename'] for x in existing]


def test_full_snapshot_can_still_remove_playlist_membership(tmp_path):
    for name in ('a.mp3', 'b.mp3'):
        (tmp_path / name).touch()
    path, _ = m3u.write_m3u(tmp_path, 'P', [{'filename': 'a.mp3'}, {'filename': 'b.mp3'}])
    _, count = m3u.write_m3u(tmp_path, 'P', [{'filename': 'b.mp3'}])
    assert count == 1
    assert m3u.read_m3u_tracks(path, tmp_path) == ['b.mp3']
