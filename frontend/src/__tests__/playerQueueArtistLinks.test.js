import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, ref } from 'vue'
import { renderToString } from '@vue/server-renderer'
import { createMemoryHistory, createRouter } from 'vue-router'
import UpNextPanel from '../components/player/UpNextPanel.vue'
import TrackDetails from '../components/player/TrackDetails.vue'

vi.mock('/src/model/player', () => ({ usePlayer: () => ({
  currentTrack: ref({ title: 'Current', artist: 'wrong joined fallback', artists: ['Earth, Wind & Fire', 'Guest'], file: 'song.mp3' }),
  played: ref([{ index: 0, track: { title: 'Played', artist: 'First; Second' } }]),
  upcoming: ref([{ index: 2, track: { title: 'Upcoming', artists: ['Next Artist'], duration: 10 } }]),
  isPlaying: ref(true), shuffle: ref(false),
}) }))
vi.mock('/src/i18n', () => ({ useI18n: () => ({ t: (key) => key, locale: ref('en') }) }))
vi.mock('/src/model/api', () => ({ default: { getAudioDetails: vi.fn(async () => ({})) } }))

it.each([UpNextPanel, TrackDetails])('renders real Library artist links without copying fullscreen query (%s)', async (component) => {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/', name: 'Home', component: {} },
    { path: '/artist', name: 'Artist', component: {} },
  ] })
  await router.push('/?np=1&panel=queue')
  const html = await renderToString(createSSRApp(component).use(router))
  expect(html).toContain('href="/artist?name=Earth,+Wind+%26+Fire"')
  expect(html).toContain('href="/artist?name=Guest"')
  expect(html).not.toContain('wrong joined fallback')
  expect(html).not.toMatch(/href="[^"]*[?&](?:np|panel)=/)
  if (component === UpNextPanel) {
    expect(html).toContain('href="/artist?name=First"')
    expect(html).toContain('href="/artist?name=Second"')
    expect(html).toContain('href="/artist?name=Next+Artist"')
  }
})
import { readFileSync } from 'node:fs'
import { parse as parseSfc } from '@vue/compiler-sfc'
import { baseParse } from '@vue/compiler-dom'

const source = (path) => readFileSync(new URL(`../components/${path}`, import.meta.url), 'utf8')
function nodes(path) {
  const text = source(path)
  const root = baseParse(parseSfc(text).descriptor.template.content)
  const result = []
  function visit(node, ancestors = []) {
    if (node.type === 1) result.push({ node, ancestors })
    for (const child of node.children || []) visit(child, [...ancestors, node])
  }
  visit(root)
  return { text, elements: result }
}
const bound = (node, name) => node.props.find((p) => p.type === 7 && p.name === 'bind' && p.arg?.content === name)?.exp?.content

describe('player and download queue artist navigation', () => {
  it('track details links individual credits and keeps clean album/grouping artist routes', () => {
    const { text, elements } = nodes('player/TrackDetails.vue')
    const credit = elements.find(({ node }) => node.tag === 'ArtistCredits')?.node
    expect(credit).toBeDefined()
    expect(bound(credit, 'artists')).toBe('track.artists')
    expect(bound(credit, 'artist')).toBe('track.artist')
    expect(text).toContain("kind: 'artist'")
    // The Go to album / Go to artist / Save buttons were removed on request;
    // artist credits are the only links left.
    const routes = elements.filter(({ node }) => node.tag === 'RouterLink')
    expect(routes).toHaveLength(0)
    expect(text).not.toContain('nowPlaying.close')
  })
  it('download queue preserves structured artists and the unknown-artist fallback', () => {
    const { text, elements } = nodes('queue/QueueItem.vue')
    const credit = elements.find(({ node }) => node.tag === 'ArtistCredits')?.node
    expect(credit).toBeDefined()
    expect(bound(credit, 'artists')).toBe('song.artists')
    expect(bound(credit, 'artist')).toBe("song.artist || t('common.unknownArtist')")
    expect(text).toContain('song.album_name')
    expect(text).not.toContain('nowPlaying.close')
  })
  it('Up next gives played/current/upcoming independent artist links outside playback buttons', () => {
    const { text, elements } = nodes('player/UpNextPanel.vue')
    const links = elements.filter(({ node }) => node.tag === 'ArtistCredits')
    expect(links).toHaveLength(3)
    expect(links.map(({ node }) => bound(node, 'artists'))).toEqual(['item.track.artists', 'current.artists', 'item.track.artists'])
    expect(links.map(({ node }) => bound(node, 'artist'))).toEqual(['item.track.artist', 'current.artist', 'item.track.artist'])
    for (const { ancestors } of links) expect(ancestors.some((n) => n.tag === 'button')).toBe(false)
    // Cover and title remain keyboard-operable playback actions in both lists.
    const playButtons = elements.filter(({ node }) => node.tag === 'button' && node.props.some((p) => p.name === 'on' && p.exp?.content === 'player.playAt(item.index)'))
    expect(playButtons).toHaveLength(4)
    expect(text.match(/\bh-14\b/g)).toHaveLength(3)
    expect(text).toContain('onMounted(showCurrent)')
    expect(text).toContain('[overflow-anchor:none]')
    // Only the playing-row reveal watches; no other reactive side effects.
    expect(text.match(/watch\(/g)).toHaveLength(1)
    expect(text).toContain('watch(() => player.currentIndex.value, revealCurrent)')
    expect(text).not.toContain('nowPlaying.close')
  })
})
