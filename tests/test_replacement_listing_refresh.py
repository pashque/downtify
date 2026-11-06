"""Replacement preserves Added, but must not preserve old listing metadata."""
from types import SimpleNamespace
from downtify import api, library_paths_cache as cache
from downtify.library_catalog import LibraryContext


def test_replacement_drops_ram_and_persisted_track_snapshots(tmp_path, monkeypatch):
    ctx=LibraryContext(download_dir=tmp_path)
    key=cache._cache_key(ctx)
    old=[{'file':'one.mp3','duration':247.73}]
    class Store:
        cleared=False
        def clear(self):self.cleared=True
        def load(self,key):
            return None if self.cleared else {'fingerprint':'old','paths':[],'entries':old}
    store=Store()
    monkeypatch.setattr(cache,'_STORE',store)
    monkeypatch.setattr(cache,'_ENTRIES_CACHE',{key:('old',old)})
    monkeypatch.setattr(cache,'_PATH_CACHE',{})
    monkeypatch.setattr(cache,'_REFRESH_FN',None)
    monkeypatch.setattr(api.state,'metadata_cache',None)
    monkeypatch.setattr(api.state,'track_index',None)
    monkeypatch.setattr(api.state,'track_owners',None)
    assert cache.peek_cached_track_entries(ctx)[0]['duration']==247.73
    api._after_replacement('one.mp3',tmp_path/'one.mp3')
    assert cache.peek_cached_track_entries(ctx) is None
    assert store.cleared
