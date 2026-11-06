import { expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

// A dynamic import of the API client splits it into its own chunk with a
// vendor -> api edge evaluated before init: the built app dies on load with
// `TypeError: e is not a function` (`__exportAll` in an unminified build).
// Dev mode and unit tests do not reproduce it, so guard the source itself.
const root = new URL('..', import.meta.url).pathname
function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name)
    if (name === '__tests__' || name === 'node_modules') return []
    if (statSync(full).isDirectory()) return files(full)
    return /\.(js|vue)$/.test(name) ? [full] : []
  })
}

it('never imports the API client dynamically', () => {
  const offenders = files(root).filter((file) => {
    const code = readFileSync(file, 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/(^|[^:])\/\/.*$/gm, '$1')
    return /import\(\s*['"][^'"]*model\/api(\.js)?['"]\s*\)/.test(code)
  })
  expect(offenders).toEqual([])
})
