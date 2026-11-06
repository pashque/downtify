import { expect, it } from 'vitest'
import { normalizeTrack, songKey, groupAlbums, groupArtists, indexTracksBySong, dedupeAlbumTracks } from '../lib/library'

it('shows featured artists separated by commas, keeping the structured list', () => {
  const t = normalizeTrack({ file: 'a.mp3', artist: 'Drake; 21 Savage', title: 'Rich Flex' })
  expect(t.artist).toBe('Drake, 21 Savage')
  expect(t.artists).toEqual(['Drake', '21 Savage'])
  expect(t.albumArtist).toBe('Drake')
  expect(songKey(t.artists, t.title)).toBe(songKey('Drake; 21 Savage', 'Rich Flex'))
})

it.each(['stale display', '', 'Tyler, The Creator; Daniel Caesar'])('derives comma display from authoritative structured names (%s)', artist => {
  const track = normalizeTrack({ artist, artists: [' Tyler, The Creator ', { name: 'Daniel Caesar' }, null, ''], title: 'ST. CHROMA' })
  expect(track.artists).toEqual(['Tyler, The Creator', 'Daniel Caesar'])
  expect(track.artist).toBe('Tyler, The Creator, Daniel Caesar')
})

it('groups solo and collaborative Tyler tracks under his complete name', () => {
  const tracks = [
    normalizeTrack({ file: 'solo.mp3', artist: 'Tyler, The Creator', album: 'CHROMAKOPIA' }),
    normalizeTrack({ file: 'collab.mp3', artist: 'Tyler, The Creator; Daniel Caesar', album: 'CHROMAKOPIA', album_artist: 'Various Artists' }),
  ]
  expect(tracks[1].artist).toBe('Tyler, The Creator, Daniel Caesar')
  expect(tracks[1].artists).toEqual(['Tyler, The Creator', 'Daniel Caesar'])
  expect(groupAlbums(tracks).map(album => [album.artist, album.tracks.length])).toEqual([['Tyler, The Creator', 2]])
  expect(groupArtists(tracks).map(artist => [artist.name, artist.tracks.length])).toEqual([['Tyler, The Creator', 2]])
})

it('matches complete lead artists without conflating comma names or real duos', () => {
  expect(songKey('Tyler, The Creator', 'ST. CHROMA')).not.toBe(songKey('Tyler', 'ST. CHROMA'))
  expect(songKey(['Tyler, The Creator', 'Daniel Caesar'], 'ST. CHROMA')).toBe(songKey('Tyler, The Creator', 'ST. CHROMA'))
  expect(songKey([{ name: 'Tyler, The Creator' }, { name: 'Daniel Caesar' }], 'ST. CHROMA')).toBe(songKey('Tyler, The Creator', 'ST. CHROMA'))
  expect(songKey('Zé Neto & Cristiano', 'Sintonia')).not.toBe(songKey('Zé Neto', 'Sintonia'))
})

it('indexes and deduplicates collaborations using structured lead credits, not display punctuation', () => {
  const collab = normalizeTrack({ file: 'playlist/collab.mp3', title: 'ST. CHROMA', artist: 'Tyler, The Creator, Daniel Caesar', artists: ['Tyler, The Creator', 'Daniel Caesar'], track_number: 1 })
  const canonical = { ...collab, file: 'Tyler, The Creator/collab.mp3' }
  const other = normalizeTrack({ file: 'other.mp3', title: 'ST. CHROMA', artist: 'Tyler', track_number: 1 })
  const index = indexTracksBySong([collab, canonical, other])
  expect(index.get(songKey('Tyler, The Creator', 'ST. CHROMA'))).toBe(collab)
  expect(index.get(songKey('Tyler', 'ST. CHROMA'))).toBe(other)
  expect(dedupeAlbumTracks([collab, canonical, other])).toEqual([canonical, other])
})

it.each(['Earth, Wind & Fire', 'Tyler, The Creator', 'Zé Neto & Cristiano', 'AC / DC'])('never splits or rewrites a literal artist name: %s', artist => {
  const t = normalizeTrack({ file: 'b.mp3', artist, artists: [], title: 'Song' })
  expect(t.artist).toBe(artist)
  expect(t.artists).toEqual([artist])
  expect(t.albumArtist).toBe(artist)
})
