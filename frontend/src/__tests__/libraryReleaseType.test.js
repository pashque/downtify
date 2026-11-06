import { expect, it } from 'vitest'
import { groupAlbums, normalizeTrack } from '../lib/library'
it('preserves authoritative release types through normalized tracks and grouped albums without guessing from count', () => {
  const ep = normalizeTrack({ file: 'x.mp3', artist: 'A', album_artist: 'A', album: 'X', release_type: 'ep' })
  expect(ep.release_type).toBe('ep')
  expect(groupAlbums([ep])[0].release_type).toBe('ep')
  expect(groupAlbums([normalizeTrack({ file: 'y.mp3', artist: 'B', album: 'Y' })])[0].release_type).toBe('')
})
