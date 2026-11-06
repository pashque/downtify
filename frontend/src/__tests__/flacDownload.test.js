import { afterEach, expect, it, vi } from 'vitest'
const f = vi.hoisted(() => ({
  api: { downloadBatch: vi.fn(async () => ({})), getQueue: vi.fn(async () => ({ data: [] })), onMessage: vi.fn() },
  settings: { audio_format: 'mp3', overwrite: false },
}))
vi.mock('/src/model/api', () => ({ default: f.api }))
vi.mock('/src/model/settings', () => ({ useSettingsManager: () => ({ settings: { value: f.settings } }) }))
import { useDownloadManager } from '../model/download'
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers() })
it('sends a request-scoped FLAC override without changing settings or the source songs', async () => {
  vi.useFakeTimers()
  const song = { song_id: 'flac-one', name: 'One' }
  const before = { ...f.settings }
  await useDownloadManager().fromSongs([song], { audioFormat: 'flac', destination: 'album' })
  expect(f.api.downloadBatch).toHaveBeenLastCalledWith(expect.objectContaining({ audioFormat: 'flac' }))
  expect(f.api.downloadBatch.mock.lastCall[0].songs[0]).toMatchObject({ downtify_destination: 'album', downtify_download_mode: 'missing' })
  expect(song).toEqual({ song_id: 'flac-one', name: 'One' })
  expect(f.settings).toEqual(before)
  await useDownloadManager().fromSongs([song])
  expect(f.api.downloadBatch.mock.lastCall[0]).not.toHaveProperty('audioFormat')
})
