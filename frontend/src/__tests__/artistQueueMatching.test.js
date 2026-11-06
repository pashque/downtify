import { expect, it, vi } from 'vitest'

const state = vi.hoisted(() => ({ local: null, play: vi.fn() }))
vi.mock('/src/model/library', () => ({ useLibrary: () => ({ findTrack: () => state.local }) }))
vi.mock('/src/model/player', () => ({ usePlayer: () => ({ isPlaying: { value: false } }) }))
vi.mock('/src/model/trackActions', () => ({ useTrackActions: () => ({ play: state.play }) }))
vi.mock('/src/model/stream', () => ({ isStreamingSong: () => false, playStream: vi.fn(), resolvingFor: () => false }))
vi.mock('/src/model/ui', () => ({ useUi: () => ({ toast: vi.fn() }) }))
vi.mock('/src/i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('/src/model/api', () => ({ default: {} }))
import { normalizeTrack } from '../lib/library'
import { useSongStarter } from '../model/songPlay'

it('finds the correct queue copy by the complete structured lead artist', () => {
  state.local = normalizeTrack({ file: 'playlist.mp3', title: 'ST. CHROMA', artists: ['Tyler, The Creator', 'Daniel Caesar'] })
  const wrong = normalizeTrack({ file: 'wrong.mp3', artist: 'Tyler', title: 'ST. CHROMA' })
  const right = normalizeTrack({ file: 'album.mp3', artist: 'Tyler, The Creator', title: 'ST. CHROMA' })
  const queue = [wrong, right]
  useSongStarter()({ artists: ['Tyler, The Creator'], name: 'ST. CHROMA' }, { queue })
  expect(state.play).toHaveBeenCalledWith(queue, 1, null)
})
