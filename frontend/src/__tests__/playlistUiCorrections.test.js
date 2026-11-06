import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { AVAILABLE_LOCALES } from '../i18n'
import en from '../i18n/locales/en.js'
const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')

it('artist catalog singles and EPs have an explicit combined shelf label', () => {
  expect(en.artist.singlesAndEps).toBe('Singles and EPs')
  for (const view of ['ArtistView', 'LinkView']) {
    expect(src(`views/${view}.vue`)).toContain("singles: t('artist.singlesAndEps')")
  }
})

it('Share has no trailing ellipsis in any locale', () => {
  expect(en.sharing.share).toBe('Share')
  for (const { messages } of AVAILABLE_LOCALES) expect(messages.sharing.share).not.toMatch(/(?:…|\.{3})$/)
})

it('playlist missing download shares the neutral native album button and phone icon-only styling', () => {
  const playlist = src('views/PlaylistView.vue')
  const button = playlist.match(/<UiButton\s+v-if="batch\?\.missing_count"[\s\S]*?<\/UiButton>/)?.[0]
  expect(button).toContain('variant="ghost"')
  expect(button).toContain('icon="download"')
  expect(button).toContain('@click="playlistActions.downloadMissing(playlist)"')
  expect(src('index.css')).toContain(".hero-actions [data-has-icon]:not([data-variant='primary']) .ui-btn-label")
  expect(src('components/ui/UiButton.vue')).toContain('shrink-0')
})

it('Library collection sorting reuses the edition/dots popup without converting settings selects', () => {
  const library = src('views/LibraryView.vue')
  expect(library).toMatch(/<EditionMenu\s+v-if="tab !== 'tracks'"\s+v-model="sortKey"/)
  expect(src('views/SettingsView.vue')).toContain('<UiSelect')
  expect(src('views/PodcastsView.vue')).toContain('<UiSelect')
})
