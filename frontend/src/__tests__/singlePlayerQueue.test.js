import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import en from '../i18n/locales/en'
const source = () => readFileSync(new URL('../components/shell/NowPlaying.vue',import.meta.url),'utf8')
it('uses only one frameless Up Next component, in the right-hand slot',()=>{
 const s=source()
 expect(s.match(/<UpNextPanel\b/g)).toHaveLength(1)
 const aside=s.slice(s.indexOf('data-np-queue'),s.indexOf('</aside>'))
 expect(aside).toContain('<UpNextPanel')
 expect(aside).not.toContain('rounded-panel')
 expect(s).toContain('desktopQueueVisible')
})
it('queue-only uses the same wide second column as a lone central panel',()=>{
 const s=source()
 const rule=s.match(/\.np-body\[data-queue-visible="true"\]\[data-central-panel="false"\]\s*\{([^}]+)\}/)?.[1]
 expect(rule).toContain('grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)')
})
it('uses concise grammatical collection context headings',()=>{
 expect(en.player.playingFrom.album).toBe('Playing album')
 expect(en.player.playingFrom.playlist).toBe('Playing playlist')
})
