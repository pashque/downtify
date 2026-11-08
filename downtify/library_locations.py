"""Read-only physical availability; never calls a source provider."""
import math
import re
from pathlib import PurePosixPath

from . import recording_equivalence
from .library_catalog import album_artist_of, resolve_library_file
from .resource_identity import exact_name_key
from .track_index import normalize_spotify_track_id


def _row_song(row):
    return dict(name=row.get('title'), artists=row.get('artists') if isinstance(row.get('artists'), list) else str(row.get('artist') or '').split(';'),
                album_artist=row.get('album_artist') or album_artist_of(row), album_name=row.get('album'),
                release_date=str(row.get('year') or ''), track_number=row.get('track_number'),
                downtify_destination='album')


def _fingerprint(song, local=False):
    """Complete exact release/credit/position evidence, never a loose song key."""
    text = exact_name_key

    title = text(song.get('title') if local else song.get('name') or song.get('title'))
    artists = song.get('artists')
    if local and not isinstance(artists, list):
        artists = str(song.get('artist') or '').split(';')
    if not isinstance(artists, list):
        return None
    credits = tuple(sorted({text(a) for a in artists if text(a)}))
    artist = text(song.get('album_artist'))
    album = text(song.get('album') if local else song.get('album_name'))
    year = str(song.get('year') or '') if local else str(song.get('release_date') or song.get('year') or '')[:4]
    try:
        number = int(song.get('track_number') or 0)
        disc = int(song.get('disc_number') or 1)
        duration = float(song.get('duration') or 0)
    except (ValueError, TypeError):
        return None
    if not (title and credits and artist and album and re.fullmatch(r'\d{4}', year)
            and number > 0 and disc > 0 and math.isfinite(duration) and duration > 0):
        return None
    return (title, credits, artist, album, year, number, disc), duration


def track_locations(ctx, songs, entries, downloader=None, track_index=None, playlists=()):
    visible = {row['file']: row for row in entries
               if resolve_library_file(row['file'], ctx) is not None}
    identities = track_index.identities_for_files(set(visible)) if track_index is not None else {}
    by_id = {}
    for filename, ids in identities.items():
        for tid in ids:
            by_id.setdefault(tid, set()).add(filename)
    fingerprints = {}
    for filename, row in visible.items():
        fp = _fingerprint(row, local=True)
        if fp:
            fingerprints.setdefault(fp[0], []).append((filename, fp[1]))
    results = []
    for song in songs:
        key = str(song.get('song_id') or song.get('url') or song.get('file') or '')
        names = {song['file']} if song.get('file') in visible else set()
        ids = identities.get(song.get('file'), set()) if song.get('file') else {normalize_spotify_track_id(song)}
        for tid in ids:
            for equivalent in recording_equivalence.registry.equivalent_tracks(tid):
                names.update(by_id.get(equivalent, ()))
        # Once an exact source-bound file is established, its measured local
        # fingerprint may join another physical copy without trusting a client
        # alias or relaxing the source/audio duration guard.
        for filename in list(names):
            anchor_fp = _fingerprint(visible[filename], local=True)
            if anchor_fp:
                for other, duration in fingerprints.get(anchor_fp[0], ()):
                    known = identities.get(other, set())
                    proven = {value for tid in ids for value in recording_equivalence.registry.equivalent_tracks(tid)}
                    if abs(duration - anchor_fp[1]) <= 5 and (not known or known.intersection(proven)):
                        names.add(other)
        anchor = visible.get(song.get('file')) if song.get('file') else song
        fp = _fingerprint(anchor, local=bool(song.get('file'))) if anchor else None
        if fp:
            for filename, duration in fingerprints.get(fp[0], ()):
                known = identities.get(filename, set())
                if abs(duration - fp[1]) <= 5 and (not known or not any(ids) or known.intersection(ids)):
                    names.add(filename)
        rows = [visible[name] for name in sorted(names) if name in visible]
        albums = set()
        album_formats = set()
        if downloader is not None:
            for row in rows:
                target = _row_song(row)
                if not target['album_artist'] or not target['album_name']:
                    continue
                parent = PurePosixPath(downloader.expected_stem_for(target)).parent
                if parent != PurePosixPath('.') and PurePosixPath(row['file']).parent == parent:
                    albums.add((album_artist_of(row), target['album_name']))
                    album_formats.add(PurePosixPath(row['file']).suffix[1:].lower())
        member_names = {p['name'] for p in playlists
                        if p.get('name') and names.intersection(p.get('files') or []).intersection(visible)}
        results.append(dict(key=key, downloaded=bool(rows),
                            formats=sorted({PurePosixPath(row['file']).suffix[1:].lower() for row in rows}),
                            album_formats=sorted(album_formats),
                            albums=[dict(artist=a, title=t) for a, t in sorted(albums)],
                            playlists=[dict(name=n) for n in sorted(member_names)]))
    return results
