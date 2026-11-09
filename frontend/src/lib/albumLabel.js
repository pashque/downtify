import { ref } from 'vue'

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

export function useAlbumLabel(fetchLabel) {
  const label = ref('')
  const loading = ref(false)
  let generation = 0
  async function load(id) {
    const current = ++generation
    label.value = ''
    loading.value = !!id
    if (!id) return
    try {
      const data = await fetchLabel(id)
      if (current === generation)
        label.value = typeof data.label === 'string' ? data.label : ''
    } catch {
      /* Optional metadata; unknown labels remain absent. */
    } finally {
      if (current === generation) loading.value = false
    }
  }
  return { label, loading, load }
}
