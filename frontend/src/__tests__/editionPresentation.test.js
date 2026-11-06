import { expect, it } from 'vitest'
import mallgrab from './fixtures/mallgrab-editions.json'
import { groupAlbumEditions, albumEditionOptions } from '../lib/albumEditions'

const release = (id, changes = {}) => ({ id, title: 'Album +', track_count: 1, explicit: true,
  release_date: '2024-01-01', tracks: [{ name: 'One', artists: ['A'], duration: 201.123, explicit: true, track_number: 1 }], ...changes })

it('collapses identical recordings while retaining exact selected source as representative', () => {
  const a = release('a'), b = release('b', { release_date: '2025-01-01' })
  const originals = JSON.stringify([a,b])
  const groups = groupAlbumEditions([a,b], 'b')
  expect(groups).toHaveLength(1)
  expect(groups[0]).toMatchObject({ id: 'b', source_ids: ['a','b'] })
  expect(JSON.stringify([a,b])).toBe(originals)
  expect(albumEditionOptions(groups, k => k)).toEqual([{ value: 'b', label: '1 library.tracks' }])
})

it('collapses the two real Mall Grab releases but keeps the remembered exact source', () => {
  const selected = '4r18cGNjieFLVFFLbHg6uC'
  expect(groupAlbumEditions(mallgrab, selected)).toEqual([
    expect.objectContaining({ id: selected, track_count: 13,
      source_ids: ['2UNAcB8u7FFK0gAqQjzszb', selected] }),
  ])
})

it.each([
  ['title punctuation', { title: 'Album' }],
  ['deluxe title', { title: 'Album + (Deluxe)' }],
  ['track title', { tracks: [{ name: 'Other', artists: ['A'], duration: 201.123, explicit: true }] }],
  ['duration', { tracks: [{ name: 'One', artists: ['A'], duration: 202, explicit: true }] }],
  ['clean', { explicit: false, tracks: [{ name: 'One', artists: ['A'], duration: 201.123, explicit: false }] }],
  ['credits', { tracks: [{ name: 'One', artists: ['B'], duration: 201.123, explicit: true }] }],
  ['missing evidence', { tracks: undefined }],
  ['unknown explicit', { tracks: [{ name: 'One', artists: ['A'], duration: 201.123 }] }],
])('retains releases differing by %s, regardless of equal count', (_, changes) => {
  const editions = groupAlbumEditions([release('a'), release('b', changes)], 'b')
  expect(editions).toHaveLength(2)
  const options = albumEditionOptions(editions, k => k)
  expect(new Set(options.map(o => o.label)).size).toBe(2)
  expect(options.map(o => o.value)).toEqual(['a', 'b'])
})

it('names clean/explicit and deluxe differences rather than only track counts', () => {
  const options = albumEditionOptions([
    release('explicit'),
    release('clean', { explicit: false }),
    release('deluxe', { title: 'Album + (Deluxe)', track_count: 2 }),
  ], k => k)
  expect(options[0].label).toContain('search.explicit')
  expect(options[1].label).toContain('search.clean')
  expect(options[2].label).toContain('(Deluxe)')
})

it('retains differing track sequence and disc positions', () => {
  const two = release('a', { track_count: 2, tracks: [release('a').tracks[0], { ...release('a').tracks[0], name: 'Two', track_number: 2 }] })
  expect(groupAlbumEditions([two, { ...two, id: 'b', tracks: [...two.tracks].reverse() }], 'b')).toHaveLength(2)
  expect(groupAlbumEditions([release('a'), release('b', { tracks: [{ ...release('a').tracks[0], disc_number: 2 }] })], 'b')).toHaveLength(2)
})
