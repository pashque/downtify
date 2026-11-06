// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, ref } from 'vue'

vi.mock('/src/model/api', () => ({ default: {} }))
vi.mock('/src/model/auth', () => ({
  useAuth: () => ({ loaded: ref(false), isAdmin: ref(true) }),
}))
import { useSettingsManager } from '../model/settings.js'
import FileDestinationSettings from '../components/settings/FileDestinationSettings.vue'

const library =
  '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'
const flat = '{artists} - {title}.{output-ext}'
const folderOn = 'Save albums and individual tracks in Artist/Artist - Album folders.'
const folderOff = 'Save all audio flat in the shared downloads folder.'
const states = [
  [true, true, 'Playlist audio shares the artist/album library.'],
  [true, false, 'Save playlist audio inside its own separate folder.'],
  [false, true, 'Save playlist audio inside its own playlist folder.'],
  [false, false, 'Save playlist audio flat in the shared downloads folder.'],
]
let app
let root
function mount(structured, playlistLibrary) {
  const sm = useSettingsManager()
  sm.settings.value = {
    ...sm.settings.value,
    folder_structure: structured,
    playlist_use_library: playlistLibrary,
    output: structured ? library : flat,
  }
  root = document.createElement('div')
  document.body.append(root)
  app = createApp({
    render: () => h(FileDestinationSettings, { settings: sm.settings.value }),
  })
  app.mount(root)
  return sm
}
afterEach(() => {
  app?.unmount()
  root?.remove()
})

describe('file destination switches', () => {
  it('orders File name before Folder structure before Playlists', () => {
    mount(true, true)
    const labels = [...root.querySelectorAll('p.font-semibold')].map((p) => p.textContent)
    expect(labels).toEqual(['File name', 'Folder structure', 'Playlists'])
  })

  it.each([true, false])('resets the actual input to the canonical default for structure=%s', async (structured) => {
    const sm = mount(structured, true)
    const input = root.querySelector('input:not([role="switch"])')
    input.value = 'custom name'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await nextTick()
    expect(sm.settings.value.output).toBe('custom name')
    const reset = [...root.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Reset')
    reset.click()
    await nextTick()
    expect(sm.settings.value.output).toBe(structured ? library : flat)
    expect(input.value).toBe(structured ? library : flat)
    expect(root.querySelector('input:not([role="switch"])')).toBe(input)
  })

  it('retains a legacy warning only for a null folder setting', () => {
    mount(null, true)
    expect(root.querySelector('[role="status"]').textContent).toContain('Legacy folder settings are still active.')
  })

  it.each(states)(
    'shows only current descriptions for structure=%s playlists=%s',
    async (structured, playlistLibrary, description) => {
      const sm = mount(structured, playlistLibrary)
      const switches = root.querySelectorAll('input[role="switch"]')
      expect(switches).toHaveLength(2)
      expect(switches[1].getAttribute('aria-label')).toBe('Playlists')
      expect(switches[1].disabled).toBe(false)
      expect(root.textContent).toContain(structured ? folderOn : folderOff)
      expect(root.textContent).not.toContain(structured ? folderOff : folderOn)
      expect(root.textContent).toContain(description)
      for (const [, , other] of states) {
        if (other !== description) expect(root.textContent).not.toContain(other)
      }
      expect(root.querySelector('[role="status"]')).toBeNull()
      expect(root.textContent).not.toContain('Organize by artist')
      expect(root.textContent).not.toContain('Organize by album')
      sm.settings.value.output = 'custom'
      switches[1].click()
      await nextTick()
      expect(sm.settings.value.playlist_use_library).toBe(!playlistLibrary)
      expect(sm.settings.value.output).toBe(structured ? library : flat)
      expect(root.textContent).toContain(
        states.find(([s, p]) => s === structured && p === !playlistLibrary)[2]
      )
      switches[0].click()
      await nextTick()
      expect(sm.settings.value.folder_structure).toBe(!structured)
      expect(sm.settings.value.output).toBe(structured ? flat : library)
      expect(switches[1].disabled).toBe(false)
    }
  )
})
