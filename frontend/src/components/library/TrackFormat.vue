<template>
  <span data-track-format class="inline-flex min-w-0 flex-nowrap items-center gap-1 whitespace-nowrap">
    <span v-for="format in labels" :key="format" class="shrink-0 rounded-[5px] border border-line-3 px-1.5 py-0.5 text-[11px] font-semibold text-muted">{{ format }}</span>
  </span>
</template>
<script setup>
import { computed } from 'vue'
const props = defineProps({ formats: { type: Array, default: () => [] } })
const labels = computed(() => [...new Set(props.formats.map(f => String(f).trim().toUpperCase()).filter(Boolean))])
</script>
