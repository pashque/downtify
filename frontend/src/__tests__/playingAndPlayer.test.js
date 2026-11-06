import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { isPlayingTarget, isPlayingRelease } from '../lib/nowPlaying'

const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')
const track = { album: 'Her Loss', albumArtist: 'Drake', artists: ['Drake', '21 Savage'] }

it('badges the album, artist and playlist card that is playing on any page', () => {
  expect(isPlayingTarget({ name: 'Album', query: { artist: 'Drake', title: 'Her Loss' } }, track, null)).toBe(true)
  expect(isPlayingTarget({ name: 'Album', query: { artist: 'Drake', title: 'Scorpion' } }, track, null)).toBe(false)
  expect(isPlayingTarget({ name: 'Artist', query: { name: 'drake' } }, track, null)).toBe(true)
  expect(isPlayingTarget({ name: 'Playlist', query: { name: 'Mix' } }, track, { type: 'playlist', title: 'Mix' })).toBe(true)
  expect(isPlayingTarget({ name: 'Album', query: { artist: 'Drake', title: 'Her Loss' } }, null, null)).toBe(false)
  expect(isPlayingRelease({ name: 'Her Loss', artists: ['Drake', '21 Savage'] }, track)).toBe(true)
  expect(isPlayingRelease({ name: 'Her Loss (Deluxe)', artist: 'Drake' }, track)).toBe(false)
  expect(src('components/library/MediaTile.vue')).toContain('isPlayingTarget(props.to')
  expect(src('components/search/ReleaseCard.vue')).toContain('isPlayingRelease(props.release')
  expect(src('components/library/CollectionHero.vue')).toContain('data-hero-playing')
})

it('liked songs page drops an unliked song at once', () => {
  const s = src('views/PlaylistView.vue')
  expect(s).toContain('list.filter((track) => likes.isLiked(track.file))')
})

it('full-screen player: format after the title, menu bottom right before the timer, Up next as wide as the tabs', () => {
  const s = src('components/shell/NowPlaying.vue')
  expect(s.indexOf('data-np-format')).toBeGreaterThan(s.indexOf('{{ track.title }}'))
  expect(s.indexOf('data-np-more')).toBeLessThan(s.indexOf(':label="t(\'player.sleepTimer\')"'))
  expect(s).toContain('xl:w-[var(--np-side)]')
  expect(s).toContain('grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)')
})

it('link pages: "SPOTIFY · ALBUM · 2022" then the library album line', () => {
  const s = src('views/LinkView.vue')
  expect(s).toContain("return [source, label, d?.kind === 'artist' ? '' : d?.year]")
})

it('full-screen player: artist – track bottom left, format by the volume, like before the menu, nothing in the middle by default', () => {
  const s = src('components/shell/NowPlaying.vue')
  const line = s.slice(s.indexOf('data-np-nowline'), s.indexOf('data-np-nowline') + 1200)
  expect(line.indexOf('track.title')).toBeLessThan(line.indexOf('track.artist'))
  // The format badge moved to the right group, left of the volume.
  expect(s.indexOf('data-np-format')).toBeGreaterThan(s.indexOf('data-np-bar-right'))
  // The heart is back under the cover (not in the bottom bar).
  expect(s).toContain('data-np-cover-like')
  expect(s).not.toContain('data-np-like')
  expect(s).toContain("requested.value === 'queue' ? '' : (requested.value || '')")
  expect(s).toContain('now-playing-aligned')
  // Title and artist stay under the cover on every screen size.
  expect(s).toContain('justify-between gap-4" data-np-undercover')
})

it('queue keeps played tracks and albums play one copy of each song', async () => {
  expect(src('components/player/UpNextPanel.vue')).toContain('data-queue-played')
  const { dedupeAlbumTracks } = await import('../lib/library')
  const a = { file: 'My Playlist #1/Drake, 21 Savage - Privileged Rappers.mp3', artist: 'Drake, 21 Savage', title: 'Privileged Rappers', trackNumber: 5, albumArtist: 'Drake' }
  const b = { file: 'Drake/Drake - Her Loss (2022)/05. Drake, 21 Savage - Privileged Rappers.mp3', artist: 'Drake, 21 Savage', title: 'Privileged Rappers', trackNumber: 5, albumArtist: 'Drake' }
  const c = { file: 'Drake/Drake - Her Loss (2022)/01. Rich Flex.mp3', artist: 'Drake, 21 Savage', title: 'Rich Flex', trackNumber: 1, albumArtist: 'Drake' }
  expect(dedupeAlbumTracks([c, a, b])).toEqual([c, b])
})

it('track lists title the check column "Library"', () => {
  expect(src('components/library/TrackDownPlayHeader.vue')).toContain("t('track.library')")
  expect(src('components/library/TrackList.vue')).toContain("t('track.library')")
})

it('mini player: slim wave seek bar at the bottom; phones hide titles, similar, check and close', () => {
  const s = src('components/shell/MiniPlayer.vue')
  expect(s).toContain('<WaveSeekBar\n        compact')
  // Phones show title and artist on two lines, but no shuffle or repeat.
  expect(s).toContain('class="flex min-w-0 flex-col" data-mini-titles')
  expect(s).toMatch(/icon="shuffle"[\s\S]*?class="max-md:portrait:!hidden"/)
  // Phones keep previous, next, a big play button and the heart.
  expect(s).not.toMatch(/icon="prev"[\s\S]{0,80}max-md:!hidden/)
  expect(s).toContain('data-mini-play')
  expect(s).toContain('data-mini-like')
  expect(s).toMatch(/repeatLabel"[\s\S]*?class="max-md:portrait:!hidden"/)
  // `!` so the buttons' own display class can't override it on phones.
  // Similar and the static check stay off phones in both orientations,
  // leaving landscape room for the title.
  expect(s).toMatch(/icon="wand"[\s\S]*?class="max-md:!hidden"/)

  expect(s).toContain('class="shrink-0 max-md:portrait:!hidden"')
  // Landscape phones have room for the desktop extras (lyrics, queue, expand).
  expect(s).toContain('hidden min-w-0 flex-1 basis-0 items-center justify-end gap-1 landscape:flex md:flex')
  // The library check is gone (the heart took its slot).
  expect(s).not.toContain('name="check"')
  expect(s.match(/max-md:!hidden/g)).toHaveLength(1)
  // Phones and narrow desktops spend the eq bars' room on the title.
  // Eq bars moved into the right row beside the clock (v46).
  expect(s).toContain('<EqBars v-if="player.isPlaying.value" :size="10" class="mr-1 shrink-0" />')
  expect(s.indexOf('data-mini-progress')).toBeGreaterThan(s.indexOf('data-player-close'))
})

it('every album page menu offers Find on Spotify and Find on YouTube Music', () => {
  for (const f of ['views/AlbumView.vue', 'views/LinkView.vue']) {
    const s = src(f)
    expect(s, f).toContain("t('link.findSpotify')")
    expect(s, f).toContain("t('link.findYoutube')")
    expect(s, f).toContain('openAlbumOn(')
  }
})

it('phones: hero secondary buttons are icon-only so actions fit', () => {
  const css = src('index.css')
  expect(css).toContain(".hero-actions [data-has-icon]:not([data-variant='primary']) .ui-btn-label")
  expect(src('components/library/CollectionHero.vue')).toContain('hero-actions')
  expect(src('components/ui/UiButton.vue')).toContain('class="ui-btn-label"')
})

it('phones in either orientation: page header puts the cover left, details right, buttons below', () => {
  const s = src('components/library/CollectionHero.vue')
  expect(s).toContain('max-lg:grid-cols-[120px_minmax(0,1fr)]')
  expect(s).toContain("'max-lg:contents'")
  expect(s).toContain('max-lg:col-span-2')
})

it('phones: facts under the artist, buttons in one row, no location badges, no top bar outside Search', () => {
  expect(src('views/AlbumView.vue')).toContain("i === 0 && album.artist ? 'max-md:hidden' : ''")
  expect(src('views/LinkView.vue')).toContain('class="max-md:block" data-link-artists')
  const css = src('index.css')
  expect(css).toContain('.hero-actions { flex-wrap: nowrap; }')
  expect(src('styles/trackRows.css')).toContain('.source-track-grid > .source-locations, .library-track-grid > .source-locations { display: none; }')
  expect(src('components/shell/AppShell.vue')).toContain("routeName === 'Search' ? '' : 'max-md:hidden'")
  expect(src('views/LinkView.vue')).toContain('label: sourceLabel.value, icon: sourceIcon.value')
})
