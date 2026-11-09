import { describe, expect, it } from 'vitest'
import { isExactLabelQuery, useLabelFinder } from '/src/lib/labels'

const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}

describe('exact versus searched label queries', () => {
  it('treats a quoted name as an exact label and plain text as a search', () => {
    expect(isExactLabelQuery('label:"Draft LTD"')).toBe(true)
    expect(isExactLabelQuery(' LABEL: "Draft" ')).toBe(true)
    expect(isExactLabelQuery('label:draft')).toBe(false)
    expect(isExactLabelQuery('draft')).toBe(false)
  })
})

describe('label finder', () => {
  it('loads candidates and exposes the fuzzy flag', async () => {
    const state = useLabelFinder(async () => ({
      labels: [{ name: 'Draft', releases: 2, artists: ['Ana'] }],
      fuzzy: true,
    }))
    await state.load('draft')
    expect(state.labels.value.map((l) => l.name)).toEqual(['Draft'])
    expect(state.fuzzy.value).toBe(true)
    expect(state.loading.value).toBe(false)
  })

  it('shows loading and clears the previous query immediately', async () => {
    const first = deferred()
    const state = useLabelFinder(() => first.promise)
    const pending = state.load('draft')
    expect(state.loading.value).toBe(true)
    first.resolve({ labels: [{ name: 'Draft' }], fuzzy: false })
    await pending
    const second = deferred()
    const next = useLabelFinder(() => second.promise)
    expect(next.labels.value).toEqual([])
  })

  it('ignores an older query that finishes after a newer one', async () => {
    const slow = deferred()
    const state = useLabelFinder((q) =>
      q === 'old'
        ? slow.promise
        : Promise.resolve({ labels: [{ name: 'New' }], fuzzy: false })
    )
    const old = state.load('old')
    await state.load('new')
    slow.resolve({ labels: [{ name: 'Stale' }], fuzzy: false })
    await old
    expect(state.labels.value.map((l) => l.name)).toEqual(['New'])
  })

  it('reports a failure and allows retry', async () => {
    let fail = true
    const state = useLabelFinder(async () => {
      if (fail) throw new Error('down')
      return { labels: [{ name: 'Draft' }], fuzzy: false }
    })
    await state.load('draft')
    expect(state.error.value).toBe('down')
    fail = false
    await state.load('draft')
    expect(state.error.value).toBe('')
    expect(state.labels.value).toHaveLength(1)
  })
})
