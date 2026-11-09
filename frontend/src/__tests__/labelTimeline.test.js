import { describe, expect, it } from 'vitest'
import { useLabelTimeline } from '/src/lib/labels'

const release = (id) => ({ album_id: id, name: id, artists: ['A'] })
const years = (map) => async (_label, year) => {
  const value = map[year]
  if (value instanceof Error) throw value
  return {
    year,
    releases: (value || []).map(release),
    complete: true,
  }
}

describe('label timeline', () => {
  it('scans newest first, shows each year as it arrives, then stops after five empty years', async () => {
    const seen = []
    const fetchYear = years({ 2024: ['a', 'b'], 2022: ['c'], 2020: ['d'] })
    const state = useLabelTimeline(
      async (label, year) => {
        seen.push(year)
        return fetchYear(label, year)
      },
      { latestYear: 2025 }
    )
    await state.load('Frucht')
    expect(seen).toEqual([
      2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015,
    ])
    expect(state.releases.value.map((r) => r.album_id)).toEqual([
      'a',
      'b',
      'c',
      'd',
    ])
    expect(state.complete.value).toBe(true)
    expect(state.loading.value).toBe(false)
  })

  it('does not count empty years before the first release toward the stop rule', async () => {
    const seen = []
    const state = useLabelTimeline(
      async (label, year) => {
        seen.push(year)
        return years({ 2010: ['old'] })(label, year)
      },
      { latestYear: 2020 }
    )
    await state.load('Quiet')
    expect(state.releases.value.map((r) => r.album_id)).toEqual(['old'])
    expect(seen.at(-1)).toBe(2005)
  })

  it('publishes releases while later years are still loading', async () => {
    let release2023
    const state = useLabelTimeline(
      (label, year) =>
        year === 2024
          ? Promise.resolve({
              year,
              releases: [release('new')],
              complete: true,
            })
          : new Promise((resolve) => {
              release2023 = () =>
                resolve({ year, releases: [], complete: true })
            }),
      { latestYear: 2024 }
    )
    const pending = state.load('Frucht')
    await new Promise((r) => setTimeout(r, 0))
    expect(state.releases.value.map((r) => r.album_id)).toEqual(['new'])
    expect(state.loading.value).toBe(false)
    expect(state.scanning.value).toBe(true)
    expect(state.year.value).toBe(2023)
    release2023()
    state.stop()
    await pending
  })

  it('marks a failed year partial, keeps cards and continues', async () => {
    const state = useLabelTimeline(
      years({ 2024: ['a'], 2023: new Error('boom'), 2022: ['b'] }),
      { latestYear: 2024 }
    )
    await state.load('Frucht')
    expect(state.releases.value.map((r) => r.album_id)).toEqual(['a', 'b'])
    expect(state.complete.value).toBe(false)
    expect(state.partial.value).toBe(true)
    expect(state.failedYears.value).toEqual([2023])
  })

  it('shows a first-year failure as an error', async () => {
    const state = useLabelTimeline(years({ 2024: new Error('down') }), {
      latestYear: 2024,
    })
    await state.load('Frucht')
    expect(state.error.value).toBe('down')
    expect(state.releases.value).toEqual([])
  })

  it('ignores an older label after navigation', async () => {
    let resolveOld
    const state = useLabelTimeline(
      (label, year) =>
        label === 'old'
          ? new Promise((r) => {
              resolveOld = () =>
                r({ year, releases: [release('stale')], complete: true })
            })
          : Promise.resolve({ year, releases: [], complete: true }),
      { latestYear: 1952 }
    )
    const old = state.load('old')
    await state.load('new')
    resolveOld()
    await old
    expect(state.releases.value).toEqual([])
  })

  it('starts from the present year by default', async () => {
    const seen = []
    const state = useLabelTimeline(async (label, year) => {
      seen.push(year)
      return { year, releases: [release('x')], complete: true }
    })
    const pending = state.load('Frucht')
    await new Promise((r) => setTimeout(r, 0))
    state.stop()
    await pending
    expect(seen[0]).toBe(new Date().getFullYear())
  })

  it('visits only the outline years of an uncapped label, across gaps', async () => {
    const seen = []
    const state = useLabelTimeline(
      async (label, year) => {
        seen.push(year)
        return years({ 2024: ['a'], 2015: ['b'] })(label, year)
      },
      {
        latestYear: 2026,
        fetchOutline: async () => ({
          years: [2024, 2015],
          capped: false,
        }),
      }
    )
    await state.load('Rectangular')
    expect(seen).toEqual([2024, 2015])
    expect(state.releases.value.map((r) => r.album_id)).toEqual(['a', 'b'])
    expect(state.complete.value).toBe(true)
  })

  it('does not stop a capped label before the oldest sampled year', async () => {
    const seen = []
    const state = useLabelTimeline(
      async (label, year) => {
        seen.push(year)
        return years({ 2024: ['a'], 2012: ['z'] })(label, year)
      },
      {
        latestYear: 2024,
        fetchOutline: async () => ({ years: [2024, 2012], capped: true }),
      }
    )
    await state.load('Big')
    expect(seen).toContain(2012)
    expect(seen.at(-1)).toBe(2007)
    expect(state.releases.value.map((r) => r.album_id)).toEqual(['a', 'z'])
  })

  it('falls back to the plain scan when the outline fails', async () => {
    const seen = []
    const state = useLabelTimeline(
      async (label, year) => {
        seen.push(year)
        return years({ 2024: ['a'] })(label, year)
      },
      {
        latestYear: 2024,
        fetchOutline: async () => {
          throw new Error('nope')
        },
      }
    )
    await state.load('Big')
    expect(seen).toEqual([2024, 2023, 2022, 2021, 2020, 2019])
  })
})
