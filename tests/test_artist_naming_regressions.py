from downtify.downloader import Downloader


def test_artist_safe_component_preserves_linux_valid_characters_and_escapes_path_syntax():
    song = dict(name='A/B', artists=['A:B*?"<>|\\'], album_artist='A:B*?"<>|\\')
    parts = Downloader._format_output_parts  # exercised below via instance
    d = Downloader('/tmp/downtify-naming-test')
    rendered = parts(d, song)
    assert rendered == ['A:B*?"<>|%5C - AB']
    assert all(p not in {'.', '..'} for p in rendered)


def test_legacy_artist_fallback_requires_full_identity_and_source_identity(tmp_path):
    d = Downloader(tmp_path, output_template='{artists} - {title}.{output-ext}')
    song = dict(name='Artist appears in title', artists=['New Artist'], album_artist='New Artist', album_name='Album', track_number=1, disc_number=1, duration=180, source_id='spotify:track:1')
    # Legacy same-path name, but tags identify a different artist: must not be reused.
    legacy = tmp_path / 'New Artist - Artist appears in title.mp3'
    legacy.write_bytes(b'not valid audio')
    assert d.existing_filename_for(song) is None


def test_legacy_template_rendering_does_not_replace_artist_text_in_title(tmp_path):
    d = Downloader(tmp_path, output_template='{artists}/{title}.{output-ext}')
    song = dict(name='Fred again.. live', artists=['Fred again..'], album_artist='Fred again..')
    assert d._format_output_parts(song) == ['Fred again..', 'Fred again.. live']


def test_explicit_format_does_not_fall_back_to_other_extensions(tmp_path):
    d = Downloader(tmp_path, audio_format='mp3', output_template='{artists} - {title}.{output-ext}')
    song = dict(name='Song', artists=['Artist'], downtify_audio_format='flac')
    (tmp_path / 'Artist - Song.mp3').write_bytes(b'')
    assert d.existing_filename_for(song) is None
