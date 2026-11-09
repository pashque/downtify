// Remembers which label an album has, so a release already seen shows its
// label at once. Entries are `{ id, label }` where `id` is the exact Spotify
// edition the label was read from; the newest `limit` entries are kept.
const STORAGE_KEY = 'downtify-album-labels'

export function createLabelMemory(store, limit = 500) {
  function read() {
    try {
      const data = JSON.parse(store?.getItem(STORAGE_KEY) || '{}')
      return data && typeof data === 'object' && !Array.isArray(data)
        ? data
        : {}
    } catch {
      return {}
    }
  }

  function write(data) {
    try {
      store?.setItem(STORAGE_KEY, JSON.stringify(data))
    } catch {
      /* Storage full or unavailable: the label is simply not remembered. */
    }
  }

  return {
    get(key) {
      const entry = read()[key]
      return entry && typeof entry.label === 'string' && entry.label
        ? { id: String(entry.id || ''), label: entry.label }
        : null
    },
    set(key, entry) {
      const data = read()
      delete data[key] // re-inserting keeps the newest entries last
      data[key] = { id: entry.id || '', label: entry.label }
      const keys = Object.keys(data)
      for (const old of keys.slice(0, Math.max(0, keys.length - limit))) {
        delete data[old]
      }
      write(data)
    },
    delete(key) {
      const data = read()
      if (key in data) {
        delete data[key]
        write(data)
      }
    },
  }
}

export const labelMemory = createLabelMemory(
  typeof localStorage === 'undefined' ? null : localStorage
)
