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
    ></span
  >
</template>
<script setup>
import { watch } from 'vue'
import api from '/src/model/api'
import { useAlbumLabel } from '/src/lib/albumLabel'
const props = defineProps({
  text: { type: String, default: '' },
  albumId: { type: String, default: '' },
})
const state = useAlbumLabel(async (id) => (await api.albumLabel(id)).data)
watch(
  () => props.albumId,
  (id) => state.load(id),
  { immediate: true }
)
</script>
