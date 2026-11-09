import { readFileSync } from 'node:fs'
import { expect, it } from 'vitest'

const view = readFileSync(
  new URL('../views/SearchView.vue', import.meta.url),
  'utf8'
)

// The positions of the markers must be present and in the listed order.
const inOrder = (source, markers) => {
  const at = markers.map((m) => source.indexOf(m))
  expect(at.every((n) => n > -1)).toBe(true)
  expect([...at].sort((a, b) => a - b)).toEqual(at)
}

it('chips are All, Songs, Artists, Albums, Labels', () => {
  inOrder(view.slice(view.indexOf('const filters = computed')), [
    "id: 'all'",
    "id: 'songs'",
    "id: 'artists'",
    "id: 'albums'",
    "id: 'labels'",
  ])
})

it('result sections are Songs, Artists, Albums, Labels', () => {
  inOrder(view, [
    "show('songs') &&",
    "show('artists') &&",
    "show('albums') &&",
    "show('labels') &&",
  ])
})
