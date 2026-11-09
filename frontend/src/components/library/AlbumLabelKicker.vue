<template>
  <span
    >{{ text
    }}<template v-if="state.label.value">
      ·
      <RouterLink
        :to="{ name: 'Label', params: { label: state.label.value } }"
        class="hover:underline focus-visible:underline"
        data-album-label
        >{{ state.label.value }}</RouterLink
      ></template
    ><template v-else-if="pending || state.loading.value">
      ·
      <span
        class="inline-block h-[0.8em] w-16 animate-pulse rounded-sm bg-current align-middle opacity-15"
        aria-hidden="true"
        data-label-pending
      ></span></template
  ></span>
</template>
<script setup>
import { watch } from 'vue'
import api from '/src/model/api'
import { useAlbumLabel } from '/src/lib/albumLabel'
const props = defineProps({
  text: { type: String, default: '' },
  albumId: { type: String, default: '' },
  // The album's exact Spotify edition is still being resolved.
  pending: { type: Boolean, default: false },
})
const state = useAlbumLabel(async (id) => (await api.albumLabel(id)).data)
watch(
  () => props.albumId,
  (id) => state.load(id),
  { immediate: true }
)
</script>
