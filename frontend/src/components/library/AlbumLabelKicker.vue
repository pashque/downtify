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
      <span data-label-pending>{{ t('labels.kickerPending') }}</span></template
    ></span
  >
</template>
<script setup>
import { watch } from 'vue'
import api from '/src/model/api'
import { useAlbumLabel } from '/src/lib/albumLabel'
import { useI18n } from '/src/i18n'
const props = defineProps({
  text: { type: String, default: '' },
  albumId: { type: String, default: '' },
  // The album's exact Spotify edition is still being resolved.
  pending: { type: Boolean, default: false },
  // Names the library album, so its label is remembered before the exact
  // Spotify edition is resolved.
  cacheKey: { type: String, default: '' },
})
const { t } = useI18n()
const state = useAlbumLabel(async (id) => (await api.albumLabel(id)).data)
watch(
  () => [props.albumId, props.cacheKey],
  ([id, key]) => state.load(id, key),
  { immediate: true }
)
</script>
