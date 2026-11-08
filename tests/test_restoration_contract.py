"""Guard newly approved album expansion: reuse native rows/controls only."""
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_playlist_approved_toolbar_keeps_native_actions():
    text = (ROOT / 'frontend/src/views/PlaylistView.vue').read_text()
    template = text.split('<script setup>')[0]
    actions = template.split('<template #actions>', 1)[1].split('</template>', 1)[0]
    assert 'icon="zip"' not in actions
    assert '<TrackSortSelect' in actions
    assert '<PlayButton' in actions
    assert 'playlistActions.openShare' in actions
    assert '<UiMenu' in actions


def test_native_finder_template_unchanged():
    name = 'frontend/src/views/FinderBrowseView.vue'
    stock = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT, text=True)
    assert (ROOT / name).read_text().split('<script setup>')[0] == stock.split('<script setup>')[0]


def test_native_download_status_controls_preserved():
    # User approved plain gray symbols instead of the earlier round badge.
    text = (ROOT / 'frontend/src/components/search/DownloadState.vue').read_text()
    assert 'AppIcon' in text
    assert 'songDownloadState' in text
    assert "t('search.inLibrary')" in text
    assert '<UiProgress ' in text
    assert "t('queue.retry')" in text


@pytest.mark.parametrize('name', ['frontend/src/views/AlbumView.vue', 'frontend/src/views/LinkView.vue'])
def test_no_unapproved_album_panels_or_controls(name):
    text = (ROOT / name).read_text()
    for forbidden in ['AlbumSourcePanel', 'Full source album', 'Downloaded files', 'All tracks downloaded', 'Re-download all', 'Choose source album', 'Source album URL']:
        assert forbidden not in text


def test_historical_custom_source_panel_not_restored():
    assert not (ROOT / 'frontend/src/components/library/AlbumSourcePanel.vue').exists()
