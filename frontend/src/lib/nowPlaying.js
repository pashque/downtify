// Is a card's target (album, artist or playlist page) what is playing now?
// Shared by every card so the "Playing" badge shows on all pages, not just
// the Library.
import { albumKey, artistKey } from '/src/lib/library'

function fold(text) {
  return String(text || '').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '')
}

export function isPlayingTarget(to, track, context, title = '') {
  if (!track || !to || typeof to !== 'object') return false
  const q = to.query || {}
  if (to.name === 'Album') {
    return albumKey(track.albumArtist, track.album) === albumKey(q.artist, q.title)
  }
  if (to.name === 'Artist') return artistKey(track.albumArtist) === artistKey(q.name)
  if (to.name === 'Playlist') {
    return context?.type === 'playlist' &&
      (context.title === q.name || (title && context.title === title))
  }
  return false
}

/** A streaming release (Spotify/YouTube card) the library track belongs to. */
export function isPlayingRelease(release, track) {
  if (!track || !release) return false
  const artist = (release.artists || [])[0] || release.artist || ''
  return fold(track.album) === fold(release.name) &&
    (!artist || fold(track.albumArtist) === fold(artist) || (track.artists || []).some((a) => fold(a) === fold(artist)))
}
