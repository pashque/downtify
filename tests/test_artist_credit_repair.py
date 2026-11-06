import hashlib
from pathlib import Path
import pytest
from mutagen.id3 import ID3, TIT2, TPE1, TXXX
from downtify.artist_credit_repair import prepare, apply_file, source_credits
from downtify.playlist_spotify_cache import PlaylistSpotifyCache


def data_file(tmp_path):
    path=tmp_path/'song.mp3'
    tags=ID3(); tags.add(TIT2(encoding=3,text='Song'));tags.add(TPE1(encoding=3,text='Tyler, The Creator'))
    tags.add(TXXX(encoding=3,desc='ARTISTS',text=['Tyler','The Creator']))
    tags.save(path,v2_version=4);path.write_bytes(path.read_bytes()+b'audio payload')
    return path


def test_repair_is_only_artist_list_and_preserves_file_identity(tmp_path):
    p=data_file(tmp_path);old=p.read_bytes();st=p.stat();tag_size=ID3(p).size
    backup=tmp_path/'backups'/'original.mp3'
    apply_file(p,['Tyler','The Creator'],['Tyler, The Creator'],hashlib.sha256(old).hexdigest(),backup)
    new=p.read_bytes()
    assert len(old)==len(new) and old[tag_size:]==new[tag_size:]
    assert p.stat().st_mtime_ns==st.st_mtime_ns
    assert backup.read_bytes()==old
    tags=ID3(p)
    assert tags['TXXX:ARTISTS'].text==['Tyler, The Creator']
    assert tags['TPE1'].text==['Tyler, The Creator']


def test_repair_rejects_changed_credit_or_changed_file(tmp_path):
    p=data_file(tmp_path);old=p.read_bytes()
    with pytest.raises(ValueError): prepare(old,['Tyler','The Creator'],['Someone'])
    with pytest.raises(ValueError): prepare(old,['Wrong'],['Wrong'])
    with pytest.raises(ValueError): apply_file(p,['Tyler','The Creator'],['Tyler, The Creator'],'wrong',tmp_path/'backup')
    assert p.read_bytes()==old


def test_exact_cached_track_restores_missing_album_row_boundaries(tmp_path):
    cache=PlaylistSpotifyCache(tmp_path/'db.sqlite')
    cache.store_track('T'*22,dict(song_id='T'*22,name='Song',artists=['A$AP Rocky','Tokischa']))
    rows=[dict(song_id='T'*22,name='Song',artists=['A$AP Rocky, Tokischa'])]
    assert source_credits(rows,cache)[0]['artists']==['A$AP Rocky','Tokischa']
    assert rows[0]['artists']==['A$AP Rocky, Tokischa']
    assert source_credits([{**rows[0],'name':'Different'}],cache)[0]['artists']==rows[0]['artists']


def test_endpoint_dry_run_apply_and_admin_boundary(tmp_path, monkeypatch):
    import asyncio
    from fastapi import HTTPException
    from downtify import api
    p=data_file(tmp_path);old=p.read_bytes()
    payload={'items':[dict(file='song.mp3',before=['Tyler','The Creator'],after=['Tyler, The Creator'],sha_before=hashlib.sha256(old).hexdigest())]}
    async def body(request): return payload
    monkeypatch.setattr(api,'_json_object',body)
    monkeypatch.setattr(api,'request_is_admin',lambda request:False)
    with pytest.raises(HTTPException) as err:
        asyncio.run(api.library_artist_credit_repair(None))
    assert err.value.status_code==403
    monkeypatch.setattr(api,'request_is_admin',lambda request:True)
    monkeypatch.setattr(api,'library_context',lambda:object())
    monkeypatch.setattr(api,'resolve_library_file',lambda stored,ctx:p if stored=='song.mp3' else None)
    monkeypatch.setattr(api,'merge_library_listing_file',lambda *args:None)
    monkeypatch.setattr(api.state,'settings_path',str(tmp_path/'settings.json'))
    monkeypatch.setattr(api.state,'metadata_cache',None)
    monkeypatch.setattr(api.state,'playlist_spotify_cache',None)
    result=asyncio.run(api.library_artist_credit_repair(None))
    assert result['dry_run'] and result['candidates']==1 and p.read_bytes()==old
    payload['dry_run']=False
    result=asyncio.run(api.library_artist_credit_repair(None))
    assert result['changed']==1 and (Path(result['backup'])/'0.mp3').read_bytes()==old
    assert ID3(p)['TXXX:ARTISTS'].text==['Tyler, The Creator']

