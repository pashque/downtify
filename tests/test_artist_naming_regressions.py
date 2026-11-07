from downtify.downloader import Downloader
from downtify.download_destination import matches_destination


def test_artist_safe_component_preserves_linux_valid_characters_and_literal_backslash(tmp_path):
    song = dict(name='A/B', artists=['A:B*?"<>|\\'], album_artist='A:B*?"<>|\\')
    parts = Downloader._format_output_parts  # exercised below via instance
    d = Downloader(tmp_path)
    rendered = parts(d, song)
    assert rendered == ['A:B*?"<>|\\ - AB']
    assert all(p not in {'.', '..'} for p in rendered)


def test_destination_match_distinguishes_literal_backslash_from_separator(tmp_path):
    d = Downloader(tmp_path, output_template='{artists} - {title}.{output-ext}')
    song = dict(name='Song', artists=['A\\B'], downtify_destination='album')
    expected = d.expected_stem_for(song)
    assert matches_destination(d, song, expected + '.mp3')
    assert not matches_destination(d, song, expected.replace('\\', '/') + '.mp3')


def test_destination_match_rejects_non_audio_suffix_and_sibling_path(tmp_path):
    d = Downloader(tmp_path, output_template='{artists} - {title}.{output-ext}')
    song = dict(name='Song', artists=['Artist'], downtify_destination='album')
    expected = d.expected_stem_for(song)
    assert not matches_destination(d, song, expected + '.txt')
    assert not matches_destination(d, song, expected + '.mp3/notes.txt')
    assert matches_destination(d, song, expected + '.flac')


def test_destination_match_is_case_sensitive(tmp_path):
    d = Downloader(tmp_path, output_template='{artists} - {title}.{output-ext}')
    song = dict(name='Song', artists=['Artist'], downtify_destination='album')
    expected = d.expected_stem_for(song)
    assert matches_destination(d, song, expected + '.mp3')
    assert not matches_destination(d, song, expected.swapcase() + '.mp3')


def test_invalid_existing_copy_conflicts_without_modifying_bytes(tmp_path):
    import pytest
    d = Downloader(tmp_path, output_template='{artists} - {title}.{output-ext}')
    song = dict(name='Artist appears in title', artists=['New Artist'], album_artist='New Artist', album_name='Album', track_number=1, disc_number=1, duration=180, source_id='spotify:track:1', downtify_download_mode='missing')
    existing = tmp_path / 'New Artist - Artist appears in title.mp3'
    existing.write_bytes(b'not valid audio')
    original = existing.read_bytes()
    with pytest.raises(RuntimeError, match='existing file'):
        d.download(song)
    assert existing.read_bytes() == original


def test_legacy_template_rendering_does_not_replace_artist_text_in_title(tmp_path):
    d = Downloader(tmp_path, output_template='{artists}/{title}.{output-ext}')
    song = dict(name='Fred again.. live', artists=['Fred again..'], album_artist='Fred again..')
    assert d._format_output_parts(song) == ['Fred again..', 'Fred again.. live']


def test_explicit_format_does_not_fall_back_to_other_extensions(tmp_path):
    d = Downloader(tmp_path, audio_format='mp3', output_template='{artists} - {title}.{output-ext}')
    song = dict(name='Song', artists=['Artist'], downtify_audio_format='flac')
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'')
    assert d.existing_filename_for(song) is None
