// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, reactive, ref } from 'vue'
import en from '../i18n/locales/en'
const f = vi.hoisted(() => ({ route:null, album:null, present:null, locations:vi.fn(), source:vi.fn(), resolve:vi.fn(), lookup:vi.fn(), globalLookup:vi.fn(), batch:vi.fn(), queue:vi.fn(), retry:vi.fn(), start:vi.fn(), items:null, version:null, local:null }))
vi.mock('vue-router', () => ({ useRoute:()=>f.route, useRouter:()=>({push:vi.fn()}), RouterLink:{props:['to'],template:'<a><slot /></a>'} }))
vi.mock('/src/model/api', () => ({ default:{lookupLibraryLocations:f.locations,getLibraryAlbumSource:f.source,resolveUrl:f.resolve,lookupLibrarySongs:f.lookup} }))
vi.mock('/src/model/library', () => ({useLibrary:()=>({loadArtistTracks:vi.fn(async()=>{}),findAlbum:()=>f.album,findArtist:()=>null,lookupSongs:f.globalLookup,hasSong:(a,n)=>f.present.has(n),findTrack:(a,n)=>n==='D4L'?f.local:null})}))
vi.mock('/src/model/download', () => ({jobSongKey:s=>s.song_id,useDownloadManager:()=>({fromSongs:f.batch,queue:f.queue,retry:f.retry}),useProgressTracker:()=>({downloadQueue:ref([]),queueVersion:f.version,getBySong:s=>f.items.get(s.song_id)||null})}))
vi.mock('/src/model/player',()=>({usePlayer:()=>({currentTrack:ref(null),isPlaying:ref(false),shuffle:ref(false),toggleShuffle:vi.fn()})}))
vi.mock('/src/model/songPlay',()=>({useSongStarter:()=>f.start,useSongPlay:()=>({isCurrent:ref(false),loading:ref(false),playable:ref(true),highlighted:ref(false),toggle:vi.fn(),ensurePlaying:vi.fn(),playLabel:ref('Play')})}))
vi.mock('/src/model/trackActions',()=>({useTrackActions:()=>({play:vi.fn(),enqueue:vi.fn(),downloadZip:vi.fn(),menuFor:()=>[],playNext:vi.fn(),remove:vi.fn()})}))
vi.mock('/src/model/playlistActions',()=>({usePlaylistActions:()=>({addMenuItems:()=>[]})}))
vi.mock('/src/model/visibility',()=>({useVisibility:()=>({albumMenu:()=>[]})}))
vi.mock('/src/model/auth',()=>({useAuth:()=>({isAdmin:ref(true)})}))
vi.mock('/src/model/ui',()=>({useUi:()=>({toast:vi.fn()})}))
vi.mock('/src/components/similar/SimilarButton.vue',()=>({default:{template:'<span />'}}))
vi.mock('/src/components/player/LikeButton.vue',()=>({default:{props:['file'],template:'<button :data-like="file">Like</button>'}}))
vi.mock('/src/i18n',()=>({useI18n:()=>({locale:ref('en'),t:(key,v={})=>key.startsWith('album.download') && key.includes('Kind.') ? key.split('.').reduce((o,k)=>o?.[k],en) || key : ({'finder.downloadAlbum':'Download album','album.downloadMissing':'Download missing tracks','link.redownloadAll':'Download all again','search.inLibrary':'In library','actions.downloadItem':`Download ${v.name}`}[key]||key)})}))
vi.mock('/src/model/monitor',()=>({default:{}}))
vi.mock('/src/components/search/ReleaseCard.vue',()=>({default:{template:'<span />'}}))
import AlbumView from '../views/AlbumView.vue'
import LinkView from '../views/LinkView.vue'
import DownloadState from '../components/search/DownloadState.vue'
it('album links keep global green badges while their primary action queues missing targets even when every row is globally present', async()=>{
 f.route.query={url:'https://open.spotify.com/album/demo'};f.present=new Set(['Deep Pockets','D4L'])
 f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',subtitle:'Drake',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 await mount(LinkView)
 root.querySelector('[data-track-row] [data-column="title"] p').click();await flush()
 expect(f.start).toHaveBeenCalledOnce()
 expect(f.start.mock.calls[0][0].name).toBe('Deep Pockets')
 root.querySelector('[data-track-row] [data-artist-credit]').click();await flush()
 expect(f.start).toHaveBeenCalledOnce()
 expect(root.querySelectorAll('[aria-label="In library"]')).toHaveLength(2)
 const button=[...root.querySelectorAll('button')].find(el=>el.textContent.trim()==='Download album');expect(button).toBeTruthy();expect(button.disabled).toBe(false);button.click();await flush()
 expect(f.batch).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({name:'D4L'}),expect.objectContaining({name:'Deep Pockets'})]),expect.objectContaining({destination:'album',downloadMode:'missing'}))
 expect(root.textContent).not.toContain('Download all again')
})
it.each([AlbumView, LinkView])('offers redownload only on complete Link releases, without a replacement status panel (%#)', async(component)=>{
 if(component===LinkView) f.route.query={url:'https://open.spotify.com/album/demo'}
 f.lookup.mockResolvedValue({data:{tracks:[],destinations:[{key:'one',exists:true,stem:'Drake/Demo/One'},{key:'two',exists:true,stem:'Drake/Demo/Two'}]}})
 f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',subtitle:'Drake',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 await mount(component)
 const buttons=[...root.querySelectorAll('button')].filter(el=>el.textContent.trim()==='Download album again')
 expect(buttons).toHaveLength(component===LinkView?1:0)
 expect(root.textContent).not.toContain('Download all again');expect(root.textContent).not.toContain('link.allInLibrary')
 expect(f.batch).not.toHaveBeenCalled()
 if(component===LinkView) {
  const play=root.querySelector('[data-link-play]');expect(play).not.toBeNull();expect(play.classList.contains('bg-accent')).toBe(true)
  play.click();await flush();expect(f.start).toHaveBeenCalledWith(expect.objectContaining({song_id:'one'}),expect.objectContaining({songs:expect.arrayContaining([expect.objectContaining({song_id:'two'})])}))
  expect(f.batch).not.toHaveBeenCalled();buttons[0].click();await flush()
  expect(f.batch.mock.calls[0][0].map(s=>s.song_id)).toEqual(['one','two'])
  expect(f.batch.mock.calls[0][1]).toMatchObject({destination:'album',downloadMode:'redownload'})
 }
})
it.each([AlbumView, LinkView])('keeps one album primary for only missing canonical targets despite global presence (%#)', async(component)=>{
 if(component===LinkView) f.route.query={url:'https://open.spotify.com/album/demo'}
 f.present=new Set(['Deep Pockets','D4L'])
 f.lookup.mockResolvedValue({data:{destinations:[{key:'one',exists:true,stem:'Drake/Demo/One'},{key:'two',exists:false,stem:'Drake/Demo/Two'}]}})
 f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 await mount(component)
 expect(root.textContent).not.toContain('Download all again')
 const buttons=[...root.querySelectorAll('button')].filter(el=>el.textContent.trim()==='Download full album')
 expect(buttons).toHaveLength(1);expect(buttons[0].disabled).toBe(false)
 expect(buttons[0].classList.contains(component===AlbumView?'bg-transparent':'bg-accent')).toBe(true)
 buttons[0].click();await flush()
 expect(f.batch.mock.calls[0][0].map(s=>s.song_id)).toEqual(['two'])
 expect(f.batch.mock.calls[0][1]).toMatchObject({destination:'album',downloadMode:'missing'})
})
it.each([AlbumView, LinkView])('never enables redownload while the album target lookup is pending or failed (%#)', async(component)=>{
 if(component===LinkView) f.route.query={url:'https://open.spotify.com/album/demo'}
 let rejectLookup
 f.lookup.mockImplementation(()=>new Promise((resolve,reject)=>{rejectLookup=reject}))
 f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']}]}})
 await mount(component)
 expect([...root.querySelectorAll('button')].find(el=>el.textContent.trim()==='Download album')).toBeUndefined()
 expect(root.textContent).not.toContain('Download all again')
 expect(f.batch).not.toHaveBeenCalled()
 expect(root.querySelector('[data-hero-loading] .animate-spin')).not.toBeNull()
 rejectLookup(new Error('lookup failed'));await flush()
 expect(root.querySelector('[data-hero-loading]')).toBeNull()
 expect([...root.querySelectorAll('button')].find(el=>el.textContent.trim()==='Download album')).toBeUndefined()
 expect(root.textContent).not.toContain('Download all again')
})
it.each(['album','single','ep'])('never flashes a %s header action before completion is known',async(type)=>{
 for(const component of [AlbumView,LinkView]) {
  for(const complete of [true,false]) {
   f.route.query=component===LinkView?{url:'https://open.spotify.com/album/demo'}:{artist:'Drake',title:'Demo'}
   const tracks=[{song_id:'one',name:'Deep Pockets',artists:['Drake']}]
   f.source.mockResolvedValue({data:{status:'resolved',release_type:type,tracks}})
   f.resolve.mockResolvedValue({data:{kind:'album',release_type:type,name:'Demo',albums:[],tracks}})
   let finish
   f.lookup.mockImplementation(()=>new Promise(resolve=>{finish=resolve}))
   await mount(component)
   const primary=()=>[...root.querySelectorAll('button')].filter(el=>/^Download (album|single|EP|full)/.test(el.textContent.trim()))
   expect(primary()).toHaveLength(0)
   finish({data:{destinations:[{key:'one',exists:complete}]}});await flush()
   expect(primary()).toHaveLength(component===LinkView?1:complete?0:1)
   expect(/Download (album|single|EP) again/.test(root.textContent)).toBe(component===LinkView && complete)
   expect(!!root.querySelector('[data-link-play]')).toBe(component===LinkView && complete)
   app.unmount();root.remove()
  }
 }
})
it.each(['playlist','artist'])('preserves the separate all-again action on mixed %s links', async(kind)=>{
 f.route.query={url:`https://open.spotify.com/${kind}/demo`}
 f.resolve.mockResolvedValue({data:{kind,name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future']}]}})
 await mount(LinkView)
 const button=[...root.querySelectorAll('button')].find(el=>el.textContent.trim()==='Download all again')
 expect(button).toBeTruthy();button.click();await flush()
 expect(f.batch.mock.calls[0][0].map(s=>s.song_id)).toEqual(['one','two'])
 expect(f.batch.mock.calls[0][1]).toMatchObject({downloadMode:'redownload'})
 expect(f.batch.mock.calls[0][1]).not.toHaveProperty('destination')
 expect(f.lookup).not.toHaveBeenCalled()
})
it.each(['album', 'single', 'ep'])('names %s downloads for every canonical destination state on both pages', async(type)=>{
 for (const component of [AlbumView, LinkView]) {
  for (const state of ['none', 'partial', 'complete']) {
   f.route.query = component === LinkView ? {url:'https://open.spotify.com/album/demo'} : {artist:'Drake',title:'Demo'}
   const tracks=[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']}]
   f.source.mockResolvedValue({data:{status:'resolved',release_type:type,tracks}})
   f.resolve.mockResolvedValue({data:{kind:'album',release_type:type,name:'Demo',albums:[],tracks}})
   f.lookup.mockResolvedValue({data:{destinations:[{key:'one',exists:state!=='none'},{key:'two',exists:state==='complete'}]}})
   f.batch.mockClear()
   await mount(component)
   const name=type==='ep'?'EP':type
   const label=state==='complete'?`Download ${name} again`:state==='partial'?`Download full ${name}`:`Download ${name}`
   const buttons=[...root.querySelectorAll('button')].filter(b=>b.textContent.trim()===label)
   expect(buttons, `${component.__name} ${state}`).toHaveLength(state==='complete' && component===AlbumView?0:1)
   expect(root.textContent).not.toContain('Download FLAC')
   if(state==='complete' && component===AlbumView) { expect(f.batch).not.toHaveBeenCalled();app.unmount();root.remove();continue }
   buttons[0].click();await flush()
   expect(f.batch.mock.lastCall[0].map(s=>s.song_id)).toEqual(state==='partial'?['two']:['one','two'])
   expect(f.batch.mock.lastCall[1]).toMatchObject({destination:'album',downloadMode:state==='complete'?'redownload':'missing'})
   expect(f.batch.mock.lastCall[1]).not.toHaveProperty('audioFormat')
   app.unmount();root.remove()
  }
 }
})
it.each([{present:[]}, {present:['D4L']}, {present:['Deep Pockets','D4L']}])('album links never expose download-state filters for presence %j', async({present})=>{
 f.route.query={url:'https://open.spotify.com/album/demo'};f.present=new Set(present)
 f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 await mount(LinkView)
 expect(root.querySelector('[data-link-filter]')).toBeNull()
 expect(root.querySelectorAll('li[data-track-row]')).toHaveLength(2)
 const checkbox=root.querySelector('li[data-track-row] [role="checkbox"]')
 checkbox.click();await flush()
 const button=[...root.querySelectorAll('button')].find(b=>b.textContent.trim()==='link.downloadSelected (1)')
 expect(button).toBeTruthy();button.click();await flush()
 expect(f.batch.mock.lastCall[0].map(s=>s.song_id)).toEqual(['one'])
 expect(f.batch.mock.lastCall[1]).toMatchObject({destination:'album',downloadMode:'missing'})
})
it('playlist links retain their download-state filter and selection',async()=>{
 f.route.query={url:'https://open.spotify.com/playlist/demo'}
 f.resolve.mockResolvedValue({data:{kind:'playlist',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future']}]}})
 await mount(LinkView)
 root.querySelector('[data-link-filter]').click();await flush()
 const newOnly=[...document.querySelectorAll('[role="menu"] button')].find(b=>b.textContent.trim()==='link.filterNew (1)')
 expect(newOnly).toBeTruthy();newOnly.click();await flush()
 expect(root.querySelectorAll('li[data-track-row]')).toHaveLength(1)
 expect(root.querySelector('li[data-track-row]').dataset.trackRow).toBe('one')
})

let app, root
const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve();await nextTick()}
beforeEach(()=>{
 vi.clearAllMocks();f.locations.mockResolvedValue({data:{locations:[]}});f.items=new Map();f.version=ref(0);f.route=reactive({query:{artist:'Drake',title:'Demo'}});f.present=new Set(['D4L']);f.local={file:'QA Playlist/D4L.mp3',title:'D4L',artist:'Future',album:'Demo',albumArtist:'Drake'}
 f.album={title:'Demo',artist:'Drake',key:'drake/demo',duration:60,size:10,tracks:[f.local]}
 f.source.mockResolvedValue({data:{status:'resolved',tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']} ]}})
 f.globalLookup.mockResolvedValue([]);f.lookup.mockResolvedValue({data:{tracks:[],destinations:[{key:'one',exists:false,stem:'Drake/Demo/One'},{key:'two',exists:false,stem:'Drake/Demo/Two'}]}});f.batch.mockResolvedValue(2)
})
afterEach(()=>{app?.unmount();root?.remove()})
async function mount(component=AlbumView,props={}){root=document.createElement('div');document.body.append(root);app=createApp({render:()=>h(component,props)});app.component('RouterLink',{template:'<a><slot/></a>'});app.mount(root);await flush()}
it.each([AlbumView, LinkView])('places one plain gray library check in the fixed download cell after time (%#)',async(component)=>{
 if(component===LinkView) {
  f.route.query={url:'https://open.spotify.com/album/demo'}
  f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',duration:180,artists:['Drake']},{song_id:'two',name:'D4L',duration:181,artists:['Future','Drake']}]}})
 }
 await mount(component)
 const badge=root.querySelector('[aria-label="In library"]')
 expect(badge).toBeTruthy()
 expect(badge.classList.contains('rounded-full')).toBe(false)
 expect(badge.classList.contains('text-muted')).toBe(true)
 const row=badge.closest('[data-track-row]')
 expect(row.querySelectorAll('[aria-label="In library"]')).toHaveLength(1)
 const time=row.querySelector('[data-track-duration]')
 expect(time.compareDocumentPosition(badge)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
 expect(root.querySelectorAll('[aria-label="In library"]')).toHaveLength(1)
 const missing=root.querySelector('[aria-label="Download Deep Pockets"]')
 expect(missing).toBeTruthy()
 expect(missing.className).toContain('text-muted');expect(missing.className).toContain('hover:text-accent');expect(missing.className).not.toContain('rounded-full')
 const missingRow=missing.closest('[data-track-row]')
 expect(missingRow.querySelector('[data-track-duration]').compareDocumentPosition(missing)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})
it.each([AlbumView, LinkView])('hides its missing action when target jobs complete (%#)',async(component)=>{
 if(component===LinkView) {
  f.route.query={url:'https://open.spotify.com/album/demo'}
  f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 }
 await mount(component)
 expect(root.textContent).toContain('Download album')
 f.items.set('one',{state:'done',filename:'Drake/Demo/One.mp3'})
 f.items.set('two',{state:'done',filename:'Drake/Demo/Two.mp3'})
 f.version.value++;await flush()
 const buttons=[...root.querySelectorAll('button')].filter(el=>el.textContent.trim()==='Download album again')
 expect(buttons).toHaveLength(component===LinkView?1:0)
 expect(root.textContent).not.toContain('Download all again')
 expect(f.batch).not.toHaveBeenCalled()
})
it.each(['all','controls'])('retains the native active progress and retry in %s presentation',async(presentation)=>{
 const song={song_id:'one',name:'Deep Pockets',artists:['Drake']}
 f.items.set('one',{state:'active',progress:42})
 await mount(DownloadState,{song,presentation})
 expect(root.textContent).toContain('42%')
 expect(root.querySelector('button')).toBeNull()
 f.items.set('one',{state:'failed'});f.version.value++;await flush()
 const retry=root.querySelector('[aria-label="queue.retry"]')
 expect(retry).toBeTruthy();retry.click()
 expect(f.retry).toHaveBeenCalledWith(song)
 expect(root.textContent).not.toContain('In library')
})
it('keeps the default DownloadState library badge for unmodified callers',async()=>{
 await mount(DownloadState,{song:{song_id:'two',name:'D4L',artists:['Future']}})
 expect(root.textContent.match(/In library/g)).toHaveLength(1)
 expect(root.querySelector('button')).toBeNull()
})
it('places the single neutral album download in the former ZIP slot after queue, including on mobile',async()=>{
 await mount()
 const buttons=[...root.querySelectorAll('button')]
 const downloads=buttons.filter(el=>el.textContent.trim()==='Download album')
 expect(downloads).toHaveLength(1)
 const button=downloads[0]
 expect(button.previousElementSibling.textContent.trim()).toBe('actions.addToQueue')
 expect(button.classList.contains('bg-transparent')).toBe(true)
 expect(button.classList.contains('bg-accent')).toBe(false)
 expect(button.classList.contains('h-10')).toBe(true)
 expect(button.classList.contains('h-12')).toBe(false)
 expect(button.classList.contains('max-sm:hidden')).toBe(false)
 expect(button.querySelector('svg')).not.toBeNull()
 expect(buttons.some(el=>el.textContent.trim()==='library.downloadZip')).toBe(false)
})
it('renders one full native list, global badges, original row download and missing-target album action',async()=>{
 await mount()
 expect(root.textContent).toContain('Deep Pockets')
 expect(root.querySelectorAll('[aria-label="In library"]')).toHaveLength(1)
 const rowButton=root.querySelector('[aria-label="Download Deep Pockets"]');expect(rowButton).not.toBeNull();rowButton.click();expect(f.queue).toHaveBeenCalledWith(expect.objectContaining({downtify_destination:'album'}))
 expect(root.querySelector('[data-like="QA Playlist/D4L.mp3"]')).not.toBeNull()
 const button=[...root.querySelectorAll('button')].find(el=>el.textContent.trim()==='Download album');expect(button).toBeTruthy();button.click();await flush()
 expect(f.batch).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({name:'D4L'}),expect.objectContaining({name:'Deep Pockets'})]),expect.objectContaining({destination:'album',downloadMode:'missing'}))
 expect(root.textContent).not.toMatch(/Retry|source album|All tracks downloaded|Re-download all/)
})
it('preserves the native local-file right-click menu on full source rows',async()=>{
 await mount()
 const row=root.querySelector('[data-like="QA Playlist/D4L.mp3"]').parentElement.parentElement
 const event=new MouseEvent('contextmenu',{bubbles:true,cancelable:true})
 row.dispatchEvent(event);await flush()
 expect(document.querySelector('[role="menu"]')).not.toBeNull()
 expect(event.defaultPrevented).toBe(true)
})
it('retains opposite-context playlist badges on the unresolved local album fallback',async()=>{
 f.source.mockResolvedValue({data:{status:'unavailable',tracks:[]}})
 f.locations.mockResolvedValue({data:{locations:[{key:f.local.file,downloaded:true,formats:['MP3'],albums:[{artist:'Drake',title:'Demo'}],playlists:[{name:'QA Playlist'}]}]}})
 await mount()
 expect(root.querySelector('[role="table"]')).not.toBeNull()
 expect(root.querySelectorAll('[data-location-kind="playlist"]')).toHaveLength(1)
 expect(root.querySelectorAll('[data-location-kind="album"]')).toHaveLength(0)
})
it('retains the original local TrackList with no source messages if unresolved',async()=>{
 f.source.mockResolvedValue({data:{status:'unavailable',tracks:[]}});await mount()
 expect(root.querySelector('[role="table"]')).not.toBeNull();expect(root.textContent).not.toContain('Deep Pockets');expect(root.querySelector('[aria-label="Download Deep Pockets"]')).toBeNull()
})
it('album link row downloads force an album only without an explicit playlist origin',async()=>{
 f.route.query={url:'https://open.spotify.com/album/demo'}
 f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',artists:['Drake']}]}})
 await mount(LinkView);root.querySelector('[aria-label="Download Deep Pockets"]').click()
 expect(f.queue).toHaveBeenCalledWith(expect.objectContaining({downtify_destination:'album'}))
 app.unmount();root.remove();f.queue.mockClear();f.route.query.playlist='QA Playlist'
 await mount(LinkView);root.querySelector('[aria-label="Download Deep Pockets"]').click()
 expect(f.queue).toHaveBeenCalledWith(expect.objectContaining({downtify_playlist_name:'QA Playlist'}))
 expect(f.queue.mock.calls[0][0]).not.toHaveProperty('downtify_destination')
})
it('playlist links keep their original completed UI and destination-policy lookup',async()=>{
 f.route.query={url:'https://open.spotify.com/playlist/demo'};f.present=new Set(['D4L'])
 f.resolve.mockResolvedValue({data:{kind:'playlist',name:'QA Playlist',albums:[],tracks:[{song_id:'two',name:'D4L',artists:['Future']}]}})
 await mount(LinkView)
 expect(root.textContent).toContain('link.allInLibrary');expect(root.textContent).not.toContain('Download all again')
 expect(f.globalLookup).toHaveBeenCalledWith(expect.any(Array),{destination:true,playlist_name:'QA Playlist'})
 expect(f.lookup).not.toHaveBeenCalled()
})
it.each([AlbumView, LinkView])('shows verified downloaded formats only and opposite-view native locations (%#)',async(component)=>{
 if(component===LinkView) {
  f.route.query={url:'https://open.spotify.com/album/demo'}
  f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'one',name:'Deep Pockets',format:'FLAC',artists:['Drake']},{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 }
 f.locations.mockImplementation(async songs=>({data:{locations:songs.map(s=>({key:s.song_id,downloaded:s.song_id==='two',formats:s.song_id==='two'?['MP3','FLAC']:[],albums:s.song_id==='two'?[{artist:'Drake',title:'Demo'}]:[],playlists:s.song_id==='two'?[{name:'Mix One'},{name:'Mix Two'}]:[]}))}}))
 await mount(component)
 const missing=root.querySelector('[data-track-row="one"]')
 const owned=root.querySelector('[data-track-row="two"]')
 expect(missing.querySelector('[data-track-format]').textContent.trim()).toBe('')
 expect(owned.querySelector('[data-track-format]').textContent).toContain('MP3')
 expect(owned.querySelector('[data-track-format]').textContent).toContain('FLAC')
 expect(owned.querySelectorAll('[data-location-kind="playlist"]')).toHaveLength(2)
 expect(owned.querySelectorAll('[data-location-kind="album"]')).toHaveLength(component===LinkView?1:0)
 expect(owned.querySelector('[data-track-download-cell] [aria-label="In library"]')).not.toBeNull()
 expect(missing.querySelector('[data-track-download-cell] button')).not.toBeNull()
 const locationLookups = 1 // Rows batch their availability; the hero only needs destination completeness.
 expect(f.locations).toHaveBeenCalledTimes(locationLookups)
 f.version.value++;await flush();expect(f.locations).toHaveBeenCalledTimes(locationLookups)
})
it('shows a green Link play action for verified global files even when the album destination is missing', async()=>{
 f.route.query={url:'https://open.spotify.com/album/demo'}
 f.resolve.mockResolvedValue({data:{kind:'album',name:'Demo',albums:[],tracks:[{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 f.locations.mockResolvedValue({data:{locations:[{key:'two',downloaded:true,formats:['MP3'],playlists:[{name:'QA Playlist'}]}]}})
 await mount(LinkView)
 const play=root.querySelector('[data-link-play]');expect(play).not.toBeNull();play.click();await flush()
 expect(f.start).toHaveBeenCalledWith(expect.objectContaining({song_id:'two'}),expect.objectContaining({songs:expect.any(Array)}))
 expect(f.batch).not.toHaveBeenCalled()
 const download=root.querySelector('[data-link-primary]');expect(download.textContent.trim()).toBe('Download album');expect(download.classList.contains('bg-transparent')).toBe(true)
})
it('uses only the explicit playlist context for row downloads and keeps it in album playback history',async()=>{
 f.route.query.playlist='QA Playlist';await mount();root.querySelector('[aria-label="Download Deep Pockets"]').click()
 const song=f.queue.mock.calls[0][0];expect(song).toMatchObject({downtify_playlist_name:'QA Playlist'});expect(song).not.toHaveProperty('downtify_destination')
})
