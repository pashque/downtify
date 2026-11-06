import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
const src = (p) => readFileSync(new URL(`../${p}`, import.meta.url), 'utf8')
const between = (s, a, b) => s.slice(s.indexOf(a), s.indexOf(b, s.indexOf(a)))

it('mini: any empty spot of the bar opens the full player, controls and links do not', () => {
  const s = src('components/shell/MiniPlayer.vue')
  expect(s).toMatch(/data-mini-bar[\s\S]{0,200}@click="openFromBar"/)
  const fn = s.slice(s.indexOf('function openFromBar'))
  expect(fn).toContain("matches('button, a, input, [role=\"slider\"], [role=\"menu\"], [data-mini-progress]')")
  expect(fn).toContain('nowPlaying.open()')
})

it('under-cover format and heart only on phones; the desktop bar carries them', () => {
  const s = src('components/shell/NowPlaying.vue')
  const under = between(s, 'data-np-undercover', 'data-np-seek')
  expect(under).not.toContain('data-np-titleline')
  expect(under).toMatch(/data-np-cover-meta[^>]*lg:hidden|lg:hidden[^>]*data-np-cover-meta/)
  expect(under).toContain('data-np-cover-format')
  expect(under).toContain('data-np-cover-like')
})

it('volume button size is configurable and a collapse icon exists', () => {
  expect(src('components/player/VolumeControl.vue')).toContain(':size="buttonSize"')
  expect(src('components/ui/icons.js')).toMatch(/\n  collapse: /)
})

it('full player volume icon matches its neighbours', () => {
  expect(src('components/ui/UiIconButton.vue')).toContain('iconPx')
  expect(src('components/player/VolumeControl.vue')).toContain(':icon-px="iconPx"')
  expect(src('components/shell/NowPlaying.vue')).toMatch(/<VolumeControl[\s\S]{0,120}:icon-px="22"/)
})

it('the heart takes the library check slot in both players; no check left', () => {
  const mini = src('components/shell/MiniPlayer.vue')
  const np = src('components/shell/NowPlaying.vue')
  for (const s of [mini, np]) {
    expect(s).not.toContain('name="check"')
    expect(s).not.toContain('showDownloadedCheck')
  }
  const ctr = mini.slice(mini.indexOf('data-mini-controls'), mini.indexOf('data-mini-right'))
  expect(ctr.indexOf('data-mini-like')).toBeGreaterThan(ctr.indexOf('repeatLabel'))
  expect(between(mini, 'data-mini-meta', 'data-mini-controls')).not.toContain('data-mini-like')
  const tr = np.slice(np.indexOf('data-np-transport'), np.indexOf('data-np-bar-right'))
  expect(tr.indexOf('data-np-bar-like')).toBeGreaterThan(tr.indexOf('repeatLabel'))
  expect(between(np, 'data-np-bar-meta', 'data-np-transport')).not.toContain('data-np-bar-like')
})

it('every player button hovers with a round background and no accent focus ring', () => {
  const mini = src('components/shell/MiniPlayer.vue')
  const iconButtons = mini.match(/<UiIconButton[\s\S]*?\/>/g)
  expect(iconButtons.every((b) => /\bround\b/.test(b))).toBe(true)
  expect(src('components/player/LikeButton.vue')).toContain('round')
  expect(src('components/player/VolumeControl.vue')).toMatch(/<UiIconButton[\s\S]*?round/)
  const css = src('styles/tokens.css')
  expect(css).toMatch(/\[data-mini-bar\] :focus-visible,\s*\[data-now-playing\] :focus-visible/)
  expect(src('components/shell/NowPlaying.vue')).toContain('data-now-playing')
})

it('a control click never also opens the full player, even when it re-renders', () => {
  const s = src('components/shell/MiniPlayer.vue')
  const fn = s.slice(s.indexOf('function openFromBar'))
  expect(fn).toContain('event.composedPath()')
})

it('Details has no album/artist/save buttons', () => {
  const s = src('components/player/TrackDetails.vue')
  expect(s).not.toContain("t('player.goToAlbum')")
  expect(s).not.toContain("t('player.goToArtist')")
  expect(s).not.toContain("t('library.saveToDevice')")
})

it('full player bottom bar mirrors the mini bar: title block left, collapse in the expand slot', () => {
  const s = src('components/shell/NowPlaying.vue')
  expect(s).toContain('<div data-np-nowline class="flex min-w-0 flex-1 flex-col">')
  const right = s.slice(s.indexOf('data-np-bar-right'), s.indexOf('</footer>'))
  expect(right).toContain('button-size="md"')
  expect(right).toMatch(/data-np-collapse[\s\S]{0,300}nowPlaying\.close\(\)/)
  expect(right).toMatch(/data-np-collapse[\s\S]{0,300}name="collapse"/)
  expect(right).not.toContain('name="timer"')
})

it('v45: format badge sits left of volume in both bars; no lyrics/up next buttons there', () => {
  const mini = src('components/shell/MiniPlayer.vue')
  const right = mini.slice(mini.indexOf('data-mini-right'), mini.indexOf('<WaveSeekBar'))
  const order = ['data-mini-format', '<VolumeControl', 'icon="expand"', 'data-player-close'].map((k) => right.indexOf(k))
  expect(order.every((i) => i > 0)).toBe(true)
  expect([...order].sort((a, b) => a - b)).toEqual(order)
  expect(right).not.toContain("t('player.lyrics')")
  expect(right).not.toContain("t('player.upNext')")
  expect(mini).not.toContain('data-mini-meta')
  const np = src('components/shell/NowPlaying.vue')
  const npRight = np.slice(np.indexOf('data-np-bar-right'), np.indexOf('</footer>'))
  const npOrder = ['data-np-format', '<VolumeControl', 'data-np-collapse', 'data-np-more'].map((k) => npRight.indexOf(k))
  expect(npOrder.every((i) => i > 0)).toBe(true)
  expect([...npOrder].sort((a, b) => a - b)).toEqual(npOrder)
  expect(npRight).not.toContain('data-np-bar-lyrics')
  expect(npRight).not.toContain('data-np-bar-queue')
  expect(np).not.toContain('data-np-bar-meta')
})

it('v46: both bars read eq bars, time, format, volume on one row; nothing floats', () => {
  const mini = src('components/shell/MiniPlayer.vue')
  const right = mini.slice(mini.indexOf('data-mini-right'), mini.indexOf('<WaveSeekBar'))
  const order = ['<EqBars', 'data-mini-clock', 'data-mini-format', '<VolumeControl'].map((k) => right.indexOf(k))
  expect(order.every((i) => i > 0)).toBe(true)
  expect([...order].sort((a, b) => a - b)).toEqual(order)
  expect(mini).not.toContain('data-mini-time')
  expect(mini.slice(mini.indexOf('data-mini-titles'), mini.indexOf('data-mini-controls'))).not.toContain('<EqBars')
  // The clock keeps one width for the whole track (invisible widest copy).
  expect(right).toContain('clockSizer')
  const np = src('components/shell/NowPlaying.vue')
  const npRight = np.slice(np.indexOf('data-np-bar-right'), np.indexOf('</footer>'))
  const npOrder = ['<EqBars', 'data-np-clock', 'data-np-format', '<VolumeControl'].map((k) => npRight.indexOf(k))
  expect(npOrder.every((i) => i > 0)).toBe(true)
  expect([...npOrder].sort((a, b) => a - b)).toEqual(npOrder)
  expect(npRight).toContain('clockSizer')
})

it('v46: the full player volume slider keeps its flex centring', () => {
  const np = src('components/shell/NowPlaying.vue')
  const vol = np.slice(np.indexOf('<VolumeControl', np.indexOf('data-np-bar-right')))
  const width = vol.match(/width="([^"]+)"/)[1]
  expect(width).not.toMatch(/\bblock\b/)
})

it('v45: full player ⋯ menu order', () => {
  const np = src('components/shell/NowPlaying.vue')
  const menu = np.slice(np.indexOf('const trackMenu'), np.indexOf('function navigate'))
  const desktop = menu.slice(menu.indexOf(': ['))
  const keys = ["'player.goToAlbum'", "'player.goToArtist'", "'link.findSpotify'", "'player.lyrics'", "'player.upNext'", "'player.details'", "'player.equalizer'", "'player.sleepTimer'"]
  const head = keys.slice(0, 3).map((k) => menu.indexOf(k))
  expect(head.every((i) => i > 0)).toBe(true)
  expect([...head].sort((a, b) => a - b)).toEqual(head)
  const tail = keys.slice(3).map((k) => desktop.indexOf(k))
  expect(tail.every((i) => i > 0)).toBe(true)
  expect([...tail].sort((a, b) => a - b)).toEqual(tail)
  expect(menu).toContain('openTrackOnSpotify(')
})

it('a streamed track offers a working download in both players', () => {
  for (const f of ['components/shell/MiniPlayer.vue', 'components/shell/NowPlaying.vue']) {
    const s = src(f)
    // Shown for any stream not in the library; usable once its video id is known.
    expect(s, f).toMatch(/showPlayerDownload = computed\(\s*\(\) => !!track\.value\?\.stream && !streamDownloaded\.value/)
    expect(s, f).toMatch(/:disabled="downloadBusy \|\| !pendingSong"/)
  }
  const mini = src('components/shell/MiniPlayer.vue')
  expect(mini.slice(mini.indexOf('data-mini-controls'), mini.indexOf('data-mini-right'))).toMatch(/v-if="showPlayerDownload"/)
})
