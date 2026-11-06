import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import en from '../i18n/locales/en.js'

const view = readFileSync(new URL('../views/SettingsView.vue', import.meta.url), 'utf8')
describe('3.7 settings migration boundaries', () => {
  it('uses the approved editor without removing 3.7 settings', () => {
    expect(view).toContain('<FileDestinationSettings :settings="s" />')
    expect(view).not.toContain('v-model.trim="s.output"')
    expect(view).not.toContain('v-model="s.organize_by_artist"')
    expect(view).not.toContain('v-model="s.organize_by_album"')
    expect(view).toContain('<HiddenLibrarySettings />')
    expect(view).toContain('v-model="s.allow_playlist_sharing"')
    expect(view).toContain('v-model="account.showPublicPlaylists.value"')
    expect(view).toContain('s.value.output = defaultOutput(s.value)')
  })
  it('has state-specific storage descriptions and preserves 3.7 text', () => {
    expect(en.settings.folderStructure).toBe('Folder structure')
    expect(en.settings.playlistUseLibrary).toBe('Playlists')
    expect(en.settings.playlistFolderHint).toBe('Save playlist audio inside its own playlist folder.')
    expect(en.settings.allowPlaylistSharing).toBeTruthy()
    expect(en.sharing).toBeTruthy()
    expect(en.visibility).toBeTruthy()
  })
})
