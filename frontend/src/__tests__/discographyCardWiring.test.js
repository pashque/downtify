import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const source = path => readFileSync(new URL(path, import.meta.url), 'utf8')
it('artist availability is physically inspected and refreshed on completion and local file changes', () => {
  const artist = source('../views/ArtistView.vue')
  expect(artist.includes("t('finder.discography')")).toBe(true)
  expect(artist.includes("t('library.title')")).toBe(true)
  expect(artist).toContain('inspectDiscography(')
  expect(artist).toContain('tracker.queueVersion.value')
  expect(artist).toContain('inspectedDiscography.value')
})
it('Library album cover has a release badge and no per-album hide menu', () => {
  const library = source('../views/LibraryView.vue')
  expect(library).toContain('releaseType: item.release_type')
  expect(library).not.toContain("if (tab.value === 'albums') return visibility.albumMenu(item)")
  const tile = source('../components/library/MediaTile.vue')
  expect(tile).toContain('v-else-if="typeLabel"')
  expect(tile).toContain("releaseKicker(props.releaseType, t)")
  expect(tile).toContain('absolute top-2.5 left-2.5 rounded-full bg-black/55 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur')
})
