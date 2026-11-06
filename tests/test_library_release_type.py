"""Authoritative embedded release kinds survive read-only Library metadata paths."""
import hashlib
import shutil
import subprocess

import pytest
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, TXXX
from mutagen.mp4 import MP4, MP4FreeForm

from downtify.downloader import embed_metadata
from downtify.library_metadata import library_entry_for_file, read_audio_metadata

FFMPEG = shutil.which('ffmpeg')
CODECS = {'mp3': 'libmp3lame', 'm4a': 'aac', 'flac': 'flac', 'ogg': 'libvorbis', 'opus': 'libopus'}


def _fixture(tmp_path, fmt, kind):
    if not FFMPEG:
        pytest.skip('ffmpeg missing')
    path = tmp_path / f'Only local track - Single.{fmt}'
    subprocess.run([FFMPEG, '-nostdin', '-loglevel', 'error', '-f', 'lavfi', '-i',
                    'anullsrc=r=48000:cl=stereo', '-t', '0.2', '-c:a', CODECS[fmt], str(path)], check=True)
    if fmt in {'mp3', 'm4a', 'flac'}:
        embed_metadata(path, {'name': 'Only local track', 'artists': ['Tyler, The Creator', 'Guest'],
                              'album_name': 'Actual Album - Single', 'album_artist': 'Tyler, The Creator',
                              'track_number': 7, 'album_track_total': 12}, download_cover=False)
    if fmt == 'mp3':
        tags = ID3(path)
        if kind:
            tags.add(TXXX(encoding=3, desc='MusicBrainz Album Type', text=[kind]))
        tags.save(path)
    elif fmt == 'm4a':
        audio = MP4(path)
        if kind:
            audio['----:com.apple.iTunes:MusicBrainz Album Type'] = [MP4FreeForm(kind.encode())]
        audio.save()
    else:
        audio = MutagenFile(path)
        if fmt in {'ogg', 'opus'}:
            audio['title'] = 'Only local track'
            audio['album'] = 'Actual Album - Single'
            audio['artist'] = 'Tyler, The Creator, Guest'
            audio['artists'] = ['Tyler, The Creator', 'Guest']
            audio['tracknumber'] = '7/12'
        if kind:
            audio['releasetype'] = kind
        audio.save()
    return path


@pytest.mark.parametrize('kind', ['album', 'single', 'ep', 'compilation', ''])
def test_lightweight_album_index_carries_authoritative_type(tmp_path, kind):
    from downtify.library_catalog import LibraryContext, library_album_index
    from downtify.library_metadata_cache import LibraryMetadataCache
    path = _fixture(tmp_path, 'mp3', kind)
    before = path.read_bytes()
    ctx = LibraryContext(download_dir=tmp_path, metadata_cache=LibraryMetadataCache(tmp_path / 'metadata.db'))
    for _ in range(2):
        rows = library_album_index(ctx)
        assert len(rows) == 1
        assert rows[0]['release_type'] == kind
    assert path.read_bytes() == before


@pytest.mark.parametrize('fmt', CODECS)
@pytest.mark.parametrize('tag, expected', [('album', 'album'), ('single', 'single'), (' EP ', 'ep'),
                                          ('compilation', 'compilation'), ('bootleg', ''), ('', '')])
def test_real_tags_are_authoritative_without_modifying_files(tmp_path, fmt, tag, expected):
    path = _fixture(tmp_path, fmt, tag)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    meta = read_audio_metadata(path)
    entry = library_entry_for_file(path.name, path)
    assert meta.get('release_type') == expected
    assert entry.get('release_type') == expected
    assert meta['artists'] == entry['artists'] == ['Tyler, The Creator', 'Guest']
    for field in ('codec', 'bitrate', 'sample_rate', 'channels', 'duration'):
        assert entry[field] == meta[field]
    assert meta['codec'] and meta['duration'] > 0
    assert meta['channels'] == 2
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize('fmt', CODECS)
@pytest.mark.parametrize('kind', ['album', 'single', 'ep', 'compilation', ''])
def test_release_type_survives_cold_and_warm_cache_and_listing(tmp_path, monkeypatch, fmt, kind):
    from downtify import library_metadata_cache as cache_module
    from downtify.library_listing_store import LibraryListingStore

    path = _fixture(tmp_path, fmt, kind)
    before = path.read_bytes()
    cache = cache_module.LibraryMetadataCache(tmp_path / 'library.db')
    direct = library_entry_for_file(path.name, path)
    cold = cache.get_entry(path.name, path)
    assert cold == direct

    def unexpected_read(*args):
        pytest.fail('warm metadata cache must not reread tags')

    monkeypatch.setattr(cache_module, 'library_entry_for_file', unexpected_read)
    warm = cache_module.LibraryMetadataCache(tmp_path / 'library.db').get_entry(path.name, path)
    assert warm == cold
    assert warm.get('release_type') == kind
    listing = LibraryListingStore(tmp_path / 'listing.db')
    listing.save('library', 'unchanged', [(path.name, str(path))], [], [warm])
    assert LibraryListingStore(tmp_path / 'listing.db').load('library')['entries'] == [direct]
    assert path.read_bytes() == before


def test_version_seven_rows_and_persisted_listing_are_invalidated(tmp_path):
    from downtify.library_metadata_cache import LibraryMetadataCache, META_VERSION
    from downtify.library_listing_store import LibraryListingStore
    from downtify.sqlite_utils import connect_sqlite

    path = _fixture(tmp_path, 'mp3', 'single')
    before = path.read_bytes()
    db = tmp_path / 'library.db'
    cache = LibraryMetadataCache(db)
    current = cache.get_entry(path.name, path)
    listing = LibraryListingStore(db)
    old = {key: value for key, value in current.items() if key != 'release_type'}
    listing.save('library', 'unchanged', [(path.name, str(path))], [], [old])
    with connect_sqlite(str(db)) as conn:
        conn.execute('ALTER TABLE library_metadata DROP COLUMN release_type')
        conn.execute('UPDATE library_metadata SET meta_version = 7')
        conn.execute('UPDATE library_listing SET meta_version = 7')

    upgraded = LibraryMetadataCache(db)
    assert LibraryListingStore(db).load('library') is None
    refreshed = upgraded.get_entry(path.name, path)
    assert refreshed == current
    assert refreshed['release_type'] == 'single'
    assert META_VERSION > 7
    with connect_sqlite(str(db)) as conn:
        assert conn.execute('SELECT meta_version FROM library_metadata').fetchone()[0] == META_VERSION
    listing.save('library', 'unchanged', [(path.name, str(path))], [], [refreshed])
    assert LibraryListingStore(db).load('library')['entries'] == [current]
    assert path.read_bytes() == before


@pytest.mark.parametrize('kind', ['album', ''])
def test_one_local_track_of_partial_album_is_never_inferred_as_single(tmp_path, kind):
    from downtify.library_catalog import LibraryContext, list_library_entries
    from downtify.library_metadata_cache import LibraryMetadataCache

    path = _fixture(tmp_path, 'mp3', kind)
    ctx = LibraryContext(download_dir=tmp_path,
                         metadata_cache=LibraryMetadataCache(tmp_path / 'library.db'))
    for _ in range(2):
        (row,) = list_library_entries(ctx)
        assert row['file'] == path.name
        assert row['track_number'] == 7
        assert row['release_type'] == kind


def test_missing_or_broken_metadata_has_unknown_release_type(tmp_path):
    assert read_audio_metadata(tmp_path / 'missing.mp3').get('release_type') == ''
    path = tmp_path / 'Artist - Title - EP.flac'
    path.write_bytes(b'not audio')
    assert library_entry_for_file(path.name, path).get('release_type') == ''
