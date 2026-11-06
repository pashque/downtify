"""Read embedded audio tags for library / player display."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mutagen import File as MutagenFile
from mutagen.id3 import ID3

from .content_advisory import (
    ADVISORY_TAG,
    EXPLICIT_VALUES,
    MP4_ADVISORY_ATOM,
)
from .cover_art import extract_cover_art
from .image_size import image_short_side


def _tag_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, list):
        parts = [_tag_text(item) for item in value]
        return '; '.join(part for part in parts if part)
    return str(value).strip()


def _split_artists(artist: str) -> list[str]:
    text = artist.strip()
    if not text:
        return []
    # Only the legacy internal separator is unambiguous. Commas and
    # slashes are part of names (Tyler, The Creator; AC/DC).
    return [part.strip() for part in text.split(';') if part.strip()]


def _structured_artists(path: Path, audio: Any) -> list[str]:
    """The multi-value ARTISTS tag (MusicBrainz/Picard convention) Downtify
    writes next to a comma-joined display artist; [] when absent."""

    try:
        values: Any = None
        suffix = path.suffix.casefold()
        if suffix == '.mp3':
            frame = ID3(str(path)).get('TXXX:ARTISTS')
            values = list(frame.text) if frame is not None else None
        elif suffix in {'.m4a', '.mp4', '.aac', '.alac'}:
            raw = MutagenFile(str(path))
            values = (raw.tags or {}).get('----:com.apple.iTunes:ARTISTS') if raw is not None else None
        else:
            # Vorbis comments (FLAC, Ogg, Opus).
            raw = MutagenFile(str(path))
            tags = getattr(raw, 'tags', None)
            values = (tags.get('artists') or tags.get('ARTISTS')) if tags is not None else None
        if not values:
            return []
        out = []
        for value in values if isinstance(values, list) else [values]:
            text = value.decode('utf-8', 'replace') if isinstance(value, bytes) else str(value)
            if text.strip() and text.strip() not in out:
                out.append(text.strip())
        return out
    except Exception:
        return []


def read_release_type(path: Path) -> str:
    """Read only authoritative release tags; unknown values stay unknown.

    Easy tags omit ID3 custom frames and MP4 freeform atoms, so use the
    native container tags. Never infer a release kind from title or size.
    """
    try:
        if path.suffix.casefold() == '.mp3':
            frame = ID3(str(path)).get('TXXX:MusicBrainz Album Type')
            values = frame.text if frame is not None else []
        else:
            audio = MutagenFile(str(path))
            tags = getattr(audio, 'tags', None)
            if tags is None:
                return ''
            values = (
                tags.get('----:com.apple.iTunes:MusicBrainz Album Type')
                or tags.get('releasetype')
                or tags.get('musicbrainz_albumtype')
                or []
            )
        if not isinstance(values, (list, tuple)):
            values = [values]
        for value in values:
            text = value.decode('utf-8', 'replace') if isinstance(value, bytes) else str(value)
            kind = text.strip().casefold()
            if kind in {'album', 'single', 'ep', 'compilation'}:
                return kind
    except Exception:
        pass
    return ''


def _track_number(value: Any) -> int:
    """``3``, ``'3'`` or ``'3/12'`` -> 3; anything unreadable -> 0."""

    text = _tag_text(value).split('/', 1)[0].strip()
    try:
        return max(0, int(text))
    except ValueError:
        return 0


def _year(value: Any) -> str:
    text = _tag_text(value)
    return text[:4] if len(text) >= 4 and text[:4].isdigit() else ''


def _duration(audio: Any) -> float:
    try:
        length = float(audio.info.length)
    except (AttributeError, TypeError, ValueError):
        return 0.0
    return round(length, 2) if length > 0 else 0.0


def _codec(audio: Any) -> str:
    """The audio codec, in the names a client knows: ``mp3``, ``flac``,
    ``aac``, ``alac``, ``opus``, ``vorbis`` - ``''`` when unknown."""

    kind = type(audio).__name__.lower()
    if kind in {'mp3', 'easymp3'}:
        return 'mp3'
    if kind == 'flac':
        return 'flac'
    if kind in {'oggopus'}:
        return 'opus'
    if kind in {'oggvorbis'}:
        return 'vorbis'
    if kind in {'mp4', 'easymp4'}:
        codec = str(getattr(audio.info, 'codec', '') or '').lower()
        if codec.startswith('mp4a'):
            return 'aac'
        return codec or 'aac'
    return ''


def audio_format(audio: Any) -> dict[str, Any]:
    """``codec``, ``bitrate`` (bits/s), ``sample_rate`` (Hz) and
    ``channels`` of a mutagen file; zeros and ``''`` when unknown."""

    info = getattr(audio, 'info', None)

    def number(name: str) -> int:
        try:
            return max(0, int(getattr(info, name, 0) or 0))
        except (TypeError, ValueError):
            return 0

    return {
        'codec': _codec(audio) if audio is not None else '',
        'bitrate': number('bitrate'),
        'sample_rate': number('sample_rate'),
        'channels': number('channels'),
    }


def read_explicit(path: Path) -> bool:
    """Whether the file is marked explicit: an ``ITUNESADVISORY`` text
    (ID3 TXXX frame, Vorbis/FLAC/Opus comment) or an MP4 ``rtng`` atom."""

    try:
        if path.suffix.lower() == '.mp3':
            frames = ID3(str(path)).getall('TXXX')
            values = [
                str(text)
                for frame in frames
                if str(frame.desc).upper() == ADVISORY_TAG
                for text in frame.text
            ]
        else:
            audio = MutagenFile(str(path))
            tags = audio.tags if audio is not None else None
            if tags is None:
                return False
            raw = tags.get(MP4_ADVISORY_ATOM) or tags.get(ADVISORY_TAG)
            values = [str(item) for item in (raw or [])]
    except Exception:
        return False
    return any(value.strip() in EXPLICIT_VALUES for value in values)


def read_audio_metadata(path: Path) -> dict[str, Any]:
    """Return display tags read from ``path``.

    ``title``, ``artist``, ``artists`` and ``album``, plus
    ``album_artist``, ``release_type`` (authoritative tag, '' when unknown),
    ``track_number`` (0 when unknown), ``year`` and
    ``duration`` in seconds (0 when unknown), plus the audio format:
    ``codec``, ``bitrate``, ``sample_rate`` and ``channels`` (see
    :func:`audio_format`), and ``explicit`` (:func:`read_explicit`).
    """

    empty: dict[str, Any] = {
        'title': '',
        'artist': '',
        'artists': [],
        'album': '',
        'release_type': '',
        'album_artist': '',
        'track_number': 0,
        'year': '',
        'genre': '',
        'duration': 0.0,
        'explicit': False,
        **audio_format(None),
    }
    if not path.is_file():
        return dict(empty)

    title = ''
    artist = ''
    album = ''
    album_artist = ''
    track_number = 0
    year = ''
    genre = ''
    duration = 0.0

    try:
        audio = MutagenFile(str(path), easy=True)
    except Exception:
        audio = None
    fmt = audio_format(audio)

    if audio is not None:
        title = _tag_text(audio.get('title'))
        artist = _tag_text(audio.get('artist'))
        album = _tag_text(audio.get('album'))
        album_artist = _tag_text(audio.get('albumartist'))
        track_number = _track_number(audio.get('tracknumber'))
        year = _year(audio.get('date'))
        genre = _tag_text(audio.get('genre'))
        duration = _duration(audio)

        if not title and audio.tags is not None:
            title = _tag_text(audio.tags.get('title'))
        if not artist and audio.tags is not None:
            artist = _tag_text(audio.tags.get('artist'))
        if not album and audio.tags is not None:
            album = _tag_text(audio.tags.get('album'))

    if not title and not artist and not album:
        try:
            id3 = ID3(str(path))
        except Exception:
            id3 = None
        if id3 is not None:
            title = _tag_text(id3.get('TIT2'))
            artist = _tag_text(id3.get('TPE1'))
            album = _tag_text(id3.get('TALB'))
            album_artist = _tag_text(id3.get('TPE2'))
            track_number = _track_number(id3.get('TRCK'))
            year = _year(id3.get('TDRC'))
            genre = _tag_text(id3.get('TCON'))

    structured = _structured_artists(path, audio)
    # Repair only an exact adjacent sequence attested by the album credit.
    # A guest on another artist's album has no such evidence; leave it alone.
    if structured and album_artist:
        for start in range(len(structured)):
            for end in range(start + 2, len(structured) + 1):
                if ', '.join(structured[start:end]) == album_artist:
                    structured = structured[:start] + [album_artist] + structured[end:]
                    break
            else:
                continue
            break
    if structured:
        # Downtify's internal artist list: one "; "-separated string, never
        # shown; tags themselves carry ", " (display) + ARTISTS (list).
        artist = '; '.join(structured)
    artists = structured or _split_artists(artist)
    return {
        'title': title,
        'artist': artist,
        'artists': artists,
        'album': album,
        'release_type': read_release_type(path),
        'album_artist': album_artist,
        'track_number': track_number,
        'year': year,
        'genre': genre,
        'duration': duration,
        'explicit': read_explicit(path),
        **fmt,
    }


def file_stat_fields(full_path: Path) -> dict[str, int]:
    """``added`` (modification time, epoch seconds) and ``size`` in bytes."""

    try:
        st = full_path.stat()
    except OSError:
        return {'added': 0, 'size': 0}
    return {'added': int(st.st_mtime), 'size': int(st.st_size)}


def library_entry_for_file(
    stored_path: str, full_path: Path
) -> dict[str, Any]:
    """Build one ``/tracks`` row using tags, then filename fallbacks."""

    fb_title, fb_artist = _fallback_title_from_filename(full_path)
    meta = read_audio_metadata(full_path)
    title = str(meta.get('title') or '').strip() or fb_title
    artist = str(meta.get('artist') or '').strip() or fb_artist
    album = str(meta.get('album') or '').strip()
    # The cover is read once and both answered from it: whether there is
    # one, and how big it is (which the library upgrade scan needs for
    # every track, and would otherwise pay a second full read for).
    cover_data, _cover_mime = (
        extract_cover_art(full_path) if full_path.is_file() else (None, None)
    )
    return {
        'file': stored_path,
        'title': title,
        'artist': artist,
        'album': album,
        'release_type': str(meta.get('release_type') or ''),
        'artists': list(meta.get('artists') or _split_artists(artist)),
        'album_artist': str(meta.get('album_artist') or '').strip(),
        'track_number': int(meta.get('track_number') or 0),
        'year': str(meta.get('year') or ''),
        'genre': str(meta.get('genre') or ''),
        'duration': float(meta.get('duration') or 0.0),
        'codec': str(meta.get('codec') or ''),
        'bitrate': int(meta.get('bitrate') or 0),
        'sample_rate': int(meta.get('sample_rate') or 0),
        'channels': int(meta.get('channels') or 0),
        'explicit': bool(meta.get('explicit')),
        'has_cover': bool(cover_data),
        'cover_px': image_short_side(cover_data),
        **file_stat_fields(full_path),
    }


def _fallback_title_from_filename(path: Path) -> tuple[str, str]:
    """Parse ``Artist - Title`` from the basename when tags are missing."""

    stem = path.stem
    dash = stem.find(' - ')
    if dash > 0:
        return stem[dash + 3 :].strip(), stem[:dash].strip()
    return stem, ''
