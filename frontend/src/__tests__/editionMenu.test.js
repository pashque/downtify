// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest'
import { createApp, h, nextTick, ref } from 'vue'
import EditionMenu from '../components/library/EditionMenu.vue'

let app
let root
afterEach(() => { app?.unmount(); root?.remove() })
it('uses the native menu with the current edition checked and emits the clicked edition', async () => {
  const selected = ref('deluxe')
  const options = [{ value: 'deluxe', label: '22 Tracks · Explicit' }, { value: 'standard', label: '16 Tracks' }]
  root = document.createElement('div'); document.body.append(root)
  app = createApp({ render: () => h(EditionMenu, {
    modelValue: selected.value, options, label: 'Tracks', 'data-album-version': '',
    'onUpdate:modelValue': value => { selected.value = value },
  }) })
  app.mount(root)
  const trigger = root.querySelector('button')
  expect(root.querySelector('[data-edition-menu]')).not.toBeNull()
  expect(trigger.querySelector('[data-edition-label]').className).toContain('truncate')
  expect(trigger.hasAttribute('data-album-version')).toBe(true)
  expect(trigger.textContent).toContain('22 Tracks · Explicit')
  expect(trigger.getAttribute('aria-haspopup')).toBe('menu')
  trigger.click(); await nextTick()
  const menu = document.querySelector('[role="menu"]')
  expect(menu.className).toContain('bg-surface')
  const items = [...menu.querySelectorAll('[role="menuitem"]')]
  expect(items[0].querySelector('.text-accent')).not.toBeNull()
  expect(items[1].querySelector('.text-accent')).toBeNull()
  items[1].click(); await nextTick()
  expect(selected.value).toBe('standard')
  expect(trigger.textContent).toContain('16 Tracks')
  await vi.waitFor(() => expect(document.querySelector('[role="menu"]')).toBeNull())
})
