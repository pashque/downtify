// @vitest-environment happy-dom
import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { createApp, h } from 'vue'
import TrackDownPlayHeader from '../components/library/TrackDownPlayHeader.vue'
const source = p => readFileSync(new URL('../'+p, import.meta.url), 'utf8')
it('heads shared rows in user order with separate reserved heart and menu cells', () => {
 const root = document.createElement('div')
 const app = createApp({render:()=>h(TrackDownPlayHeader,{hideAlbum:false,showAdded:true})})
 app.mount(root)
 expect([...root.querySelectorAll('[data-column]')].map(e=>e.dataset.column)).toEqual(['number','title','album','time','format','added','download','locations','heart','menu'])
 expect(root.firstElementChild.className).toContain('border-b')
 app.unmount()
})
it('renders neutral icon-only confirmation, gray arrows with green icon-only hover and gray locations',()=>{
 const s=source('components/search/DownloadState.vue')
 expect(s).not.toContain('rounded-full')
 expect(s).not.toContain('bg-accent')
 expect(s).toContain('hover:text-accent')
 expect(s).toContain('text-muted')
 expect(source('components/library/LocationBadges.vue')).not.toContain('accent')
})
it('all source row families expose the same ordered columns without per-row location lookup',()=>{
 for(const p of ['components/library/TrackDownPlay.vue','components/search/SongRow.vue','components/similar/SimilarTrackRow.vue','views/LinkView.vue']) {
  const s=source(p).split('<script')[0]
  const cols=[...s.matchAll(/data-column="([^"]+)"/g)].map(m=>m[1])
  expect(cols, p).toEqual(['number','title','album','time','format','download','locations','heart','menu'])
  expect(source(p)).not.toContain('lookupLibraryLocations(')
 }
})
it('search and similar lists use shared headers and batched locations without changing recommendation providers',()=>{
 for(const p of ['views/SearchView.vue','views/SimilarView.vue']) {
  const s=source(p)
  expect(s).toContain('<TrackDownPlayHeader hide-album')
  expect(s).toContain('useLibraryLocations')
  expect(s).toContain(':location="locationFor(song)"')
  expect(s).not.toContain('Header legacy')
 }
})
it('only real monitored batch metadata enables Added, never manual playlist timestamps',()=>{
 expect(source('views/PlaylistView.vue')).toContain(':show-added="batch?.monitored === true && !playlist.manual"')
 expect(source('components/library/TrackList.vue')).toContain('showAdded: { type: Boolean, default: false }')
})
it('source, search, similar and link rows show the heart for songs already in the library',()=>{
 for(const p of ['components/library/TrackDownPlay.vue','components/search/SongRow.vue','components/similar/SimilarTrackRow.vue','views/LinkView.vue']) expect(source(p),p).toContain('<LocalLike')
 expect(source('components/library/LocalLike.vue')).toContain('library.findTrack')
})
