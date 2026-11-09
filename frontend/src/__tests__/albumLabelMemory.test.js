import { describe, expect, it } from 'vitest'
import { createLabelMemory } from '/src/lib/albumLabelMemory'
import { useAlbumLabel } from '/src/lib/albumLabel'

const storage = () => {
  const data = {}
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => {
      data[k] = String(v)
    },
  }
}
const deferred = () => {
  let resolve, reject
  const promise = new Promise((yes, no) => {
    resolve = yes
    reject = no
  })
  return { promise, resolve, reject }
}
const ID = '7JnSZnUKnwnfdfVYQ8Eivb'
const OTHER = '0eyTz4axCv1nyRSCHxDNY0'

describe('label memory', () => {
  it('stores and returns an entry, and survives a new instance', () => {
    const s = storage()
    createLabelMemory(s).set('lib:a|b', { id: ID, label: 'Frucht' })
    expect(createLabelMemory(s).get('lib:a|b')).toEqual({
      id: ID,
      label: 'Frucht',
    })
  })

  it('forgets an entry', () => {
    const memory = createLabelMemory(storage())
    memory.set('k', { id: ID, label: 'Frucht' })
    memory.delete('k')
    expect(memory.get('k')).toBeNull()
  })

  it('keeps only the newest entries', () => {
    const memory = createLabelMemory(storage(), 3)
    for (const n of [1, 2, 3, 4])
      memory.set(`k${n}`, { id: '', label: `L${n}` })
    expect(memory.get('k1')).toBeNull()
    expect(memory.get('k4')?.label).toBe('L4')
  })

  it('ignores damaged or unavailable storage', () => {
    const broken = {
      getItem: () => '{nope',
      setItem: () => {
        throw new Error('full')
      },
    }
    const memory = createLabelMemory(broken)
    expect(memory.get('k')).toBeNull()
    expect(() => memory.set('k', { id: ID, label: 'x' })).not.toThrow()
  })
})

describe('remembered album label', () => {
  it('shows the remembered label at once, before the lookup finishes', async () => {
    const memory = createLabelMemory(storage())
    memory.set('lib:a|b', { id: ID, label: 'Frucht' })
    const reply = deferred()
    const state = useAlbumLabel(() => reply.promise, memory)
    const pending = state.load('', 'lib:a|b')
    expect(state.label.value).toBe('Frucht')
    expect(state.loading.value).toBe(false)
    reply.resolve({ label: 'Frucht' })
    await pending
  })

  it('keeps it while the same edition is confirmed, and remembers it under both keys', async () => {
    const memory = createLabelMemory(storage())
    memory.set('lib:a|b', { id: ID, label: 'Frucht' })
    const reply = deferred()
    const state = useAlbumLabel(() => reply.promise, memory)
    const pending = state.load(ID, 'lib:a|b')
    expect(state.label.value).toBe('Frucht')
    reply.resolve({ label: 'Frucht Records' })
    await pending
    expect(state.label.value).toBe('Frucht Records')
    expect(memory.get('lib:a|b')).toEqual({ id: ID, label: 'Frucht Records' })
    expect(memory.get(`spotify:${ID}`)).toEqual({
      id: ID,
      label: 'Frucht Records',
    })
  })

  it('drops a remembered label that belongs to a different edition', async () => {
    const memory = createLabelMemory(storage())
    memory.set('lib:a|b', { id: ID, label: 'Frucht' })
    const reply = deferred()
    const state = useAlbumLabel(() => reply.promise, memory)
    const pending = state.load(OTHER, 'lib:a|b')
    expect(state.label.value).toBe('')
    reply.resolve({ label: 'LUCKYME®' })
    await pending
    expect(state.label.value).toBe('LUCKYME®')
  })

  it('forgets the label when Spotify says there is none', async () => {
    const memory = createLabelMemory(storage())
    memory.set(`spotify:${ID}`, { id: ID, label: 'Frucht' })
    const state = useAlbumLabel(async () => ({ label: '' }), memory)
    await state.load(ID, '')
    expect(state.label.value).toBe('')
    expect(memory.get(`spotify:${ID}`)).toBeNull()
  })

  it('keeps the remembered label when the lookup fails', async () => {
    const memory = createLabelMemory(storage())
    memory.set(`spotify:${ID}`, { id: ID, label: 'Frucht' })
    const state = useAlbumLabel(async () => {
      throw new Error('down')
    }, memory)
    await state.load(ID, '')
    expect(state.label.value).toBe('Frucht')
    expect(state.loading.value).toBe(false)
  })

  it('works without any memory', async () => {
    const state = useAlbumLabel(async () => ({ label: 'Frucht' }))
    await state.load(ID)
    expect(state.label.value).toBe('Frucht')
  })
})

describe('wiring', () => {
  it('the kicker, Library page and Link page use the memory', async () => {
    const { readFileSync } = await import('node:fs')
    const read = (f) => readFileSync(new URL(f, import.meta.url), 'utf8')
    expect(read('../components/library/AlbumLabelKicker.vue')).toContain(
      'cacheKey'
    )
    expect(read('../views/AlbumView.vue')).toContain(':cache-key=')
    expect(read('../lib/albumLabel.js')).toContain('albumLabelMemory')
  })
})
