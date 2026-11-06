import { expect, it, vi } from 'vitest'
import { effectScope, nextTick, reactive } from 'vue'
const f=vi.hoisted(()=>({get:vi.fn(),save:vi.fn(),lookup:vi.fn()}))
vi.mock('/src/model/api',()=>({default:{getLibraryAlbumSource:f.get,setLibraryAlbumSource:f.save}}))
vi.mock('/src/model/library',()=>({useLibrary:()=>({lookupSongs:f.lookup})}))
vi.mock('/src/model/download',()=>({useProgressTracker:()=>({})}))
import { useAlbumSource } from '../model/albumSource'
import { selectedAlbumMetadata } from '../lib/albumRouting'
const A='A'.repeat(22),B='B'.repeat(22)
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve();await nextTick()}
it('clears old source when the next explicit selection is unavailable',async()=>{
 f.lookup.mockResolvedValue([]);f.save.mockResolvedValue({})
 f.get.mockImplementation(async(a,t,id)=>({data:id==='bad'?{status:'unavailable',tracks:[]}:{status:'resolved',edition:id,tracks:[{song_id:'one'}]}}))
 const route=reactive({query:{artist:'Artist',title:'Album',edition:A}});let model;const scope=effectScope();scope.run(()=>model=useAlbumSource(route))
 await flush();expect(model.songs.value).toHaveLength(1)
 route.query.edition='bad';await flush();expect(model.songs.value).toBe(null);expect(model.edition.value).toBe(null);scope.stop()
})
it('serializes saves so an earlier completion cannot overwrite the latest choice',async()=>{
 f.lookup.mockResolvedValue([]);f.get.mockImplementation(async(a,t,id)=>({data:{status:'resolved',edition:id,tracks:[{song_id:id}]}}))
 let finishA;const writes=[]
 f.save.mockImplementation((a,t,id)=>{writes.push(id);return id===A?new Promise(resolve=>finishA=resolve):Promise.resolve({})})
 const route=reactive({query:{artist:'Artist',title:'Album',edition:A}});let model;const scope=effectScope();scope.run(()=>model=useAlbumSource(route))
 await flush();model.selectEdition(B);await flush();expect(writes).toEqual([A]);finishA({});await flush();expect(writes).toEqual([A,B]);expect(model.edition.value).toBe(B);scope.stop()
})
it('uses selected source cover and year without rewriting local album metadata',()=>{
 const local={title:'Album',cover:'old.jpg',year:'2020',tracks:[{file:'existing.mp3'}]}
 const shown=selectedAlbumMetadata(local,{cover_url:'selected.jpg',release_date:'2021-10-22'})
 expect(shown).toMatchObject({cover:'selected.jpg',year:'2021',tracks:local.tracks})
 expect(local.cover).toBe('old.jpg');expect(local.year).toBe('2020')
})
