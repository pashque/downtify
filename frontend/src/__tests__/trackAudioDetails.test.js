// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, nextTick, ref } from 'vue'
import TrackDetails from '../components/player/TrackDetails.vue'
const state = vi.hoisted(() => ({}))
vi.mock('/src/model/player', () => ({ usePlayer: () => state.player }))
vi.mock('/src/model/api', () => ({ default: { getAudioDetails: (...args) => state.fetch(...args) } }))
vi.mock('/src/i18n', () => ({ useI18n: () => ({ t: key => key, locale: ref('en') }) }))
vi.mock('../components/library/ArtistCredits.vue', () => ({ default: { template: '<span />' } }))
let app, host
const settle = async () => { await new Promise(resolve => setTimeout(resolve, 0)); await nextTick() }
afterEach(() => { app?.unmount(); host?.remove(); vi.restoreAllMocks() })
function mount(track = {file: 'song.mp3', title: 'Song', format: 'MP3'}) {
  state.player = { currentTrack: ref(track) }
  host = document.createElement('div'); document.body.append(host)
  app = createApp(TrackDetails)
  app.component('RouterLink', {template: '<a><slot /></a>'})
  app.mount(host)
}
it('loads measured details once per file and renders neutral MP3 mode, not a quality rating', async () => {
  state.fetch = vi.fn().mockResolvedValue({codec:'mp3',bitrate:191996,sample_rate:44100,channels:2,channel_mode:'Joint stereo',lossless:false})
  mount(); await settle()
  expect(state.fetch).toHaveBeenCalledExactlyOnceWith('song.mp3')
  // One Format line, not a row per parameter.
  expect(host.textContent).toContain('MP3 · 192 kbps · 44.1 kHz · Joint stereo')
  for (const label of ['track.codec','track.bitrate','track.sampleRate','track.channels','track.channelMode','track.bitDepth','track.encoding'])
    expect(host.textContent).not.toContain(label)
  expect(host.textContent).not.toMatch(/lower|inferior|bad|16-bit|24-bit/i)
  state.player.currentTrack.value = {...state.player.currentTrack.value, title:'Renamed'}
  await settle(); expect(state.fetch).toHaveBeenCalledTimes(1)
})
it('clears previous facts immediately and ignores stale responses', async () => {
  let oldResolve
  state.fetch = vi.fn().mockImplementationOnce(() => new Promise(resolve => {oldResolve=resolve}))
    .mockResolvedValue({codec:'flac',bit_depth:24,sample_rate:96000,channels:2,lossless:true})
  mount(); await settle()
  state.player.currentTrack.value={file:'new.flac',format:'FLAC'}; await settle()
  oldResolve({codec:'mp3',bitrate:320000,channel_mode:'Joint stereo'}); await settle()
  expect(host.textContent).toContain('FLAC · 24-bit · 96 kHz · Stereo')
  expect(host.textContent).not.toContain('320 kbps')
  expect(host.textContent).not.toContain('Joint stereo')
})
it('hides unavailable facts and never probes a remote stream', async () => {
  state.fetch=vi.fn().mockRejectedValue(new Error('not available'))
  mount(); await settle()
  expect(host.textContent).not.toContain('kbps')
  state.player.currentTrack.value={file:'stream:abc',isStream:true}; await settle()
  expect(state.fetch).toHaveBeenCalledTimes(1)
})
it('names the codec beside a different container and never calls lossy 2-channel audio Stereo', async () => {
  state.fetch=vi.fn().mockResolvedValue({codec:'aac',bitrate:256000,sample_rate:44100,channels:2,lossless:false})
  mount({file:'song.m4a',format:'M4A'}); await settle()
  expect(host.textContent).toContain('M4A (AAC) · 256 kbps · 44.1 kHz · 2 ch')
  expect(host.textContent).not.toContain('Stereo')
})
