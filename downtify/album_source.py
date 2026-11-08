"""Exact provenance expansion and conservative legacy edition recovery."""
import math
import re
import unicodedata
from pathlib import Path

from mutagen import File
from mutagen.id3 import ID3

from . import spotify


def _exact(value):
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).lower().split())


def _title(value):
    # Credits are checked separately; only punctuation and explicit credit suffixes
    # differ here. Never remove version labels such as Live, Remaster or Remix.
    text = re.sub(r'\s*(?:[(\[](?:feat\.?|ft\.?|with)\s+[^)\]]+[)\]]|-\s*(?:feat\.?|ft\.?)\s+.+)$', '', str(value), flags=re.I)
    return ''.join(c for c in unicodedata.normalize('NFKC', text).casefold() if c.isalnum())


_RELEASE_TYPES = {'album', 'single', 'ep', 'compilation'}


def _release_type(value):
    """Spotify's release type ('ALBUM', 'SINGLE', 'EP', 'COMPILATION') as a
    lower-case label, or '' when it is missing or unknown (never guessed)."""
    kind = str(value or '').strip().casefold()
    return kind if kind in _RELEASE_TYPES else ''


def _album_key(value):
    # Punctuation and version suffixes are identity, not decoration. Search
    # may use broader queries, but must never call a distinct title the same.
    return ' '.join(unicodedata.normalize('NFKC', str(value or '')).lower().split())


def _fingerprint(local, source, positional=True):
    try:
        duration = float(local.get('duration', 0))
        remote_duration = float(source.get('duration', 0))
        return ((not positional or int(local.get('track_number', 0)) == int(source.get('track_number', 0)))
                and int(source.get('track_number', 0)) > 0
                and _title(local.get('title')) == _title(source.get('name'))
                and bool(_title(local.get('title')))
                and {_exact(a) for a in str(local.get('artist') or '').split(';') if a.strip()}
                == {_exact(a) for a in source.get('artists', []) if a.strip()}
                and _exact(local.get('album_artist')) == _exact(source.get('album_artist'))
                and bool(_album_key(local.get('album'))) and _album_key(local.get('album')) == _album_key(source.get('album_name'))
                and str(local.get('year')) == str(source.get('release_date', ''))[:4]
                and math.isfinite(duration) and math.isfinite(remote_duration)
                and duration > 0 and remote_duration > 0 and abs(duration - remote_duration) <= 5)
    except (ValueError, TypeError):
        return False


def enrich_legacy_edition(row, path):
    """Read edition evidence only from a server-resolved visible physical file.

    Never mutate cached metadata or accept cached/client edition hints. Missing
    or malformed tags provide no evidence; ambiguity still fails closed.
    """
    result = {k: v for k, v in row.items() if k not in {'album_track_total', 'album_type'}}
    try:
        if Path(path).suffix.casefold() == '.mp3':
            tags = ID3(path)
            number = str(tags.get('TRCK', ''))
            kind = str(tags.get('TXXX:MusicBrainz Album Type', ''))
            total = ''
        else:
            audio = File(path, easy=True)
            tags = audio.tags if audio is not None else {}
            number = str((tags.get('tracknumber') or [''])[0])
            total = str((tags.get('tracktotal') or tags.get('totaltracks') or [''])[0])
            kind = str((tags.get('musicbrainz_albumtype') or tags.get('releasetype') or [''])[0])
        match = re.fullmatch(r'\s*([0-9]+)/([0-9]+)\s*', number)
        if match and int(match[1]) == int(row['track_number']) and 0 < int(match[1]) <= int(match[2]) <= 500:
            result['album_track_total'] = int(match[2])
        elif re.fullmatch(r'[0-9]+', total) and 0 < int(row['track_number']) <= int(total) <= 500:
            result['album_track_total'] = int(total)
        if kind.strip().casefold() in {'album', 'ep', 'single', 'compilation'}:
            result['album_type'] = kind.strip().upper()
    except Exception:
        pass  # Unreadable tags cannot establish an edition.
    return result


def _recover_legacy(local_tracks, title, edition=None):
    """Strict versions first, then every other version Spotify search finds.

    Versions found by the looser search are offered in the version selector
    too; when no strict version exists they are the only source.
    """
    strict = _strict_versions(local_tracks, title)
    loose = _loose_versions(local_tracks, title, {m['id'] for m in strict},
                            any_name=not strict)
    matches = strict + loose
    if not matches:
        return {'status': 'unavailable', 'tracks': []}
    return _with_editions(_order_editions(matches, local_tracks), edition, local_tracks)


_LOOSE_FETCH_LIMIT = 6
_LOOSE_SECONDS = 10


def _bare_title(title):
    return re.sub(r'\s*(?:-\s*|[(\[]\s*)?\b(?:ep|single|compilation)\s*[)\]]?\s*$', '',
                  str(title or ''), flags=re.I)


def _loose_versions(local_tracks, title, skip=(), any_name=False, seen_types=None):
    """Best-effort versions: every local file appears by title and length.

    Year, album-artist tag and track number may differ. With *any_name* the
    album title may differ as well (credited artist must still overlap), so
    albums Spotify only returns for a track query can be found.
    """
    rows = [r for r in local_tracks if r.get('file')]
    try:
        if not rows or len(rows) > 500 or any(
                not _title(r.get('title')) or not float(r.get('duration') or 0) > 0 for r in rows):
            return []
    except (TypeError, ValueError):
        return []
    names = []
    for r in rows[:1]:
        for value in (r.get('album_artist'), *str(r.get('artist') or '').split(';')):
            if str(value or '').strip() and str(value).strip() not in names:
                names.append(str(value).strip())
    lead = names[0] if names else ''
    queries = []
    for raw_query in (f'{lead} {title}', f'{lead} {_bare_title(title)}', str(title),
                      f"{lead} {rows[0].get('title')}"):
        query = raw_query.strip()
        if query and query not in queries:
            queries.append(query)
    known = {_exact(n) for n in names}
    same, other = {}, {}
    for q in queries:
        try:
            albums = spotify.search(q).get('albums', [])
        except Exception:
            continue
        for a in albums:
            if not (isinstance(a, dict) and re.fullmatch(r'[A-Za-z0-9]{22}', str(a.get('id', '')))):
                continue
            if seen_types is not None and _release_type(a.get('type')):
                seen_types.setdefault(a['id'], _release_type(a.get('type')))
            if a['id'] in skip:
                continue
            # A common title is not evidence for a different artist. Only
            # candidates sharing an intact known credit may be recovered.
            if not lead or _exact(lead) not in {_exact(x) for x in a.get('artists') or []}:
                continue
            if _album_key(a.get('name')) == _album_key(title):
                same.setdefault(a['id'], a)
            elif any_name and known & {_exact(x) for x in a.get('artists') or []}:
                other.setdefault(a['id'], a)
    found = []
    for album_id in [*same, *other][:_LOOSE_FETCH_LIMIT]:
        try:
            tracks = spotify.album_tracks_from_id(album_id)
        except Exception:
            continue
        if not tracks or len(tracks) > 500 or any(
                not re.fullmatch(r'[A-Za-z0-9]{22}', str(t.get('song_id', ''))) for t in tracks):
            continue
        mapping = {}
        for row in rows:
            hits = [t for t in tracks if _title(t.get('name')) == _title(row.get('title'))
                    and abs(float(t.get('duration') or 0) - float(row['duration'])) <= _LOOSE_SECONDS]
            if not hits:
                break
            mapping.setdefault(hits[0]['song_id'], []).append(row['file'])
        else:
            found.append(dict(id=album_id, tracks=tracks, local_matches=mapping,
                              url=f'https://open.spotify.com/album/{album_id}',
                              release_type=_release_type((same.get(album_id) or other.get(album_id) or {}).get('type'))))
    return found


def _strict_versions(local_tracks, title):
    unavailable = []
    if not local_tracks or len(local_tracks) > 500:
        return unavailable
    artist = _exact(local_tracks[0].get('album_artist'))
    year = str(local_tracks[0].get('year') or '')
    for row in local_tracks:
        try:
            number = int(row.get('track_number', 0))
            duration = float(row.get('duration', 0))
        except (ValueError, TypeError):
            return unavailable
        if (not artist or _exact(row.get('album_artist')) != artist
                or _album_key(row.get('album')) != _album_key(title)
                or str(row.get('year') or '') != year or not re.fullmatch(r'\d{4}', year)
                or not row.get('title') or not row.get('artist') or not row.get('file')
                or number <= 0 or duration <= 0 or not math.isfinite(duration)):
            return unavailable
    # Every available file must supply a complete fingerprint; a unique matching
    # source edition, not an arbitrary minimum file count, establishes identity.
    albums = spotify.search(f"{local_tracks[0]['album_artist']} {title}").get('albums', [])
    bare = re.sub(r'\s*(?:-\s*|[(\[]\s*)?\b(?:ep|single|compilation)\s*[)\]]?\s*$', '', str(title), flags=re.I)
    if bare and bare != title and not any(
            isinstance(a, dict) and _album_key(a.get('name')) == _album_key(title) for a in albums):
        # Tags often carry a release-type suffix Spotify's search ranks poorly.
        albums = spotify.search(f"{local_tracks[0]['album_artist']} {bare}").get('albums', [])
    candidates = {a['id']: a for a in albums
                  if isinstance(a, dict) and re.fullmatch(r'[A-Za-z0-9]{22}', str(a.get('id', '')))
                  and _album_key(a.get('name')) == _album_key(title)
                  # Providers expose either the primary authoritative album
                  # credit or the joined structured credits. Accept either exact
                  # representation here; full track-resource credit fingerprints
                  # must still agree. Never split literal duo/comma names.
                  and bool(a.get('artists'))
                  and artist in {_exact(a['artists'][0]), _exact(', '.join(a['artists']))}
                  and str(a.get('year') or '') == year}
    if not candidates or len(candidates) > 5:
        return unavailable
    verified = []
    for album_id, candidate in candidates.items():
        # Spotify's Web API (and embedded tags) classifies EPs as singles,
        # while its search resource can expose the more specific EP type.
        def release_family(value):
            kind = _exact(value)
            return 'single' if kind == 'ep' else kind
        if any(row.get('album_type') and release_family(row['album_type']) != release_family(candidate.get('type'))
               for row in local_tracks):
            continue
        try:
            tracks = spotify.album_tracks_from_id(album_id)
        except Exception:
            # One unreadable version must not hide the others.
            continue
        if (not tracks or len(tracks) > 500
                or len({r.get('song_id') for r in tracks}) != len(tracks)
                or any(not re.fullmatch(r'[A-Za-z0-9]{22}', str(r.get('song_id', '')))
                       or str(r.get('track_number')) != str(i)
                       or str(r.get('album_track_total')) != str(len(tracks))
                       or _exact(r.get('album_artist')) != artist
                       or _album_key(r.get('album_name')) != _album_key(title)
                       or str(r.get('release_date') or '')[:4] != year
                       for i, r in enumerate(tracks, 1))):
            continue
        # A file's "n/total" tag only names the version it came from; every
        # verified version is offered, so a total never excludes one.
        if any(row.get('album_track_total') is not None
               and not re.fullmatch(r'[0-9]+', str(row['album_track_total']))
               for row in local_tracks):
            continue
        verified.append((album_id, tracks))
    # Exact positions win; only when no version matches by position may a
    # renumbered (deluxe/reissue) file match one unique fingerprint elsewhere.
    matches = []
    for positional in (True, False):
        for album_id, tracks in verified:
            mapping = {}
            for row in local_tracks:
                number = int(row['track_number'])
                source = tracks[number - 1] if number <= len(tracks) else None
                if not positional:
                    found = [t for t in tracks if _fingerprint(row, t, positional=False)]
                    source = found[0] if len(found) == 1 else None
                if source is None or not _fingerprint(row, source, positional=positional):
                    break
                mapping.setdefault(source['song_id'], []).append(row['file'])
            else:
                matches.append(dict(id=album_id, tracks=tracks, local_matches=mapping,
                                    url=f'https://open.spotify.com/album/{album_id}',
                                    release_type=_release_type(candidates[album_id].get('type'))))
        if matches:
            break
    return matches


def _order_editions(matches, local_tracks):
    """Every verified version may be shown; the fullest one opens first.

    Each candidate already contains every local file by full fingerprint, so
    these are versions of the same album (standard/deluxe, explicit/clean).
    Explicit beats clean: a missing local explicit tag reads as False, so
    only a positive local flag would be evidence, and it agrees anyway.
    """
    def key(m):
        explicit = sum(bool(t.get('explicit')) for t in m['tracks'])
        return (-len(m['tracks']), -explicit, m['id'])
    return sorted(matches, key=key)


def _with_editions(ordered, edition=None, local_tracks=(), owned_ids=()):
    if edition is not None and not any(m['id'] == edition for m in ordered):
        return {'status': 'unavailable', 'tracks': []}
    # Keep the menu fullest-first, but open the actually owned source edition.
    # Another edition's song IDs cannot truthfully inherit its file formats.
    owned = set(owned_ids)
    default = max(ordered, key=lambda m: len(owned.intersection(
        t.get('song_id') for t in m['tracks']))) if owned else ordered[0]
    chosen = next((m for m in ordered if m['id'] == edition), default)
    tracks = []
    for source_song in chosen['tracks']:
        song = source_song
        credits = song.get('artists') or []
        # Album embed subtitles can flatten several artists into one string.
        # Restore boundaries only from an unambiguous matching local recording
        # with identical full credit text; no punctuation-based guessing or I/O.
        candidates = set()
        if len(credits) == 1:
            for local in local_tracks:
                names = local.get('artists') or []
                if (names and ', '.join(names) == credits[0]
                        and _exact(local.get('title')) == _exact(song.get('name'))
                        and _album_key(local.get('album')) == _album_key(song.get('album_name'))):
                    candidates.add(tuple(names))
        if len(candidates) == 1:
            song = {**song, 'artists': list(next(iter(candidates)))}
        tracks.append(song)
    return dict(status='resolved', tracks=tracks, local_matches=chosen['local_matches'],
                url=chosen['url'], edition=chosen['id'], release_type=chosen.get('release_type') or chosen['tracks'][0].get('release_type', ''),
                editions=[dict(id=m['id'], url=m['url'], track_count=len(m['tracks']),
                               title=m['tracks'][0].get('album_name', ''),
                               release_date=m['tracks'][0].get('release_date', ''),
                               tracks=[{k: t[k] for k in ('name', 'artists', 'duration', 'explicit',
                                                         'track_number', 'disc_number') if k in t}
                                       for t in m['tracks']],
                               explicit=any(t.get('explicit') for t in m['tracks']),
                               release_type=m.get('release_type') or m['tracks'][0].get('release_type', ''))
                          for m in ordered])


def discover_album_editions(album_id):
    """Read-only Link discovery; no Library files, bindings or preferences needed.

    The opened ID stays authoritative. Only independently fetched releases of
    the same intact artist and title family enter the menu; presentation groups
    equivalent recording sequences in the client. Never strip punctuation.
    """
    unavailable = {'status': 'unavailable', 'tracks': []}
    if not isinstance(album_id, str) or not re.fullmatch(r'[A-Za-z0-9]{22}', album_id):
        return unavailable
    try:
        selected = spotify.album_tracks_from_id(album_id)
    except Exception:
        return unavailable
    if not selected or len(selected) > 500:
        return unavailable
    title = selected[0].get('album_name', '')
    artist = selected[0].get('album_artist', '')

    def family(value):
        # Recognized version annotations only, not '+' or arbitrary subtitles.
        value = re.sub(r'\s*[\[(](?:deluxe|expanded|extended|standard|special|anniversary|remastered|explicit|clean)'
                       r'(?:\s+(?:edition|version))?[\])]\s*$', '', str(value), flags=re.I)
        return _exact(value)

    def verified(rows):
        return bool(rows) and len(rows) <= 500 and all(
            _exact(t.get('album_artist')) == _exact(artist)
            and family(t.get('album_name')) == family(title)
            and re.fullmatch(r'[A-Za-z0-9]{22}', str(t.get('song_id', '')))
            for t in rows)

    if not title or not artist or not verified(selected):
        return unavailable
    matches = [dict(id=album_id, tracks=selected, local_matches={},
                    url=f'https://open.spotify.com/album/{album_id}')]
    seen = {album_id}
    try:
        candidates = spotify.search(f'{artist} {family(title)}').get('albums', [])
    except Exception:
        candidates = []
    attempts = 0
    for candidate in candidates:
        aid = candidate.get('id')
        if (not isinstance(aid, str) or not re.fullmatch(r'[A-Za-z0-9]{22}', aid)
                or _exact(artist) not in {_exact(a) for a in candidate.get('artists') or []}
                or family(candidate.get('name')) != family(title)):
            continue
        if aid == album_id:
            matches[0]['release_type'] = _release_type(candidate.get('type'))
        if aid in seen or attempts >= _LOOSE_FETCH_LIMIT:
            continue
        seen.add(aid)
        attempts += 1
        try:
            tracks = spotify.album_tracks_from_id(aid)
        except Exception:
            continue
        if verified(tracks):
            matches.append(dict(id=aid, tracks=tracks, local_matches={},
                                url=f'https://open.spotify.com/album/{aid}',
                                release_type=_release_type(candidate.get('type'))))
    return _with_editions(_order_editions(matches, []), album_id)


def resolve_album_source(local_tracks, title, track_index, edition=None):
    unavailable = {'status': 'unavailable', 'tracks': []}
    if edition is not None:
        if not isinstance(edition, str) or not re.fullmatch(r'[A-Za-z0-9]{22}', edition):
            return unavailable
        artists = {_exact(r.get('album_artist')) for r in local_tracks if r.get('album_artist')}
        if not artists:
            return unavailable
        try:
            selected = spotify.album_tracks_from_id(edition)
        except Exception:
            return unavailable
        if (not selected or len(selected) > 500 or any(
                not re.fullmatch(r'[A-Za-z0-9]{22}', str(t.get('song_id', '')))
                or _album_key(t.get('album_name')) != _album_key(title)
                or _exact(t.get('album_artist')) not in artists for t in selected)):
            return unavailable
        matches = [dict(id=edition, tracks=selected, local_matches={},
                        url=f'https://open.spotify.com/album/{edition}')]
        seen_types = {}
        try:
            matches += _loose_versions(local_tracks, title, {edition}, seen_types=seen_types)
        except Exception:
            pass
        matches[0]['release_type'] = seen_types.get(edition, '')
        return _with_editions(_order_editions(matches, local_tracks), edition, local_tracks)

    if track_index is None:
        return unavailable
    ids = {tid for row in local_tracks
           if (tid := track_index.spotify_id_for_filename(row['file']))}
    if not ids:
        return _recover_legacy(local_tracks, title, edition)
    album_id, _ = spotify._album_ref_from_open_track_page(next(iter(sorted(ids))))
    exact = []
    if isinstance(album_id, str) and re.fullmatch(r'[A-Za-z0-9]{22}', album_id):
        tracks = spotify.album_tracks_from_id(album_id)
        if (tracks
                and all(str(row.get('album_name') or '').strip().casefold()
                        == title.strip().casefold() for row in tracks)
                and ids.issubset({row.get('song_id') for row in tracks})):
            exact = [dict(id=album_id, tracks=tracks, local_matches={},
                          url=f'https://open.spotify.com/album/{album_id}')]
    # Downloaded albums also offer every other version Spotify has, so a
    # different edition can be chosen and downloaded.
    seen_types = {}
    try:
        others = _loose_versions(local_tracks, title, {m['id'] for m in exact},
                                 any_name=not exact, seen_types=seen_types)
    except Exception:
        others = []
    for m in exact:
        # Its type comes from the same search the other versions came from.
        m['release_type'] = seen_types.get(m['id'], '')
    for m in others:
        m['local_matches'] = {}
    matches = exact + others
    if not matches:
        return unavailable
    return _with_editions(_order_editions(matches, local_tracks), edition, local_tracks, owned_ids=ids)
