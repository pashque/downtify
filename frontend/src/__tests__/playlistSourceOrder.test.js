import { describe, expect, it, vi } from 'vitest'
import { buildPlaylists, normalizeTrack, sortTracks } from '../lib/library.js'

const api = vi.hoisted(() => ({
  onMessage: vi.fn(),
  getLibrarySummary: vi.fn(), listPlaylists: vi.fn(),
  getPlaylistBatches: vi.fn(), listTracks: vi.fn(),
}))
vi.mock('/src/model/api', () => ({ default: api }))
vi.mock('/src/model/player', () => ({
  usePlayer: () => ({ refreshTracks: vi.fn(), forgetFiles: vi.fn() }),
}))
import { useLibrary } from '../model/library.js'

const rows = [
  { file: 'dont.mp3', title: "Don't", track_number: 2 },
  { file: 'fake.mp3', title: 'FAKE', track_number: 1 },
  { file: 'pidval.mp3', title: 'ПІДВАЛ', track_number: 12 },
  { file: 'fountains.mp3', title: 'Fountains (with Tems)', track_number: 16 },
]

describe('playlist source order', () => {
  it('replaces a stale restored manifest order on opening the playlist', async () => {
    api.getLibrarySummary.mockResolvedValue({ data: {} })
    api.getPlaylistBatches.mockResolvedValue({ data: { playlists: [] } })
    api.listPlaylists.mockResolvedValueOnce({ data: [{ name: 'P', files: rows.slice().reverse().map(r => r.file) }] })
    const library = useLibrary()
    await library.load({ force: true })
    const files = rows.map(r => r.file)
    // The monitor/metadata-only recovery rewrote the manifest while this
    // browser's rawPlaylists snapshot still points at the broken order.
    api.listPlaylists.mockResolvedValue({ data: [{ name: 'P', files }] })
    api.listTracks.mockResolvedValue({ data: rows })
    await library.loadPlaylistTracks('P')
    expect(library.findPlaylist('P').tracks.map(t => t.title)).toEqual(rows.map(r => r.title))
    expect(sortTracks(library.findPlaylist('P').tracks, { key: 'order' }).map(t => t.file)).toEqual(files)
  })

  it('joins by manifest order, not library insertion order or album number, retaining repeats', () => {
    const tracks = rows.slice().reverse().map(normalizeTrack)
    const files = ['dont.mp3', 'unavailable.mp3', 'pidval.mp3', 'fake.mp3', 'dont.mp3']
    const [playlist] = buildPlaylists([{ name: 'P', files }], new Map(tracks.map(t => [t.file, t])))
    expect(playlist.tracks.map(t => t.title)).toEqual(["Don't", 'ПІДВАЛ', 'FAKE', "Don't"])
    expect(playlist.tracks.map(t => t.trackNumber)).toEqual([2, 12, 1, 2])
  })
})
