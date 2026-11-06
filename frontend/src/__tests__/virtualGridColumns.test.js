import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { columnsFor } from '/src/lib/virtualGrid'

// Tailwind v4 emits min-[1900px]:grid-cols-7 before 2xl:grid-cols-6, so at
// >=1900px the CSS drew 6 columns while rows held 7 albums. The grid must
// take its column count from the same function that slices the rows.
describe('library virtual grid columns', () => {
  it('binds the drawn column count to columnsFor()', () => {
    const src = readFileSync(new URL('../components/library/VirtualGrid.vue', import.meta.url), 'utf8')
    expect(src).toContain('gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`')
  })
  it('uses 7 columns at wide windows', () => {
    expect(columnsFor(1920)).toBe(7)
    expect(columnsFor(1640)).toBe(6)
  })
})
