import { artistKey } from './library'

const releaseKey = release => JSON.stringify([artistKey(release.artist || release.artists?.[0]), artistKey(release.name || release.title)])

// Discovery is bounded and separate from physical presence. A stale catalog
// row, matching title or one local track never proves a complete release.
export async function inspectDiscography(releases, libraryAlbums, api) {
  const local = new Set((libraryAlbums || []).map(releaseKey))
  const counts = new Map()
  for (const release of releases) counts.set(releaseKey(release), (counts.get(releaseKey(release)) || 0) + 1)
  const results = releases.map(release => ({ ...release, physicallyComplete: false }))
  let cursor = 0
  async function worker() {
    while (cursor < results.length) {
      const release = results[cursor++]
      const key = releaseKey(release)
      if (!local.has(key) && counts.get(key) < 2) continue
      try {
        const response = await api.resolveUrl(release.url)
        const songs = response.data?.tracks
        if (!Array.isArray(songs) || !songs.length || songs.some(song => Number(song.album_track_total) > songs.length)) continue
        release.sourceTracks = songs
        const present = new Map()
        for (let i = 0; i < songs.length; i += 100) {
          const response = await api.lookupLibraryLocations(songs.slice(i, i + 100))
          for (const location of response.data?.locations || []) present.set(String(location.key), location.downloaded === true)
        }
        release.physicallyComplete = songs.every(song => present.get(String(song.song_id || song.url || '')) === true)
      } catch { /* Unknown or failed verification stays available. */ }
    }
  }
  await Promise.all(Array.from({ length: Math.min(3, results.length) }, worker))
  return results
}

function duplicateFingerprint(release) {
  const tracks = release.sourceTracks
  if (!tracks?.length || tracks.some(t => !t.name || !t.artists?.length || !(t.duration > 0) || typeof t.explicit !== 'boolean')) return null
  return JSON.stringify([release.source || release.provider || 'spotify', releaseKey(release),
    artistKey(release.release_type), String(release.year || ''), tracks.map(t => [
      artistKey(t.name), t.artists.map(artistKey), t.duration, t.explicit,
      t.track_number || 0, t.disc_number || 0, t.release_date || '',
    ])])
}

export function discographySections(releases, libraryAlbums, labels) {
  const duplicates = new Map()
  const grouped = []
  for (const release of releases || []) {
    const fingerprint = duplicateFingerprint(release)
    const previous = fingerprint && duplicates.get(fingerprint)
    if (previous) {
      previous.duplicateIds.push(release.album_id)
      previous.physicallyComplete ||= release.physicallyComplete === true
    } else {
      const item = fingerprint ? { ...release, duplicateIds: [release.album_id] } : release
      if (fingerprint) duplicates.set(fingerprint, item)
      grouped.push(item)
    }
  }
  const albums = []
  const singles = []
  const seen = new Set()
  for (const release of grouped) {
    const provider = release.provider || release.source ||
      (/deezer\.com\//i.test(release.url || '') ? 'deezer' :
        /(?:youtube\.com|youtu\.be)\//i.test(release.url || '') ? 'youtube' : 'spotify')
    const id = release.album_id
      ? JSON.stringify([String(provider).toLowerCase(), String(release.album_id)])
      : release.url || ''
    const type = String(release.release_type || '').toLowerCase()
    if (id && seen.has(id)) continue
    if (id) seen.add(id)
    if (release.physicallyComplete === true) continue
    ;(type === 'single' || type === 'ep' ? singles : albums).push(release)
  }
  return [
    { id: 'albums', label: labels.albums, items: albums },
    { id: 'singles', label: labels.singles, items: singles },
  ].filter((group) => group.items.length)
}
