import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

it('wires the label route to native release cards and the static API facade', () => {
  const view = readFileSync(
    new URL('../views/LabelView.vue', import.meta.url),
    'utf8'
  )
  const router = readFileSync(
    new URL('../router/index.js', import.meta.url),
    'utf8'
  )
  expect(router).toContain("path: '/label/:label'")
  expect(view).toContain('ReleaseCard')
  expect(view).toContain('api.labelReleases')
  expect(view).toContain("t('labels.limited')")
  expect(view).toContain('state.error.value')
  expect(view).toContain('state.load(label)')
})

it('renders the scanning year as text so it has no thousands separator', () => {
  const source = readFileSync(
    new URL('../views/LabelView.vue', import.meta.url),
    'utf8'
  )
  expect(source).toContain('year: String(state.year.value)')
})
