// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
const f = vi.hoisted(() => ({ play: vi.fn(), start: vi.fn(), retry: vi.fn(), remove: vi.fn(), retryWithAudio: vi.fn(), local: null, album: null, playable: null }))
vi.mock('/src/model/library', () => ({ useLibrary: () => ({ tracksByFile: ref(new Map(f.local ? [[f.local.file, f.local]] : [])), findAlbum: () => f.album }) }))
vi.mock('/src/model/download', () => ({ useDownloadManager: () => ({ retry: f.retry, remove: f.remove, retryWithAudio: f.retryWithAudio }) }))
vi.mock('/src/model/trackActions', () => ({ useTrackActions: () => ({ play: f.play }) }))
vi.mock('/src/model/songPlay', () => ({ useSongPlay: () => ({ playable: f.playable, ensurePlaying: f.start }) }))
vi.mock('/src/i18n', () => ({ useI18n: () => ({ t: key => key }) }))
import QueueItem from '../components/queue/QueueItem.vue'
let app, root, router
const song = { name: 'Track', artist: 'Guest; Owner', artists: ['Guest', 'Owner'], album_name: 'Album', album_artist: 'Owner' }
async function mount(item = {}) {
  router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/', name: 'Home', component: {} }, { path: '/album', name: 'Album', component: {} },
    { path: '/artist', name: 'Artist', component: {} }, { path: '/link', name: 'Link', component: {} },
  ] })
  await router.push('/')
  root = document.createElement('div'); document.body.append(root)
  app = createApp({ render: () => h(QueueItem, { item: { song, state: 'queued', ...item } }) }).use(router)
  app.mount(root); await nextTick()
}
beforeEach(() => { vi.clearAllMocks(); f.local = null; f.album = null; f.playable = ref(true) })
afterEach(() => { app?.unmount(); root?.remove() })
it('plays from row background, title and cover, never queues a download', async () => {
  await mount()
  root.querySelector('article').click()
  ;[...root.querySelectorAll('span')].find(el => el.textContent === 'Track').click()
  root.querySelector('article > div > div, article > div > img').click()
  expect(f.start).toHaveBeenCalledTimes(3)
  expect(f.retry).not.toHaveBeenCalled(); expect(f.remove).not.toHaveBeenCalled()
})
it('opens a Library album using authoritative grouping artist without playback', async () => {
  f.album = { title: 'Album', artist: 'Owner' }
  await mount()
  const album = root.querySelector('[data-queue-album]')
  expect(album?.getAttribute('href')).toBe('/album?artist=Owner&title=Album')
  album.click(); await nextTick()
  expect(f.start).not.toHaveBeenCalled()
  root.querySelector('[data-artist-credit]').click(); await nextTick()
  expect(f.start).not.toHaveBeenCalled()
})
it('opens an actual known album source when the album is not local', async () => {
  await mount({ song: { ...song, album_url: 'https://open.spotify.com/album/known', url: 'https://open.spotify.com/track/not-an-album' } })
  expect(root.querySelector('[data-queue-album]')?.getAttribute('href')).toBe('/link?url=https://open.spotify.com/album/known')
})
it('preserves controls, form input and text selection without starting playback', async () => {
  await mount({ state: 'failed' })
  root.querySelector('input').click()
  root.querySelector('label').click()
  const retry = [...root.querySelectorAll('button')].find(el => el.textContent.includes('queue.retry'))
  retry.click()
  root.querySelector('[aria-label="queue.remove"]').click()
  expect(f.retry).toHaveBeenCalledOnce(); expect(f.remove).toHaveBeenCalledOnce()
  const selection = vi.spyOn(window, 'getSelection').mockReturnValue({ toString: () => 'selected text' })
  root.querySelector('article').click(); selection.mockRestore()
  expect(f.start).not.toHaveBeenCalled()
})
it('does not play incomplete unresolved metadata', async () => {
  f.playable.value = false
  await mount({ song: { name: 'Track' } })
  root.querySelector('article').click()
  expect(f.start).not.toHaveBeenCalled()
})
it('keeps unknown sources on the grouping-artist Album route, never a track URL', async () => {
  await mount({ song: { ...song, album_artist: 'Various Artists', url: 'https://open.spotify.com/track/not-an-album' } })
  expect(root.querySelector('[data-queue-album]').getAttribute('href')).toBe('/album?artist=Guest&title=Album')
})
it('row keyboard playback excludes descendant controls and modifier clicks', async () => {
  await mount({ state: 'failed' })
  const article = root.querySelector('article')
  article.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  article.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }))
  root.querySelector('input').dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
  article.dispatchEvent(new MouseEvent('click', { bubbles: true, ctrlKey: true }))
  expect(f.start).toHaveBeenCalledTimes(2)
})
it('plays an exact completed file once and excludes its save link', async () => {
  f.local = { file: 'Owner/Track.mp3', title: 'Track', artist: 'Owner' }
  await mount({ state: 'done', filename: f.local.file, web_download_url: '/save' })
  root.querySelector('[aria-label="actions.play"]').click()
  expect(f.play).toHaveBeenCalledExactlyOnceWith([f.local], 0, null)
  root.querySelector('a[download]').dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
  expect(f.play).toHaveBeenCalledTimes(1); expect(f.start).not.toHaveBeenCalled()
})
