// @vitest-environment happy-dom
import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { rowPlaybackClick } from '../lib/rowPlayback'
it('all native track rows guard controls and play on a single click',()=>{
 for(const file of ['components/library/TrackList.vue','components/library/TrackDownPlay.vue','components/search/SongRow.vue','components/similar/SimilarTrackRow.vue','components/player/UpNextPanel.vue','views/LinkView.vue']) {
  const s=readFileSync(new URL('../'+file,import.meta.url),'utf8')
  expect(s,file).toContain('rowPlaybackClick')
 }
})
it('plays a plain primary row click but not links, controls, modifiers or text selection',()=>{
 const row=document.createElement('div');row.innerHTML='<span>Track</span><a>Artist</a><button><i></i></button><input><span role="checkbox"></span>'
 const event=target=>({target,button:0,defaultPrevented:false})
 expect(rowPlaybackClick(event(row.firstChild))).toBe(true)
 for(const target of [row.querySelector('a'),row.querySelector('i'),row.querySelector('input'),row.lastChild]) expect(rowPlaybackClick(event(target))).toBe(false)
 expect(rowPlaybackClick({...event(row),ctrlKey:true})).toBe(false)
 expect(rowPlaybackClick({...event(row),button:2})).toBe(false)
 expect(rowPlaybackClick({...event(row),defaultPrevented:true})).toBe(false)
})
