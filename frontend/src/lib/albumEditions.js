// Presentation only: never replace a selected source ID or merge track IDs.
const text = value => String(value || '').normalize('NFKC').trim().toLowerCase().replace(/\s+/g, ' ')

function recordingKey(edition) {
  const tracks = edition.tracks
  if (!text(edition.title) || !Array.isArray(tracks) || !tracks.length || tracks.length !== edition.track_count) return null
  const sequence = []
  for (const [index, track] of tracks.entries()) {
    if (!text(track.name) || !Array.isArray(track.artists) || !track.artists.length ||
        track.artists.some(a => !text(a)) || typeof track.duration !== 'number' ||
        !Number.isFinite(track.duration) || track.duration <= 0 || typeof track.explicit !== 'boolean') return null
    sequence.push([text(track.name), track.artists.map(text), track.duration, track.explicit,
      track.disc_number ?? 1, track.track_number ?? index + 1])
  }
  // Release dates and provider track IDs alone are not different recordings.
  // Punctuation, version words, ordered credits and explicit flags ARE evidence.
  return JSON.stringify([text(edition.title), sequence])
}

export function groupAlbumEditions(editions, selectedId) {
  const groups = []
  const keys = new Map()
  for (const edition of editions) {
    const key = recordingKey(edition)
    const index = key === null ? undefined : keys.get(key)
    if (index === undefined) {
      if (key !== null) keys.set(key, groups.length)
      groups.push({ ...edition, source_ids: [edition.id] })
    } else {
      const group = groups[index]
      const source_ids = [...group.source_ids, edition.id]
      groups[index] = { ...(edition.id === selectedId ? edition : group), source_ids }
    }
  }
  return groups
}

export function albumEditionOptions(editions, t) {
  return editions.map((edition, index) => {
    const peers = editions.filter(e => e.track_count === edition.track_count)
    let label = `${edition.track_count} ${t('library.tracks')}`
    if (editions.some(e => Boolean(e.explicit) !== Boolean(edition.explicit))) {
      label += ` · ${t(edition.explicit ? 'search.explicit' : 'search.clean')}`
    }
    const titleDistinguishes = edition.title && editions.some(e => text(e.title) !== text(edition.title))
    if (titleDistinguishes) label += ` · ${edition.title}`
    const same = peers.filter(e => Boolean(e.explicit) === Boolean(edition.explicit))
    if (same.length > 1) {
      if (edition.title && !titleDistinguishes) label += ` · ${edition.title}`
      if (same.some(e => text(e.title) === text(edition.title) && e.id !== edition.id)) {
        const date = edition.release_date || ''
        if (date && same.some(e => e.release_date !== date)) label += ` · ${date}`
        else label += ` · Version ${index + 1}`
      }
    }
    return { value: edition.id, label }
  })
}
