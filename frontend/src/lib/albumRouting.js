// Row downloads carry only the origin that actually opened this album.
// Target lookup status belongs to the top action, never the green row badge.
export function albumRowSong(song, query = {}) {
  const copy = { ...song }
  for (const key of ['downtify_destination', 'downtify_playlist_name', 'downtify_playlist_url', 'downtify_destination_exists', 'downtify_destination_stem', 'downtify_destination_file']) delete copy[key]
  const playlist = String(query.playlist || '')
  const playlistUrl = String(query.playlistUrl || '')
  if (playlist) {
    copy.downtify_playlist_name = playlist
    if (playlistUrl) copy.downtify_playlist_url = playlistUrl
  } else copy.downtify_destination = 'album'
  return copy
}

// Presentation follows the shown source; local file metadata stays untouched.
export function selectedAlbumMetadata(local, source) {
  if (!local || !source) return local
  return { ...local,
    cover: source.cover_url || local.cover,
    year: String(source.release_date || source.year || local.year || '').slice(0, 4),
  }
}

// Only the playlist row that opened this album can supply its origin.
export function albumRoute(track, context = null) {
  const query = { artist: track.albumArtist, title: track.album }
  const edition = track.spotify_album_id || (track.source === 'spotify' ? track.album_id : '')
  if (/^[A-Za-z0-9]{22}$/.test(edition || '')) query.edition = edition
  if (context?.type === 'playlist' && context.title) {
    query.playlist = context.title
    const url = context.playlistUrl || context.route?.query?.url
    if (url) query.playlistUrl = url
  }
  return { name: 'Album', query }
}
