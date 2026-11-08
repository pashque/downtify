"""Bounded process-local proof of complete equivalent source editions.

No library bindings, metadata or audio are changed. Availability readers use
only established proofs; provider discovery is kept outside rendering.
"""
import math
import re
import threading
import time
import unicodedata
from collections import OrderedDict
from typing import Any

from . import spotify


def _norm(value: Any) -> str:
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).casefold().split())


def _sequence(rows: list[dict[str, Any]]) -> tuple | None:
    if not isinstance(rows, list) or not rows or len(rows) > 500:
        return None
    result, ids = [], set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            return None
        tid, artists = str(row.get('song_id') or ''), row.get('artists')
        try:
            duration = float(row.get('duration') or 0)
            disc, number = int(row.get('disc_number') or 1), int(row.get('track_number') or 0)
            total = int(row.get('album_track_total') or 0)
        except (ValueError, TypeError):
            return None
        title, album, credit = _norm(row.get('name')), _norm(row.get('album_name')), _norm(row.get('album_artist'))
        names = tuple(_norm(a) for a in artists) if isinstance(artists, list) else ()
        if (not re.fullmatch(r'[A-Za-z0-9]{22}', tid) or tid in ids
                or not title or not album or not credit or not names or not all(names)
                or row.get('artists_structured') is False
                or not math.isfinite(duration) or duration <= 0 or disc != 1
                or number != index + 1 or total != len(rows)
                or not isinstance(row.get('explicit'), bool)):
            return None
        ids.add(tid)
        result.append((title, names, credit, album, duration, row['explicit'], disc, number))
    return tuple(result)


class RecordingEquivalenceRegistry:
    def __init__(self, max_albums: int = 128) -> None:
        self._albums = OrderedDict()
        self._lock = threading.RLock()
        self._max = max_albums

    def add(self, album_id: str, rows: list[dict[str, Any]]) -> bool:
        fingerprint = _sequence(rows)
        with self._lock:
            self._albums.pop(album_id, None)
            if not re.fullmatch(r'[A-Za-z0-9]{22}', str(album_id)) or fingerprint is None:
                return False
            self._albums[album_id] = (fingerprint, tuple(row['song_id'] for row in rows), time.monotonic())
            while len(self._albums) > self._max:
                self._albums.popitem(last=False)
        return True

    def equivalent_tracks(self, track_id: str) -> set[str]:
        with self._lock:
            albums = [item for item in self._albums.values() if time.monotonic() - item[2] < 3600]
            result = {track_id} if track_id else set()
            for fingerprint, ids, _ in albums:
                if track_id not in ids:
                    continue
                position = ids.index(track_id)
                result.update(other_ids[position] for other, other_ids, _ in albums if other == fingerprint)
            return result

    def knows_track(self, track_id: str) -> bool:
        with self._lock:
            return any(track_id in item[1] and time.monotonic() - item[2] < 3600
                       for item in self._albums.values())


registry = RecordingEquivalenceRegistry()


def warm_source_equivalence(result: dict[str, Any], entries: list[dict[str, Any]], index: Any) -> None:
    """Bounded source-stage lookup of an owned edition, never an availability call."""
    tracks = result.get('tracks') or []
    if result.get('status') != 'resolved' or not tracks or index is None:
        return
    selected = result.get('edition')
    if not selected or not registry.add(selected, tracks):
        return
    first = tracks[0]
    visible = [r for r in entries if _norm(r.get('album')) == _norm(first.get('album_name'))
               and _norm(r.get('album_artist')) == _norm(first.get('album_artist'))]
    identities = index.identities_for_files({r['file'] for r in visible})
    ids = sorted({tid for values in identities.values() for tid in values})
    # One original edition is enough to prove equivalence; no per-row fetching.
    missing = [tid for tid in ids if not registry.knows_track(tid)]
    if not missing:
        return
    try:
        album_id, _ = spotify._album_ref_from_open_track_page(missing[0])
        if re.fullmatch(r'[A-Za-z0-9]{22}', str(album_id)):
            registry.add(album_id, spotify.album_tracks_from_id(album_id))
    except Exception:
        pass  # Missing source evidence must never create equivalent identities.
