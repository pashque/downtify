"""A playlist copy must not stand in for a missing album destination."""
from pathlib import Path

from downtify.downloader import Downloader
from downtify.track_index import TrackIndex, resolve_existing_download

FULL = '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'
SONG = dict(song_id='5fHrHoJKfCgBd35zwIBmUK', source='spotify', name='D4L', artists=['Future','Drake','Young Thug'], album_artist='Drake', album_name='Dark Lane Demo Tapes', release_date='2020-05-01', track_number=9)


def setup_playlist(tmp_path, structured=True):
    d=Downloader(tmp_path/'downloads', output_template=FULL if structured else '{artists} - {title}', folder_structure=structured, playlist_use_library=not structured, overwrite_existing_files=False)
    target,prefix,name=d._target_location(SONG,'My Playlist')
    old=target/(name+'.mp3')
    import subprocess
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t','0.1','-q:a','9',str(old)], check=True)
    index=TrackIndex(tmp_path/'index.db');index.register_song(SONG,prefix+old.name,full_path=old)
    return d,index,old


def test_artist_trailing_dots_are_preserved_in_generated_destination(tmp_path):
    d = Downloader(tmp_path/'downloads', output_template=FULL, folder_structure=True,
                   playlist_use_library=True, overwrite_existing_files=False)
    song = {**SONG, 'album_artist': 'Fred again..', 'artists': ['Fred again..']}
    path = d.expected_stem_for(song)
    assert path == 'Fred again../Fred again.. - Dark Lane Demo Tapes (2020)/09. Fred again.. - D4L'


def test_legacy_collision_with_wrong_tagged_artist_does_not_satisfy_album(tmp_path):
    from mutagen import File
    d = Downloader(tmp_path/'downloads', output_template=FULL, folder_structure=True,
                   playlist_use_library=True, overwrite_existing_files=False)
    song = {**SONG, 'album_artist': 'Fred again..', 'artists': ['Fred again..'],
            'name': 'Actual title', 'album_name': 'Actual album'}
    legacy = tmp_path/'downloads'/'Fred again'/'Fred again - Actual album (2020)'/'09. Fred again - Actual title.mp3'
    legacy.parent.mkdir(parents=True)
    # A valid tagged MP3 with the same filename but conflicting embedded artist.
    from mutagen.mp3 import MP3
    import subprocess
    audio = tmp_path/'silence.mp3'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t','0.1','-q:a','9',str(audio)], check=True)
    import shutil
    shutil.copyfile(audio, legacy)
    mp3 = MP3(str(legacy))
    from mutagen.id3 import TIT2, TPE1, TALB, TPE2
    mp3.tags.add(TIT2(encoding=3,text='Actual title'))
    mp3.tags.add(TPE1(encoding=3,text='Wrong artist'))
    mp3.tags.add(TPE2(encoding=3,text='Fred again..'))
    mp3.tags.add(TALB(encoding=3,text='Actual album'))
    mp3.save(str(legacy))
    original = legacy.read_bytes()
    assert d.existing_filename_for(song) is None
    assert legacy.read_bytes() == original


def test_legacy_sanitized_artist_folder_is_not_looked_up(tmp_path):
    d = Downloader(tmp_path/'downloads', output_template=FULL, folder_structure=True,
                   playlist_use_library=True, overwrite_existing_files=False)
    song = {**SONG, 'album_artist': 'Fred again..', 'artists': ['Fred again..']}
    legacy = tmp_path/'downloads'/'Fred again'/'Fred again - Dark Lane Demo Tapes (2020)'/'09. Fred again - D4L.mp3'
    legacy.parent.mkdir(parents=True)
    from mutagen.mp3 import MP3
    from mutagen.id3 import TIT2, TPE1, TALB, TPE2
    import subprocess, shutil
    audio = tmp_path/'silence.mp3'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t','0.1','-q:a','9',str(audio)], check=True)
    shutil.copyfile(audio, legacy)
    mp3 = MP3(str(legacy))
    mp3.tags.add(TIT2(encoding=3,text='D4L'))
    mp3.tags.add(TPE1(encoding=3,text='Fred again..'))
    mp3.tags.add(TPE2(encoding=3,text='Fred again..'))
    mp3.tags.add(TALB(encoding=3,text='Dark Lane Demo Tapes'))
    mp3.save(str(legacy))
    original = legacy.read_bytes()
    assert d.existing_filename_for(song) is None
    assert legacy.read_bytes() == original


def test_legacy_sanitized_artist_filename_is_not_looked_up_in_playlist_destination(tmp_path):
    d = Downloader(tmp_path/'downloads', output_template=FULL, folder_structure=True,
                   playlist_use_library=False, overwrite_existing_files=False)
    song = {**SONG, 'album_artist': 'Fred again..', 'artists': ['Fred again..']}
    legacy = tmp_path/'downloads'/'My Playlist'/'Fred again - D4L.mp3'
    legacy.parent.mkdir(parents=True)
    from mutagen.mp3 import MP3
    from mutagen.id3 import TIT2, TPE1
    import subprocess, shutil
    audio = tmp_path/'silence.mp3'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','anullsrc=r=44100:cl=stereo','-t','0.1','-q:a','9',str(audio)], check=True)
    shutil.copyfile(audio, legacy)
    mp3 = MP3(str(legacy))
    mp3.tags.add(TIT2(encoding=3,text='D4L'))
    mp3.tags.add(TPE1(encoding=3,text='Fred again..'))
    mp3.save(str(legacy))
    original = legacy.read_bytes()
    assert d.existing_filename_for(song, 'My Playlist') is None
    assert legacy.read_bytes() == original


def test_corrected_destination_wins_over_legacy_copy(tmp_path):
    d = Downloader(tmp_path/'downloads', output_template=FULL, folder_structure=True,
                   playlist_use_library=True, overwrite_existing_files=False)
    song = {**SONG, 'album_artist': 'Fred again..', 'artists': ['Fred again..']}
    for folder, basename in [('Fred again', 'Fred again'), ('Fred again..', 'Fred again..')]:
        target = tmp_path/'downloads'/folder/f'{basename} - Dark Lane Demo Tapes (2020)'/f'09. {basename} - D4L.mp3'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(folder.encode())
    assert d.existing_filename_for(song) == 'Fred again../Fred again.. - Dark Lane Demo Tapes (2020)/09. Fred again.. - D4L.mp3'


def test_indexed_playlist_copy_does_not_satisfy_album_request(tmp_path):
    d,index,old=setup_playlist(tmp_path)
    assert resolve_existing_download(d,SONG,track_index=index) is None
    assert index.lookup_song(SONG)=='My Playlist/Future, Drake, Young Thug - D4L.mp3'
    assert old.is_file()


def test_same_destination_is_still_skipped(tmp_path):
    d,index,old=setup_playlist(tmp_path)
    result=resolve_existing_download(d,SONG,subdir='My Playlist',track_index=index)
    assert result and result[0]=='My Playlist/Future, Drake, Young Thug - D4L.mp3'


def test_flat_root_does_not_scan_other_playlist_folders(tmp_path):
    d,index,old=setup_playlist(tmp_path,structured=False)
    assert d.find_existing_download(SONG) is None
    assert resolve_existing_download(d,SONG,track_index=index) is None


def test_second_playlist_requires_its_own_copy(tmp_path):
    d,index,old=setup_playlist(tmp_path)
    assert resolve_existing_download(d,SONG,subdir='Another Playlist',track_index=index) is None


def test_completed_playlist_job_does_not_satisfy_album_request(tmp_path, monkeypatch):
    import asyncio
    from downtify import api
    d,index,old=setup_playlist(tmp_path)
    song_id=SONG['song_id']
    monkeypatch.setattr(api.state,'downloader',d)
    monkeypatch.setattr(api.state,'loop',None)
    monkeypatch.setattr(api.state,'download_jobs',{song_id:{'status':'done','filename':'My Playlist/'+old.name,'user_ids':set()}})
    calls=[]
    async def run(*args,**kwargs):
        calls.append(kwargs.get('subdir'))
        return 'new-album-copy.mp3'
    monkeypatch.setattr(api,'_run_download_locked',run)
    assert asyncio.run(api._run_download(SONG,song_id))=='new-album-copy.mp3'
    assert calls==[None]


def test_library_lookup_reports_destination_without_hiding_other_copy(tmp_path, monkeypatch):
    import asyncio
    from downtify import api
    d,index,old=setup_playlist(tmp_path)
    monkeypatch.setattr(api.state,'downloader',d)
    monkeypatch.setattr(api,'allowed_entry_keys',lambda request:None)
    monkeypatch.setattr(api,'lookup_library_songs',lambda *args,**kwargs:[])
    monkeypatch.setattr(api,'filter_paths_for_request',lambda paths,request:paths)
    class Request:
        async def json(self):
            return {'songs':[SONG],'destination_status':True}
    result=asyncio.run(api.library_lookup(Request()))
    assert result['tracks']==[]
    assert result['destinations'][0]['exists'] is False
    assert result['destinations'][0]['stem'].startswith('Drake/')


def test_destination_status_reports_missing_album_despite_playlist_copy(tmp_path):
    from downtify.download_destination import destination_status
    d,index,old=setup_playlist(tmp_path)
    album=destination_status(d,SONG)
    playlist=destination_status(d,SONG,'My Playlist')
    assert album['exists'] is False
    assert album['stem']=='Drake/Drake - Dark Lane Demo Tapes (2020)/09. Future, Drake, Young Thug - D4L'
    assert playlist['exists'] is True
    assert playlist['file']=='My Playlist/Future, Drake, Young Thug - D4L.mp3'
