import { expect, it } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { releaseKicker } from '../lib/releaseType'

const t = (key) => ({ 'album.kicker': 'Album', 'album.kinds.album': 'Album', 'album.kinds.single': 'Single',
  'album.kinds.ep': 'EP', 'album.kinds.compilation': 'Compilation' })[key] || key

it('labels the release by its real type, Album only when unknown', () => {
  expect(releaseKicker('single', t)).toBe('Single')
  expect(releaseKicker('ep', t)).toBe('EP')
  expect(releaseKicker('compilation', t)).toBe('Compilation')
  expect(releaseKicker('album', t)).toBe('Album')
  expect(releaseKicker('', t)).toBe('Album')
  expect(releaseKicker('mixtape', t)).toBe('Album')
})

it('album source falls back to the authoritative local release tag when provider type is absent', async () => {
  const { effectiveReleaseType } = await import('../lib/releaseType')
  expect(effectiveReleaseType('', 'single')).toBe('single')
  expect(effectiveReleaseType('ep', 'single')).toBe('ep')
  expect(effectiveReleaseType('', '')).toBe('')
})

it('album and link pages use the release type', () => {
  const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')
  // Template refs auto-unwrap: no .value inside the template.
  expect(src('views/AlbumView.vue')).toContain('releaseKicker(effectiveType, t)')
  expect(src('views/AlbumView.vue')).toContain('effectiveReleaseType(releaseType.value, album.value?.release_type)')
  expect(src('model/albumSource.js')).toContain('release_type')
  expect(src('views/LinkView.vue')).toMatch(/releaseKicker\(d\.release_type, t\)/)
})

it('every locale names all four release types', () => {
  const dir = new URL('../i18n/locales/', import.meta.url)
  for (const file of readdirSync(dir)) {
    const s = readFileSync(new URL(file, dir), 'utf8')
    const block = s.slice(s.indexOf('kinds: {', s.indexOf('  album: {')))
    for (const k of ['album', 'single', 'ep', 'compilation']) expect(block, file).toMatch(new RegExp(`\\b${k}: '`))
  }
})

it('the album download button names the release type', async () => {
  const { downloadReleaseLabel } = await import('../lib/releaseType')
  const tt = (key) => ({ 'finder.downloadAlbum': 'Download album', 'album.downloadKind.single': 'Download single',
    'album.downloadKind.ep': 'Download EP', 'album.downloadKind.album': 'Download album',
    'album.downloadKind.compilation': 'Download compilation' })[key] || key
  expect(downloadReleaseLabel('single', tt)).toBe('Download single')
  expect(downloadReleaseLabel('ep', tt)).toBe('Download EP')
  expect(downloadReleaseLabel('', tt)).toBe('Download album')
  const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')
  expect(src('views/AlbumView.vue')).toContain('downloadReleaseLabel(effectiveType.value, t,')
  expect(src('views/LinkView.vue')).toContain('downloadReleaseLabel(details.value?.release_type, t,')
  const dir = new URL('../i18n/locales/', import.meta.url)
  for (const file of readdirSync(dir)) {
    const s = readFileSync(new URL(file, dir), 'utf8')
    const block = s.slice(s.indexOf('downloadKind: {', s.indexOf('  album: {')))
    for (const k of ['album', 'single', 'ep', 'compilation']) expect(block, file).toMatch(new RegExp(`\\b${k}: ["']`))
    expect(s, file).toMatch(/loadingTracks: ["']/)
  }
})

it('album hero shows grey spinning arrows while the full tracklist loads', () => {
  const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')
  const hero = src('components/library/CollectionHero.vue')
  expect(hero).toMatch(/v-if="loading && !banner"[\s\S]{0,200}data-hero-loading/)
  expect(hero).toMatch(/v-if="loading && banner"[\s\S]{0,200}data-hero-loading/)
  const spin = hero.slice(hero.indexOf('data-hero-loading'), hero.indexOf('data-hero-loading') + 600)
  expect(spin).toContain('name="refresh"')
  expect(spin).toContain('animate-spin')
  expect(spin).toMatch(/right-\d+ bottom-\d+/)
  expect(spin).not.toContain('bg-accent')
  expect(src('model/albumSource.js')).toMatch(/loading/)
  expect(src('views/AlbumView.vue')).toContain(':loading="sourceLoading || targetLoading"')
})
