"""Destination-aware presence, independent of copies elsewhere in the library."""
from pathlib import PurePosixPath
from typing import Any, Optional


def skip_existing_for(song: dict[str, Any], overwrite_default: bool) -> bool:
    """A UI action overrides overwrite for this request, never other jobs."""
    mode = song.get('downtify_download_mode')
    if mode == 'missing':
        return True
    if mode == 'redownload':
        return False
    return not overwrite_default


def managed_destination(downloader: Any) -> bool:
    return type(getattr(downloader, 'folder_structure', None)) is bool


def matches_destination(downloader: Any, song: dict[str, Any], stored: str,
                        subdir: Optional[str] = None) -> bool:
    """Can a completed job/file satisfy this particular requested path?"""
    if not managed_destination(downloader) and song.get('downtify_destination') != 'album':
        return True
    if not stored:
        return False
    expected = downloader.expected_stem_for(song, subdir)
    actual = str(PurePosixPath(str(stored).replace('\\', '/')).with_suffix(''))
    return actual.casefold() == expected.casefold()


def verified_destination_copy(downloader: Any, song: dict[str, Any],
                              subdir: Optional[str] = None, track_index=None):
    """Only a server-verified source ID in this exact intended parent qualifies."""
    if track_index is None:
        return None
    parent = PurePosixPath(downloader.expected_stem_for(song, subdir)).parent
    for stored in track_index.source_copies_for_song(song):
        if PurePosixPath(stored).parent == parent:
            return stored
    return None


def destination_status(downloader: Any, song: dict[str, Any],
                       subdir: Optional[str] = None, *, track_index=None) -> dict[str, Any]:
    """No network calls; rendering the intended path must not scan the library."""
    stem = downloader.expected_stem_for(song, subdir)
    stored = (downloader.existing_filename_for(song, subdir)
              or verified_destination_copy(downloader, song, subdir, track_index))
    return {
        'key': str(song.get('song_id') or song.get('url') or ''),
        'stem': stem,
        'exists': bool(stored),
        'file': stored or None,
    }
