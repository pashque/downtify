"""Convert existing MP3 artist tags from "A; B" to "A, B" + ARTISTS list.

Only the TPE1 frame changes (and a TXXX:ARTISTS frame is added); audio,
cover, every other frame, the ID3 version and the file's dates stay. Every
original value is written to a backup JSON before anything is saved, so the
run can be undone with :func:`restore_from_backup`.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from mutagen.id3 import ID3, TPE1, TXXX, ID3NoHeaderError


def _parts(text: str) -> list[str]:
    return [p.strip() for p in str(text).split(';') if p.strip()]


def plan(files: Iterable[tuple[str, Path]]) -> list[dict[str, Any]]:
    """Files whose TPE1 still uses ';' (stored path, full path, before, after)."""
    out = []
    for stored, full in files:
        if full.suffix.casefold() != '.mp3' or not full.is_file():
            continue
        try:
            tags = ID3(str(full))
        except (ID3NoHeaderError, Exception):
            continue
        frame = tags.get('TPE1')
        if frame is None:
            continue
        values = [str(v) for v in frame.text]
        joined = '; '.join(values)
        if ';' not in joined and len(values) < 2:
            continue
        artists = [a for v in values for a in _parts(v)]
        if not artists:
            continue
        out.append({'file': stored, 'path': str(full), 'before': values,
                    'after': ', '.join(artists), 'artists': artists,
                    'version': tags.version[1]})
    return out


def apply(items: list[dict[str, Any]], backup_path: Path,
          on_done: Optional[Callable[[str], None]] = None) -> dict[str, Any]:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup = [{'file': i['file'], 'path': i['path'], 'tpe1': i['before'],
               'artists_frame': None} for i in items]
    for row, item in zip(backup, items):
        try:
            existing = ID3(item['path']).get('TXXX:ARTISTS')
            row['artists_frame'] = list(existing.text) if existing is not None else None
        except Exception:
            pass
    backup_path.write_text(json.dumps({'created': time.time(), 'files': backup},
                                      ensure_ascii=False, indent=1), encoding='utf-8')
    os.chmod(backup_path, 0o600)
    changed, failed = [], []
    for item in items:
        path = item['path']
        if item['version'] != 4:
            # ID3v2.3 re-joins every multi-value frame on save; leave those
            # files untouched rather than risk changing other tags.
            failed.append({'file': item['file'], 'error': f"ID3v2.{item['version']} skipped"})
            continue
        try:
            st = os.stat(path)
            tags = ID3(path)
            tags.delall('TPE1')
            tags.delall('TXXX:ARTISTS')
            tags.add(TPE1(encoding=3, text=item['after']))
            tags.add(TXXX(encoding=3, desc='ARTISTS', text=item['artists']))
            tags.save(path, v2_version=4)
            os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))
            check = ID3(path)
            if str(check['TPE1']) != item['after'] or list(check['TXXX:ARTISTS'].text) != item['artists']:
                raise ValueError('verification failed')
            changed.append(item['file'])
            if on_done:
                on_done(item['file'])
        except Exception as exc:
            failed.append({'file': item['file'], 'error': str(exc)[:200]})
    return {'changed': len(changed), 'failed': failed, 'backup': str(backup_path)}


def restore_from_backup(backup_path: Path) -> dict[str, Any]:
    data = json.loads(Path(backup_path).read_text(encoding='utf-8'))
    restored, failed = 0, []
    for row in data['files']:
        try:
            st = os.stat(row['path'])
            tags = ID3(row['path'])
            tags.delall('TPE1')
            tags.delall('TXXX:ARTISTS')
            tags.add(TPE1(encoding=3, text=row['tpe1']))
            if row.get('artists_frame'):
                tags.add(TXXX(encoding=3, desc='ARTISTS', text=row['artists_frame']))
            tags.save(row['path'], v2_version=tags.version[1] if tags.version[1] in {3, 4} else 4)
            os.utime(row['path'], ns=(st.st_atime_ns, st.st_mtime_ns))
            restored += 1
        except Exception as exc:
            failed.append({'file': row['file'], 'error': str(exc)[:200]})
    return {'restored': restored, 'failed': failed}
