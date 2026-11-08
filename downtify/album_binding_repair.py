"""Explicit admin-approved source aliases; never edits, retags or moves audio."""
import hashlib
import json
import math
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .resource_identity import exact_name_key as key
from .library_catalog import resolve_library_file


def repair_bindings(ctx, index, entries, tracks, files, dry_run=True):
    if not isinstance(dry_run, bool) or not isinstance(files, list) or not 1 <= len(files) <= 100:
        raise ValueError('Invalid repair manifest')
    if len(files) > len(tracks):
        raise ValueError('More files than selected release tracks')
    visible = {r['file']: r for r in entries}
    selected = []
    seen = set()
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get('file'), str) or not re.fullmatch(r'[a-f0-9]{64}', str(item.get('sha256', ''))):
            raise ValueError('Invalid file/hash')
        name = item['file']
        if name in seen or name not in visible:
            raise ValueError('Duplicate or unavailable file')
        seen.add(name)
        row = visible[name]
        path = resolve_library_file(name, ctx)
        if path is None:
            raise ValueError('Unavailable file')
        before = path.stat()
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('File hash changed')
        credits = row.get('artists') or str(row.get('artist') or '').split(';')

        def matches(song):
            try:
                durations = float(row.get('duration') or 0), float(song.get('duration') or 0)
                return (key(row.get('title')) == key(song.get('name'))
                    and key(row.get('album')) == key(song.get('album_name'))
                    and key(row.get('album_artist')) == key(song.get('album_artist'))
                    and key(', '.join(credits)) == key(', '.join(song.get('artists') or []))
                    and int(row.get('track_number') or 0) == int(song.get('track_number') or 0) > 0
                    and int(row.get('disc_number') or 1) == int(song.get('disc_number') or 1)
                    and str(row.get('year') or '') == str(song.get('release_date') or '')[:4]
                    and all(math.isfinite(d) and d > 0 for d in durations)
                    and abs(durations[0] - durations[1]) <= 5)
            except (TypeError, ValueError):
                return False
        candidates = [song for song in tracks if matches(song)]
        if len(candidates) != 1 or not re.fullmatch(r'[A-Za-z0-9]{22}', str(candidates[0].get('song_id', ''))):
            raise ValueError('No unambiguous complete track fingerprint: ' + name)
        after = path.stat()
        stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if stamp(before) != stamp(after):
            raise ValueError('File changed during validation')
        selected.append((candidates[0]['song_id'], name, str(path.resolve()), after.st_size, after.st_mtime_ns))
    if len({r[0] for r in selected}) != len(files):
        raise ValueError('Each selected source track requires exactly one file')
    report = {'candidates': len(selected), 'applied': 0, 'dry_run': dry_run}
    if dry_run:
        return report
    directory = Path(index._path).parent / 'source-binding-repair-backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory.mkdir(parents=True, mode=0o700)
    backup = directory / 'before.sqlite3'
    with index._connect() as source, sqlite3.connect(backup) as dest:
        source.backup(dest)
    os.chmod(backup, 0o600)
    plan = directory / 'plan.json'
    plan.write_text(json.dumps({'files': files, 'bindings': selected}, indent=2))
    os.chmod(plan, 0o600)
    with index._connect() as conn:
        conn.executemany('INSERT OR REPLACE INTO library_source_copies (spotify_track_id,filename,full_path,size,mtime_ns) VALUES (?,?,?,?,?)', selected)
    return {**report, 'applied': len(selected), 'backup': str(backup)}
