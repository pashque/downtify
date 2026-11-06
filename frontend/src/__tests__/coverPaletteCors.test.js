import { afterEach, expect, it, vi } from 'vitest'
import { effectScope, ref } from 'vue'
import { useCoverPalette } from '../model/coverPalette.js'

afterEach(() => vi.unstubAllGlobals())
it('requests cross-origin artwork anonymously before assigning src so the canvas remains readable', () => {
  const images = []
  vi.stubGlobal('Image', class {
    constructor() { images.push(this) }
    set src(value) { this.url = value; this.corsAtLoad = this.crossOrigin }
  })
  const scope = effectScope()
  scope.run(() => useCoverPalette(ref({ hasCover: true, cover: 'https://i.scdn.co/image/test-palette-cors' })))
  expect(images[0].corsAtLoad).toBe('anonymous')
  scope.stop()
})
