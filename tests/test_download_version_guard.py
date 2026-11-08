"""Synthetic offline audio proves mismatched automatic downloads never publish."""
import shutil
import subprocess

import pytest

from downtify.downloader import Downloader

SONG = dict(source='spotify', song_id='4Ug8J5Vo31likL5f1HNP5z',
            name='On Your Side', artists=['Jacques Greene', 'How To Dress Well'],
            album_name='ANTH01', duration=343)


@pytest.fixture(scope='module')
def recordings(tmp_path_factory):
    root = tmp_path_factory.mktemp('synthetic-version-audio')
    for name, duration in [('radio', 247.7), ('album', 343.2)]:
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi',
                        '-i', 'anullsrc=r=16000:cl=mono', '-t', str(duration),
                        '-c:a', 'libmp3lame', '-b:a', '16k', str(root / f'{name}.mp3')],
                       check=True, timeout=30)
    return root


def fetched(monkeypatch, downloader, fixture):
    def acquire(video_id, target_dir, basename, **kwargs):
        path = target_dir / f'{basename}.mp3'
        shutil.copyfile(fixture, path)
        return path
    monkeypatch.setattr(downloader, '_fetch_audio', acquire)


def test_radio_audio_cannot_overwrite_existing_album_file(tmp_path, monkeypatch, recordings):
    downloader = Downloader(tmp_path)
    destination = tmp_path / 'On Your Side.mp3'
    destination.write_bytes(b'correct existing user file')
    fetched(monkeypatch, downloader, recordings / 'radio.mp3')
    with pytest.raises(RuntimeError, match='(?i)duration|version|length'):
        downloader.fetch_audio('radio', tmp_path, 'On Your Side', song=SONG)
    assert destination.read_bytes() == b'correct existing user file'
    assert sorted(p.name for p in tmp_path.iterdir()) == [destination.name]


def test_correct_album_audio_is_published_after_validation(tmp_path, monkeypatch, recordings):
    downloader = Downloader(tmp_path)
    fetched(monkeypatch, downloader, recordings / 'album.mp3')
    result = downloader.fetch_audio('album', tmp_path, 'On Your Side', song=SONG)
    assert result == tmp_path / 'On Your Side.mp3'
    assert result.read_bytes() == (recordings / 'album.mp3').read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == [result.name]


def test_invalid_automatic_audio_is_not_published(tmp_path, monkeypatch):
    downloader = Downloader(tmp_path)
    invalid = tmp_path / 'fixture.bin'
    invalid.write_bytes(b'not an audio recording')
    fetched(monkeypatch, downloader, invalid)
    with pytest.raises(RuntimeError, match='(?i)duration|verify|audio'):
        downloader.fetch_audio('invalid', tmp_path, 'On Your Side', song=SONG)
    assert not (tmp_path / 'On Your Side.mp3').exists()


def test_local_provider_radio_file_is_rejected_before_tagging_or_copy(tmp_path, monkeypatch, recordings):
    downloader = Downloader(tmp_path, download_cover_art=False)
    monkeypatch.setattr('downtify.downloader._MetadataLookups',
                        lambda *args: pytest.fail('wrong file reached metadata publication'))
    with pytest.raises(RuntimeError, match='(?i)version|duration'):
        downloader._finalize_local_source(SONG, recordings / 'radio.mp3', 'slskd', None, None)
    assert list(tmp_path.iterdir()) == []


def test_manual_video_choice_keeps_its_requested_version(tmp_path, monkeypatch, recordings):
    downloader = Downloader(tmp_path)
    fetched(monkeypatch, downloader, recordings / 'radio.mp3')
    result = downloader.fetch_audio('manual', tmp_path, 'Selected',
                                    song=dict(SONG, source='youtube', youtube_id='manual'))
    assert result.read_bytes() == (recordings / 'radio.mp3').read_bytes()
