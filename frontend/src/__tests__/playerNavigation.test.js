import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { playerAlbumRoute, playerArtistRoute, playerContextRoute } from '../lib/playerNavigation'
const track = { album: 'Her Loss', albumArtist: 'Drake', artist: 'Drake, 21 Savage', artists: ['Drake', '21 Savage'] }
const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')
it('album playback opens the Library album instead of its source link', () => {
  expect(playerAlbumRoute(track)).toEqual({ name: 'Album', query: { artist: 'Drake', title: 'Her Loss' } })
  expect(playerContextRoute({ type: 'album', route: { name: 'Link', query: { url: 'https://open.spotify.com/album/example' } } }, track)).toEqual(playerAlbumRoute(track))
  const playlist = { type: 'playlist', route: { name: 'Playlist', query: { name: 'Mix' } } }
  expect(playerContextRoute(playlist, track)).toEqual(playlist.route)
  expect(playerContextRoute(null, track)).toEqual(playerAlbumRoute(track))
  expect(playerAlbumRoute({ isPodcast: true, album: 'Podcast' })).toBeNull()
})
it('artist links use the Library grouping artist, including tracks without albumArtist', () => {
  expect(playerArtistRoute(track)).toEqual({ name: 'Artist', query: { name: 'Drake' } })
  expect(playerArtistRoute({ artists: ['Earth, Wind & Fire'], artist: 'Earth, Wind & Fire' })).toEqual({ name: 'Artist', query: { name: 'Earth, Wind & Fire' } })
  expect(playerArtistRoute({ isPodcast: true })).toBeNull()
})
it('mini cover opens the full player; plain title, linked artists/album', () => {
  const s = src('components/shell/MiniPlayer.vue')
  const cover = s.slice(s.indexOf('data-mini-open'), s.indexOf('data-mini-titles'))
  expect(cover).toMatch(/@click(\.stop)?="nowPlaying\.open\(\)"/)
  expect(cover).toContain('<CoverArt')
  const titles = s.slice(s.indexOf('data-mini-titles'), s.indexOf('data-mini-controls'))
  // The track title is plain text, like everywhere else in the app.
  expect(titles).not.toContain('data-mini-album-title')
  expect(titles).toMatch(/<span[^>]*data-mini-title[^>]*>\{\{ track\.title \}\}/)
  expect(titles).toContain('<ArtistCredits')
  expect(titles).toMatch(/<RouterLink[\s\S]*?:to="albumRoute"[\s\S]*?track\.album/)
  // Format and heart order across both players: see playerBarParity.test.js.
  // The heart sits in the controls (former check slot); transport centred by equal sides.
  expect(s.slice(s.indexOf('data-mini-controls'))).toContain('data-mini-like')
  expect(s).toContain('flex min-w-0 flex-1 basis-0 items-center gap-1')
  expect(s).toContain('hidden min-w-0 flex-1 basis-0 items-center justify-end gap-1 landscape:flex md:flex')
  expect(s).toContain('playerAlbumRoute(track.value)')
  // The expand arrow still opens the full player.
  expect(s).toMatch(/icon="expand"[\s\S]*?nowPlaying\.open\(\)/)
})
it('Up next does not animate row removal when a track changes', () => {
  const s = src('components/player/UpNextPanel.vue')
  expect(s).not.toContain('<TransitionGroup')
  expect(s).toContain('[overflow-anchor:none]')
  expect(s).toContain('onMounted(showCurrent)')
})
