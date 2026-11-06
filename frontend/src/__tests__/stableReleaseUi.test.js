import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
const src = path => readFileSync(new URL('../'+path, import.meta.url), 'utf8')
it('shares hover/focus-only type badges and the same green action glow on all cover cards', () => {
 for (const file of ['components/library/MediaTile.vue','components/search/ReleaseCard.vue']) {
  const component=src(file)
  expect(component).toContain('data-release-badge')
  expect(component).toContain('tile-badge')
  expect(component).toContain('tile-action-glow')
 }
 const css=src('index.css')
 expect(css).toMatch(/\.tile\s+\.tile-badge\s*\{[^}]*opacity:\s*0/s)
 expect(css).toContain('.tile:hover .tile-badge')
 expect(css).toContain('.tile:focus-within .tile-badge')
 expect(src('components/library/MediaTile.vue')).toContain("t('link.kind.playlist')")
 expect(src('views/HomeView.vue')).toContain(':release-type="album.release_type')
})
it('labels the local artist shelf Library and provider shelf Discography', () => {
 const artist=src('views/ArtistView.vue')
 expect(artist).toContain("t('library.title')")
 expect(artist).toContain("t('finder.discography')")
 expect(artist).not.toContain("t('artist.availableToDownload')")
})
it('never publishes an uninspected provider shelf while checking availability', () => {
 expect(src('views/ArtistView.vue')).not.toContain('inspectedDiscography.value = discography.value')
 expect(src('views/LinkView.vue')).not.toContain('inspectedReleases.value = d?.albums || []')
})
it('only Library release headers have no again state or redownload handler', () => {
 for(const name of ['Album']) {
  const source=src(`views/${name}View.vue`)
  const start=source.indexOf('function downloadAlbum()')
  expect(source.slice(start,source.indexOf('\n}',start)+2)).not.toContain('redownload')
 }
})
