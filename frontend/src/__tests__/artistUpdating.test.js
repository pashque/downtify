import { expect, it } from 'vitest'
import { ref } from 'vue'
import { readFileSync } from 'node:fs'

const view = readFileSync(`${process.cwd()}/src/views/ArtistView.vue`, 'utf8')
const hero = readFileSync(`${process.cwd()}/src/components/library/CollectionHero.vue`, 'utf8')

it('shows the shared round-arrow indicator for pending artist updates in both hero layouts', () => {
  expect(view).toContain(':loading="artistUpdating"')
  expect(hero).toContain('data-hero-loading')
  expect(hero).toContain('class="animate-spin"')
  expect(hero).toContain('v-if="loading && !banner"')
  expect(hero).toContain('v-if="loading && banner"')
})

it('keeps artist busy state through concurrent requests and settles on success or failure', async () => {
  const start = view.indexOf('function createBusyTracker()')
  const end = view.indexOf('\nconst busyTracker', start)
  expect(start).toBeGreaterThanOrEqual(0)
  const code = view.slice(start, end)
  const tracker = new Function('ref', `${code}; return createBusyTracker()`)(ref)
  const finishOne = tracker.begin('art')
  const finishTwo = tracker.begin('profile')
  expect(tracker.updating.value).toBe(true)
  finishOne()
  expect(tracker.updating.value).toBe(true)
  finishTwo()
  expect(tracker.updating.value).toBe(false)
  const fail = tracker.begin('discography')
  expect(tracker.updating.value).toBe(true)
  fail()
  expect(tracker.updating.value).toBe(false)
})

it('invalidates pending work when artist changes or the view is disposed', () => {
  expect(view).toContain('busyTracker.invalidate()')
  expect(view).toContain('generations[key]++')
  expect(view).toContain('artist.value?.name !== requestArtist')
  expect(view).toContain('if (current === inspectionRequest) inspectedDiscography.value = inspected')
})
