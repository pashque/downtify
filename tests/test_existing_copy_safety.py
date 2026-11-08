import shutil
import subprocess
from pathlib import Path

import mutagen
import pytest
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TXXX

from downtify.downloader import Downloader


def mp3(path: Path, title='Song', artist='Artist', extra=()):
    if not shutil.which('ffmpeg'):
        pytest.skip('ffmpeg unavailable')
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.2', '-metadata', f'title={title}', '-metadata', f'artist={artist}', *extra, '-q:a', '9', '-y', str(path)], check=True)


def test_missing_only_refuses_invalid_occupied_exact_target_before_source_lookup(tmp_path, monkeypatch):
    target = tmp_path / 'Artist - Song.mp3'
    mp3(target, title='Different Song')
    original = target.read_bytes()
    d = Downloader(tmp_path)
    calls = []
    monkeypatch.setattr(d, '_resolve_source', lambda *a: calls.append('source'))
    with pytest.raises(RuntimeError, match='existing.*does not match'):
        d.download({'name': 'Song', 'artists': ['Artist'], 'downtify_download_mode': 'missing'})
    assert not calls
    assert target.read_bytes() == original


def test_unreadable_occupied_target_refuses_without_lookup_or_overwrite(tmp_path, monkeypatch):
    target = tmp_path / 'Artist - Song.mp3'
    target.write_bytes(b'not audio')
    original = target.read_bytes()
    d = Downloader(tmp_path)
    monkeypatch.setattr(d, '_resolve_source', lambda *a: pytest.fail('provider lookup'))
    with pytest.raises(RuntimeError, match='existing'):
        d.download({'name': 'Song', 'artists': ['Artist'], 'downtify_download_mode': 'missing'})
    assert target.read_bytes() == original


def test_matching_identity_and_unknown_optional_tag_are_reused(tmp_path, monkeypatch):
    target = tmp_path / 'Artist - Song.mp3'
    mp3(target, extra=['-metadata', 'album=Unrelated Optional Album'])
    d = Downloader(tmp_path)
    monkeypatch.setattr(d, '_resolve_source', lambda *a: pytest.fail('provider lookup'))
    assert d.download({'name': 'Song', 'artists': ['Artist'], 'downtify_download_mode': 'missing'}) == target.name


def test_explicit_redownload_bypasses_existing_copy_guard_without_source_resolution(tmp_path, monkeypatch):
    target = tmp_path / 'Artist - Song.mp3'
    target.write_bytes(b'occupied')
    original = target.read_bytes()
    d = Downloader(tmp_path)
    calls = []
    monkeypatch.setattr(d, '_resolve_source', lambda *a: calls.append('source'))
    with pytest.raises(Exception):
        d.download({'name': 'Song', 'artists': ['Artist'], 'downtify_download_mode': 'redownload'})
    assert calls == ['source']
    assert target.read_bytes() == original


def test_direct_validation_rejects_missing_path(tmp_path):
    d = Downloader(tmp_path)
    with pytest.raises(RuntimeError, match='existing'):
        d._validate_existing_copy({'name': 'Song', 'artists': ['Artist']}, 'absent.mp3')


def test_readable_file_without_tags_is_not_a_contradiction(tmp_path):
    target = tmp_path / 'untagged.mp3'
    mp3(target)
    audio = MutagenFile(str(target), easy=True)
    audio.delete()
    audio.save()
    Downloader(tmp_path)._validate_existing_copy({'name': 'Song', 'artists': ['Artist']}, target.name)


def test_joined_collaboration_tag_matches_exact_artist_credits(tmp_path):
    target = tmp_path / 'collab.mp3'
    mp3(target, artist='Artist One, Artist Two')
    Downloader(tmp_path)._validate_existing_copy(
        {'name': 'Song', 'artists': ['Artist One', 'Artist Two']}, target.name
    )


@pytest.mark.parametrize('bad', [
    {'name': 'Different Song', 'artists': ['Artist']},
    {'name': 'Song', 'artists': ['Other Artist']},
])
def test_wrong_identity_is_rejected(tmp_path, bad):
    target = tmp_path / 'copy.mp3'
    mp3(target)
    with pytest.raises(RuntimeError, match='existing'):
        Downloader(tmp_path)._validate_existing_copy(bad, target.name)


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / f'{tmp_path.name}-outside.mp3'
    mp3(outside)
    link = tmp_path / 'escape.mp3'
    link.symlink_to(outside)
    try:
        with pytest.raises(RuntimeError, match='existing'):
            Downloader(tmp_path)._validate_existing_copy({'name': 'Song', 'artists': ['Artist']}, link.name)
    finally:
        outside.unlink(missing_ok=True)


def test_change_during_validation_is_rejected(tmp_path, monkeypatch):
    target = tmp_path / 'changing.mp3'
    mp3(target)
    original = mutagen.File

    def mutate(*args, **kwargs):
        audio = original(*args, **kwargs)
        target.write_bytes(target.read_bytes() + b'changed')
        return audio
    monkeypatch.setattr(mutagen, 'File', mutate)
    with pytest.raises(RuntimeError, match='existing'):
        Downloader(tmp_path)._validate_existing_copy({'name': 'Song', 'artists': ['Artist']}, target.name)


def test_truncated_after_valid_mp3_tags_is_rejected(tmp_path):
    target = tmp_path / 'truncated.mp3'
    mp3(target)
    original = target.read_bytes()
    target.write_bytes(original[: min(500, len(original) - 1)])
    # Mutagen can still parse the ID3/container header after the audio payload
    # is truncated; a bounded ffprobe must find an actual audio stream.
    with pytest.raises(RuntimeError, match='existing'):
        Downloader(tmp_path)._validate_existing_copy({'name': 'Song', 'artists': ['Artist']}, target.name)


def test_structured_collaboration_credit_requires_complete_joined_match(tmp_path):
    target = tmp_path / 'collab.mp3'
    mp3(target, artist='Artist One')
    tags = ID3(str(target))
    tags.add(TXXX(encoding=3, desc='ARTISTS', text=['Artist One']))
    tags.save()
    expected = {'name': 'Song', 'artists': ['Artist One', 'Artist Two'], 'artists_structured': True}
    with pytest.raises(RuntimeError, match='existing'):
        Downloader(tmp_path)._validate_existing_copy(expected, target.name)


def test_structured_literal_comma_artist_is_not_split_or_partial_match(tmp_path):
    target = tmp_path / 'comma.mp3'
    mp3(target, artist='Earth, Wind & Fire')
    tags = ID3(str(target))
    tags.add(TXXX(encoding=3, desc='ARTISTS', text=['Earth, Wind & Fire']))
    tags.save()
    Downloader(tmp_path)._validate_existing_copy(
        {'name': 'Song', 'artists': ['Earth, Wind & Fire'], 'artists_structured': True}, target.name
    )
    with pytest.raises(RuntimeError, match='existing'):
        Downloader(tmp_path)._validate_existing_copy(
            {'name': 'Song', 'artists': ['Earth, Wind'], 'artists_structured': True}, target.name
        )
