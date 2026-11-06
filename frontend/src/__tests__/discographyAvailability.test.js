import { expect, it, vi } from 'vitest'
import { inspectDiscography, discographySections } from '../lib/discography'
import { readFileSync } from 'node:fs'

const labels = { albums: 'Albums', singles: 'Singles' }
const release = (album_id, name = 'CHROMAKOPIA') => ({ album_id, name, artist: 'Tyler, The Creator', year: '2024', release_type: 'Album', url: `https://open.spotify.com/album/${album_id}` })
const tracks = (id, explicit = true) => [1, 2].map(n => ({ song_id: `${id}-${n}`, name: `Song ${n}`, artists: ['Tyler, The Creator'], duration: id === 'partial' ? 181 : id === 'removed' ? 182 : 180, explicit, track_number: n, album_name: 'CHROMAKOPIA' }))
const local = [{ artist: 'Tyler, The Creator', title: 'CHROMAKOPIA', tracks: [{ file: 'stale.mp3' }] }]

it('hides only fully physically present sources, not partial, removed or same-title other editions', async () => {
  const releases = ['full', 'partial', 'removed', 'clean'].map(id => release(id))
  const resolveUrl = vi.fn(async url => ({ data: { tracks: tracks(url.split('/').pop(), !url.endsWith('clean')) } }))
  const lookupLibraryLocations = vi.fn(async songs => ({ data: { locations: songs.map(s => ({ key: s.song_id, downloaded: s.song_id.startsWith('full') || s.song_id === 'partial-1' })) } }))
  const inspected = await inspectDiscography(releases, local, { resolveUrl, lookupLibraryLocations })
  expect(inspected.find(r => r.album_id === 'full').physicallyComplete).toBe(true)
  expect(inspected.find(r => r.album_id === 'partial').physicallyComplete).toBe(false)
  expect(inspected.find(r => r.album_id === 'removed').physicallyComplete).toBe(false)
  expect(discographySections(inspected, local, labels).flatMap(g => g.items.map(r => r.album_id))).toEqual(['partial', 'removed', 'clean'])
})

it('collapses proven duplicate editions retaining aliases, but keeps explicit/clean, deluxe and punctuation', async () => {
  const releases = [release('a'), release('b'), release('clean'), release('plus', 'CHROMAKOPIA +'), release('deluxe', 'CHROMAKOPIA (Deluxe)')]
  const inspected = await inspectDiscography(releases, [], {
    resolveUrl: async url => ({ data: { tracks: tracks(url.split('/').pop(), !url.endsWith('clean')) } }),
    lookupLibraryLocations: async songs => ({ data: { locations: songs.map(s => ({ key: s.song_id, downloaded: false })) } }),
  })
  const items = discographySections(inspected, [], labels).flatMap(g => g.items)
  expect(items.map(r => r.album_id)).toEqual(['a', 'clean', 'plus', 'deluxe'])
  expect(items[0].duplicateIds).toEqual(['a', 'b'])
})

it('never hides a release when the provider supplied only a truncated tracklist', async () => {
  const inspected = await inspectDiscography([release('a')], local, {
    resolveUrl: async () => ({ data: { tracks: tracks('a').map(t => ({ ...t, album_track_total: 13 })) } }),
    lookupLibraryLocations: async songs => ({ data: { locations: songs.map(s => ({ key: s.song_id, downloaded: true })) } }),
  })
  expect(inspected[0].physicallyComplete).toBe(false)
})

it('real Mall Grab editions collapse to one partial release, keeping the exact first URL and both IDs', async () => {
  const fixtures = JSON.parse(readFileSync(new URL('./fixtures/mall-grab-discography.json', import.meta.url), 'utf8'))
  const releases = fixtures.map(f => ({ album_id: f.id, name: f.data.name, artist: f.data.subtitle, year: f.data.year, release_type: f.data.release_type, url: `https://open.spotify.com/album/${f.id}` }))
  const inspected = await inspectDiscography(releases, [{ title: 'What I Breathe', artist: 'Mall Grab' }], {
    resolveUrl: async url => ({ data: { tracks: fixtures.find(f => url.endsWith(f.id)).tracks } }),
    lookupLibraryLocations: async songs => ({ data: { locations: fixtures.find(f => f.tracks[0].song_id === songs[0].song_id).locations } }),
  })
  const items = discographySections(inspected, [], labels)[0].items
  expect(items).toHaveLength(1)
  expect(items[0].duplicateIds).toEqual(fixtures.map(f => f.id))
  expect(items[0].url).toBe(releases[0].url)
  expect(items[0].physicallyComplete).toBe(false)
})

it('rechecks physical availability even when the cached local catalog still contains removed files', async () => {
  let downloaded = true
  const api = {
    resolveUrl: async () => ({ data: { tracks: tracks('a') } }),
    lookupLibraryLocations: async songs => ({ data: { locations: songs.map(s => ({ key: s.song_id, downloaded })) } }),
  }
  expect(discographySections(await inspectDiscography([release('a')], local, api), local, labels)).toEqual([])
  downloaded = false
  expect(discographySections(await inspectDiscography([release('a')], local, api), local, labels)[0].items).toHaveLength(1)
})

it('uses bounded batches and fails open when physical status is unavailable', async () => {
  const many = Array.from({ length: 205 }, (_, n) => ({ ...tracks('a')[0], song_id: String(n) }))
  const lookup = vi.fn(async songs => ({ data: { locations: songs.map(s => ({ key: s.song_id, downloaded: true })) } }))
  const api = { resolveUrl: async () => ({ data: { tracks: many } }), lookupLibraryLocations: lookup }
  expect((await inspectDiscography([release('a')], local, api))[0].physicallyComplete).toBe(true)
  expect(lookup.mock.calls.map(c => c[0].length)).toEqual([100, 100, 5])
  lookup.mockRejectedValue(new Error('offline'))
  expect((await inspectDiscography([release('a')], local, api))[0].physicallyComplete).toBe(false)
})
