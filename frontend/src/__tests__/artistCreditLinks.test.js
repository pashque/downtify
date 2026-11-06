// @vitest-environment happy-dom
import { afterEach, expect, it } from 'vitest'
import { createApp, h, nextTick } from 'vue'
import { createRouter, createMemoryHistory } from 'vue-router'
import ArtistLinks from '../components/library/ArtistCredits.vue'
import { normalizeTrack } from '../lib/library'
let app, root, router
afterEach(() => { app?.unmount(); root?.remove() })
async function mount(props, onClick) {
  router=createRouter({history:createMemoryHistory(),routes:[{path:'/',component:{render:()=>null}},{path:'/library/artist',name:'Artist',component:{render:()=>null}}]})
  await router.push('/'); await router.isReady()
  root=document.createElement('div');document.body.append(root)
  app=createApp({render:()=>h('div',{onClick},[h(ArtistLinks,props)])});app.use(router);app.mount(root)
  return root.querySelectorAll('a')
}
it('links each structured artist separately to their own Library page',async()=>{
  const links=await mount({artists:['Drake','21 Savage']})
  expect([...links].map(a=>a.textContent)).toEqual(['Drake','21 Savage'])
  expect(root.textContent).toBe('Drake, 21 Savage')
  links[1].click();await new Promise(resolve=>setTimeout(resolve,20));await nextTick()
  expect(router.currentRoute.value.query.name).toBe('21 Savage')
})
it('preserves literal comma names and only splits legacy semicolon credits',async()=>{
  const links=await mount({artist:'Earth, Wind & Fire; Guest'})
  expect([...links].map(a=>a.textContent)).toEqual(['Earth, Wind & Fire','Guest'])
})
it('keeps normalized Tyler credits as one complete artist link', async () => {
  const track = normalizeTrack({ artist: 'Tyler, The Creator', title: 'EARFQUAKE' })
  const links = await mount(track)
  expect([...links].map(a => a.textContent)).toEqual(['Tyler, The Creator'])
  expect(root.textContent).toBe('Tyler, The Creator')
  links[0].click(); await new Promise(resolve => setTimeout(resolve, 20)); await nextTick()
  expect(router.currentRoute.value.query.name).toBe('Tyler, The Creator')
})
it.each([
  ['Tyler, The Creator', 'Daniel Caesar'],
  [{ name: 'Tyler, The Creator' }, { name: 'Daniel Caesar' }],
])('uses structured collaboration credits instead of ambiguous display text: %j', async (...artists) => {
  const track = normalizeTrack({
    artist: 'Tyler, The Creator, Daniel Caesar', artists, title: 'ST. CHROMA',
  })
  const links = await mount(track)
  expect([...links].map(a => a.textContent)).toEqual(['Tyler, The Creator', 'Daniel Caesar'])
  expect(track.albumArtist).toBe('Tyler, The Creator')
  expect(root.textContent).toBe('Tyler, The Creator, Daniel Caesar')
  links[1].click(); await new Promise(resolve => setTimeout(resolve, 20)); await nextTick()
  expect(router.currentRoute.value.query.name).toBe('Daniel Caesar')
})
it('does not trigger the surrounding row/card action',async()=>{
  let clicked=0
  const links=await mount({artists:['Artist']},()=>clicked++)
  links[0].click();await nextTick()
  expect(clicked).toBe(0)
})
