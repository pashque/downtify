import { describe, expect, it, vi } from 'vitest'
import { artistKey, songKey, albumKey, normalizeTrack, indexTracksBySong, providerSongKey, dedupeAlbumTracks } from '../lib/library'
import { discographySections } from '../lib/discography'

vi.mock('/src/model/api', () => ({ default: { onMessage: vi.fn() } }))
vi.mock('/src/model/player', () => ({ usePlayer: () => ({}) }))
import { useLibrary } from '../model/library'

const labels = { albums: 'Albums', singles: 'Singles' }
describe('global punctuation-preserving identity', () => {
  it('keeps symbol-only artists, delimiters, dots, commas, slash and ampersand distinct', () => {
    const names = ['!!!', '+++', '|', '.', ',', 'A/B', 'A&B', 'A B', 'A.B', 'AB', 'A,B']
    expect(new Set(names.map(name => songKey(name, 'Track'))).size).toBe(names.length)
    expect(songKey('A|B', 'C')).not.toBe(songKey('A', 'B|C'))
    expect(songKey('Artist', 'CHROMAKOPIA')).not.toBe(songKey('Artist', 'CHROMAKOPIA +'))
    expect(songKey('Artist', 'ST. CHROMA')).not.toBe(songKey('Artist', 'ST CHROMA'))
    expect(songKey('Artist', 'Song (Remastered)')).not.toBe(songKey('Artist', 'Song'))
  })
  it('matches the NFKC lower + whitespace contract without accent folding or casefold', () => {
    expect(artistKey('  Ａ/B  Band\t')).toBe('a/b band')
    expect(songKey('  Ａ/B  Band\t', 'Ｔrack')).toBe(songKey('a/b band', 'track'))
    expect(songKey('Straße', 'Song')).not.toBe(songKey('Strasse', 'Song'))
    expect(songKey('Beyoncé', 'Song')).not.toBe(songKey('Beyonce', 'Song'))
    expect(albumKey(' Ａ/B ', ' Ｔitle  + ')).toBe(albumKey('a/b', 'title +'))
  })
  it('never aliases punctuation-distinct library presence or playback files', () => {
    const library = useLibrary()
    const local = normalizeTrack({ file: 'symbols.mp3', artist: '!!!', title: 'ST. CHROMA' })
    library.tracks.value = [local]
    expect(library.hasSong('+++', 'ST. CHROMA')).toBe(false)
    expect(library.findTrack('!!!', 'ST CHROMA')).toBeNull()
    expect(library.findTrack('!!!', 'ST. CHROMA')).toBe(local)
  })
})

it('prefers exact provider track IDs without aliasing different IDs or ambiguous id-less requests', () => {
  const library = useLibrary()
  const first = normalizeTrack({ file: 'first.mp3', artist: 'A/B', title: 'Track', song_id: 'one', provider: 'spotify' })
  const second = normalizeTrack({ file: 'second.mp3', artist: 'A/B', title: 'Track', song_id: 'two', provider: 'spotify' })
  library.tracks.value = [first, second]
  expect(library.findTrack('A/B', 'Track', { song_id: 'two', provider: 'spotify' })).toBe(second)
  expect(library.findTrack('A/B', 'Track', { song_id: 'one', provider: 'deezer' })).toBeNull()
  expect(library.findTrack('A/B', 'Track', { song_id: 'missing', provider: 'spotify' })).toBeNull()
  expect(library.findTrack('A/B', 'Track')).toBeNull()
  library.tracks.value = [normalizeTrack({ file: 'legacy.mp3', artist: 'A/B', title: 'Track' })]
  expect(library.findTrack('A/B', 'Track', { song_id: 'two', provider: 'spotify' })?.file).toBe('legacy.mp3')
})

it('never collapses known provider editions in the exported index or local album queue', () => {
  const one = normalizeTrack({ file: 'one.mp3', artist: 'Artist', title: 'Song', provider: 'spotify', song_id: 'one' })
  const two = normalizeTrack({ file: 'two.mp3', artist: 'Artist', title: 'Song', provider: 'spotify', song_id: 'two' })
  const index = indexTracksBySong([one, two])
  expect(index.get(songKey('Artist', 'Song'))).toBeUndefined()
  expect(index.get(`id:${providerSongKey(two)}`)).toBe(two)
  const older = { artist: 'Artist', title: 'Song', file: 'old.mp3', year: '2020', explicit: true }
  const newer = { ...older, file: 'new.mp3', year: '2025' }
  const clean = { ...older, file: 'clean.mp3', explicit: false }
  expect(dedupeAlbumTracks([older, newer, clean])).toEqual([older, newer, clean])
})

it('dedupes only identical provider release IDs, independent of URL query strings', () => {
  const releases = [
    { album_id: '123', provider: 'spotify', name: 'Same', url: 'https://open.spotify.com/album/123?si=one' },
    { album_id: '123', provider: 'spotify', name: 'Same', url: 'https://open.spotify.com/album/123?si=two' },
    { album_id: '123', provider: 'deezer', name: 'Same', url: 'https://www.deezer.com/album/123' },
    { name: 'No ID' }, { name: 'No ID' },
  ]
  expect(discographySections(releases, [], labels)[0].items).toEqual([releases[0], releases[2], releases[3], releases[4]])
})

it('keeps every distinct release ID, original title, edition, year and type despite local partial ownership', () => {
  const releases = [
    { album_id: 'explicit', name: 'CHROMAKOPIA', explicit: true, release_type: 'album', year: '2024' },
    { album_id: 'clean', name: 'CHROMAKOPIA', explicit: false, release_type: 'album', year: '2024' },
    { album_id: 'reissue', name: 'CHROMAKOPIA', release_type: 'album', year: '2025' },
    { album_id: 'plus', name: 'CHROMAKOPIA +', release_type: 'album' },
    { album_id: 'ep', name: 'CHROMAKOPIA', release_type: 'EP' },
    { album_id: 'symbols', name: '!!! +++ | ., / &', release_type: 'single' },
  ]
  const groups = discographySections([...releases, releases[0]], [{ title: 'CHROMAKOPIA', tracks: [{}] }], labels)
  expect(groups.flatMap(group => group.items)).toEqual(releases)
})
