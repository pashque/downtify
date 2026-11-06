import { expect,it } from 'vitest'
import {readFileSync} from 'node:fs'
const src=()=>readFileSync(new URL('../components/shell/NowPlaying.vue',import.meta.url),'utf8')
it('caps full-screen play button at 60px on every viewport',()=>{
 expect(src()).toContain('width: clamp(3rem, 7vh, 3.75rem)')
 expect(src()).toContain('height: clamp(3rem, 7vh, 3.75rem)')
})
it('puts a plain mobile Up Next action in the transport and moves extras to the top menu',()=>{
 const s=src()
 expect(s).toContain('data-np-mobile-queue')
 expect(s).not.toContain('<!-- Phone extras -->')
 expect(s).toContain('ref="mobileSleepMenu"')
 expect(s).toContain("openMobileMenu(mobileSleepMenu.value)")
 expect(s).toContain("panels.value.filter((tab) => tab.id !== 'queue')")
})
