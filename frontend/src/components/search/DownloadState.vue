<template>
  <template v-if="presentation === 'all' || (presentation === 'library') === (state === 'library')">
    <span v-if="round && (state === 'library' || (state === 'done' && globalPresence))" role="img" :aria-label="t('search.inLibrary')" :title="t('search.inLibrary')" class="flex size-9 shrink-0 items-center justify-center text-muted"><AppIcon name="check" :size="16" stroke-width="3" /></span>
    <UiBadge v-else-if="state === 'library'" tone="accent" icon="check">
      {{ t('search.inLibrary') }}
    </UiBadge>
    <UiBadge v-else-if="state === 'done'" tone="accent" icon="check">
      {{ t('queue.statusDone') }}
    </UiBadge>
    <UiBadge v-else-if="state === 'queued'" tone="neutral">
      {{ t('queue.statusQueued') }}
    </UiBadge>
    <div v-else-if="state === 'active'" class="flex w-28 items-center gap-2">
      <UiProgress :value="item.progress" :indeterminate="!item.progress" />
      <span class="tabular w-9 text-right text-xs text-muted">{{
        item.progress ? `${Math.round(item.progress)}%` : ''
      }}</span>
    </div>
    <button
      v-else
      type="button"
      class="flex size-9 shrink-0 items-center justify-center transition-colors"
      :class="
        state === 'failed'
          ? 'text-danger hover:text-danger'
          : 'text-muted hover:text-accent'
      "
      :title="state === 'failed' ? t('queue.retry') : t('actions.download')"
      :aria-label="
        state === 'failed'
          ? t('queue.retry')
          : t('actions.downloadItem', { name: song.name })
      "
      @click="download"
    >
      <AppIcon
        :name="state === 'failed' ? 'retry' : 'download'"
        :size="16"
        stroke-width="2"
      />
    </button>
  </template>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import UiBadge from '../ui/UiBadge.vue'
import UiProgress from '../ui/UiProgress.vue'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { destinationAvailable, songDownloadState } from '/src/lib/downloadState'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  round: { type: Boolean, default: false },
  downloaded: { type: Boolean, default: undefined },
  // Split the existing badge from controls only in rows with a duration column.
  // All other callers retain the original single download-state presentation.
  presentation: { type: String, default: 'all' },
})

const { t } = useI18n()
const tracker = useProgressTracker()
const dm = useDownloadManager()
const library = useLibrary()

const item = computed(() => {
  tracker.queueVersion.value
  return tracker.getBySong(props.song)
})

const globalPresence = computed(() => {
  const artist = (props.song.artists || [])[0] || props.song.artist
  return props.downloaded === true || library.hasSong(artist, props.song.name, props.song)
})

const inLibrary = computed(() => {
  if (props.round) return globalPresence.value
  const artist = (props.song.artists || [])[0] || props.song.artist
  return destinationAvailable(props.song, item.value, library.hasSong(artist, props.song.name, props.song))
})

const state = computed(() => songDownloadState(item.value, inLibrary.value))

function download() {
  if (state.value === 'failed') dm.retry(props.song)
  else dm.queue(props.song)
}
</script>
