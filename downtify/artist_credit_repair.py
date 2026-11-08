"""Explicit admin artist-credit repairs, without changing audio or other tags."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

from mutagen.id3 import ID3


def prepare(data: bytes, before: list[str], after: list[str]) -> bytes:
    if not before or not after or any(not isinstance(s, str) or not s.strip() for s in before + after):
        raise ValueError('Nonempty artist lists required')
    if ', '.join(before) != ', '.join(after):
        raise ValueError('Repair must preserve the full display credit')
    tags = ID3(io.BytesIO(data))
    if tags.version[1] != 4:
        raise ValueError('Only ID3v2.4 is supported')
    frame = tags.get('TXXX:ARTISTS')
    if frame is None or list(frame.text) != before:
        raise ValueError('Artist tags changed since planning')
    original_size = tags.size
    other = {k: v.pprint() for k, v in tags.items() if k != 'TXXX:ARTISTS'}
    frame.text = after
    buf = io.BytesIO(data)
    tags.save(buf, v2_version=4, padding=lambda info: max(0, info.padding))
    result = buf.getvalue()
    check = ID3(io.BytesIO(result))
    if len(result) != len(data) or check.size != original_size or result[original_size:] != data[original_size:]:
        raise ValueError('Repair would change file size or audio')
    if {k: v.pprint() for k, v in check.items() if k != 'TXXX:ARTISTS'} != other:
        raise ValueError('Unrelated tags changed')
    return result


def apply_file(path: Path, before: list[str], after: list[str], sha: str, backup: Path) -> None:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise ValueError('File changed since planning')
    result = prepare(data, before, after)
    st = path.stat()
    backup.parent.mkdir(parents=True, exist_ok=True)
    with backup.open('xb') as out:
        out.write(data)
    os.chmod(backup, 0o600)
    # App account owns these folders. A short temporary name avoids NAME_MAX.
    stage = path.with_name('.artist-credit-repair-' + sha[:16])
    try:
        with stage.open('xb') as out:
            out.write(result)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(stage, st.st_mode)
        os.chown(stage, st.st_uid, st.st_gid)
        os.utime(stage, ns=(st.st_atime_ns, st.st_mtime_ns))
        if path.read_bytes() != data:
            raise ValueError('Concurrent file change')
        os.replace(stage, path)
        if path.read_bytes() != result:
            raise ValueError('Read-back verification failed')
    finally:
        if stage.exists():
            stage.unlink()


def source_credits(rows: list[dict], cache) -> list[dict]:
    """Use exact cached Spotify track entities; no network during rendering."""
    if cache is None:
        return rows
    result = []
    for original_row in rows:
        row = original_row
        if row.get('artists_structured') is True:
            result.append(row)
            continue
        cached = cache.get_cached_track(row.get('song_id', ''))
        names = cached.get('artists') if cached else None
        old = row.get('artists') or []
        if (names and cached.get('artists_structured') is not False
                and all(isinstance(n, str) and n.strip() for n in names)
                and cached.get('name') == row.get('name')
                and ', '.join(names) == ', '.join(old)):
            identity = {key: cached[key] for key in ('artist_ids', 'artist_entities') if cached.get(key)}
            row = {**row, **identity, 'artists': list(names), 'artist': ', '.join(names)}
        result.append(row)
    return result
