import { describe, expect, it } from 'vitest'
import { labelFromQuery, useLabelReleases } from '/src/lib/labels'

it('keeps partial cards and exposes scoped completion counts', async () => {
  const state = useLabelReleases(async () => ({
    releases: [{ album_id: 'one', name: 'Release' }],
    total: 100,
    complete: false,
    partial_reason: 'provider_error',
  }))
  await state.load('LuckyMe')
  expect(state.releases.value).toHaveLength(1)
  expect(state.complete.value).toBe(false)
  expect(state.partial.value).toBe(true)
  expect(state.total.value).toBe(100)
})

it('does not expose old counts or completion after label navigation', async () => {
  let resolve
  const state = useLabelReleases((name) =>
    name === 'old'
      ? Promise.resolve({ releases: [], total: 100, complete: true })
      : new Promise((r) => {
          resolve = r
        })
  )
  await state.load('old')
  const pending = state.load('new')
  expect(state.complete.value).toBe(false)
  expect(state.total.value).toBeNull()
  resolve({ releases: [], total: 0, complete: true })
  await pending
  expect(state.complete.value).toBe(true)
})

const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}

describe('label search entry', () => {
  it('recognizes quoted and unquoted Spotify label searches', () => {
    expect(labelFromQuery('label:LuckyMe')).toBe('LuckyMe')
    expect(labelFromQuery(' LABEL: "Ninja Tune" ')).toBe('Ninja Tune')
    expect(labelFromQuery('Jacques Greene')).toBe('')
    expect(labelFromQuery('label:')).toBe('')
  })
})

describe('label discovery loading', () => {
  it('exposes loading and maps native release-card artist and type', async () => {
    const result = deferred()
    const state = useLabelReleases(() => result.promise)
    const pending = state.load('LuckyMe')
    expect(state.loading.value).toBe(true)
    result.resolve({
      releases: [{ album_id: 'a', artists: ['Jacques Greene'], type: 'ALBUM' }],
    })
    await pending
    expect(state.loading.value).toBe(false)
    expect(state.releases.value[0].artist).toBe('Jacques Greene')
    expect(state.releases.value[0].release_type).toBe('album')
  })

  it('distinguishes failure from an empty result and can retry', async () => {
    let fail = true
    const state = useLabelReleases(async () => {
      if (fail) throw { response: { data: { detail: 'Spotify unavailable' } } }
      return { releases: [] }
    })
    await state.load('LuckyMe')
    expect(state.error.value).toBe('Spotify unavailable')
    expect(state.loading.value).toBe(false)
    fail = false
    await state.load('LuckyMe')
    expect(state.error.value).toBe('')
    expect(state.releases.value).toEqual([])
  })

  it('ignores old results and old failures after navigating', async () => {
    const old = deferred(),
      latest = deferred()
    const state = useLabelReleases((label) =>
      label === 'old' ? old.promise : latest.promise
    )
    const first = state.load('old')
    const second = state.load('new')
    old.reject(new Error('stale'))
    await first
    expect(state.loading.value).toBe(true)
    expect(state.error.value).toBe('')
    latest.resolve({ releases: [{ name: 'new' }] })
    await second
    expect(state.releases.value[0].name).toBe('new')
  })

  it('clears old release cards immediately during navigation', async () => {
    const state = useLabelReleases(async () => ({
      releases: [{ name: 'old' }],
    }))
    await state.load('old')
    const next = state.load('new')
    expect(state.releases.value).toEqual([])
    await next
  })
})
