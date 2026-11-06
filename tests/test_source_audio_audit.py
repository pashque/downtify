"""Probe native input without ever adding a conversion postprocessor."""
import shutil, subprocess
from pathlib import Path
import pytest
from downtify.source_audio_audit import audit_source


def test_raw_audit_uses_downloader_selection_and_auth_without_conversion(tmp_path, monkeypatch):
    from downtify import source_audio_audit as mod
    original=tmp_path/'input.m4a'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=duration=1','-c:a','aac','-b:a','96k',str(original)],check=True)
    used=[]
    class Downloader:
        def _ydl_options(self, template, hook):
            return {'outtmpl':template,'format':'bestaudio/best','cookiefile':'private-cookie-file'},True
    class YDL:
        def __init__(self,opts):self.opts=opts;used.append(opts)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def extract_info(self,url,download):
            assert download is True
            self.file=Path(self.opts['outtmpl'].replace('%(ext)s','m4a'))
            shutil.copyfile(original,self.file)
            return {'id':'6eD8eJeZ9F8','format_id':'140','ext':'m4a','acodec':'mp4a.40.2','abr':96}
        def prepare_filename(self,info):return str(self.file)
        def add_post_processor(self,*args,**kwargs):pytest.fail('must not convert source')
    monkeypatch.setattr(mod.yt_dlp,'YoutubeDL',YDL)
    result=audit_source(Downloader(),'6eD8eJeZ9F8',tmp_path/'audit')
    assert result['codec']=='aac'
    assert 70 < result['measured_audio_kbps'] < 120
    assert result['converted'] is False and result['cookies_used'] is True
    assert used[0]['format']=='bestaudio/best'
    assert used[0]['cookiefile']=='private-cookie-file'
    assert 'private-cookie-file' not in str(result)
    assert not list((tmp_path/'audit').glob('raw-*'))


def test_source_audit_endpoint_is_admin_only():
    from downtify.auth import classify,ADMIN
    assert classify('POST','/api/library/source-audio-audit')==ADMIN
