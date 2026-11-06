// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, reactive, ref } from 'vue'
import en from '../i18n/locales/en'
const f = vi.hoisted(() => ({ route:null, album:null, present:null, locations:vi.fn(), source:vi.fn(), resolve:vi.fn(), lookup:vi.fn(), globalLookup:vi.fn(), batch:vi.fn(), queue:vi.fn(), retry:vi.fn(), start:vi.fn(), items:null, version:null, local:null }))
vi.mock('vue-router', () => ({ useRoute:()=>f.route, useRouter:()=>({push:vi.fn()}), RouterLink:{props:['to'],template:'<a><slot /></a>'} }))
vi.mock('/src/model/api', () => ({ default:{lookupLibraryLocations:f.locations,getLibraryAlbumSource:f.source,resolveUrl:f.resolve,lookupLibrarySongs:f.lookup} }))
vi.mock('/src/model/library', () => ({useLibrary:()=>({loadArtistTracks:vi.fn(async()=>{}),findAlbum:()=>f.album,findArtist:()=>null,lookupSongs:f.globalLookup,hasSong:(a,n)=>f.present.has(n),findTrack:(a,n)=>n==='D4L'?f.local:null})}))
vi.mock('/src/model/download', () => ({jobSongKey:s=>s.song_id,useDownloadManager:()=>({fromSongs:f.batch,queue:f.queue,retry:f.retry}),useProgressTracker:()=>({queueVersion:f.version,getBySong:s=>f.items.get(s.song_id)||null})}))
vi.mock('/src/model/player',()=>({usePlayer:()=>({currentTrack:ref(null),isPlaying:ref(false),shuffle:ref(false),toggleShuffle:vi.fn()})}))
vi.mock('/src/model/songPlay',()=>({useSongStarter:()=>f.start,useSongPlay:()=>({isCurrent:ref(false),loading:ref(false),playable:ref(true),highlighted:ref(false),toggle:vi.fn(),ensurePlaying:vi.fn(),playLabel:ref('Play')})}))
vi.mock('/src/model/trackActions',()=>({useTrackActions:()=>({play:vi.fn(),enqueue:vi.fn(),downloadZip:vi.fn(),menuFor:()=>[],playNext:vi.fn(),remove:vi.fn()})}))
vi.mock('/src/model/playlistActions',()=>({usePlaylistActions:()=>({addMenuItems:()=>[]})}))
vi.mock('/src/model/visibility',()=>({useVisibility:()=>({albumMenu:()=>[]})}))
vi.mock('/src/model/auth',()=>({useAuth:()=>({isAdmin:ref(true)})}))
vi.mock('/src/model/ui',()=>({useUi:()=>({toast:vi.fn()})}))
vi.mock('/src/components/similar/SimilarButton.vue',()=>({default:{template:'<span />'}}))
vi.mock('/src/components/player/LikeButton.vue',()=>({default:{props:['file'],template:'<button :data-like="file">Like</button>'}}))
vi.mock('/src/i18n',()=>({useI18n:()=>({locale:ref('en'),t:(key,v={})=>key.startsWith('album.download') && key.includes('Kind.') ? key.split('.').reduce((o,k)=>o?.[k],en) || key : ({'finder.downloadAlbum':'Download album','album.downloadMissing':'Download missing tracks','link.redownloadAll':'Download all again','actions.downloadFlac':'Download FLAC','search.inLibrary':'In library','actions.downloadItem':`Download ${v.name}`}[key]||key)})}))
vi.mock('/src/model/monitor',()=>({default:{}}))
vi.mock('/src/components/search/ReleaseCard.vue',()=>({default:{template:'<span />'}}))
import AlbumView from '../views/AlbumView.vue'
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


const complete = () => f.lookup.mockResolvedValue({data:{destinations:[{key:'one',exists:true},{key:'two',exists:true}]}})
const formats = (one,two) => f.locations.mockResolvedValue({data:{locations:[{key:'one',formats:['mp3','flac'],album_formats:one},{key:'two',formats:['mp3','flac'],album_formats:two}]}})
const primary = label => [...root.querySelectorAll('button')].find(b=>b.textContent.trim()===label)
it('hides the completed release action even when only some canonical tracks have FLAC',async()=>{
 complete();formats(['mp3','flac'],['mp3']);await mount()
 expect(primary('Download FLAC')).toBeUndefined()
 expect(primary('Download album again')).toBeUndefined()
 expect(f.batch).not.toHaveBeenCalled()
})
it('hides the action when every canonical track already has FLAC',async()=>{
 complete();formats(['flac'],['flac']);await mount()
 expect(primary('Download FLAC')).toBeUndefined()
 expect(primary('Download album again')).toBeUndefined()
 expect(f.batch).not.toHaveBeenCalled()
})
it('does not infer canonical MP3 or FLAC ownership from global playlist-only formats',async()=>{
 complete();formats([],[]);await mount()
 expect(primary('Download FLAC')).toBeUndefined();expect(primary('Download album again')).toBeUndefined()
})
it('keeps missing-track semantics even when the existing canonical track has MP3',async()=>{
 f.lookup.mockResolvedValue({data:{destinations:[{key:'one',exists:true},{key:'two',exists:false}]}})
 formats(['mp3'],[]);await mount()
 expect(primary('Download FLAC')).toBeUndefined()
 primary('Download full album').click();await flush()
 expect(f.batch.mock.lastCall).toEqual([[expect.objectContaining({song_id:'two'})],{destination:'album',downloadMode:'missing'}])
})
it('hides the FLAC menu action for a verified global FLAC copy',async()=>{
 formats([],['flac']);await mount()
 root.querySelector('[data-track-row="two"] [aria-label="common.more"]').click();await flush()
 expect(document.querySelector('[role="menu"]').textContent).not.toContain('Download FLAC')
})
it('does not offer FLAC for a local FLAC file while optional locations are unavailable',async()=>{
 f.local.format='FLAC';f.local.file='Drake/Demo/D4L.flac'
 await mount();root.querySelector('[data-track-row="two"] [aria-label="common.more"]').click();await flush()
 expect(document.querySelector('[role="menu"]').textContent).not.toContain('Download FLAC')
})
it('keeps unverified editions distinct without displaying opaque provider ID suffixes',async()=>{
 f.source.mockResolvedValue({data:{status:'resolved',edition:'edition111111',editions:[{id:'edition111111',track_count:12},{id:'edition222222',track_count:12}],tracks:[{song_id:'two',name:'D4L',artists:['Future','Drake']}]}})
 await mount();root.querySelector('button[data-album-version]').click();await flush()
 const menu = document.querySelector('[role="menu"]').textContent
 expect(menu).not.toContain('111111')
 expect(menu).not.toContain('222222')
 expect(menu).toContain('Version 1')
 expect(menu).toContain('Version 2')
})
