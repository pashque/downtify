// Exact source metadata and album-target availability are deliberately separate:
// row badges/playback use the global library, never a destination's absence.
import { computed, ref, watch } from 'vue'
import API from '/src/model/api'
import { useLibrary } from '/src/model/library'
import { useProgressTracker } from '/src/model/download'
import { destinationAvailable } from '/src/lib/downloadState'
import { albumRowSong } from '/src/lib/albumRouting'
import { groupAlbumEditions } from '/src/lib/albumEditions'
export { albumEditionOptions } from '/src/lib/albumEditions'

export function useAlbumSource(route) {
  const library = useLibrary()
  const source = ref(null)
  // Spotify version shown (standard/deluxe, explicit/clean); null = server default.
  const edition = ref(null)
  watch(() => route.query.edition, value => { edition.value = value ? String(value) : null }, { immediate: true })
  // True while the full source tracklist is being fetched.
  const loading = ref(false)
  let request = 0
  let saving = false
  let pendingSave = null
  async function rememberSelection(artist, title, chosen) {
    pendingSave = [artist, title, chosen]
    if (saving) return
    saving = true
    try {
      while (pendingSave) {
        const args = pendingSave
        pendingSave = null
        try { await API.setLibraryAlbumSource?.(...args) }
        catch { console.warn('Could not remember selected album source') }
      }
    } finally { saving = false }
  }
  watch(
    [() => String(route.query.artist || ''), () => String(route.query.title || ''), edition],
    async ([artist, title, chosen], previous) => {
      const current = ++request
      const sameAlbum = previous && previous[0] === artist && previous[1] === title
      if (!sameAlbum) {
        // A different album starts from its own default version.
        const routed = route.query.edition ? String(route.query.edition) : null
        if (previous && chosen !== routed) { edition.value = routed; return }
        source.value = null
      }
      source.value = null
      if (!artist || !title) return
      loading.value = true
      try {
        const res = chosen
          ? await API.getLibraryAlbumSource(artist, title, chosen)
          : await API.getLibraryAlbumSource(artist, title)
        if (current !== request) return
        if (res.data?.status !== 'resolved' || !res.data.tracks?.length) return
        await library.lookupSongs(res.data.tracks)
        if (current === request) {
          source.value = res.data
          if (chosen && res.data.edition === chosen) {
            void rememberSelection(artist, title, chosen)
          }
        }
      } catch {
        // Exact provenance is optional: keep the original local track list.
      } finally {
        if (current === request) loading.value = false
      }
    },
    { immediate: true }
  )
  const songs = computed(() => {
    if (!source.value) return null
    return source.value.tracks.map((song) => albumRowSong(song, route.query))
  })
  const editions = computed(() => groupAlbumEditions(source.value?.editions || [], source.value?.edition))
  const currentEdition = computed(() => source.value?.edition || null)
  // album / single / ep / compilation of the shown version ('' = unknown).
  const releaseType = computed(() => source.value?.release_type || '')
  function selectEdition(id) {
    if (id && id !== currentEdition.value) edition.value = id
  }
  return { songs, editions, edition: currentEdition, selectEdition, releaseType, loading }
}

export function useAlbumDestination(songs) {
  const targets = ref([])
  const loaded = ref(false)
  const loading = ref(false)
  const tracker = useProgressTracker()
  let request = 0
  watch(songs, async (list) => {
    const current = ++request
    loaded.value = false
    targets.value = []
    loading.value = false
    if (!list?.length) return
    loading.value = true
    const copies = list.map((song) => albumRowSong(song))
    try {
      const res = await API.lookupLibrarySongs(copies, { destination_status: true, destination: 'album' })
      if (current !== request) return
      const statuses = new Map((res.data?.destinations || []).map((status) => [String(status.key), status]))
      targets.value = copies.map((song) => {
        const status = statuses.get(String(song.song_id || song.url || ''))
        return { ...song, downtify_destination_exists: status?.exists === true, downtify_destination_stem: status?.stem || '', downtify_destination_file: status?.file || null }
      })
      loaded.value = Array.isArray(res.data?.destinations)
    } catch {
      // No new error UI or guessed availability.
    } finally {
      if (current === request) loading.value = false
    }
  }, { immediate: true })
  const missing = computed(() => {
    tracker.queueVersion.value
    return targets.value.filter((song) => !destinationAvailable(song, tracker.getBySong(song)))
  })
  return { missing, loaded, loading }
}
