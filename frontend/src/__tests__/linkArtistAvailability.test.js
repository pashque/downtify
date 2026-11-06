import { expect, it, vi } from 'vitest'
import { computed, ref, watch, effectScope, nextTick } from 'vue'
import { readFileSync } from 'node:fs'
import { discographySections } from '../lib/discography'
const view=readFileSync(`${process.cwd()}/src/views/LinkView.vue`,'utf8')
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve();await nextTick()}
it('inspects Link artist releases with library albums and refreshes after completed jobs',async()=>{
 expect(view.includes('const inspectedReleases =')).toBe(true)
 const details=ref({kind:'artist',name:'Artist',albums:[{album_id:'one',name:'Album'}]})
 const local=[{title:'Album',artist:'Artist'}]
 const library={ensureArtists:vi.fn(async()=>{}),findArtist:vi.fn(()=>({albums:local}))}
 const inspect=vi.fn(async list=>list.map(r=>({...r,physicallyComplete:true})))
 const tracker={queueVersion:ref(0),downloadQueue:ref([])}
 const scope=effectScope();let model
 // Evaluate only checked-in source, never data supplied by users or providers.
 const code=view.slice(view.indexOf('const inspectedReleases ='),view.indexOf('const filterOptions ='))
 scope.run(()=>model=new Function('ref','computed','watchValue','details','library','API','tracker','inspectDiscography','discographySections','t',`${code}; return {releaseGroups}`)(ref,computed,watch,details,library,{},tracker,inspect,discographySections,k=>k))
 await flush()
 expect(library.ensureArtists).toHaveBeenCalledOnce()
 expect(inspect).toHaveBeenCalledWith(details.value.albums,local,{})
 expect(model.releaseGroups.value).toEqual([])
 tracker.downloadQueue.value=[{state:'done',filename:'new.mp3'}];await flush()
 expect(inspect).toHaveBeenCalledTimes(2)
 details.value={kind:'album',albums:[]};await flush();expect(model.releaseGroups.value).toEqual([])
 scope.stop()
})
