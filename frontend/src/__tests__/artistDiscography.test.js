import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { discographySections } from '../lib/discography'

const labels = { albums: 'Albums', singles: 'Singles' }
const r = (id, name, release_type) => ({ album_id: id, name, release_type, url: `https://open.spotify.com/album/${id}` })

describe('artist discography shelves', () => {
  it('splits albums from singles/EPs without hiding same-title local albums', () => {
    const groups = discographySections(
      [r('1', 'Her Loss', 'Album'), r('2', 'Rich Flex', 'Single'), r('3', 'Scary Hours', 'EP'),
       r('4', 'Best Of', 'Compilation'), r('5', 'Owned One - EP', 'EP'), r('1', 'Her Loss', 'Album')],
      [{ title: 'Owned One' }], labels)
    expect(groups.map((g) => [g.id, g.items.map((i) => i.album_id)])).toEqual([
      ['albums', ['1', '4']],
      ['singles', ['2', '3', '5']],
    ])
  })
  it('hides empty shelves', () => {
    const twins = discographySections([r('a', 'ICEMAN', 'Album'), r('b', 'ICEMAN', 'Album'), r('c', 'ICEMAN', 'Single')], [], labels)
    expect(twins.map((g) => g.items.map((i) => i.album_id))).toEqual([['a', 'b'], ['c']])
    expect(discographySections([r('2', 'X', 'Single')], [], labels).map((g) => g.id)).toEqual(['singles'])
    expect(discographySections([], [], labels)).toEqual([])
  })
  it('artist Albums tab renders both shelves with the native release card', () => {
    const src = readFileSync(new URL('../views/ArtistView.vue', import.meta.url), 'utf8')
    expect(src).toContain('<ReleaseCard')
    expect(src).toContain('discographySections(')
    expect(src).toContain('API.resolveUrl(`https://open.spotify.com/artist/${id}`)')
  })
})
