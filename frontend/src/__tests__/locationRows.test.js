// @vitest-environment happy-dom
import { expect, it } from 'vitest'
import { createApp, h } from 'vue'
import { readFileSync } from 'node:fs'
import LocationBadges from '../components/library/LocationBadges.vue'
const source = path => readFileSync(new URL('../'+path,import.meta.url),'utf8')
it('links each verified native location, hiding the current resource kind', () => {
 const root=document.createElement('div')
 const location={albums:[{artist:'A',title:'Album'}],playlists:[{name:'One'},{name:'Two'}]}
 const app=createApp({render:()=>h(LocationBadges,{location,contextKind:'album'})})
 app.component('RouterLink',{props:['to'],render(){return h('a',{'data-route':JSON.stringify(this.to)},this.$slots.default())}})
 app.mount(root)
 expect(root.querySelectorAll('[data-location-kind="playlist"]')).toHaveLength(2)
 expect(root.querySelector('[data-location-kind="album"]')).toBeNull()
 expect(root.querySelector('a').dataset.route).toContain('Playlist')
 app.unmount()
})
it('keeps Similar in menus rather than standalone wands in search and similar track rows', () => {
 for (const path of ['components/search/SongRow.vue', 'components/similar/SimilarTrackRow.vue']) {
  expect(source(path)).not.toContain('SimilarButton')
  expect(source(path)).toContain('SourceSongMenu')
 }
})
it('uses reserved grids, actual format cells and round controls without row wands',()=>{
 for(const path of ['components/library/TrackDownPlay.vue','views/LinkView.vue']) {
  const s=source(path)
  expect(s).not.toContain('SimilarButton')
  expect(s).toContain('data-track-duration')
  expect(s).toContain('data-track-download-cell')
  expect(s).toContain('TrackFormat')
  expect(s).toContain('LocationBadges')
  expect(s).toContain('source-track-grid')
  expect(s).toContain('round')
 }
 expect(source('components/library/TrackDownPlayHeader.vue')).toContain('source-track-grid')
 expect(source('components/library/TrackList.vue')).toContain('LocationBadges')
 const playlist=source('views/PlaylistView.vue')
 expect(playlist).not.toContain('actions.downloadZip(playlist.tracks)')
 expect(playlist.indexOf('<TrackSortSelect')).toBeLessThan(playlist.indexOf('</CollectionHero>'))
})
