// @vitest-environment happy-dom
import { createApp, h } from 'vue'
import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
const css = readFileSync('src/styles/trackRows.css', 'utf8')
import TrackFormat from '../components/library/TrackFormat.vue'
it('keeps mixed actual formats on one non-shrinking inline row with room for both pills', () => {
 const root=document.createElement('div')
 const app=createApp({render:()=>h(TrackFormat,{formats:['mp3','flac']})});app.mount(root)
 const badges=root.querySelector('[data-track-format]')
 expect(badges.classList.contains('flex-nowrap')).toBe(true)
 expect(badges.classList.contains('whitespace-nowrap')).toBe(true)
 expect([...badges.children].every(p=>p.classList.contains('shrink-0'))).toBe(true)
 expect(css).toContain('--format: 112px')
 expect(css).toContain('48px var(--format)')
 expect(css).toContain('.source-format { display: none; }')
 app.unmount()
})
