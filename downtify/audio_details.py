"""On-demand, read-only audio facts; never invoked while listing the library."""
import json
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.mp3 import MP3, HeaderNotFoundError, MPEGFrame

from .library_metadata import audio_format

_MODES = ('Stereo', 'Joint stereo', 'Dual channel', 'Mono')


def _mp3_modes(path: Path, offset: int) -> str:
    """Read actual frame headers, excluding Xing/Info/VBRI metadata frames.

    A file can switch mode between frames; hide mixed/unknown modes rather
    than picking the metadata frame (often Stereo for Joint stereo audio).
    Bounded to 100,000 frames; omit the mode if the scan cannot finish.
    """
    modes = set()
    with path.open('rb') as stream:
        stream.seek(offset)
        for _ in range(100_000):
            start = stream.tell()
            marker = stream.read(8)
            if not marker or marker.startswith((b'TAG', b'APETAGEX', b'ID3')):
                return _MODES[next(iter(modes))] if len(modes) == 1 else ''
            stream.seek(start)
            try:
                frame = MPEGFrame(stream)
            except HeaderNotFoundError:
                return ''
            if frame.sketchy:  # no Xing/Info/VBRI header
                modes.add(frame.mode)
    return ''


def _packet_bitrate(path: Path) -> int:
    """Average encoded audio packet rate, not container/nominal/PCM rate.

    Optional bounded on-demand ffprobe; failure means unavailable, never
    substitute the configured download quality or an encoder target.
    """
    try:
        process = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'a:0',
             '-show_entries', 'packet=size,duration_time', '-of', 'json', str(path)],
            capture_output=True, check=True, timeout=10,
        )
        packets = json.loads(process.stdout).get('packets', [])
        size = duration = 0
        for packet in packets:
            packet_size = int(packet['size'])
            packet_duration = float(packet['duration_time'])
            if packet_size <= 0 or packet_duration <= 0:
                return 0
            size += packet_size
            duration += packet_duration
        return round(size * 8 / duration) if duration > 0 else 0
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return 0


def read_audio_details(path: Path) -> dict[str, Any]:
    """Cache only unchanged files; callers must authorize before calling."""
    try:
        stat = path.stat()
        key = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        result = _read_cached(path, key)
        after = path.stat()
        if key != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            return {}  # file changed during probing: don't show stale facts
        return dict(result)
    except OSError:
        return {}


@lru_cache(maxsize=256)
def _read_cached(path: Path, stat_key: tuple[int, ...]) -> dict[str, Any]:
    """Return only measured/known facts. Bitrate is bits/s, sample rate Hz.

    MP3 mode is Mutagen's parsed MPEG frame-header mode, not a quality
    rating or an inference from the number of channels.
    """
    try:
        audio = MutagenFile(str(path))
    except Exception:
        return {}
    if audio is None:
        return {}
    result = {key: value for key, value in audio_format(audio).items() if value}
    codec = result.get('codec', '')
    if type(audio).__name__ == 'WAVE' and audio.info.audio_format in {1, 3}:
        codec = result['codec'] = 'pcm' if audio.info.audio_format == 1 else 'pcm_float'
    if codec == 'opus':
        # Opus decoding always uses 48 kHz; its header input rate is not
        # the playback rate (RFC 7845 section 5.1).
        result['sample_rate'] = 48000
    if codec in {'mp3', 'aac', 'opus', 'vorbis', 'flac', 'alac', 'pcm', 'pcm_float'}:
        result['lossless'] = codec in {'flac', 'alac', 'pcm', 'pcm_float'}
    if result.get('lossless'):
        depth = getattr(audio.info, 'bits_per_sample', 0)
        if depth > 0:
            result['bit_depth'] = depth
    if codec in {'alac', 'vorbis'}:
        # Mutagen's ALAC bitrate is decoded PCM rate; Vorbis is the nominal
        # encoder rate. Neither is the actual encoded audio bitrate.
        result.pop('bitrate', None)
        measured = _packet_bitrate(path)
        if measured > 0:
            result['bitrate'] = measured
    if isinstance(audio, MP3):
        result['lossless'] = False
        mode = _mp3_modes(path, audio.info.frame_offset)
        if mode:
            result['channel_mode'] = mode
    return result
