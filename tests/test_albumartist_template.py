from downtify.downloader import Downloader

TEMPLATE = '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'


def test_albumartist_keeps_feature_in_filename_not_folders(tmp_path):
    d = Downloader(tmp_path, output_template=TEMPLATE)
    song = dict(name='Second Song', artists=['Main Artist', 'Guest Artist'], album_artist='Main Artist', album_name='Album Name', release_date='2024-02-03', track_number=2)
    assert d._format_basename(song) == 'Main Artist/Main Artist - Album Name (2024)/02. Main Artist, Guest Artist - Second Song'


def test_albumartist_prefers_album_credit_over_first_track_artist():
    song = dict(artists=['Guest Artist', 'Main Artist'], album_artist='Main Artist')
    assert Downloader._template_values(song)['albumartist'] == 'Main Artist'


def test_albumartist_falls_back_to_first_artist():
    assert Downloader._template_values(dict(artists=['Main Artist', 'Guest Artist']))['albumartist'] == 'Main Artist'


def test_albumartist_unknown_and_sanitized():
    assert Downloader._template_values({})['albumartist'] == 'Unknown Artist'
    assert Downloader._template_values(dict(album_artist='AC/DC'))['albumartist'] == 'ACDC'


def test_artist_names_keep_trailing_punctuation_in_safe_download_names():
    values = Downloader._template_values(dict(artists=['Fred again..']))
    assert values['artists'] == 'Fred again..'
    assert Downloader._template_values(dict(album_artist='A:B'))['albumartist'] == 'A:B'


def test_albumartist_template_is_library_relative_not_playlist_relative(tmp_path):
    d = Downloader(tmp_path, output_template=TEMPLATE)
    song = dict(name='Song', artists=['Main Artist', 'Guest'], album_artist='Main Artist', album_name='Album', release_date='2024', track_number=1)
    target, prefix, basename = d._expected_location(song, 'Some Playlist')
    assert target == tmp_path / 'Main Artist' / 'Main Artist - Album (2024)'
    assert prefix == 'Main Artist/Main Artist - Album (2024)/'
    assert basename == '01. Main Artist, Guest - Song'


def test_existing_tokens_unchanged():
    values = Downloader._template_values(dict(artists=['Main Artist', 'Guest Artist']))
    assert values['artist'] == values['artists'] == 'Main Artist, Guest Artist'
