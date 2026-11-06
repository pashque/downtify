import { expect, it, vi } from 'vitest'
import { normalizeTrack } from '../lib/library'

vi.mock('/src/model/api', () => ({ default: { onMessage: vi.fn() } }))
vi.mock('/src/model/player', () => ({ usePlayer: () => ({}) }))
import { useLibrary } from '../model/library'

it('keeps library presence and lookup aligned on full structured lead artists', () => {
  const library = useLibrary()
  const collaboration = normalizeTrack({
    file: 'collab.mp3', title: 'ST. CHROMA',
    artist: 'Tyler, The Creator, Daniel Caesar',
    artists: ['Tyler, The Creator', 'Daniel Caesar'],
  })
  library.tracks.value = [collaboration]
  expect(library.hasSong('Tyler, The Creator', 'ST. CHROMA')).toBe(true)
  expect(library.hasSong(['Tyler, The Creator', 'Daniel Caesar'], 'ST. CHROMA')).toBe(true)
  expect(library.findTrack('Tyler, The Creator', 'ST. CHROMA')).toBe(collaboration)
  expect(library.hasSong('Tyler', 'ST. CHROMA')).toBe(false)
  expect(library.findTrack('Tyler', 'ST. CHROMA')).toBeNull()
})
