<template>
  <div role="row" data-track-header class="source-track-grid h-9 border-b border-line px-3 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase" :class="{ 'source-selectable': selectable, 'source-hide-album': hideAlbum, 'source-show-added': showAdded }">
    <span v-if="selectable" class="source-selection flex items-center justify-center">
      <button
        v-if="selectedCount"
        type="button"
        class="flex size-[18px] items-center justify-center rounded-[5px] text-muted transition-colors hover:text-fg"
        :aria-label="t('library.clearSelection')"
        :title="t('library.clearSelection')"
        data-clear-selection
        @click="emit('clear-selection')"
      >
        <AppIcon name="x" :size="14" stroke-width="2.4" />
      </button>
    </span>
    <span data-column="number" role="columnheader" class="source-number text-center">#</span>
    <span class="source-cover" aria-hidden="true" />
    <span data-column="title" role="columnheader">{{ t('track.title') }}</span>
    <span v-if="!hideAlbum" data-column="album" role="columnheader" class="source-album">{{ t('track.album') }}</span>
    <span data-column="time" role="columnheader" class="source-duration text-right">{{ t('track.time') }}</span>
    <span data-column="format" role="columnheader" class="source-format">{{ t('track.format') }}</span>
    <span v-if="showAdded" data-column="added" role="columnheader" class="source-added">{{ t('track.added') }}</span>
    <span data-column="download" role="columnheader" class="source-download">{{ t('track.library') }}</span>
    <span data-column="locations" class="source-locations" aria-hidden="true" />
    <span data-column="heart" class="source-heart" aria-hidden="true" />
    <span data-column="menu" class="source-actions" aria-hidden="true" />
  </div>
</template>
<script setup>
import { useI18n } from '/src/i18n'
import AppIcon from '../ui/AppIcon.vue'
import '/src/styles/trackRows.css'
defineProps({ selectable: { type: Boolean, default: false }, selectedCount: { type: Number, default: 0 }, hideAlbum: { type: Boolean, default: true }, showAdded: { type: Boolean, default: false } })
const emit = defineEmits(['clear-selection'])
const { t } = useI18n()
</script>
