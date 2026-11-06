import { beforeEach, expect, it, vi } from 'vitest'
import { effectScope, nextTick, reactive, ref } from 'vue'
const f = vi.hoisted(() => ({ source: vi.fn(), lookup: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: { getLibraryAlbumSource: f.source, lookupLibrarySongs: vi.fn() } }))
vi.mock('/src/model/library', () => ({ useLibrary: () => ({ lookupSongs: f.lookup }) }))
vi.mock('/src/model/download', () => ({ useProgressTracker: () => ({ queueVersion: ref(0), getBySong: () => null }) }))
import { useAlbumSource } from '../model/albumSource'
const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); await nextTick() }
const editions = [{ id: 'D'.repeat(22), track_count: 22, explicit: true }, { id: 'S'.repeat(22), track_count: 16, explicit: true }]
const reply = (id, n) => ({ data: { status: 'resolved', edition: id, editions, url: 'u', tracks: Array.from({ length: n }, (_, i) => ({ song_id: `${id[0]}${i}`, name: `T${i}`, artists: ['A'] })) } })
beforeEach(() => {
  vi.clearAllMocks(); f.lookup.mockResolvedValue([])
  f.source.mockImplementation(async (a, t, e) => (e === 'S'.repeat(22) ? reply(e, 16) : reply('D'.repeat(22), 22)))
})

it('offers every verified version and switches the tracklist to the chosen one', async () => {
  const route = reactive({ query: { artist: 'Future', title: 'I NEVER LIKED YOU' } })
  const scope = effectScope(); let m
  scope.run(() => { m = useAlbumSource(route) })
  await flush()
  expect(f.source).toHaveBeenLastCalledWith('Future', 'I NEVER LIKED YOU')
  expect(m.editions.value.map((e) => e.track_count)).toEqual([22, 16])
  expect(m.edition.value).toBe('D'.repeat(22)); expect(m.songs.value).toHaveLength(22)
  m.selectEdition('S'.repeat(22)); await flush()
  expect(f.source).toHaveBeenLastCalledWith('Future', 'I NEVER LIKED YOU', 'S'.repeat(22))
  expect(m.edition.value).toBe('S'.repeat(22)); expect(m.songs.value).toHaveLength(16)
  // Opening another album starts again from that album's default version.
  route.query = { artist: 'Drake', title: 'Her Loss' }; await flush()
  expect(f.source).toHaveBeenLastCalledWith('Drake', 'Her Loss')
  scope.stop()
})

it('presents identical releases once without replacing an explicitly selected ID', async () => {
  const tracks = [{ name: 'One', artists: ['A'], duration: 200, explicit: true }]
  const twins = ['A'.repeat(22), 'B'.repeat(22)].map(id => ({ id, title: 'Album', track_count: 1, explicit: true, tracks }))
  f.source.mockImplementation(async (a, t, id) => ({ data: { status: 'resolved', edition: id, editions: twins, tracks: [{ ...tracks[0], song_id: id }] } }))
  const scope = effectScope(); let model
  scope.run(() => { model = useAlbumSource(reactive({ query: { artist: 'A', title: 'Album', edition: twins[1].id } })) })
  await flush()
  expect(model.editions.value).toHaveLength(1)
  expect(model.editions.value[0].id).toBe(twins[1].id)
  expect(model.edition.value).toBe(twins[1].id)
  expect(model.songs.value[0].song_id).toBe(twins[1].id)
  expect(f.source).toHaveBeenLastCalledWith('A', 'Album', twins[1].id)
  scope.stop()
})
