<template>
  <span>
    <template v-for="(name, i) in names" :key="name">
      <span v-if="i">, </span>
      <RouterLink
        :to="{ name: 'Artist', query: { name } }"
        class="hover:text-fg hover:underline"
        data-artist-credit
        @click.stop
        @dblclick.stop
      >{{ name }}</RouterLink>
    </template>
  </span>
</template>
<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
const props = defineProps({
  artists: { type: Array, default: () => [] },
  artist: { type: String, default: '' },
})
// Structured credits are authoritative. Never split literal comma names.
const names = computed(() => {
  const structured = props.artists.map(value => typeof value === 'string' ? value : value?.name).filter(Boolean)
  return [...new Set((structured.length ? structured : props.artist.split(';')).map(name => String(name).trim()).filter(Boolean))]
})
</script>
