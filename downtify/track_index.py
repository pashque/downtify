"""Global Spotify track id → library file mapping for cross-playlist deduplication."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .download_destination import (
    managed_destination,
    verified_destination_copy,
)
from .library_cache_keys import file_content_key
from .library_paths import (
    locate_library_file,
    slskd_dir_from_downloader,
)
from .resource_identity import exact_name_key
from .sqlite_utils import connect_sqlite

_SPOTIFY_TRACK_ID = re.compile(r'^[a-zA-Z0-9]{22}$')
_SPOTIFY_TRACK_URL = re.compile(
    r'(?:open\.spotify\.com|spotify\.com)/track/([a-zA-Z0-9]{22})'
)


def normalize_spotify_track_id(song: dict[str, Any]) -> Optional[str]:
    """Return a 22-char Spotify track id when ``song`` has one, else ``None``."""

    raw = str(song.get('song_id') or '').strip()
    if not raw:
        url = str(song.get('url') or '').strip()
        if url:
            raw = url
        else:
            return None
    if raw.startswith('spotify:track:'):
        raw = raw.rsplit(':', 1)[-1]
    else:
        match = _SPOTIFY_TRACK_URL.search(raw)
        if match:
            raw = match.group(1)
    if _SPOTIFY_TRACK_ID.fullmatch(raw):
        return raw
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrackIndex:
    """SQLite index: one canonical relative path per Spotify track id."""

    def __init__(self, db_path: Path) -> None:
        self._path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self._path, row_factory=True)

    def album_preference(self, user_id: int, artist: str, title: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute('SELECT edition FROM library_album_preferences WHERE user_id=? AND artist=? AND title=?',
                               (user_id, exact_name_key(artist), exact_name_key(title))).fetchone()
        return row['edition'] if row else None

    def set_album_preference(self, user_id: int, artist: str, title: str, edition: str) -> None:
        if not _SPOTIFY_TRACK_ID.fullmatch(edition):
            raise ValueError('Invalid Spotify album ID')
        with self._connect() as conn:
            conn.execute('INSERT OR REPLACE INTO library_album_preferences (user_id,artist,title,edition) VALUES (?,?,?,?)',
                         (user_id, exact_name_key(artist), exact_name_key(title), edition))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS library_album_preferences (user_id INTEGER NOT NULL, artist TEXT NOT NULL, title TEXT NOT NULL, edition TEXT NOT NULL, PRIMARY KEY(user_id,artist,title))')
            conn.execute('''CREATE TABLE IF NOT EXISTS library_source_copies (
                spotify_track_id TEXT NOT NULL, filename TEXT NOT NULL,
                full_path TEXT NOT NULL, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
                PRIMARY KEY (spotify_track_id, filename))''')
            conn.execute("""
                CREATE TABLE IF NOT EXISTS library_tracks (
                    spotify_track_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_key TEXT,
                    registered_at TEXT NOT NULL
                )
            """)
            try:
                conn.execute(
                    'ALTER TABLE library_tracks ADD COLUMN content_key TEXT'
                )
            except Exception:
                pass
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_library_tracks_content_key
                ON library_tracks (content_key)
                WHERE content_key IS NOT NULL
            """)

    def register_source_copy(self, song: dict[str, Any], filename: str, full_path: Path) -> None:
        """Internal only: bind a fingerprint-verified local copy to a source ID.

        Separate from canonical download provenance: playlist and album copies
        coexist, and changed/deleted files immediately lose the recovered claim.
        """
        tid = normalize_spotify_track_id(song)
        path = Path(full_path)
        if not tid or not filename or not path.is_file():
            return
        stat = path.stat()
        with self._connect() as conn:
            conn.execute('''INSERT OR REPLACE INTO library_source_copies
                            (spotify_track_id, filename, full_path, size, mtime_ns)
                            VALUES (?, ?, ?, ?, ?)''',
                         (tid, filename, str(path.resolve()), stat.st_size, stat.st_mtime_ns))

    def source_copies_for_song(self, song: dict[str, Any]) -> list[str]:
        tid = normalize_spotify_track_id(song)
        if not tid:
            return []
        with self._connect() as conn:
            rows = conn.execute('SELECT * FROM library_source_copies WHERE spotify_track_id = ? ORDER BY filename', (tid,)).fetchall()
        found = []
        for row in rows:
            try:
                path = Path(row['full_path'])
                stat = path.stat()
                if path.is_file() and (stat.st_size, stat.st_mtime_ns) == (row['size'], row['mtime_ns']):
                    found.append(str(row['filename']))
            except OSError:
                pass
        return found

    def validated_source_copy_ids(self, filename: str) -> set[str]:
        """Return IDs from unchanged, stat-validated source-copy rows only."""
        with self._connect() as conn:
            rows = conn.execute('SELECT * FROM library_source_copies WHERE filename=?', (filename,)).fetchall()
        result: set[str] = set()
        for row in rows:
            try:
                path = Path(row['full_path'])
                stat = path.stat()
                if path.is_file() and (stat.st_size, stat.st_mtime_ns) == (row['size'], row['mtime_ns']):
                    result.add(str(row['spotify_track_id']))
            except OSError:
                pass
        return result

    def validated_source_copy_ids_for_path(self, full_path: Path) -> set[str]:
        """Return stat-valid identities attached to this resolved physical path."""
        path = Path(full_path)
        try:
            resolved = str(path.resolve(strict=True))
            stat = path.stat()
        except OSError:
            return set()
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT spotify_track_id, size, mtime_ns FROM library_source_copies WHERE full_path=?',
                (resolved,),
            ).fetchall()
        if not path.is_file():
            return set()
        return {str(row['spotify_track_id']) for row in rows
                if (stat.st_size, stat.st_mtime_ns) == (row['size'], row['mtime_ns'])}

    def validate_source_identity(self, song: dict[str, Any], filename: str,
                                 full_path: Path) -> None:
        """Reject conflicting provenance for this unchanged physical file."""
        requested = normalize_spotify_track_id(song)
        if not requested:
            return
        path = Path(full_path)
        known = self.validated_source_copy_ids_for_path(path)
        if known and requested not in known:
            raise RuntimeError(f'Existing file {filename!r} is indexed to a different source track')

    def identities_for_files(self, filenames: set[str]) -> dict[str, set[str]]:
        """Batch reverse provenance, including stat-validated recovered copies.

        Only caller-selected visible files are returned. No source requests or
        writes are performed; changed recovered files immediately lose identity.
        """
        found: dict[str, set[str]] = {}
        with self._connect() as conn:
            canonical = conn.execute('SELECT spotify_track_id, filename FROM library_tracks').fetchall()
            recovered = conn.execute('SELECT * FROM library_source_copies').fetchall()
        for row in canonical:
            if row['filename'] in filenames:
                found.setdefault(row['filename'], set()).add(row['spotify_track_id'])
        for row in recovered:
            if row['filename'] not in filenames:
                continue
            try:
                path = Path(row['full_path'])
                stat = path.stat()
                if path.is_file() and (stat.st_size, stat.st_mtime_ns) == (row['size'], row['mtime_ns']):
                    found.setdefault(row['filename'], set()).add(row['spotify_track_id'])
            except OSError:
                pass
        return found

    def lookup(self, spotify_track_id: str) -> Optional[str]:
        tid = str(spotify_track_id or '').strip()
        if not _SPOTIFY_TRACK_ID.fullmatch(tid):
            return None
        with self._connect() as conn:
            row = conn.execute(
                'SELECT filename FROM library_tracks WHERE spotify_track_id = ?',
                (tid,),
            ).fetchone()
        if row is None:
            return None
        return str(row['filename'])

    def lookup_song(self, song: dict[str, Any]) -> Optional[str]:
        tid = normalize_spotify_track_id(song)
        if not tid:
            return None
        return self.lookup(tid)

    def spotify_id_for_filename(self, filename: str) -> Optional[str]:
        """The Spotify track a library file was downloaded for, if known.

        The reverse of :meth:`lookup`: a library upgrade starts from a
        file on disk and needs the track it came from to re-fetch its
        metadata and cover.
        """

        name = str(filename or '').strip().replace('\\', '/')
        if not name:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """SELECT spotify_track_id FROM library_tracks
                   WHERE filename = ? LIMIT 1""",
                (name,),
            ).fetchone()
        return str(row['spotify_track_id']) if row is not None else None

    def register(
        self,
        spotify_track_id: str,
        filename: str,
        *,
        full_path: Optional[Path] = None,
    ) -> None:
        tid = str(spotify_track_id or '').strip()
        name = str(filename or '').strip().replace('\\', '/')
        if not _SPOTIFY_TRACK_ID.fullmatch(tid) or not name:
            return
        ck: Optional[str] = None
        if full_path is not None:
            ck = file_content_key(full_path)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO library_tracks
                   (spotify_track_id, filename, content_key, registered_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(spotify_track_id) DO UPDATE SET
                   filename=excluded.filename,
                   content_key=COALESCE(excluded.content_key, library_tracks.content_key),
                   registered_at=excluded.registered_at""",
                (tid, name, ck, _now_iso()),
            )

    def register_song(
        self,
        song: dict[str, Any],
        filename: str,
        *,
        full_path: Optional[Path] = None,
    ) -> None:
        tid = normalize_spotify_track_id(song)
        if tid:
            self.register(tid, filename, full_path=full_path)

    def update_filename(
        self,
        spotify_track_id: str,
        filename: str,
        *,
        content_key: Optional[str] = None,
    ) -> bool:
        tid = str(spotify_track_id or '').strip()
        name = str(filename or '').strip().replace('\\', '/')
        if not _SPOTIFY_TRACK_ID.fullmatch(tid) or not name:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE library_tracks SET filename = ?,
                   content_key = COALESCE(?, content_key)
                   WHERE spotify_track_id = ? AND filename != ?""",
                (name, content_key, tid, name),
            )
            return cur.rowcount > 0

    def all_rows(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT spotify_track_id, filename, content_key
                   FROM library_tracks"""
            ).fetchall()
        return [
            {
                'spotify_track_id': str(row['spotify_track_id']),
                'filename': str(row['filename']).replace('\\', '/'),
                'content_key': row['content_key'],
            }
            for row in rows
        ]

    def set_content_key(self, spotify_track_id: str, content_key: str) -> bool:
        tid = str(spotify_track_id or '').strip()
        ck = str(content_key or '').strip()
        if not _SPOTIFY_TRACK_ID.fullmatch(tid) or not ck:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE library_tracks SET content_key = ?
                   WHERE spotify_track_id = ? AND COALESCE(content_key, '') = ''""",
                (ck, tid),
            )
            return cur.rowcount > 0

    def remove_by_filename(self, filename: str) -> bool:
        name = str(filename or '').strip().replace('\\', '/')
        if not name:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                'DELETE FROM library_tracks WHERE filename = ?', (name,)
            )
            return cur.rowcount > 0

    def list_filenames(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT filename FROM library_tracks ORDER BY filename'
            ).fetchall()
        return [
            str(row['filename']).replace('\\', '/')
            for row in rows
            if row['filename']
        ]

    def filenames_by_spotify_id(self) -> dict[str, str]:
        """Every ``{spotify_track_id: filename}``, in one query - for
        checking many tracks at once instead of one :meth:`lookup` each."""

        with self._connect() as conn:
            rows = conn.execute(
                'SELECT spotify_track_id, filename FROM library_tracks'
            ).fetchall()
        return {
            str(row['spotify_track_id']): str(row['filename']).replace(
                '\\', '/'
            )
            for row in rows
            if row['spotify_track_id'] and row['filename']
        }

    def forget(self, spotify_track_id: str) -> None:
        tid = str(spotify_track_id or '').strip()
        if not _SPOTIFY_TRACK_ID.fullmatch(tid):
            return
        with self._connect() as conn:
            conn.execute(
                'DELETE FROM library_tracks WHERE spotify_track_id = ?',
                (tid,),
            )

    def backfill_from_monitor_db(self, monitor_db_path: Path) -> int:
        """Import rows from monitored-playlist history (best-effort, idempotent)."""

        path = Path(monitor_db_path)
        if not path.is_file():
            return 0
        imported = 0
        with sqlite3.connect(str(path)) as src:
            try:
                rows = src.execute(
                    """SELECT track_spotify_id, filename
                       FROM downloaded_tracks
                       WHERE filename IS NOT NULL AND filename != ''"""
                ).fetchall()
            except sqlite3.Error:
                return 0
        for track_id, filename in rows:
            tid = str(track_id or '').strip()
            if not _SPOTIFY_TRACK_ID.fullmatch(tid):
                continue
            before = self.lookup(tid)
            self.register(tid, str(filename))
            if before != str(filename):
                imported += 1
        return imported


def resolve_existing_download(
    downloader: Any,
    song: dict[str, Any],
    *,
    subdir: Optional[str] = None,
    track_index: Optional[TrackIndex] = None,
) -> Optional[tuple[str, str]]:
    """Return ``(relative_filename, skip_message)`` when a file already exists."""

    download_dir = Path(downloader.download_dir)
    slskd_dir = slskd_dir_from_downloader(downloader)

    def has_source_conflict(local: str, full_path: Path, requested_id: Optional[str]) -> bool:
        if track_index is None:
            return False
        if requested_id is None:
            return bool(track_index.validated_source_copy_ids_for_path(full_path))
        try:
            track_index.validate_source_identity({'song_id': requested_id}, local, full_path)
        except RuntimeError:
            return True
        return False

    def validate_existing(local: str, full_path: Path) -> None:
        validator = getattr(downloader, '_validate_existing_copy', None)
        if not callable(validator):
            raise RuntimeError('existing file cannot be accepted without a validator')
        # Validate the resolved physical file, including authorized slskd paths.
        physical = full_path.resolve(strict=True)
        try:
            physical.relative_to(download_dir.resolve(strict=True))
            validator(song, local)
        except ValueError:
            slskd_root = slskd_dir.resolve(strict=True) if slskd_dir and slskd_dir.exists() else None
            if slskd_root is None:
                raise RuntimeError('existing file is outside authorized roots')
            try:
                physical.relative_to(slskd_root)
            except ValueError as exc:
                raise RuntimeError('existing file is outside authorized roots') from exc
            validator(song, str(physical))

    def has_trustworthy_source_evidence(full_path: Path, requested_id: Optional[str]) -> bool:
        if track_index is None or requested_id is None:
            return False
        return requested_id in track_index.validated_source_copy_ids_for_path(full_path)

    if managed_destination(downloader) or song.get('downtify_destination') == 'album':
        local = (downloader.existing_filename_for(song, subdir=subdir)
                 or verified_destination_copy(downloader, song, subdir, track_index))
        if local:
            full = locate_library_file(local, download_dir, slskd_dir)
            if full is not None:
                if has_source_conflict(local, full, normalize_spotify_track_id(song)):
                    return None
                validate_existing(local, full)
                if has_trustworthy_source_evidence(full, normalize_spotify_track_id(song)):
                    assert track_index is not None
                    track_index.register_song(song, local, full_path=full)
                return local, 'Already at destination'
        # A valid indexed copy elsewhere must remain indexed, but must not
        # suppress a missing destination in an album or a separate playlist.
        return None

    tid = normalize_spotify_track_id(song)
    if track_index is not None:
        if tid:
            canonical = track_index.lookup(tid)
            if canonical:
                full = locate_library_file(canonical, download_dir, slskd_dir)
                if full is not None:
                    if has_source_conflict(canonical, full, tid):
                        return None
                    validate_existing(canonical, full)
                    return canonical, 'Already in library'
                track_index.forget(tid)

    local = downloader.existing_filename_for(song, subdir=subdir)
    if local:
        full = locate_library_file(local, download_dir, slskd_dir)
        if full is not None:
            if has_source_conflict(local, full, tid):
                return None
            validate_existing(local, full)
            if has_trustworthy_source_evidence(full, tid):
                assert track_index is not None
                track_index.register_song(song, local, full_path=full)
            return local, 'Already on disk'

    return None
