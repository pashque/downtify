import { ref } from 'vue'

export function labelFromQuery(query) {
  const match = String(query || '')
    .trim()
    .match(/^label:\s*(.+)$/i)
  if (!match) return ''
  const value = match[1].replace(/^"(.*)"$/, '$1').trim()
  return value
}

// Keep request state local to the page. An earlier label must never replace
// the current label's cards, error or loading state after navigation.
export function useLabelReleases(fetchReleases) {
  const releases = ref([])
  const loading = ref(false)
  const error = ref('')
  const complete = ref(false)
  const partial = ref(false)
  const total = ref(null)
  let generation = 0

  async function load(label) {
    const request = ++generation
    releases.value = []
    error.value = ''
    complete.value = false
    partial.value = false
    total.value = null
    loading.value = true
    try {
      const result = await fetchReleases(label)
      if (request !== generation) return
      complete.value = result.complete === true
      partial.value = result.complete === false
      total.value = Number.isInteger(result.total) ? result.total : null
      releases.value = (result.releases || []).map((release) => ({
        ...release,
        artist: (release.artists || []).join(', '),
        release_type: String(release.type || '').toLowerCase(),
      }))
    } catch (err) {
      if (request !== generation) return
      error.value =
        err?.response?.data?.detail || err?.message || 'Request failed'
    } finally {
      if (request === generation) loading.value = false
    }
  }

  return { releases, loading, error, complete, partial, total, load }
}

const FIRST_YEAR = 1950
const STOP_AFTER_EMPTY = 5

const toCard = (release) => ({
  ...release,
  artist: (release.artists || []).join(', '),
  release_type: String(release.type || '').toLowerCase(),
})

// Load a label one release year at a time, newest first, publishing each
// year as it arrives. Spotify caps one search at 100 rows, so a year is the
// unit that stays under the cap. After the first year with releases, stop
// once five years in a row are empty.
export function useLabelTimeline(fetchYear, options = {}) {
  const releases = ref([])
  const loading = ref(false)
  const scanning = ref(false)
  const error = ref('')
  const complete = ref(false)
  const partial = ref(false)
  const year = ref(null)
  const failedYears = ref([])
  const excluded = ref(0)
  let generation = 0

  const latest = () => options.latestYear ?? new Date().getFullYear()

  function stop() {
    generation++
    scanning.value = false
    loading.value = false
  }

  async function load(label) {
    const request = ++generation
    releases.value = []
    error.value = ''
    complete.value = false
    partial.value = false
    failedYears.value = []
    excluded.value = 0
    year.value = null
    loading.value = true
    scanning.value = true
    let outline = null
    if (options.fetchOutline) {
      try {
        outline = await options.fetchOutline(label)
      } catch {
        outline = null
      }
      if (request !== generation) return
    }
    const known = (outline?.years || []).filter(
      (y) => Number.isInteger(y) && y >= FIRST_YEAR
    )
    // An uncapped search lists every release of the label, so its years are
    // exact: visit only those, however far apart they are.
    const exact = outline && outline.capped === false
    const oldestSeen = known.length ? Math.min(...known) : null
    let found = false
    let empty = 0
    const queue = exact
      ? [...known].sort((a, b) => b - a)
      : Array.from(
          { length: latest() - FIRST_YEAR + 1 },
          (_, i) => latest() - i
        )
    for (const current of queue) {
      year.value = current
      let result
      try {
        result = await fetchYear(label, current)
      } catch (err) {
        if (request !== generation) return
        if (!found && current === queue[0] && !releases.value.length) {
          error.value =
            err?.response?.data?.detail || err?.message || 'Request failed'
          break
        }
        failedYears.value = [...failedYears.value, current]
        empty = 0
        continue
      }
      if (request !== generation) return
      const rows = (result.releases || []).map(toCard)
      excluded.value += (result.excluded || 0) + (result.self_released || 0)
      if (result.complete === false) {
        failedYears.value = [...failedYears.value, current]
      }
      if (rows.length) {
        releases.value = [...releases.value, ...rows]
        found = true
        empty = 0
        loading.value = false
      } else if (found && !exact) {
        empty += 1
        // Never stop above the oldest year the label's own search showed.
        const reached = oldestSeen === null || current <= oldestSeen
        if (empty >= STOP_AFTER_EMPTY && reached) break
      }
    }
    if (request !== generation) return
    loading.value = false
    scanning.value = false
    year.value = null
    partial.value = failedYears.value.length > 0
    complete.value = !error.value && !partial.value
  }

  return {
    releases,
    loading,
    scanning,
    error,
    complete,
    partial,
    year,
    failedYears,
    excluded,
    load,
    stop,
  }
}
