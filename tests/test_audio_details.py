"""Read-only, on-demand technical details from actual generated audio."""
import hashlib
import subprocess

import pytest

from downtify import audio_details


def test_details_cache_is_stat_validated_and_returns_independent_results(tmp_path, monkeypatch):
    path = generate(tmp_path / 'cached.mp3', '-c:a', 'libmp3lame')
    original = audio_details.MutagenFile
    calls = []

    def counted(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)
    monkeypatch.setattr(audio_details, 'MutagenFile', counted)
    first = audio_details.read_audio_details(path)
    first['codec'] = 'wrong'
    assert audio_details.read_audio_details(path)['codec'] == 'mp3'
    assert len(calls) == 1
    import os
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1))
    audio_details.read_audio_details(path)
    assert len(calls) == 2


def test_compressed_bitrate_is_measured_not_nominal_or_decoded_pcm_rate(tmp_path):
    for suffix, encoder in [('m4a', 'alac'), ('ogg', 'libvorbis')]:
        path = generate(tmp_path / f'silence.{suffix}', '-c:a', encoder)
        details = audio_details.read_audio_details(path)
        assert 0 < details['bitrate'] < 20000


def test_endpoint_preserves_external_and_slskd_roots_but_rejects_escape(tmp_path, monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request

    from downtify import api
    from downtify.library_catalog import LibraryContext
    from downtify.library_paths import library_stored_path
    root, extra, slskd, outside = [tmp_path / name for name in ('downloads', 'extra', 'slskd', 'outside')]
    for folder in (root, extra, slskd, outside):
        folder.mkdir()
    ctx = LibraryContext(download_dir=root, slskd_dir=slskd, extra_dirs=[extra])
    monkeypatch.setattr(api, 'library_context', lambda: ctx)
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda request: None)
    request = Request({'type': 'http', 'headers': []})
    for folder in (extra, slskd):
        path = generate(folder / 'file.mp3', '-c:a', 'libmp3lame')
        stored = library_stored_path(path, root, slskd, [extra])
        assert api.library_audio_details(request, stored)['codec'] == 'mp3'
    secret = generate(outside / 'secret.mp3', '-c:a', 'libmp3lame')
    (root / 'escape.mp3').symlink_to(secret)
    for bad in ('escape.mp3', '../outside/secret.mp3', 'ext/unknown/file.mp3', 'notes.txt'):
        with pytest.raises(HTTPException) as exc:
            api.library_audio_details(request, bad)
        assert exc.value.status_code == 404


def test_ffprobe_failure_does_not_expose_nominal_bitrate(tmp_path, monkeypatch):
    path = generate(tmp_path / 'file.ogg', '-c:a', 'libvorbis')

    def missing(*args, **kwargs):
        raise FileNotFoundError('ffprobe unavailable')
    monkeypatch.setattr(audio_details.subprocess, 'run', missing)
    details = audio_details.read_audio_details(path)
    assert details['codec'] == 'vorbis'
    assert 'bitrate' not in details


def test_mp3_mixed_modes_are_hidden_and_dual_channel_is_read_from_headers(tmp_path):
    from mutagen.mp3 import MP3, MPEGFrame
    path = generate(tmp_path / 'modes.mp3', '-c:a', 'libmp3lame', '-joint_stereo', '0')
    data = bytearray(path.read_bytes())
    with path.open('rb') as stream:
        stream.seek(MP3(path).info.frame_offset)
        frames = []
        while stream.tell() < len(data):
            frame = MPEGFrame(stream)
            if frame.sketchy:
                frames.append(frame.frame_offset)
    for offset in frames:
        data[offset + 3] = (data[offset + 3] & 0x3f) | 0x80
    path.write_bytes(data)
    assert audio_details.read_audio_details(path)['channel_mode'] == 'Dual channel'
    data[frames[-1] + 3] &= 0x3f
    before = path.stat()
    path.write_bytes(data)
    # Overlay filesystems can give rapid, same-size writes identical stat keys.
    # This test exercises mixed frame modes, not cache invalidation timing.
    import os
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    assert 'channel_mode' not in audio_details.read_audio_details(path)


def test_audio_details_endpoint_is_available_to_authenticated_library_clients():
    from downtify.auth import CLIENT, classify
    assert classify('GET', '/api/library/audio-details') == CLIENT


def test_audio_details_endpoint_resolves_visible_real_file_and_rechecks_access(tmp_path, monkeypatch):
    from fastapi import HTTPException
    from starlette.requests import Request

    from downtify import api
    from downtify.library_catalog import LibraryContext
    path = generate(tmp_path / 'track.mp3', '-c:a', 'libmp3lame')
    monkeypatch.setattr(api, 'library_context', lambda: LibraryContext(download_dir=tmp_path))
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda request: None)
    request = Request({'type': 'http', 'headers': []})
    assert api.library_audio_details(request, 'track.mp3')['codec'] == 'mp3'
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda request: set())
    with pytest.raises(HTTPException) as exc:
        api.library_audio_details(request, 'track.mp3')
    assert exc.value.status_code == 404
    monkeypatch.setattr(api, 'allowed_entry_keys', lambda request: None)
    for bad in ['../track.mp3', str(path), 'missing.mp3']:
        with pytest.raises(HTTPException) as exc:
            api.library_audio_details(request, bad)
        assert exc.value.status_code == 404


@pytest.mark.parametrize(('suffix', 'args', 'codec', 'depth', 'lossless'), [
    ('flac', ['-c:a', 'flac', '-sample_fmt', 's32'], 'flac', 24, True),
    ('m4a', ['-c:a', 'alac', '-sample_fmt', 's32p'], 'alac', 24, True),
    ('wav', ['-c:a', 'pcm_s16le'], 'pcm', 16, True),
    ('m4a', ['-c:a', 'aac'], 'aac', None, False),
    ('ogg', ['-c:a', 'libvorbis'], 'vorbis', None, False),
    ('opus', ['-c:a', 'libopus'], 'opus', None, False),
])
def test_codec_facts_and_bit_depth_only_for_lossless(tmp_path, suffix, args, codec, depth, lossless):
    details = audio_details.read_audio_details(generate(tmp_path / f'file.{suffix}', *args))
    assert details['codec'] == codec
    assert details['channels'] == 2
    assert details['sample_rate'] > 0
    assert details['lossless'] is lossless
    assert details.get('bit_depth') == depth
    assert 'channel_mode' not in details


def test_unknown_or_corrupt_audio_does_not_invent_facts(tmp_path):
    path = tmp_path / 'bad.mp3'
    path.write_bytes(b'not audio')
    assert audio_details.read_audio_details(path) == {}
    assert audio_details.read_audio_details(tmp_path / 'missing.mp3') == {}


@pytest.mark.parametrize(('args', 'expected', 'channels'), [
    (['-joint_stereo', '0'], 'Stereo', 2),
    (['-ac', '1'], 'Mono', 1),
])
def test_mp3_other_real_modes(tmp_path, args, expected, channels):
    details = audio_details.read_audio_details(generate(tmp_path / 'file.mp3', '-c:a', 'libmp3lame', *args))
    assert details['channel_mode'] == expected
    assert details['channels'] == channels


def generate(path, *args):
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                    'anullsrc=r=44100:cl=stereo', '-t', '1', *args, str(path)], check=True)
    return path


def test_mp3_reports_real_bitrate_sample_rate_channels_and_joint_stereo(tmp_path):
    path = generate(tmp_path / 'joint.mp3', '-c:a', 'libmp3lame', '-b:a', '192k', '-joint_stereo', '1')
    before = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
    details = audio_details.read_audio_details(path)
    assert details['codec'] == 'mp3'
    assert abs(details['bitrate'] - 192000) < 100
    assert details['sample_rate'] == 44100
    assert details['channels'] == 2
    assert details['channel_mode'] == 'Joint stereo'
    assert details['lossless'] is False
    assert 'bit_depth' not in details
    assert before == (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
