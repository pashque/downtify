import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')

it('link page keeps filters, source link and a menu in the hero action row, styled like album buttons', () => {
  const s = src('views/LinkView.vue')
  const actions = s.slice(s.indexOf('<template #actions>'), s.indexOf('</CollectionHero>'))
  expect(actions).toContain('data-link-filter')
  // Provider actions are available without opening the three-dot menu.
  expect(actions).toContain('data-link-source')
  expect(actions).toContain(':icon="action.icon"')
  expect(actions).toContain('@click="action.action"')
  expect(actions).toContain('v-for="action in providerActions"')
  expect(actions).toContain('<UiMenu :items="heroMenu"')
  expect(s).not.toContain('<UiChips')
  expect(s).not.toContain('variant="plain"')
})

it('album editions and link filters use the shared checked UiMenu without changing their update handlers', () => {
  const album = src('views/AlbumView.vue')
  const link = src('views/LinkView.vue')
  expect(album).toContain('<EditionMenu')
  expect(album).toContain('@update:model-value="selectEdition"')
  expect(album).not.toContain('<UiSelect')
  expect(link).toContain('<EditionMenu')
  expect(link).toContain('v-model="filter"')
  expect(link).not.toContain('<UiSelect')
})

it('ticking tracks turns the primary button into Download selected; the clear X sits atop the tick column', () => {
  const s = src('views/LinkView.vue')
  expect(s).toContain("selected.size ? downloadSelection() :")
  expect(s).toContain("`${t('link.downloadSelected')} (${selected.size})`")
  expect(s).not.toContain("t('library.selectedCount'")
  expect(s).toContain('@clear-selection="selected = new Set()"')
  const h = src('components/library/TrackDownPlayHeader.vue')
  expect(h).toContain('data-clear-selection')
  expect(h.indexOf('data-clear-selection')).toBeLessThan(h.indexOf('data-column="number"'))
})

it('link page artists are clickable and artist releases split into Albums / Singles', () => {
  const s = src('views/LinkView.vue')
  expect(s).toContain('data-link-artists')
  expect(s).toContain("router.push({ name: 'Artist', query: { name, tab: 'albums' } })")
  expect(s).toContain('await library.ensureArtists()')
  expect(s).toContain('API.getArtistSpotifyId(name)')
  expect(s).toContain('discographySections(inspectedReleases.value')
  expect(s).toContain('inspectDiscography(d.albums || [], localAlbums, API)')
})

it('mini player close stops playback', () => {
  const s = src('components/shell/MiniPlayer.vue')
  expect(s).toContain('data-player-close')
  expect(s).toContain('@click="player.stop()"')
})
