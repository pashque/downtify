import { groupingArtistName } from './library'

export function playerAlbumRoute(track) {
  if (!track?.album || track.isPodcast) return null
  const artist = groupingArtistName(track)
  return artist ? { name: 'Album', query: { artist, title: track.album } } : null
}

export function playerArtistRoute(track) {
  if (!track || track.isPodcast) return null
  const name = groupingArtistName(track)
  return name ? { name: 'Artist', query: { name } } : null
}

export function playerContextRoute(context, track) {
  // An album started from a provider link still opens its Library page.
  // Playlist/artist contexts keep their own collection destination.
  if (!context || context.type === 'album') return playerAlbumRoute(track)
  return context.route || null
}
