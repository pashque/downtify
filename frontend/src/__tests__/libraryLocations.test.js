// @vitest-environment happy-dom
import { expect, it, vi } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'
const f = vi.hoisted(() => ({ lookup: vi.fn(), version: null, done: false }))
vi.mock('/src/model/api', () => ({ default: { lookupLibraryLocations: f.lookup } }))
vi.mock('/src/model/download', () => ({ useProgressTracker: () => ({ queueVersion: f.version, getBySong: () => f.done ? { state: 'done', filename: 'album/track.mp3' } : { state: 'active', progress: f.version.value } }) }))
import { useLibraryLocations } from '../model/libraryLocations'
it('batches at most 100 rows, refreshes on completion and never writes destination state', async () => {
 f.version = ref(0)
 f.lookup.mockImplementation(async songs => ({ data: { locations: songs.map(s => ({ key:s.song_id, downloaded:true, formats:['MP3'], albums:[], playlists:[{name:'Mix'}] })) } }))
 const songs=ref(Array.from({length:501},(_,i)=>({song_id:String(i),downtify_destination_exists:false})))
 const scope=effectScope(); const model=scope.run(()=>useLibraryLocations(songs))
 const flush=async()=>{for(let i=0;i<30;i++) await Promise.resolve(); await nextTick()}
 await flush()
 expect(f.lookup.mock.calls.map(c=>c[0].length)).toEqual([100,100,100,100,100,1])
 expect(model.locationFor(songs.value[0]).formats).toEqual(['MP3'])
 expect(songs.value[0].downtify_destination_exists).toBe(false)
 songs.value=songs.value.map(song=>({...song}));await flush()
 expect(f.lookup).toHaveBeenCalledTimes(6)
 f.version.value++; await flush()
 expect(f.lookup).toHaveBeenCalledTimes(6)
 f.done = true; f.version.value++; await flush()
 expect(f.lookup).toHaveBeenCalledTimes(12)
 f.lookup.mockRejectedValueOnce(new Error('unavailable')); songs.value=[{song_id:'new'}];await flush()
 expect(model.locationFor(songs.value[0])).toBeNull()
 scope.stop()
})
