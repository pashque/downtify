// @vitest-environment happy-dom
import { afterEach, describe, expect, it } from 'vitest'
import { createApp, h, nextTick, ref } from 'vue'
import FilenameTemplate from '../components/settings/FilenameTemplate.vue'

let app
let root
function mount(initial) {
  const value = ref(initial)
  root = document.createElement('div')
  document.body.append(root)
  app = createApp({
    render: () =>
      h(FilenameTemplate, {
        modelValue: value.value,
        'onUpdate:modelValue': (v) => {
          value.value = v
        },
        defaultTemplate: '{artists} - {title}.{output-ext}',
        format: 'flac',
      }),
  })
  app.mount(root)
  return { value, input: root.querySelector('input') }
}
function chip(token) {
  return [...root.querySelectorAll('button')].find(
    (b) => b.textContent.trim() === token
  )
}
afterEach(() => {
  app?.unmount()
  root?.remove()
})

describe('filename token editing', () => {
  it('uses a single visible File name heading and an accessible label-free input aligned with Reset', () => {
    const { input } = mount('custom')
    expect(root.querySelector('label')).toBeNull()
    expect(input.getAttribute('aria-label')).toBe('File name')
    const reset = [...root.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Reset')
    const inputWrapper = input.closest('span').parentElement
    expect(reset.parentElement).toBe(inputWrapper.parentElement)
    expect(reset.parentElement.classList.contains('items-end')).toBe(true)
  })

  it('sizes the visible input box to the Reset button height at every viewport', () => {
    const { input } = mount('custom')
    const reset = chip('Reset')
    const inputWrapper = input.closest('span').parentElement
    // happy-dom does not perform layout: assert the unprefixed sizing contract.
    // Target UiInput's bordered span, not only its outer flex wrapper.
    expect(reset.classList.contains('h-10')).toBe(true)
    expect(inputWrapper.classList.contains('[&>span]:h-10')).toBe(true)
  })

  it('resets the value to the default template', async () => {
    const { input, value } = mount('custom / file')
    chip('Reset').click()
    await nextTick()
    expect(value.value).toBe('{artists} - {title}.{output-ext}')
    expect(input.value).toBe(value.value)
  })

  it('previews the artist alias with all track artists, matching the backend', () => {
    mount('{artist}');
    expect(root.querySelector('p.text-xs').textContent).toContain('Kenji Aoki, Mira Kovač')
  })

  it('offers albumartist and previews the album credit separately from track artists', async () => {
    const { value } = mount('')
    expect(chip('{albumartist}')).toBeDefined()
    chip('{albumartist}').click()
    await nextTick()
    expect(value.value).toBe('{albumartist}')
    expect(root.querySelector('p.text-xs').textContent).toContain('Kenji Aoki')
    expect(root.querySelector('p.text-xs').textContent).not.toContain(
      '{albumartist}'
    )
  })

  it('replaces selected text and remembers it after keyboard focus moves to a chip', async () => {
    const { input, value } = mount('before REPLACE after')
    input.focus()
    input.setSelectionRange(7, 14)
    input.dispatchEvent(new Event('select', { bubbles: true }))
    chip('{album}').focus()
    chip('{album}').click()
    await nextTick()
    expect(value.value).toBe('before {album} after')
    expect(document.activeElement).toBe(input)
    expect(input.selectionStart).toBe(14)
  })

  it('prevents pointerdown from stealing the input selection', () => {
    const { input } = mount('abc')
    input.focus()
    input.setSelectionRange(1, 2)
    const event = new Event('pointerdown', { bubbles: true, cancelable: true })
    chip('/').dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })

  it('keeps typing spaces and native input focus without rebuilding the input', async () => {
    const { input, value } = mount('')
    input.focus()
    input.value = ' artist / '
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await nextTick()
    expect(value.value).toBe(' artist / ')
    expect(root.querySelector('input')).toBe(input)
    expect(document.activeElement).toBe(input)
    expect(input.value).toBe(' artist / ')
  })

  it('inserts only the token into an empty input and permits consecutive insertions', async () => {
    const { input, value } = mount('')
    chip('{artist}').click()
    await nextTick()
    chip('/').click()
    await nextTick()
    chip('{title}').click()
    await nextTick()
    expect(value.value).toBe('{artist}/{title}')
    expect(input.selectionStart).toBe(16)
  })

  it('inserts at the caret without moving the extension or injecting separators', async () => {
    const { input, value } = mount('prefix .{output-ext}')
    input.focus()
    input.setSelectionRange(7, 7)
    chip('{title}').click()
    await nextTick()
    expect(value.value).toBe('prefix {title}.{output-ext}')
    expect(document.activeElement).toBe(input)
    expect(input.selectionStart).toBe(14)
    expect(input.selectionEnd).toBe(14)
  })
})
