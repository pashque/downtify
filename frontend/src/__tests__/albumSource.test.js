import { beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope, nextTick, reactive, ref } from 'vue'
const f = vi.hoisted(() => ({ source: vi.fn(), lookup: vi.fn(), globalLookup: vi.fn(), getBySong: vi.fn(), version: null }))
vi.mock('/src/model/api', () => ({ default: { getLibraryAlbumSource: f.source, lookupLibrarySongs: f.lookup } }))
vi.mock('/src/model/library', () => ({ useLibrary: () => ({ lookupSongs: f.globalLookup }) }))
vi.mock('/src/model/download', () => ({ useProgressTracker: () => ({ queueVersion: f.version, getBySong: f.getBySong }) }))
import { useAlbumSource, useAlbumDestination } from '../model/albumSource'
import { albumRoute } from '../lib/albumRouting'
const flush = async () => { for(let i=0;i<8;i++) await Promise.resolve(); await nextTick() }
const song = { song_id: 'one', name: 'One', artists: ['Guest'], album_name: 'Album' }
beforeEach(() => { vi.clearAllMocks(); f.version = ref(0); f.source.mockResolvedValue({ data: { status: 'resolved', tracks: [song], url: 'https://source/album' } }); f.globalLookup.mockResolvedValue([]); f.lookup.mockResolvedValue({ data: { tracks: [], destinations: [{ key:'one', stem:'Artist/Album/One', exists:false, file:null }] } }); f.getBySong.mockReturnValue(null) })
describe('native album source and target state', () => {
  it('resolves once per scalar album identity, globally looks up badges and forces only origin-free rows', async () => {
    const route = reactive({ query: { artist:'Artist', title:'Album' } })
    const scope = effectScope(); let model
    scope.run(() => { model = useAlbumSource(route) })
    await flush()
    expect(f.source).toHaveBeenCalledWith('Artist', 'Album')
    expect(f.globalLookup).toHaveBeenCalledWith([expect.objectContaining({ song_id:'one' })])
    expect(model.songs.value[0]).toMatchObject({ downtify_destination:'album' })
    route.query.playlist = 'Chosen'; route.query.playlistUrl = 'https://source/playlist'; await flush()
    expect(f.source).toHaveBeenCalledTimes(1)
    expect(model.songs.value[0]).toMatchObject({ downtify_playlist_name:'Chosen', downtify_playlist_url:'https://source/playlist' })
    expect(model.songs.value[0]).not.toHaveProperty('downtify_destination')
    scope.stop()
  })
  it('silently yields null for unavailable or failed exact source', async () => {
    f.source.mockResolvedValue({ data: { status:'unavailable', tracks:[] } })
    const scope = effectScope(); let model
    scope.run(() => { model = useAlbumSource(reactive({ query: { artist:'Artist', title:'Album' } })) })
    await flush(); expect(model.songs.value).toBe(null); scope.stop()
  })
  it('keeps target presence separate from global rows and observes completed queue filenames', async () => {
    const songs = ref([song]); const scope = effectScope(); let model
    scope.run(() => { model = useAlbumDestination(songs) }); await flush()
    expect(f.lookup).toHaveBeenCalledWith([expect.objectContaining({ song_id:'one', downtify_destination:'album' })], { destination_status:true, destination:'album' })
    expect(songs.value[0]).not.toHaveProperty('downtify_destination_exists')
    expect(model.missing.value).toHaveLength(1)
    f.getBySong.mockReturnValue({ state:'done', filename:'Playlist/One.mp3' }); f.version.value++; await nextTick()
    expect(model.missing.value).toHaveLength(1)
    f.getBySong.mockReturnValue({ state:'done', filename:'Artist/Album/One.mp3' }); f.version.value++; await nextTick()
    expect(model.missing.value).toHaveLength(0)
    expect(f.lookup).toHaveBeenCalledTimes(1); scope.stop()
  })
  it('carries a known source playlist URL from native playlist context without looking for another playlist', () => {
    expect(albumRoute({albumArtist:'Artist',album:'Album'},{type:'playlist',title:'Chosen',playlistUrl:'https://source/known'}).query).toMatchObject({playlist:'Chosen',playlistUrl:'https://source/known'})
  })
  it('adds origin only to an existing album link opened from a specific playlist row', () => {
    const track = { albumArtist:'Artist', album:'Album' }
    expect(albumRoute(track,{type:'playlist',title:'Chosen',route:{query:{url:'known'}}})).toEqual({name:'Album',query:{artist:'Artist',title:'Album',playlist:'Chosen',playlistUrl:'known'}})
    expect(albumRoute(track,{type:'album',title:'Other'}).query).toEqual({artist:'Artist',title:'Album'})
  })
})
