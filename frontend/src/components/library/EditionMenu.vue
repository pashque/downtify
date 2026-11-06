<template>
  <span class="inline-flex min-w-0" data-edition-menu>
  <UiMenu :items="items" :label="label" align="start">
    <template #trigger="{ open }">
      <button
        v-bind="$attrs"
        type="button"
        :aria-label="label"
        aria-haspopup="menu"
        :aria-expanded="open"
        class="inline-flex h-10 w-full min-w-0 items-center gap-3 rounded-control border border-line-2 bg-transparent px-3 text-[13px] text-fg-3 transition-colors hover:border-line-3 focus-visible:border-accent focus-visible:outline-none"
      >
        <AppIcon :name="icon" :size="15" class="text-muted" />
        <span class="min-w-0 truncate" data-edition-label>{{ options.find(option => option.value === modelValue)?.label || label }}</span>
        <AppIcon name="chevron-down" :size="14" class="text-muted" />
      </button>
    </template>
  </UiMenu>
  </span>
</template>
<script setup>
import { computed } from 'vue'
import UiMenu from '../ui/UiMenu.vue'
import AppIcon from '../ui/AppIcon.vue'
defineOptions({ inheritAttrs: false })
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, required: true },
  label: { type: String, default: '' },
  icon: { type: String, default: 'disc' },
})
const emit = defineEmits(['update:modelValue'])
const items = computed(() => props.options.map(option => ({
  label: option.label,
  checked: option.value === props.modelValue,
  action: () => emit('update:modelValue', option.value),
})))
</script>
