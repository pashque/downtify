import { afterEach, expect, it, vi } from 'vitest'
const api = vi.hoisted(() => ({ downloadBatch: vi.fn(async () => ({})), getQueue: vi.fn(async () => ({ data: [] })), onMessage: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: api }))
vi.mock('/src/model/settings', () => ({ useSettingsManager: () => ({ settings: { value: {} } }) }))
import { useDownloadManager } from '../model/download'
afterEach(() => { vi.clearAllTimers(); vi.useRealTimers() })
it('forces only explicit album batches without modifying original songs or playlist batches', async () => {
  vi.useFakeTimers()
  const song = { song_id: 'a', name: 'Track', downtify_playlist_name: 'Origin' }
  await useDownloadManager().fromSongs([song], { destination: 'album' })
  expect(api.downloadBatch.mock.calls[0][0].songs[0]).toMatchObject({ downtify_destination: 'album', downtify_download_mode: 'missing' })
  expect(song).not.toHaveProperty('downtify_destination')
  await useDownloadManager().fromSongs([song], { playlistName: 'Origin' })
  expect(api.downloadBatch.mock.calls[1][0].songs[0]).not.toHaveProperty('downtify_destination')
})
