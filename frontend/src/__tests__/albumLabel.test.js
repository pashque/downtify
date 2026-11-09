import { expect, it } from 'vitest'
import { spotifyAlbumId, useAlbumLabel } from '/src/lib/albumLabel'

it('only accepts exact Spotify album identifiers and canonical album URLs', () => {
  const id = '0eyTz4axCv1nyRSCHxDNY0'
  expect(spotifyAlbumId(id)).toBe(id)
  expect(spotifyAlbumId(`https://open.spotify.com/album/${id}?si=x`)).toBe(id)
  expect(spotifyAlbumId(`https://evil.test/album/${id}`)).toBe('')
  expect(spotifyAlbumId('bad')).toBe('')
})
it('clears old labels immediately and rejects stale responses', async () => {
  let resolve
  const first = new Promise((r) => {
    resolve = r
  })
  const state = useAlbumLabel((id) =>
    id === 'a' ? first : Promise.resolve({ label: 'New Label' })
  )
  const old = state.load('a')
  await state.load('b')
  resolve({ label: 'Old Label' })
  await old
  expect(state.label.value).toBe('New Label')
  const pending = state.load('a')
  expect(state.label.value).toBe('')
  await pending
})
it('omits failed or unknown metadata, never using a fallback company', async () => {
  const state = useAlbumLabel(async () => {
    throw new Error('unavailable')
  })
  await state.load('a')
  expect(state.label.value).toBe('')
})
