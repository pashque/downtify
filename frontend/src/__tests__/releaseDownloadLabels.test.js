import { expect, it } from 'vitest'
import { readdirSync } from 'node:fs'
import { downloadReleaseLabel } from '../lib/releaseType'
import en from '../i18n/locales/en'
const t = key => key.split('.').reduce((o, k) => o?.[k], en) || key

it.each([
  ['album', 'Download album', 'Download full album', 'Download album again'],
  ['single', 'Download single', 'Download full single', 'Download single again'],
  ['ep', 'Download EP', 'Download full EP', 'Download EP again'],
  ['compilation', 'Download compilation', 'Download full compilation', 'Download compilation again'],
  ['', 'Download album', 'Download full album', 'Download album again'],
  ['unknown', 'Download album', 'Download full album', 'Download album again'],
])('labels all destination completeness states for %s', (type, none, partial, complete) => {
  expect(downloadReleaseLabel(type, t)).toBe(none)
  expect(downloadReleaseLabel(type, t, 'partial')).toBe(partial)
  expect(downloadReleaseLabel(type, t, 'complete')).toBe(complete)
})

it('every locale translates each type and destination completeness state', async () => {
  for (const file of readdirSync(new URL('../i18n/locales/', import.meta.url))) {
    const { default: locale } = await import(`../i18n/locales/${file.replace(/\.js$/, '')}.js`)
    for (const key of ['downloadKind', 'downloadFullKind', 'downloadAgainKind']) {
      for (const type of ['album', 'single', 'ep', 'compilation']) {
        expect(locale.album[key]?.[type], `${file}: ${key}.${type}`).toEqual(expect.any(String))
        expect(locale.album[key][type].trim()).not.toBe('')
        if (key !== 'downloadKind') expect(locale.album[key][type]).not.toBe(locale.album.downloadKind[type])
      }
    }
  }
})
