// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import * as Vue from 'vue'
import { parse, compile } from '@vue/compiler-dom'
import ArtistCredits from '../components/library/ArtistCredits.vue'
import { createMemoryHistory, createRouter } from 'vue-router'

const rows = [
  ['library/TrackList.vue', 'row.track'],
  ['library/TrackDownPlay.vue', 'song'],
  ['search/SongRow.vue', 'song'],
  ['similar/SimilarTrackRow.vue', 'song'],
  ['library/TopSongsPanel.vue', 'row.song'],
  ['queue/QueueItem.vue', 'song'],
]
const source = path => readFileSync(new URL('../components/' + path, import.meta.url), 'utf8')
function artistParagraph(source) {
  const template = source.match(/<template>([\s\S]*?)<\/template>\s*<script/)[1]
  const ast = parse(template)
  const find = node => {
    if (node.tag === 'p' && node.props?.some(p => p.name === 'class' && p.value?.content === 'truncate text-[13px] text-muted')) return node
    for (const child of node.children || []) {
      const result = find(child)
      if (result) return result
    }
  }
  return find(ast)
}

describe.each(rows)('%s artist credits', (path, creditPath) => {
  it('forwards structured credits and fallback through the existing styled text container', () => {
    const s = source(path)
    expect(s).toContain("import ArtistCredits from '/src/components/library/ArtistCredits.vue'")
    const paragraph = artistParagraph(s)
    const links = paragraph.children.find(node => node.tag === 'ArtistCredits')
    expect(links).toBeDefined()
    expect(links.props.find(p => p.arg?.content === 'artists')?.exp?.content).toBe(`${creditPath}.artists`)
    expect(links.props.find(p => p.arg?.content === 'artist')?.exp?.content).toContain(`${creditPath}.artist`)
  })

  it('navigates each literal credit without bubbling click or double-click to playback', async () => {
    const paragraph = artistParagraph(source(path))
    expect(paragraph.loc.source).toContain('<ArtistCredits')
    const { code } = compile(paragraph.loc.source, { mode: 'function', prefixIdentifiers: true })
    // Only compile trusted, checked-in Vue template fragments, never user input.
    const render = new Function('Vue', code)(Vue)
    const song = { artists: ['Earth, Wind & Fire', 'Guest'], artist: 'wrong fallback', format: 'FLAC' }
    let playback = 0
    const root = document.createElement('div')
    const app = Vue.createApp({
      render: () => Vue.h('div', { onClick: () => playback++, onDblclick: () => playback++ }, [Vue.h({
        render,
        setup: () => ({ song, row: { track: song, song }, linkArtist: true, hideAlbum: false, artistName: song.artist, artists: song.artist }),
      })]),
    })
    app.component('ArtistCredits', ArtistCredits)
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path: '/', component: { render: () => null } },
      { path: '/library/artist', name: 'Artist', component: { render: () => null } },
    ] })
    app.use(router)
    await router.push('/')
    await router.isReady()
    app.mount(root)
    try {
      const links = root.querySelectorAll('a')
      expect(links).toHaveLength(2)
      expect(links[0].textContent).toBe('Earth, Wind & Fire')
      expect(links[0].getAttribute('href')).toBe(router.resolve({ name: 'Artist', query: { name: 'Earth, Wind & Fire' } }).href)
      expect(root.textContent).toContain('Earth, Wind & Fire, Guest')
      for (const event of ['click', 'dblclick']) links[0].dispatchEvent(new MouseEvent(event, { bubbles: true }))
      expect(playback).toBe(0)
    } finally { app.unmount() }
  })
})

it('the artist top songs shelf inherits artist navigation from its native TrackDownPlay rows', () => {
  expect(source('library/TopSongsShelf.vue')).toContain('<TrackDownPlay')
  expect(source('library/TrackDownPlay.vue')).toContain('<ArtistCredits')
})
