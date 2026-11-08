"""Bounded native-input audit using the production downloader's exact options."""

import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

import yt_dlp


def audit_source(downloader, video_id, directory):
    if not isinstance(video_id, str) or not re.fullmatch(
        r'[A-Za-z0-9_-]{11}', video_id
    ):
        raise ValueError('Invalid YouTube video ID')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='raw-', dir=directory) as work:
        template = str(Path(work) / 'source.%(ext)s')
        opts, cookies = downloader._ydl_options(template, lambda data: None)
        # Same source format selection, extractor clients and authentication.
        # Unlike fetch_audio, NEVER attach _ExtractAudioPP or any postprocessor.
        opts['match_filter'] = lambda item, **kwargs: (
            'Audit is limited to ten-minute tracks'
            if float(item.get('duration') or 0) > 600
            else None
        )
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f'https://music.youtube.com/watch?v={video_id}', download=True
            )
            path = Path(ydl.prepare_filename(info))
        if not path.is_file() or not path.resolve().is_relative_to(
            Path(work).resolve()
        ):
            raise ValueError('Native source file unavailable')
        probe = subprocess.run(
            [
                'ffprobe',
                '-v',
                'error',
                '-select_streams',
                'a:0',
                '-show_entries',
                'stream=codec_name,sample_rate,channels,bit_rate,duration:format=format_name,duration,size,bit_rate',
                '-of',
                'json',
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        facts = json.loads(probe.stdout)
        streams = facts.get('streams', [])
        if not streams:
            raise ValueError('No audio stream')
        stream = streams[0]
        packets = subprocess.run(
            [
                'ffprobe',
                '-v',
                'error',
                '-select_streams',
                'a:0',
                '-show_entries',
                'packet=size,duration_time',
                '-of',
                'json',
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        rows = json.loads(packets.stdout).get('packets', [])
        valid = [
            (int(p['size']), float(p['duration_time']))
            for p in rows
            if p.get('size') and p.get('duration_time')
        ]
        seconds = sum(d for _, d in valid)
        if not valid or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('No measured packet duration')
        return {
            'video_id': video_id,
            'format_id': info.get('format_id'),
            'container_extension': path.suffix[1:],
            'codec': stream['codec_name'],
            'extractor_codec': info.get('acodec'),
            'sample_rate_hz': int(stream.get('sample_rate') or 0),
            'channels': int(stream.get('channels') or 0),
            'measured_audio_kbps': round(
                sum(size for size, _ in valid) * 8 / seconds / 1000, 3
            ),
            'extractor_reported_kbps': info.get('abr'),
            'duration_seconds': round(seconds, 3),
            'file_bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'cookies_used': cookies,
            'format_selector': opts.get('format'),
            'converted': False,
            'lossless': stream['codec_name'] in {'flac', 'alac', 'wavpack'},
            'measurement': 'sum of encoded audio packet bytes / sum of audio packet durations',
        }
