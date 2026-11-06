import { ref, watch, onScopeDispose } from 'vue'
import API from './api'
import { useProgressTracker } from './download'

export const locationKey = song => String(song?.song_id || song?.url || song?.file || '')

// One bounded list-level lookup. Rows are consumers only; destination status
// and global library presence deliberately remain independent models.
export function useLibraryLocations(songs) {
  const locations = ref(new Map())
  const tracker = useProgressTracker()
  let generation = 0
  let disposed = false
  let running = false
  let dirty = false
  async function refresh() {
    dirty = true
    if (running) return
    running = true
    while (dirty && !disposed) {
      dirty = false
      const current = generation
      const list = [...new Map((songs.value || []).filter(Boolean).map(s => [locationKey(s), s])).values()].filter(s => locationKey(s))
      const next = new Map()
      for (let i = 0; i < list.length && !disposed && current === generation; i += 100) {
        try {
          const response = await API.lookupLibraryLocations(list.slice(i, i + 100))
          for (const location of response.data?.locations || []) next.set(String(location.key), location)
        } catch {
          // Older/unavailable servers expose no guessed locations or formats.
        }
      }
      if (!disposed && current === generation) locations.value = next
    }
    running = false
  }
  watch(() => {
    tracker.queueVersion.value
    return JSON.stringify((songs.value || []).map(song => {
      const item = tracker.getBySong?.(song)
      return [locationKey(song), song.artist, song.name, item?.state === 'done' ? item.filename || 'done' : '']
    }))
  }, () => {
    generation++
    locations.value = new Map()
    void refresh()
  }, { immediate: true })
  onScopeDispose(() => { disposed = true; generation++ })
  return { locations, refresh, locationFor: song => locations.value.get(locationKey(song)) || null }
}
