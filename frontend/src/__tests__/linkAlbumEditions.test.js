import { expect, it, vi } from 'vitest'
import { computed, ref, reactive, watch, effectScope, nextTick } from 'vue'
import { readFileSync } from 'node:fs'
import { classifyInput } from '../lib/input'
import { groupAlbumEditions, albumEditionOptions } from '../lib/albumEditions'
const view = readFileSync(`${process.cwd()}/src/views/LinkView.vue`, 'utf8')
const A='A'.repeat(22), B='B'.repeat(22)
const url=id=>`https://open.spotify.com/album/${id}`
const flush=async()=>{for(let i=0;i<30;i++)await Promise.resolve();await nextTick()}
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve}}
function harness(initial=url(A)) {
 const route=reactive({query:{url:initial, origin:'keep'}})
 const API={resolveUrl:vi.fn(),getSpotifyAlbumEditions:vi.fn()}
 const library={lookupSongs:vi.fn(async()=>{})}
 const router={replace:vi.fn()}
 const scope=effectScope()
 // Evaluate only checked-in component source, never untrusted data.
 const code=view.slice(view.indexOf('const details ='),view.indexOf('const SOURCE_LABELS ='))
 let model
 scope.run(()=>model=new Function('ref','computed','watchValue','route','router','API','library','classifyInput','useLibraryLocations','useAlbumDestination','albumRowSong','groupAlbumEditions','albumEditionOptions','t',`${code};return {details,loading,error,selected,editionOptions,selectEdition,resolve}`)(ref,computed,watch,route,router,API,library,classifyInput,()=>({}),()=>({missing:ref([]),loaded:ref(true)}),s=>s,groupAlbumEditions,albumEditionOptions,k=>k))
 return {model,route,API,router,scope}
}
const data=name=>({data:{kind:'album',name,tracks:[{name}],albums:[]}})
it('offers genuine grouped editions without replacing the explicitly opened source',async()=>{
 expect(view).toContain('data-link-editions')
 const h=harness('');h.API.resolveUrl.mockResolvedValue(data('Opened'))
 const edition=(id,explicit)=>({id,title:'Album',track_count:1,explicit,tracks:[{name:'One',artists:['Artist'],duration:100,explicit}]})
 h.API.getSpotifyAlbumEditions.mockResolvedValue({data:{edition:B,editions:[edition(B,false),edition(A,true),edition('C'.repeat(22),true)]}})
 h.route.query.url=url(A);await flush()
 expect(h.API.getSpotifyAlbumEditions).toHaveBeenCalledWith(A)
 expect(h.model.details.value.name).toBe('Opened');expect(h.router.replace).not.toHaveBeenCalled()
 expect(h.model.editionOptions.value.map(o=>o.value)).toEqual([B,A])
 h.model.selectEdition(B)
 expect(h.router.replace).toHaveBeenCalledWith({query:{url:url(B),origin:'keep'}})
 expect(h.model.details.value).toBeNull();expect(h.model.loading.value).toBe(true)
 h.scope.stop()
})
it('ignores stale resolution/discovery and clears selected rows while loading',async()=>{
 const h=harness('');const a=deferred(),b=deferred(),ed=deferred()
 h.API.resolveUrl.mockImplementation(u=>u===url(A)?a.promise:b.promise)
 h.API.getSpotifyAlbumEditions.mockReturnValue(ed.promise)
 h.route.query.url=url(A);await flush();h.route.query.url=url(B);await flush()
 b.resolve(data('Latest'));await flush();a.resolve(data('Old'));ed.resolve({data:{editions:[]}});await flush()
 expect(h.model.details.value.name).toBe('Latest');expect(h.model.loading.value).toBe(false)
 h.model.selected.value=new Set(['old']);h.route.query.url=url(A);await nextTick()
 expect(h.model.selected.value.size).toBe(0)
 h.scope.stop()
})
it('loads local artist tracks before checking unique Link artist releases', async () => {
 const localAlbum = { title: 'Only Release', artist: 'Artist' }
 let loaded = false
 const library = { ensureArtists: vi.fn(async () => {}),
  loadArtistTracks: vi.fn(async () => { loaded = true }),
  findArtist: () => ({ albums: loaded ? [localAlbum] : [] }) }
 const inspect = vi.fn(async releases => releases)
 const tracker = { queueVersion: ref(0), downloadQueue: ref([]) }
 const details = ref({ kind: 'artist', name: 'Artist', albums: [{ album_id: A, name: 'Only Release' }] })
 const code = view.slice(view.indexOf('const inspectedReleases ='), view.indexOf('const releaseGroups ='))
 // Test harness executes checked-in component source only; no user/provider text.
 const scope = effectScope()
 scope.run(() => new Function('ref','watchValue','details','tracker','library','inspectDiscography','API',code)(ref,watch,details,tracker,library,inspect,{}))
 await flush()
 expect(library.loadArtistTracks).toHaveBeenCalledWith('Artist')
 expect(inspect).toHaveBeenCalledWith(details.value.albums, [localAlbum], {})
 scope.stop()
})

it('never guesses Spotify choices for a non-Spotify album',async()=>{
 const h=harness('');h.API.resolveUrl.mockResolvedValue(data('Deezer'))
 h.route.query.url='https://www.deezer.com/album/123';await flush()
 expect(h.API.getSpotifyAlbumEditions).not.toHaveBeenCalled();expect(h.model.editionOptions.value).toEqual([])
 h.scope.stop()
})
