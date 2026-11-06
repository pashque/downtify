import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
const src=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8')
it('desktop header/body/transport align to the wave seek edges',()=>{
 const s=src('components/shell/NowPlaying.vue')
 expect(s).toContain('np-edge-aligned')
 expect(s).toContain('data-np-seek')
 const css=src('index.css')
 expect(css).toContain('.np-edge-aligned { margin-inline: 60px; }')
})
it('bottom information is title first, then artist and clickable album',()=>{
 const s=src('components/shell/NowPlaying.vue')
 const line=s.slice(s.indexOf('data-np-nowline'),s.indexOf('data-np-nowline')+2200)
 expect(line.indexOf('track.title')).toBeLessThan(line.indexOf('track.artist'))
 expect(line).toContain('data-np-bottom-album')
 expect(line).toContain('flex-col')
 expect(s).toContain('data-np-cover-album')
 expect(s).toContain('playerAlbumRoute(track.value)')
})
it('close arrow has no accent outline but retains a keyboard focus background',()=>{
 const s=src('components/shell/NowPlaying.vue')
 const button=s.slice(s.indexOf('ref="closeButton"'),s.indexOf('ref="closeButton"')+600)
 expect(button).toContain('focus-visible:outline-none')
 expect(button).toContain('focus-visible:bg-white/20')
})
it('playback source title underlines only when navigable and hovered',()=>{
 const s=src('components/shell/NowPlaying.vue')
 expect(s).toContain("contextRoute ? 'hover:underline'")
})
