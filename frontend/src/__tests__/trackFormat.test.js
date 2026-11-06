// @vitest-environment happy-dom
import { createApp, h } from 'vue'
import { expect, it } from 'vitest'
import TrackFormat from '../components/library/TrackFormat.vue'
it('uses native uppercase format labels for actual lowercase API formats',()=>{
 const root=document.createElement('div');document.body.append(root)
 const app=createApp({render:()=>h(TrackFormat,{formats:['mp3','flac','MP3']})});app.mount(root)
 expect([...root.querySelector('[data-track-format]').children].map(e=>e.textContent)).toEqual(['MP3','FLAC'])
 app.unmount();root.remove()
})
