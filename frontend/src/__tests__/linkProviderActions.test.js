// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { computed, ref } from 'vue'
import { openAlbumOn, openYouTubeMusic, songProvider } from '../lib/sourceLinks'
import { FILLED, STROKE } from '../components/ui/icons'

// Exercise the view's actual computed actions, isolated from unrelated playback,
// library polling and router setup. Both the menu and buttons share these actions.
const view = readFileSync(`${process.cwd()}/src/views/LinkView.vue`, 'utf8')
// Only trusted, checked-in component source is evaluated here; never user data.
const actionsCode = view.slice(view.indexOf('const heroMenu ='), view.indexOf('// The primary button downloads'))
function actions(source, url) {
  const API = { spotifyLink: vi.fn(), youtubeMusicLink: vi.fn() }
  const ui = { toast: vi.fn() }
  const build = new Function('computed', 'details', 'kind', 'url', 'sourceLabel', 'sourceIcon', 't', 'API', 'ui', 'songProvider', 'openAlbumOn', 'openYouTubeMusic', `${actionsCode}; return { items: providerActions.value, menu: heroMenu.value }`)
  const items = build(computed,
    ref({ kind: 'album', name: 'Album title', tracks: [{ album_artist: 'Album Artist', artists: ['Guest'] }] }),
    ref({ source }), ref(url), ref(`link.open${source}`), ref(source === 'youtube' ? 'youtube-music' : source),
    key => key, API, ui, songProvider, openAlbumOn, openYouTubeMusic)
  return { ...items, API, ui }
}
afterEach(() => vi.restoreAllMocks())
it.each([
  ['spotify', 'https://open.spotify.com/album/exact', 'spotify', 'youtube-music', 'youtubeMusicLink', 'https://music.youtube.com/browse/MPREexact'],
  ['youtube', 'https://music.youtube.com/browse/MPREoriginal', 'youtube-music', 'spotify', 'spotifyLink', 'https://open.spotify.com/album/matched'],
])('restored %s album buttons open the known source and resolve the other real album', async (source, ownUrl, ownIcon, otherIcon, lookupName, target) => {
  const tab = { opener: {}, location: { href: '' }, close: vi.fn() }
  const open = vi.spyOn(window, 'open').mockImplementation(() => tab)
  const { items, menu, API } = actions(source, ownUrl)
  expect(items).toHaveLength(1)
  expect(items[0].icon).toBe(ownIcon)
  for (const item of items) expect(STROKE[item.icon] || FILLED[item.icon]).toBeTruthy()
  await items.find(item => item.icon === ownIcon).action()
  expect(open).toHaveBeenLastCalledWith(ownUrl, '_blank', 'noopener')
  expect(API.spotifyLink).not.toHaveBeenCalled()
  expect(API.youtubeMusicLink).not.toHaveBeenCalled()
  API[lookupName].mockResolvedValue({ data: { url: target } })
  await menu.find(item => item.icon === otherIcon).action()
  expect(API[lookupName]).toHaveBeenCalledWith(expect.objectContaining({ kind: 'album', title: 'Album title', artist: 'Album Artist' }))
  expect(tab.location.href).toBe(target)
  expect(tab.opener).toBeNull()
  expect(target).not.toContain('search')
})
it('keeps the Deezer source button alongside both album resolvers', async () => {
  const open = vi.spyOn(window, 'open').mockImplementation(() => null)
  const { items } = actions('deezer', 'https://www.deezer.com/album/123')
  expect(items.map(item => item.icon)).toEqual(['deezer'])
  await items[0].action()
  expect(open).toHaveBeenCalledWith('https://www.deezer.com/album/123', '_blank', 'noopener')
})
it('closes the pending provider tab and reports missing albums rather than opening search', async () => {
  const tab = { location: { href: '' }, close: vi.fn() }
  vi.spyOn(window, 'open').mockImplementation(() => tab)
  const { menu, API, ui } = actions('spotify', 'https://open.spotify.com/album/exact')
  API.youtubeMusicLink.mockRejectedValue(new Error('not found'))
  await menu.find(item => item.icon === 'youtube-music').action()
  expect(tab.close).toHaveBeenCalledOnce()
  expect(tab.location.href).toBe('')
  expect(ui.toast).toHaveBeenCalledWith('link.notOnYoutubeMusic', { kind: 'error' })
})
