import { readFileSync } from 'node:fs'
import { expect, it } from 'vitest'

const read = (file) => readFileSync(new URL(file, import.meta.url), 'utf8')

it('search page shows label matches instead of a normal search for label: queries', () => {
  const view = read('../views/SearchView.vue')
  expect(view).toContain('LabelMatches')
  expect(view).toContain('labelFromQuery(query.value)')
  expect(view).toContain('if (labelFromQuery(value)) return')
})

it('each match opens that exact label page', () => {
  const component = read('../components/search/LabelList.vue')
  expect(component).toContain("name: 'Label'")
  expect(component).toContain('params: { label: item.name }')
})

it('the search box opens the list for plain label: text and the page for quoted names', () => {
  const box = read('../components/shell/GlobalSearch.vue')
  expect(box).toContain('isExactLabelQuery(text.value)')
  expect(box).toContain("name: 'Search'")
})
