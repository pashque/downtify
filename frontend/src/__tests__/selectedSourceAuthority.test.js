import { expect, it, vi } from 'vitest'
import { effectScope, nextTick, reactive } from 'vue'
const f = vi.hoisted(() => ({ get:vi.fn(), remember:vi.fn(), lookup:vi.fn() }))
vi.mock('/src/model/api',()=>({default:{getLibraryAlbumSource:f.get,setLibraryAlbumSource:f.remember}}))
vi.mock('/src/model/library',()=>({useLibrary:()=>({lookupSongs:f.lookup})}))
vi.mock('/src/model/download',()=>({useProgressTracker:()=>({})}))
import { useAlbumSource } from '../model/albumSource'
import { albumRoute } from '../lib/albumRouting'
const id='53wStBoNAK1lhbfbuCJ2zd'
const flush=async()=>{for(let i=0;i<15;i++)await Promise.resolve();await nextTick()}
it('keeps the explicit route release and remembers native menu choices',async()=>{
 f.get.mockImplementation(async(a,t,e)=>({data:{status:'resolved',edition:e,tracks:[{song_id:'track',name:'One'}]}}))
 f.remember.mockResolvedValue({data:{edition:id}});f.lookup.mockResolvedValue([])
 const route=reactive({query:{artist:'Artist',title:'Album',edition:id}})
 const scope=effectScope();let model;scope.run(()=>{model=useAlbumSource(route)})
 await flush();expect(f.get).toHaveBeenCalledWith('Artist','Album',id)
 expect(f.remember).toHaveBeenCalledWith('Artist','Album',id)
 model.selectEdition('B'.repeat(22));await flush()
 expect(f.get).toHaveBeenLastCalledWith('Artist','Album','B'.repeat(22))
 expect(f.remember).toHaveBeenLastCalledWith('Artist','Album','B'.repeat(22))
 scope.stop()
})
it('carries exact Spotify album identity through native Library routes',()=>{
 expect(albumRoute({albumArtist:'Artist',album:'Album',source:'spotify',album_id:id}).query.edition).toBe(id)
 expect(albumRoute({albumArtist:'Artist',album:'Album',source:'youtube',album_id:id}).query.edition).toBeUndefined()
})
