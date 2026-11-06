import { expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { columnsFor, columnGap, ROW_GAP } from '../lib/virtualGrid'

const SRC = new URL('..', import.meta.url).pathname
function vueFiles(dir) {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n)
    return statSync(p).isDirectory() ? vueFiles(p) : p.endsWith('.vue') ? [p] : []
  })
}

it('card grids everywhere use the shared tile-grid, not their own column sets', () => {
  const stray = vueFiles(SRC).filter((f) => /grid grid-cols-2 gap-x-[45] gap-y-[67] sm:grid-cols-3/.test(readFileSync(f, 'utf8')))
  expect(stray).toEqual([])
})

it('tile-grid columns and gaps match the Library virtual grid', () => {
  const css = readFileSync(join(SRC, 'index.css'), 'utf8')
  for (const [w, cols] of [[640, 3], [768, 4], [1024, 5], [1536, 6], [1900, 7]]) {
    expect(columnsFor(w)).toBe(cols)
    expect(css).toContain(`@media (min-width: ${w}px) { .tile-grid { grid-template-columns: repeat(${cols}, minmax(0, 1fr)); } }`)
  }
  expect(columnGap(500)).toBe(20); expect(css).toContain('.tile-grid { column-gap: 20px; }')
  expect(css).toContain(`row-gap: ${ROW_GAP}px;`)
})
