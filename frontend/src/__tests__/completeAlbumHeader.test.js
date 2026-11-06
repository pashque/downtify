import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'

const view = name => readFileSync(new URL(`../views/${name}View.vue`, import.meta.url), 'utf8')
// Expressions come only from trusted, checked-in Vue templates, never user input.
const condition = (source, click) => source.match(new RegExp(`<UiButton\\s+v-if="([^"]+)"(?:(?!</UiButton>)[\\s\\S])*?@click="${click}"`))?.[1]

it('Library album header hides its download action only when the canonical destination is complete', () => {
 const expression = condition(view('Album'), 'downloadAlbum')
 expect(expression).toBeTruthy()
 const visible = new Function('sourceSongs', 'albumComplete', 'targetLoaded = false', `return Boolean(${expression})`)
 expect(visible([{}], true)).toBe(false)
 expect(visible([{}], false)).toBe(false)
 expect(visible([{}], false, true)).toBe(true)
 expect(visible(null, false)).toBe(false)
})

it('Link album header waits for verified completeness and preserves selected-track and non-album actions', () => {
 const source = view('Link')
 const expression = source.match(/<UiButton\s+v-if="([^"]+)"[\s\S]*?data-link-primary/)?.[1]
 const visible = new Function('selected', 'details', 'albumComplete', 'newSongs', 'albumTargetLoaded = false', `return Boolean(${expression})`)
 expect(visible(new Set(), {kind:'album'}, true, [{}])).toBe(false)
 expect(visible(new Set(), {kind:'album'}, false, [])).toBe(false)
 expect(visible(new Set(), {kind:'album'}, false, [], true)).toBe(true)
 expect(visible(new Set(), {kind:'album'}, true, [], true)).toBe(true)
 expect(visible(new Set(['one']), {kind:'album'}, true, [])).toBe(true)
 expect(visible(new Set(), {kind:'playlist'}, true, [{}])).toBe(true)
 expect(visible(new Set(), {kind:'playlist'}, false, [])).toBe(false)
 // Hiding an album action must not replace it with an unrequested status panel.
 expect(source).toMatch(/<span\s+v-else-if="details.kind !== 'album'"/)
})
