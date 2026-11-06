import { expect, it, vi } from 'vitest'
const state = vi.hoisted(() => ({ current: { value: null }, local: null, play: vi.fn(), find: vi.fn() }))
vi.mock('/src/model/library', () => ({ useLibrary: () => ({ findTrack: state.find }) }))
vi.mock('/src/model/player', () => ({ usePlayer: () => ({ currentTrack: state.current, isPlaying: { value: false } }) }))
vi.mock('/src/model/trackActions', () => ({ useTrackActions: () => ({ play: state.play }) }))
vi.mock('/src/model/ui', () => ({ useUi: () => ({ toast: vi.fn() }) }))
vi.mock('/src/i18n', () => ({ useI18n: () => ({ t: key => key }) }))
vi.mock('/src/model/api', () => ({ default: {} }))
import { normalizeTrack, dedupeAlbumTracks } from '../lib/library'
import { rowKey } from '../model/streamResolve'
import { isStreamingSong, streamTrack } from '../model/stream'
import { songToPlayerTrack, useSongStarter } from '../model/songPlay'

it('uses scoped source IDs in row identity and preserves them through stream/local queue conversion', () => {
  const one = { song_id: 'one', provider: 'spotify', artist: '!!!', name: 'A|B' }
  const two = { ...one, song_id: 'two' }
  expect(rowKey(one)).not.toBe(rowKey(two))
  expect(rowKey(one)).not.toBe(rowKey({ artist: 'spotify', name: 'one' }))
  expect(rowKey({ artist: 'A|B', name: 'C' })).not.toBe(rowKey({ artist: 'A', name: 'B|C' }))
  expect(rowKey({ artist: ' Ａ/B ', name: 'Ｔrack' })).toBe(rowKey({ artist: 'a/b', name: 'track' }))
  state.find.mockReturnValue(null)
  const queued = songToPlayerTrack(one, state.find)
  expect(state.find).toHaveBeenLastCalledWith('!!!', 'A|B', one)
  expect(rowKey(queued)).toBe(rowKey(one))
  state.current.value = streamTrack(one, 'stream-url', 'abcdefghijk')
  expect(isStreamingSong(two)).toBe(false)
  expect(isStreamingSong(one)).toBe(true)
  expect(isStreamingSong({ artist: '!!!', name: 'A|B' })).toBe(true)
  expect(isStreamingSong({ artist: '+++', name: 'A|B' })).toBe(false)
})

it('does not select another edition or an empty-file stream when finding a local queue copy', () => {
  const local = normalizeTrack({ file: 'local.mp3', artist: 'A/B', title: 'Track', song_id: 'two', provider: 'spotify' })
  const wrong = normalizeTrack({ file: 'wrong.mp3', artist: 'A/B', title: 'Track', song_id: 'one', provider: 'spotify' })
  const right = { ...local, file: 'album.mp3' }
  const stream = { ...local, file: '', stream: true }
  state.find.mockReturnValue(local)
  const queue = [stream, wrong, right]
  useSongStarter()({ artist: 'A/B', name: 'Track', song_id: 'two', provider: 'spotify' }, { queue })
  expect(state.play).toHaveBeenLastCalledWith(queue, 2, null)
  expect(dedupeAlbumTracks([wrong, right])).toEqual([wrong, right])
})

it('starts the actual clicked provider edition in a same-title mixed queue', () => {
  const one = { song_id: 'one', provider: 'spotify', artist: 'Artist', name: 'Song' }
  const two = { ...one, song_id: 'two' }
  state.find.mockReturnValue(null)
  useSongStarter()(two, { songs: [one, two] })
  expect(state.play.mock.calls.at(-1)[1]).toBe(1)
})
