"""Filesystem component rendering and legacy, lossy name matching.

Linux filename rendering preserves valid punctuation. ``file_name_key`` is a
historical search compatibility key, not proof that two names or recordings
are identical on disk; it can collapse distinct names such as ``*NSYNC`` and
``NSYNC``. This leaf module imports no other Downtify modules.
"""

from __future__ import annotations

import re

_INVALID_FS_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
_WHITESPACE = re.compile(r'\s+')
# "Song (Remastered 2011)", "Song [Live]", "Song - Radio Edit": the part a
# title match ignores.
_TITLE_EXTRAS = re.compile(r'\s*(?:[(\[].*?[)\]]|\s-\s.*)$')


def _without_invalid_chars(text: str) -> str:
    return _INVALID_FS_CHARS.sub('', text or '').strip().strip('.')


def sanitize_file_name(text: str) -> str:
    """Render a Linux filename component, retaining supported punctuation.

    Slash and control characters are removed, surrounding whitespace and
    leading dots are stripped, and empty results become ``'unknown'``.
    """

    # The legacy comparison key intentionally retains its older, lossy
    # normalization. Rendering a Linux component must not use that key.
    component = re.sub(r'[/\x00-\x1f]', '', text or '').strip().lstrip('.')
    return component or 'unknown'


def file_name_key(name: str) -> str:
    """Return the legacy lossy comparison key, not a filesystem identity.

    ``'AC/DC'`` and ``'ACDC'`` give the same key, as do ``'*NSYNC'`` and
    ``'NSYNC'`` or ``'M.I.A.'`` and ``'M.I.A'``. Case and runs of spaces
    are ignored too.

    Empty when nothing is left of *name* (``'???'``) - unlike
    :func:`sanitize_file_name` there is no ``'unknown'`` stand-in, so two
    such names can't be mistaken for each other or for a real one; callers
    should not match on an empty key.
    """

    return _WHITESPACE.sub(' ', _without_invalid_chars(name)).casefold()


def title_key(title: str) -> str:
    """A song or album title as a title match compares it: its
    :func:`file_name_key`, without trailing ``(…)``/``[…]`` parts or a
    `` - …`` suffix - so ``Dummy (Deluxe Edition)``, ``Roads - Live`` and
    ``Glory Box [Remastered]`` match ``Dummy``, ``Roads`` and ``Glory Box``.
    """

    text = str(title or '').strip()
    while True:
        trimmed = _TITLE_EXTRAS.sub('', text).strip()
        if trimmed == text or not trimmed:
            break
        text = trimmed
    return file_name_key(text)
