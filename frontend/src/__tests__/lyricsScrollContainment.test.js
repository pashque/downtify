// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, nextTick, ref } from 'vue'
import LyricsPanel from '../components/player/LyricsPanel.vue'
const state = vi.hoisted(() => ({}))
vi.mock('/src/model/player', () => ({ usePlayer: () => state.player }))
vi.mock('/src/model/lyrics', () => ({ loadLyrics: async () => ({ lines: Array.from({length: 30}, (_, i) => ({time:i*10,text:`Line ${i}`})), plain:'' }) }))
vi.mock('/src/i18n', () => ({ useI18n: () => ({ t: key => key }) }))
let app
let host
afterEach(() => { app?.unmount();host?.remove();vi.restoreAllMocks() })
it('autoscrolls only the lyrics viewport at the final line, never ancestor elements', async () => {
 state.player = {currentTrack:ref({file:'test.mp3'}),currentTime:ref(0),seek:vi.fn()}
 const ancestorScroll = vi.fn()
 vi.stubGlobal('ResizeObserver', class {observe(){} disconnect(){}})
 HTMLElement.prototype.scrollIntoView = ancestorScroll
 host=document.createElement('div');document.body.append(host)
 app=createApp(LyricsPanel);app.mount(host)
 await new Promise(resolve=>setTimeout(resolve,0));await nextTick()
 const scroller=host.querySelector('button').parentElement
 Object.defineProperties(scroller,{clientHeight:{value:300},scrollHeight:{value:1000}})
 scroller.getBoundingClientRect=()=>({top:200})
 scroller.scrollTo=vi.fn()
 for(const line of scroller.querySelectorAll('button')) line.getBoundingClientRect=()=>({top:1150,height:40})
 state.player.currentTime.value=290
 await nextTick();await nextTick()
 expect(scroller.scrollTo).toHaveBeenCalledWith({top:700,behavior:'smooth'})
 expect(ancestorScroll).not.toHaveBeenCalled()
})
