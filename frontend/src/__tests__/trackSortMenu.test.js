// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, ref } from 'vue'
import TrackSortSelect from '../components/library/TrackSortSelect.vue'

let app
let root
afterEach(() => { app?.unmount(); root?.remove() })
it('playlist order uses the native popup, checks current sort and keeps the sort object contract', async () => {
  const selected = ref({ key: 'order', dir: 'asc' })
  root = document.createElement('div'); document.body.append(root)
  app = createApp({ render: () => h(TrackSortSelect, {
    modelValue: selected.value, playlistOrder: true,
    'onUpdate:modelValue': value => { selected.value = value },
  }) })
  app.mount(root)
  expect(root.querySelector('select')).toBeNull()
  const trigger = root.querySelector('button')
  expect(trigger.getAttribute('aria-haspopup')).toBe('menu')
  trigger.click(); await nextTick()
  const menu = document.querySelector('[role="menu"]')
  expect(menu.className).toContain('bg-surface')
  const items = [...menu.querySelectorAll('[role="menuitem"]')]
  expect(items[0].querySelector('.text-accent')).not.toBeNull()
  items.find(item => item.textContent.includes('Title (A')).click(); await nextTick()
  expect(selected.value).toEqual({ key: 'title', dir: 'asc' })
  await vi.waitFor(() => expect(document.querySelector('[role="menu"]')).toBeNull())
})
