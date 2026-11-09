// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import AlbumLabelKicker from '/src/components/library/AlbumLabelKicker.vue'
const mocks = vi.hoisted(() => ({ albumLabel: vi.fn() }))
vi.mock('/src/model/api', () => ({ default: mocks }))
let app, element

afterEach(() => { app?.unmount(); element?.remove(); vi.clearAllMocks() })

it('renders an exact clickable label in the header without brackets', async () => {
  mocks.albumLabel.mockResolvedValue({data:{label:'LUCKYME®'}})
  const router = createRouter({ history:createMemoryHistory(), routes:[{path:'/label/:label', name:'Label', component:{template:'<div />'}}] })
  element = document.createElement('div'); document.body.append(element)
  app = createApp(AlbumLabelKicker, {text:'Album · 2026',albumId:'0eyTz4axCv1nyRSCHxDNY0'})
  app.use(router); app.mount(element)
  await Promise.resolve(); await nextTick(); await nextTick()
  expect(element.textContent).toBe('Album · 2026 · LUCKYME®')
  expect(element.querySelector('a').getAttribute('href')).toBe('/label/LUCKYME%C2%AE')
})

it('omits both the label and separator when metadata is unavailable', async () => {
  mocks.albumLabel.mockRejectedValue(new Error('unavailable'))
  element = document.createElement('div'); document.body.append(element)
  app = createApp(AlbumLabelKicker, {text:'Album · 2026',albumId:'0eyTz4axCv1nyRSCHxDNY0'})
  app.mount(element)
  await Promise.resolve(); await nextTick(); await nextTick()
  expect(element.textContent).toBe('Album · 2026')
  expect(element.querySelector('a')).toBeNull()
})
