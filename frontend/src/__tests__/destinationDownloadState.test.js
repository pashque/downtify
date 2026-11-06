import { describe, it, expect } from 'vitest'
import { destinationAvailable, songDownloadState } from '../lib/downloadState'

describe('destination-aware download buttons', () => {
  const song={downtify_destination_exists:false,downtify_destination_stem:'Drake/Album/09. Future, Drake - D4L'}
  it('offers album download despite a playable copy in a playlist', () => {
    expect(destinationAvailable(song,null,true)).toBe(false)
  })
  it('ignores an old completed playlist job for the album destination', () => {
    const item={state:'done',filename:'Playlist/Future, Drake - D4L.mp3'}
    expect(songDownloadState(item,destinationAvailable(song,item,true))).toBe('new')
  })
  it('recognizes a newly completed job at the intended album destination', () => {
    const item={state:'done',filename:'Drake/Album/09. Future, Drake - D4L.mp3'}
    expect(destinationAvailable(song,item,false)).toBe(true)
    expect(songDownloadState(item,destinationAvailable(song,item,false))).toBe('done')
  })
  it('keeps legacy global presence when no destination status was requested', () => {
    expect(destinationAvailable({},null,true)).toBe(true)
    expect(destinationAvailable({},null,false)).toBe(false)
  })
})
