"""Tags show featured artists as "A, B"; the exact list rides in ARTISTS."""
import shutil
import subprocess
import pytest
from mutagen import File as MutagenFile
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from downtify.downloader import embed_metadata
from downtify.library_metadata import read_audio_metadata

FFMPEG = shutil.which('ffmpeg')
pytestmark = pytest.mark.skipif(not FFMPEG, reason='ffmpeg missing')
CODECS = {'mp3': ['-c:a', 'libmp3lame'], 'm4a': ['-c:a', 'aac'], 'flac': ['-c:a', 'flac']}


def _audio(path):
    subprocess.run([FFMPEG, '-nostdin', '-loglevel', 'error', '-f', 'lavfi', '-i',
                    'anullsrc=r=22050:cl=mono', '-t', '1', *CODECS[path.suffix[1:]], str(path)], check=True)
    return path


@pytest.mark.parametrize('fmt', sorted(CODECS))
def test_display_tag_uses_commas_and_reads_back_structured(tmp_path, fmt):
    path = _audio(tmp_path / f'a.{fmt}')
    song = {'name': 'Rich Flex', 'artists': ['Drake', '21 Savage'], 'album_name': 'Her Loss',
            'album_artist': 'Drake'}
    embed_metadata(path, song, download_cover=False)
    if fmt == 'mp3':
        assert str(ID3(str(path))['TPE1']) == 'Drake, 21 Savage'
    elif fmt == 'm4a':
        assert MP4(str(path)).tags['\xa9ART'] == ['Drake, 21 Savage']
    else:
        assert MutagenFile(str(path)).tags['artist'] == ['Drake, 21 Savage']
    meta = read_audio_metadata(path)
    assert meta['artists'] == ['Drake', '21 Savage']


def test_literal_comma_name_is_never_split(tmp_path):
    path = _audio(tmp_path / 'b.mp3')
    embed_metadata(path, {'name': 'September', 'artists': ['Earth, Wind & Fire']}, download_cover=False)
    assert str(ID3(str(path))['TPE1']) == 'Earth, Wind & Fire'
    assert read_audio_metadata(path)['artists'] == ['Earth, Wind & Fire']
