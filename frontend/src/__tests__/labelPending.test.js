import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { useAlbumLabel } from '/src/lib/albumLabel'

const read = (file) => readFileSync(new URL(file, import.meta.url), 'utf8')
const deferred = () => {
  let resolve
  const promise = new Promise((yes) => {
    resolve = yes
  })
  return { promise, resolve }
}

describe('album label loading state', () => {
  it('is loading while the label is fetched, then settles', async () => {
    const reply = deferred()
    const state = useAlbumLabel(() => reply.promise)
    const pending = state.load('0eyTz4axCv1nyRSCHxDNY0')
    expect(state.loading.value).toBe(true)
    reply.resolve({ label: 'Frucht' })
    await pending
    expect(state.loading.value).toBe(false)
    expect(state.label.value).toBe('Frucht')
  })

  it('stops loading when the label cannot be read', async () => {
    const state = useAlbumLabel(async () => {
      throw new Error('down')
    })
    await state.load('0eyTz4axCv1nyRSCHxDNY0')
    expect(state.loading.value).toBe(false)
    expect(state.label.value).toBe('')
  })

  it('is not loading without an album id', async () => {
    const state = useAlbumLabel(async () => ({ label: 'x' }))
    await state.load('')
    expect(state.loading.value).toBe(false)
  })

  it('an older album never ends the newer loading', async () => {
    const slow = deferred()
    const state = useAlbumLabel((id) =>
      id === 'old'
        ? slow.promise
        : new Promise(() => {
            /* newer request stays pending */
          })
    )
    const old = state.load('old')
    state.load('new')
    slow.resolve({ label: 'Stale' })
    await old
    expect(state.label.value).toBe('')
    expect(state.loading.value).toBe(true)
  })
})

describe('label slot is reserved so nothing pops in late', () => {
  it('the kicker shows a placeholder while the label is pending', () => {
    const kicker = read('../components/library/AlbumLabelKicker.vue')
    expect(kicker).toContain('data-label-pending')
    expect(kicker).toContain('pending')
    expect(kicker).toContain('state.loading.value')
  })

  it('the album page keeps the slot while the edition is being resolved', () => {
    expect(read('../views/AlbumView.vue')).toContain(':pending="sourceLoading"')
  })

  it('the Labels chip is always offered and shows a placeholder count while loading', () => {
    const view = read('../views/SearchView.vue')
    expect(view).toContain("id: 'labels'")
    expect(view).toContain('labelFinder.loading.value')
    expect(view).toContain("'…'")
  })

  it('the Labels filter explains an empty or pending result instead of a blank page', () => {
    const view = read('../views/SearchView.vue')
    expect(view).toContain("filter === 'labels'")
    expect(view).toContain("t('labels.matchesEmpty')")
  })
})
