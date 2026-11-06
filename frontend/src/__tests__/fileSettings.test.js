import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

const { setSettings } = vi.hoisted(() => ({ setSettings: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: { setSettings } }))
vi.mock('/src/model/auth', () => ({
  useAuth: () => ({ loaded: ref(false), isAdmin: ref(true) }),
}))
vi.mock('/src/i18n', () => ({ currentLocale: ref('en') }))

import { useSettingsManager } from '../model/settings.js'

const library =
  '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'
const flat = '{artists} - {title}.{output-ext}'
const sm = useSettingsManager()

beforeEach(async () => {
  sm.settings.value.folder_structure = null
  sm.settings.value.playlist_use_library = true
  await nextTick()
  sm.settings.value.output = 'custom'
  setSettings.mockImplementation(async (payload) => ({ data: { ...payload } }))
  setSettings.mockClear()
})

describe('managed file settings', () => {
  it.each([true, false])(
    'saves legacy organization flags disabled in managed mode %s',
    async (structured) => {
      sm.settings.value.folder_structure = structured
      sm.settings.value.organize_by_artist = true
      sm.settings.value.organize_by_album = true
      await sm.saveSettings()
      expect(setSettings.mock.calls[0][0]).toMatchObject({
        folder_structure: structured,
        playlist_use_library: true,
        organize_by_artist: false,
        organize_by_album: false,
      })
      expect(sm.dirty.value).toBe(false)
    }
  )

  it('keeps the global library template when playlists use their own folder', async () => {
    sm.settings.value.folder_structure = true
    sm.settings.value.output = 'custom'
    sm.settings.value.playlist_use_library = false
    await nextTick()
    expect(sm.settings.value.output).toBe(library)
  })

  it('keeps all audio flat regardless of the playlist switch when structure is off', async () => {
    sm.settings.value.folder_structure = false
    sm.settings.value.playlist_use_library = false
    await nextTick()
    expect(sm.settings.value.output).toBe(flat)
  })

  it('preserves custom templates when a saved object is loaded or discarded', async () => {
    sm.settings.value = {
      ...sm.settings.value,
      folder_structure: true,
      output: 'custom saved',
    }
    await nextTick()
    expect(sm.settings.value.output).toBe('custom saved')
    await sm.saveSettings()
    sm.settings.value.folder_structure = false
    sm.reset()
    expect(sm.settings.value.output).toBe('custom saved')
    expect(sm.settings.value.folder_structure).toBe(true)
  })

  it('preserves legacy settings until folder structure is explicitly selected', async () => {
    sm.settings.value.organize_by_artist = true
    await sm.saveSettings()
    expect(setSettings.mock.calls[0][0]).toMatchObject({
      folder_structure: null,
      organize_by_artist: true,
      output: 'custom',
    })
  })
  it('updates the template immediately when folder structure changes', async () => {
    sm.settings.value.folder_structure = true
    await nextTick()
    expect(sm.settings.value.output).toBe(library)
    sm.settings.value.folder_structure = false
    await nextTick()
    expect(sm.settings.value.output).toBe(flat)
  })
})
