// @vitest-environment happy-dom
import { expect, it, vi } from 'vitest'
import { createApp, h } from 'vue'
const push = vi.hoisted(() => vi.fn())
const lookup = vi.hoisted(() => vi.fn())
const toast = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('/src/i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('/src/model/api', () => ({ default: { youtubeMusicLink: lookup } }))
vi.mock('/src/model/ui', () => ({ useUi: () => ({ toast }) }))
vi.mock('../components/ui/UiMenu.vue', () => ({ default: { props:['items','label','size'], template:'<button v-for="item in items.filter(i=>!i.hidden)" @click="item.action">{{ item.label }}</button>' } }))
import SourceSongMenu from '../components/library/SourceSongMenu.vue'
import { youtubeMusicUrl } from '../lib/sourceLinks'
const flush = async () => { for (let i = 0; i < 6; i++) await Promise.resolve() }
function mount(song) {
 const root=document.createElement('div')
 const app=createApp({ render: () => h(SourceSongMenu,{song}) })
 app.mount(root)
 return { app, button: label => [...root.querySelectorAll('button')].find(b => b.textContent === label) }
}
it('keeps the former source-row Similar action in the native menu with original metadata', () => {
 const m=mount({name:'Track & title',artists:['Artist, duo']})
 m.button('similar.findSimilar').click()
 expect(push).toHaveBeenCalledWith({name:'Similar',query:{artist:'Artist, duo',track:'Track & title'}})
 m.app.unmount()
})
it('labels a Spotify song as Spotify and opens its real YouTube Music track, not Spotify or a search', async () => {
 const tab={ location:{ href:'' }, close: vi.fn(), opener: 'x' }
 const open=vi.spyOn(window,'open').mockImplementation((url)=> url ? null : tab)
 lookup.mockResolvedValue({ data:{ url:'https://music.youtube.com/watch?v=abcDEF12345' } })
 const m=mount({name:'Rich Flex',artists:['Drake','21 Savage'],duration:239,url:'https://open.spotify.com/track/abc',source:'youtube'})
 expect(m.button('search.openSource')).toBeUndefined()
 m.button('link.openSpotify').click()
 expect(open).toHaveBeenLastCalledWith('https://open.spotify.com/track/abc','_blank','noopener')
 m.button('link.openYoutube').click(); await flush()
 expect(lookup).toHaveBeenCalledWith({ kind:'track', artist:'Drake, 21 Savage', artists:['Drake','21 Savage'], title:'Rich Flex', duration:239 })
 expect(tab.location.href).toBe('https://music.youtube.com/watch?v=abcDEF12345')
 expect(tab.opener).toBe(null)
 m.app.unmount(); open.mockRestore()
})
it('closes the tab and says so when YouTube Music has no match', async () => {
 const tab={ location:{ href:'' }, close: vi.fn() }
 const open=vi.spyOn(window,'open').mockImplementation(()=>tab)
 lookup.mockRejectedValue(new Error('404'))
 const m=mount({name:'Nothing',artists:['Nobody'],url:'https://open.spotify.com/track/x'})
 m.button('link.openYoutube').click(); await flush()
 expect(tab.close).toHaveBeenCalled(); expect(tab.location.href).toBe('')
 expect(toast).toHaveBeenCalledWith('link.notOnYoutubeMusic', { kind:'error' })
 m.app.unmount(); open.mockRestore()
})
it('never builds a search URL; uses a known video directly', () => {
 expect(youtubeMusicUrl({video_id:'abcdefghijk',name:'x'})).toBe('https://music.youtube.com/watch?v=abcdefghijk')
 expect(youtubeMusicUrl({url:'https://music.youtube.com/watch?v=abcdefghijk'})).toBe('https://music.youtube.com/watch?v=abcdefghijk')
 expect(youtubeMusicUrl({name:'Rich Flex',artists:['Drake']})).toBe('')
})
