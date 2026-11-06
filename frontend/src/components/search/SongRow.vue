<template>
  <div
    :data-track-row="song.song_id || song.url || `${song.artist}|${song.name}`"
    class="group source-track-grid source-hide-album h-16 rounded-[12px] px-3 transition-colors hover:bg-surface"
    @click="onRowClick"
    @dblclick="rowPlaybackClick($event) && ensurePlaying()"
  >
    <span
      data-column="number"
      class="source-number tabular w-6 text-center text-[13px] text-faint max-sm:hidden"
    >
      {{ index === null ? '' : index + 1 }}
    </span>
    <button
      type="button"
      class="source-cover relative shrink-0"
      :aria-label="play.playLabel.value"
      :disabled="!play.playable.value"
      @click.stop="play.toggle()"
    >
      <CoverArt
        :src="song.cover_url"
        :name="song.album_name || song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
      <span
        v-if="play.playable.value"
        class="absolute inset-0 hidden items-center justify-center rounded-[8px] bg-black/45 text-white group-hover:flex"
        :class="play.isCurrent.value ? '!flex' : ''"
      >
        <AppIcon
          v-if="play.loading.value"
          name="refresh"
          :size="16"
          class="animate-spin"
        />
        <AppIcon v-else :name="overlayIcon" :size="16" />
      </span>
    </button>
    <div data-column="title" class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <span class="truncate text-sm font-semibold">{{ song.name }}</span>
        <ExplicitBadge v-if="song.explicit" />
      </p>
      <p class="truncate text-[13px] text-muted">
        <ArtistCredits :artists="song.artists" :artist="song.artist || t('common.unknownArtist')" /><span v-if="song.album_name" class="lg:hidden">
          · {{ song.album_name }}</span
        >
      </p>
    </div>
    <span v-if="false" data-column="album" class="source-album" />
    <span data-column="time" data-track-duration class="source-duration tabular text-right text-[13px] text-muted">{{ song.duration ? formatDuration(song.duration) : '' }}</span>
    <TrackFormat data-column="format" class="source-format" :formats="location?.formats || []" />
    <div data-column="download" data-track-download-cell class="source-download">
      <DownloadState :song="song" :downloaded="location?.downloaded" round />
    </div>
    <LocationBadges data-column="locations" class="source-locations" :location="location" />
    <span data-column="heart" class="source-heart"><LocalLike :song="song" /></span>
    <span data-column="menu" class="source-actions"><SourceSongMenu :song="song" /></span>
  </div>
</template>

<script setup>
import { rowPlaybackClick } from '/src/lib/rowPlayback'
import ArtistCredits from '/src/components/library/ArtistCredits.vue'
import LocalLike from '/src/components/library/LocalLike.vue'
// A search result: full playback on the cover (from the library, else
// streamed) without downloading anything, and the wand next to the
// download button, styled like it (as on Charts).
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import DownloadState from './DownloadState.vue'
import TrackFormat from '../library/TrackFormat.vue'
import LocationBadges from '../library/LocationBadges.vue'
import '/src/styles/trackRows.css'
import SourceSongMenu from '../library/SourceSongMenu.vue'
import { formatDuration } from '/src/lib/format'
import { useSongPlay } from '/src/model/songPlay'
import { usePlayer } from '/src/model/player'
import { useI18n } from '/src/i18n'

const props = defineProps({
  song: { type: Object, required: true },
  location: { type: Object, default: null },
  index: { type: Number, default: null },
  // The whole song list, for a mixed queue (downloaded rows from the
  // library, the rest streamed) the player works through to the end.
  songs: { type: Array, default: null },
})
const { t } = useI18n()
const player = usePlayer()

// Playing works like every other track row: a downloaded song plays in
// full through the built-in player, anything else streams in full.
const play = useSongPlay(props)
const overlayIcon = computed(() =>
  play.isCurrent.value && player.isPlaying.value ? 'pause' : 'play'
)
const { toggle, ensurePlaying } = play

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick(event) {
  if (rowPlaybackClick(event)) ensurePlaying()
}

const sourceUrl = computed(() => {
  const url = String(props.song.url || '')
  return /^https?:\/\//.test(url) ? url : ''
})
// Charts' Deezer tracks reuse this row; their link opens Deezer, not
// YouTube Music.
const openSourceLabel = computed(() =>
  props.song.source === 'deezer' ? t('link.openDeezer') : t('search.openSource')
)
</script>
