"""Storage settings shared by API, monitoring and library bookkeeping."""

from typing import Any, Mapping

STRUCTURED_OUTPUT = (
    '{albumartist}/{albumartist} - {album} ({year})/'
    '{tracknumber}. {artists} - {title}.{output-ext}'
)
FLAT_OUTPUT = '{artists} - {title}.{output-ext}'
STORAGE_KEYS = ('folder_structure', 'playlist_use_library')


def settings_use_shared_playlists(settings: Mapping[str, Any]) -> bool:
    """Whether playlist audio is shared, including flat-root managed mode."""
    structured = settings.get('folder_structure')
    if structured is not None:
        playlists = bool(settings.get('playlist_use_library', True))
        return playlists if structured else not playlists
    return bool(
        settings.get('organize_by_artist', False)
        or settings.get('organize_by_album', False)
    )


def downloader_uses_shared_playlists(downloader: Any) -> bool:
    """Use the downloader's policy; tolerate legacy test/extension fakes."""
    if downloader is None:
        return False
    shared = getattr(downloader, 'uses_shared_playlist_storage', None)
    if type(shared) is bool:
        return shared
    values = {
        key: getattr(downloader, key, default)
        for key, default in (
            ('folder_structure', None),
            ('playlist_use_library', True),
            ('organize_by_artist', False),
            ('organize_by_album', False),
        )
    }
    # MagicMock invents missing attributes. Only explicit booleans opt in.
    if type(values['folder_structure']) is not bool:
        values['folder_structure'] = None
    return settings_use_shared_playlists(values)


def storage_update(
    payload: Mapping[str, Any], current: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate without mutation; reset templates only for changed toggles."""
    for key in STORAGE_KEYS:
        if key in payload and type(payload[key]) is not bool:
            if key != 'folder_structure' or payload[key] is not None:
                suffix = ' or null' if key == 'folder_structure' else ''
                raise ValueError(f'{key} must be a boolean{suffix}')
    updated = dict(payload)
    changed = any(
        key in payload
        and payload[key]
        != current.get(key, None if key == 'folder_structure' else True)
        for key in STORAGE_KEYS
    )
    structured = updated.get(
        'folder_structure', current.get('folder_structure')
    )
    if changed and structured is not None:
        updated.update(
            output=STRUCTURED_OUTPUT if structured else FLAT_OUTPUT,
            organize_by_artist=False,
            organize_by_album=False,
        )
    return updated
