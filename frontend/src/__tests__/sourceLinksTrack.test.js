import { afterEach, expect, it, vi } from 'vitest'
import { openTrackOnSpotify } from '../lib/sourceLinks'

afterEach(() => vi.unstubAllGlobals())

it('opens the exact Spotify track page in a tab opened at click time', async () => {
  const tab = { location: { href: '' }, close: vi.fn() }
  vi.stubGlobal('window', { open: vi.fn(() => tab) })
  const lookup = vi.fn(async () => ({ data: { url: 'https://open.spotify.com/track/' + 'T'.repeat(22) } }))
  const url = await openTrackOnSpotify({ title: 'SWAT TEAM', artist: 'A$AP Rocky', album: "Don't Be Dumb" }, { lookup })
  expect(lookup).toHaveBeenCalledWith({ kind: 'track', artist: 'A$AP Rocky', title: 'SWAT TEAM', album: "Don't Be Dumb" })
  expect(tab.location.href).toBe(url)
  expect(url).toMatch(/^https:\/\/open\.spotify\.com\/track\//)
})

it('closes the tab and reports when there is no exact match (never a search page)', async () => {
  const tab = { location: { href: '' }, close: vi.fn() }
  vi.stubGlobal('window', { open: vi.fn(() => tab) })
  const onMissing = vi.fn()
  const url = await openTrackOnSpotify({ title: 'X', artist: 'Y' }, { lookup: async () => { throw new Error('404') }, onMissing })
  expect(url).toBe('')
  expect(tab.close).toHaveBeenCalled()
  expect(onMissing).toHaveBeenCalled()
})
