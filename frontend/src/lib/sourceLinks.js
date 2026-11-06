// Where a song (or release) opens: its own provider page, labelled by that
// provider, and its real YouTube Music page (never a search result).

export function songProvider(song) {
  const url = String(song?.url || '')
  if (/open\.spotify\.com/.test(url)) return 'spotify'
  if (/deezer\.com/.test(url)) return 'deezer'
  if (/(music\.)?youtube\.com|youtu\.be/.test(url)) return 'youtube'
  return String(song?.source || '')
}

/** The YouTube Music page already known from the item itself, or ''. */
export function youtubeMusicUrl(item) {
  const url = String(item?.url || '')
  if (/music\.youtube\.com\/(watch|browse|playlist)/.test(url)) return url
  const video = item?.video_id || (url.match(/youtube\.com\/watch\?(?:.*&)?v=([\w-]{11})/) || [])[1]
  return video ? `https://music.youtube.com/watch?v=${video}` : ''
}

/**
 * Open the item's YouTube Music track (`kind` 'track') or album ('album').
 * The tab opens at once (so the browser doesn't block it) and is pointed at
 * the matched page when the server finds one; otherwise it closes and
 * `onMissing` runs.
 */
export async function openYouTubeMusic(item, kind, { lookup, onMissing } = {}) {
  const known = youtubeMusicUrl(item)
  if (known) {
    window.open(known, '_blank', 'noopener')
    return known
  }
  const tab = window.open('', '_blank')
  if (tab) tab.opener = null
  try {
    const artist = (item?.artists || []).join(', ') || item?.artist || ''
    const res = await lookup({
      kind,
      artist,
      ...(item?.artists?.length ? { artists: item.artists } : {}),
      title: item?.name || item?.title || '',
      duration: Math.round(Number(item?.duration) || 0),
    })
    const url = String(res?.data?.url || '')
    if (!url.startsWith('https://music.youtube.com/')) throw new Error('no match')
    if (tab) tab.location.href = url
    else window.open(url, '_blank', 'noopener')
    return url
  } catch {
    if (tab) tab.close()
    onMissing?.()
    return ''
  }
}

/** Album menus: the real page of `album` ({name, artist, url}) on
 * 'spotify' or 'youtube', opened in a new tab; `onMissing` otherwise. */
export async function openAlbumOn(service, album, { lookups, onMissing } = {}) {
  const own = String(album?.url || '')
  if (service === 'spotify' && /open\.spotify\.com\/album\//.test(own)) {
    window.open(own, '_blank', 'noopener')
    return own
  }
  if (service === 'youtube') {
    return openYouTubeMusic(album, 'album', { lookup: lookups.youtube, onMissing })
  }
  const tab = window.open('', '_blank')
  if (tab) tab.opener = null
  try {
    const res = await lookups.spotify({ kind: 'album', artist: album?.artist || '', ...(album?.artists?.length ? { artists: album.artists } : {}), title: album?.name || '' })
    const url = String(res?.data?.url || '')
    if (!url.startsWith('https://open.spotify.com/')) throw new Error('no match')
    if (tab) tab.location.href = url
    else window.open(url, '_blank', 'noopener')
    return url
  } catch {
    if (tab) tab.close()
    onMissing?.()
    return ''
  }
}

/** The exact Spotify track page of a library track (found on its album),
 * opened in a tab created at click time; `onMissing` when there is none.
 * Never a search page. */
export async function openTrackOnSpotify(track, { lookup, onMissing } = {}) {
  const tab = window.open('', '_blank')
  if (tab) tab.opener = null
  try {
    const res = await lookup({
      kind: 'track',
      artist: track?.albumArtist || track?.artist || '',
      title: track?.title || track?.name || '',
      album: track?.album || '',
      ...(track?.artists?.length ? { artists: track.artists } : {}),
      ...(track?.spotify_id || (track?.source === 'spotify' && track?.song_id) ? { source_id: track.spotify_id || track.song_id } : {}),
    })
    const url = String(res?.data?.url || '')
    if (!url.startsWith('https://open.spotify.com/track/')) throw new Error('no match')
    if (tab) tab.location.href = url
    else window.open(url, '_blank', 'noopener')
    return url
  } catch {
    if (tab) tab.close()
    onMissing?.()
    return ''
  }
}
