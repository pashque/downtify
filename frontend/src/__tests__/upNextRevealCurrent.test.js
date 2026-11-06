import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { revealScrollTop } from '../lib/revealRow'

it('leaves the list alone while the playing row is already fully visible', () => {
  expect(revealScrollTop({ scrollTop: 100, viewHeight: 400, rowTop: 150, rowHeight: 56, maxScroll: 2000 })).toBeNull()
  expect(revealScrollTop({ scrollTop: 100, viewHeight: 400, rowTop: 444, rowHeight: 56, maxScroll: 2000 })).toBeNull()
})

it('brings an off-screen playing row to about a third of the view, clamped', () => {
  // Below the view.
  expect(revealScrollTop({ scrollTop: 0, viewHeight: 300, rowTop: 1000, rowHeight: 56, maxScroll: 5000 })).toBe(900)
  // Above the view.
  expect(revealScrollTop({ scrollTop: 900, viewHeight: 300, rowTop: 200, rowHeight: 56, maxScroll: 5000 })).toBe(100)
  // Partly hidden counts as hidden; near the edges it clamps.
  expect(revealScrollTop({ scrollTop: 0, viewHeight: 300, rowTop: 280, rowHeight: 56, maxScroll: 5000 })).toBe(180)
  expect(revealScrollTop({ scrollTop: 300, viewHeight: 300, rowTop: 20, rowHeight: 56, maxScroll: 5000 })).toBe(0)
  expect(revealScrollTop({ scrollTop: 0, viewHeight: 300, rowTop: 1990, rowHeight: 56, maxScroll: 1800 })).toBe(1800)
})

it('Up next follows the playing track with a smooth scroll of its own list only', () => {
  const s = readFileSync(new URL('../components/player/UpNextPanel.vue', import.meta.url), 'utf8')
  expect(s).toContain('watch(() => player.currentIndex.value')
  expect(s).toContain('revealScrollTop(')
  expect(s).toContain("behavior: 'smooth'")
  expect(s).not.toContain('scrollIntoView')
})
