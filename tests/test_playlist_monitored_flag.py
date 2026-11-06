"""Added-column monitor status is authoritative, not inferred from batches."""
from types import SimpleNamespace
import pytest
from downtify import api
SID='A'*22

@pytest.mark.parametrize(('scope','kind','source','expected'),[
 (None,'playlist','spotify',True),(None,'artist','spotify',False),
 (None,'playlist','ytmusic',False),(7,'playlist','spotify',False),
])
def test_batch_reports_expose_real_monitor_status(monkeypatch,scope,kind,source,expected):
 monkeypatch.setattr(api.state,'downloader',object())
 monkeypatch.setattr(api.state,'track_index',object())
 def watches():
  assert scope is None,'Non-admin reports must not read admin monitor state'
  return [SimpleNamespace(kind=kind,source=source,spotify_id=SID)]
 monkeypatch.setattr(api.state,'monitor_db',SimpleNamespace(list_playlists=watches))
 monkeypatch.setattr(api,'_known_spotify_playlist_sources',lambda user_id:{SID:{'playlist_name':'Source','playlist_url':'https://open.spotify.com/playlist/'+SID}})
 monkeypatch.setattr(api,'_library_snapshot',lambda:None)
 report=lambda sid,name,url,**kw:{'spotify_playlist_id':sid,'playlist_name':name,'status':'complete'}
 monkeypatch.setattr(api,'_playlist_batch_summary',report)
 monkeypatch.setattr(api,'_playlist_completeness_report',report)
 assert api._build_playlist_batch_reports(user_id=scope)[0].get('monitored') is expected
 assert api._report_for_spotify_playlist(SID,user_id=scope).get('monitored') is expected
 assert api._report_for_spotify_playlist(SID,user_id=scope,mode='spotify').get('monitored') is expected
