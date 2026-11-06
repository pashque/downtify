<template>
  <SettingRow
    :label="t('settings.template')"
    :description="t('settings.templateHint')"
    stacked
  >
    <div class="flex w-full flex-col gap-2">
      <div class="flex items-end gap-2">
        <UiInput
          ref="templateInput"
          v-model="output"
          class="flex-1 [&>span]:h-10"
          :placeholder="defaultTemplate"
          :aria-label="t('settings.template')"
          mono
          @focusin="rememberSelection"
          @focusout="rememberSelection"
          @select="rememberSelection"
          @keyup="rememberSelection"
          @mouseup="rememberSelection"
          @input="rememberSelection"
        />
        <UiButton variant="ghost" @click="output = defaultTemplate">
          {{ t('settings.reset') }}
        </UiButton>
      </div>
      <div class="flex flex-wrap gap-1.5">
        <button
          v-for="token in templateTokens"
          :key="token"
          type="button"
          class="rounded-md border border-line-3 bg-surface-2 px-2 py-1 font-mono text-xs text-fg-3 hover:border-accent hover:text-accent"
          @pointerdown.prevent
          @click="addToken(token)"
        >
          {{ token }}
        </button>
      </div>
      <p class="text-xs text-muted">
        {{ t('settings.templatePreview') }}
        <span class="font-mono text-fg-3">{{ templatePreview }}</span>
      </p>
    </div>
  </SettingRow>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import UiButton from '../ui/UiButton.vue'
import UiInput from '../ui/UiInput.vue'
import SettingRow from './SettingRow.vue'
import { useI18n } from '/src/i18n'

const props = defineProps({
  defaultTemplate: { type: String, required: true },
  format: { type: String, default: 'mp3' },
})
const output = defineModel({ type: String, default: '' })
const { t } = useI18n()
const templateTokens = [
  '{albumartist}',
  '{artists}',
  '{artist}',
  '{title}',
  '{album}',
  '{tracknumber}',
  '{year}',
  '{output-ext}',
  '/',
]

const templateInput = ref(null)
let selection = null

function rememberSelection(event) {
  const input = event.target
  if (input.tagName === 'INPUT') {
    selection = [input.selectionStart, input.selectionEnd]
  }
}

async function addToken(token) {
  const input = templateInput.value.$el.querySelector('input')
  const current = String(output.value || '')
  const [start, end] =
    document.activeElement === input
      ? [input.selectionStart, input.selectionEnd]
      : selection || [current.length, current.length]
  output.value = current.slice(0, start) + token + current.slice(end)
  const caret = start + token.length
  await nextTick()
  input.focus()
  input.setSelectionRange(caret, caret)
  selection = [caret, caret]
}

const templatePreview = computed(() => {
  const template = String(output.value || props.defaultTemplate)
  const values = {
    '{albumartist}': 'Kenji Aoki',
    '{artists}': 'Kenji Aoki, Mira Kovač',
    '{artist}': 'Kenji Aoki, Mira Kovač',
    '{title}': 'Harbor Lights',
    '{album}': 'Glass Harbor',
    '{tracknumber}': '01',
    '{year}': '2025',
    '{output-ext}': props.format || 'mp3',
  }
  return Object.entries(values).reduce(
    (text, [token, value]) => text.split(token).join(value),
    template
  )
})
</script>
