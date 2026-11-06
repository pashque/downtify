import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')

it('playlist header has no completion status or extra row beneath the actions', () => {
  const playlist = src('views/PlaylistView.vue').split('<script setup>')[0]
  expect(playlist).not.toContain('<PlaylistStatus')
  expect(playlist).not.toContain('data-playlist-completion')
  expect(playlist).not.toContain('#status')
})

it('compact collection heroes extend through phone landscape without sm size overrides', () => {
  const hero = src('components/library/CollectionHero.vue')
  expect(hero).toContain('max-lg:grid-cols-[120px_minmax(0,1fr)]')
  expect(hero).not.toContain('sm:size-56')
  expect(hero).not.toContain('sm:text-5xl')
  expect(src('index.css')).toContain('@media (max-width: 1023px)')
})

it('all collection hero backgrounds use the same artwork palette as progress bars with a no-art fallback', () => {
  const hero = src('components/library/CollectionHero.vue')
  expect(hero).toContain("import { useCoverPalette } from '/src/model/coverPalette'")
  expect(hero).toContain('useCoverPalette(paletteTrack)')
  expect(hero).toContain('props.cover || props.covers.find(Boolean) || props.coverFallback')
  expect(hero).toContain('palette.value?.primary')
  expect(hero).toContain('hueFor(props.name || props.title)')
})
