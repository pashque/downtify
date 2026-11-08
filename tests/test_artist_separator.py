"""Existing ';' artist tags convert to ', ' + ARTISTS, keep everything else, and can be undone."""

import os
import shutil
import subprocess
from pathlib import Path
import pytest
from mutagen.id3 import ID3, TPE1, TIT2, APIC, TXXX
from downtify import artist_separator as sep

FFMPEG = shutil.which('ffmpeg')
pytestmark = pytest.mark.skipif(not FFMPEG, reason='ffmpeg missing')


def _mp3(path, artist, version=4):
    subprocess.run(
        [
            FFMPEG,
            '-nostdin',
            '-loglevel',
            'error',
            '-f',
            'lavfi',
            '-i',
            'anullsrc=r=22050:cl=mono',
            '-t',
            '1',
            '-c:a',
            'libmp3lame',
            str(path),
        ],
        check=True,
    )
    tags = ID3()
    tags.add(TIT2(encoding=3, text='Song'))
    tags.add(TPE1(encoding=3, text=artist))
    tags.add(
        APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Cover',
            data=b'\xff\xd8jpegdata',
        )
    )
    tags.save(str(path), v2_version=version)
    os.utime(path, (1_600_000_000, 1_600_000_000))
    return path


@pytest.mark.parametrize('version', [4])
def test_converts_only_the_artist_and_keeps_dates_cover_and_version(
    tmp_path, version
):
    f = _mp3(tmp_path / 'a.mp3', 'Drake; 21 Savage', version)
    audio_before = f.read_bytes()[-2000:]
    items = sep.plan([('x/a.mp3', f)])
    assert [(i['before'], i['after']) for i in items] == [
        (['Drake; 21 Savage'], 'Drake, 21 Savage')
    ]
    out = sep.apply(items, tmp_path / 'backup' / 'b.json')
    assert out['changed'] == 1 and not out['failed']
    tags = ID3(str(f))
    assert str(tags['TPE1']) == 'Drake, 21 Savage'
    assert list(tags['TXXX:ARTISTS'].text) == ['Drake', '21 Savage']
    assert (
        str(tags['TIT2']) == 'Song'
        and tags.getall('APIC')[0].data == b'\xff\xd8jpegdata'
    )
    assert tags.version[1] == version
    assert os.stat(f).st_mtime == 1_600_000_000
    assert f.read_bytes()[-2000:] == audio_before
    assert (
        oct(os.stat(tmp_path / 'backup' / 'b.json').st_mode & 0o777) == '0o600'
    )
    # Undo puts the original back.
    assert (
        sep.restore_from_backup(tmp_path / 'backup' / 'b.json')['restored']
        == 1
    )
    assert str(ID3(str(f))['TPE1']) == 'Drake; 21 Savage'
    assert ID3(str(f)).get('TXXX:ARTISTS') is None


def test_leaves_commas_singles_and_non_mp3_alone(tmp_path):
    a = _mp3(tmp_path / 'a.mp3', 'Earth, Wind & Fire')
    b = _mp3(tmp_path / 'b.mp3', 'Drake')
    c = tmp_path / 'c.flac'
    c.write_bytes(b'not audio')
    assert sep.plan([('a', a), ('b', b), ('c', c)]) == []


def test_id3v23_files_are_reported_not_changed(tmp_path):
    f = _mp3(tmp_path / 'a.mp3', 'Drake; 21 Savage', 3)
    before = f.read_bytes()
    out = sep.apply(sep.plan([('a', f)]), tmp_path / 'b.json')
    assert (
        out['changed'] == 0 and out['failed'][0]['error'] == 'ID3v2.3 skipped'
    )
    assert f.read_bytes() == before
