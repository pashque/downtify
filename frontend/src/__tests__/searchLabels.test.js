import { readFileSync } from 'node:fs'
import { expect, it } from 'vitest'

const read = (file) => readFileSync(new URL(file, import.meta.url), 'utf8')

it('normal search offers a Labels chip with a count and a section', () => {
  const view = read('../views/SearchView.vue')
  expect(view).toContain("id: 'labels'")
  expect(view).toContain("show('labels')")
  expect(view).toContain('LabelList')
  expect(view).toContain('labelFinder.labels.value')
})

it('ordinary searches ask for the light label lookup', () => {
  const view = read('../views/SearchView.vue')
  expect(view).toContain('useLabelFinder')
  expect(view).toContain('fuzzy: false')
})

it('label results count as results so a label-only search is not empty', () => {
  const view = read('../views/SearchView.vue')
  expect(view).toMatch(/hasResults[\s\S]*labelFinder\.labels\.value\.length/)
})

it('the api facade can request the light lookup', () => {
  const api = read('../model/api.js')
  expect(api).toContain('fuzzy')
})

it('label rows are shared by the search list and the label: list', () => {
  expect(read('../components/search/LabelList.vue')).toContain("name: 'Label'")
  expect(read('../components/search/LabelMatches.vue')).toContain('LabelList')
})

it('label rows have no thumbnails because Spotify has no label logos', () => {
  const list = read('../components/search/LabelList.vue')
  expect(list).not.toContain('CoverArt')
  expect(list).not.toContain('<img')
  expect(list).not.toContain('item.image')
})
