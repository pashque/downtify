import { expect, it } from 'vitest'
import { dismissPlayerSwipe } from '../lib/playerSwipe'
import { readFileSync } from 'node:fs'
it('dismisses a deliberate downward mobile swipe from a permitted surface', () => {
  expect(dismissPlayerSwipe({ x: 100, y: 30 }, { x: 110, y: 160 }, true)).toBe(true)
})
it('does not dismiss for taps, upward/horizontal gestures, desktop or cancelled touches', () => {
  for (const [start,end,mobile] of [
    [{x:100,y:30},{x:101,y:36},true],
    [{x:100,y:160},{x:110,y:30},true],
    [{x:100,y:30},{x:250,y:140},true],
    [{x:100,y:30},{x:110,y:160},false],
    [null,{x:110,y:160},true],
  ]) expect(dismissPlayerSwipe(start,end,mobile)).toBe(false)
})
it('player only starts swipe tracking on its non-scrolling top and cover surfaces', () => {
  const s=readFileSync(new URL('../components/shell/NowPlaying.vue',import.meta.url),'utf8')
  expect(s).toContain('@touchstart.passive="startDismissSwipe"')
  expect(s).toContain('@touchend="endDismissSwipe"')
  expect(s).toContain('@touchcancel="dismissStart = null"')
  expect(s).toContain("closest('[data-np-swipe-surface]')")
  expect(s).toContain('dismissPlayerSwipe(dismissStart, end, isMobile.value)')
})
