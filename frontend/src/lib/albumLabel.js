import { ref } from 'vue'
import { labelMemory } from '/src/lib/albumLabelMemory'

export function spotifyAlbumId(value) {
  const text = String(value || '')
  if (/^[A-Za-z0-9]{22}$/.test(text)) return text
  try {
    const url = new URL(text)
    if (url.protocol !== 'https:' || url.hostname !== 'open.spotify.com')
      return ''
    return (
      url.pathname.match(
        /^\/(?:intl-[a-z]+\/)?album\/([A-Za-z0-9]{22})\/?$/
      )?.[1] || ''
    )
  } catch {
    return ''
  }
}

export function useAlbumLabel(fetchLabel, memory = labelMemory) {
  const label = ref('')
  const loading = ref(false)
  let generation = 0

  // `key` names the library album (so the label is known before its Spotify
  // edition is); the edition's own key is added once the id is known.
  async function load(id, key = '') {
    const current = ++generation
    const keys = [key, id && `spotify:${id}`].filter(Boolean)
    // A remembered label is shown only for the same edition. An entry
    // without an id came from the library album before its edition was known.
    const known = keys
      .map((k) => memory?.get(k))
      .find((entry) => entry && (!id || !entry.id || entry.id === id))
    label.value = known ? known.label : ''
    loading.value = !!id
    if (!id) return
    try {
      const data = await fetchLabel(id)
      if (current !== generation) return
      const fresh = typeof data.label === 'string' ? data.label : ''
      label.value = fresh
      for (const k of keys) {
        if (fresh) memory?.set(k, { id, label: fresh })
        else memory?.delete(k)
      }
    } catch {
      /* Optional metadata; a remembered label stays, unknown stays absent. */
    } finally {
      if (current === generation) loading.value = false
    }
  }
  return { label, loading, load }
}
