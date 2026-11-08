"""Real ffmpeg audio streams across supported containers; tags intentionally absent."""
import shutil
import subprocess

import pytest

from downtify.downloader import Downloader

# encoder, muxer, suffix; MP4/M4A and ADTS/AAC share the native AAC encoder.
CASES = [
    pytest.param('libmp3lame', 'mp3', '.mp3', id='mp3'),
    pytest.param('flac', 'flac', '.flac', id='flac'),
    pytest.param('aac', 'ipod', '.m4a', id='m4a'),
    pytest.param('libvorbis', 'ogg', '.ogg', id='ogg'),
    pytest.param('libopus', 'opus', '.opus', id='opus'),
    pytest.param('pcm_s16le', 'wav', '.wav', id='wav'),
    pytest.param('aac', 'adts', '.aac', id='aac'),
]


@pytest.mark.parametrize(('encoder', 'muxer', 'suffix'), CASES)
def test_real_audio_in_supported_container_with_missing_optional_identity_tags(tmp_path, encoder, muxer, suffix):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('ffmpeg/ffprobe unavailable')
    available = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True, check=True).stdout
    if encoder not in available:
        pytest.skip(f'ffmpeg encoder {encoder} unavailable')

    target = tmp_path / f'untagged{suffix}'
    # Deliberately omit title, artist, album and other optional metadata.
    subprocess.run([
        'ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.35',
        '-c:a', encoder, '-f', muxer, '-y', str(target),
    ], check=True)
    assert target.stat().st_size > 0
    probe = subprocess.run([
        'ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name,duration',
        '-of', 'json', str(target),
    ], capture_output=True, text=True, check=True)
    assert 'codec_name' in probe.stdout

    # Missing optional tags mean unknown, not a contradictory identity.
    Downloader(tmp_path)._validate_existing_copy(
        {'name': 'Song', 'artists': ['Artist'], 'album': 'Album'}, target.name
    )
