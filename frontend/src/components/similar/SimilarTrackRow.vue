<template>
  <div
    :data-track-row="song.song_id || song.url || `${song.artist}|${song.name}`"
    class="group source-track-grid source-hide-album h-16 rounded-[12px] px-3 transition-colors hover:bg-surface"
    @click="rowPlaybackClick($event) && play.ensurePlaying()"
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
        :name="song.name"
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
      <p class="truncate text-sm font-semibold">{{ song.name }}</p>
      <p class="truncate text-[13px] text-muted"><ArtistCredits :artists="song.artists" :artist="song.artist || t('common.unknownArtist')" /></p>
    </div>
    <span v-if="false" data-column="album" class="source-album" />
    <span data-column="time" data-track-duration class="source-duration tabular text-right text-[13px] text-muted">{{ song.duration ? formatDuration(song.duration) : '' }}</span>
    <TrackFormat data-column="format" class="source-format" :formats="location?.formats || []" />
    <!-- Same grid as every other track row: the wand re-seeds the mix
         from this track, then the download state. Wide enough for the
         wand plus the download's widest state (see TrackDownPlay). -->
    <div data-column="download" data-track-download-cell class="source-download">
      <span v-if="inLibrary || location?.downloaded" role="img" :aria-label="t('search.inLibrary')" class="flex size-9 items-center justify-center text-muted"><AppIcon name="check" :size="16" /></span>
      <DownloadState
        v-else-if="resolved || downloadable"
        :song="resolved || song" :downloaded="location?.downloaded" round
      />
      <button
        v-else
        type="button"
        class="flex size-9 shrink-0 items-center justify-center text-muted transition-colors hover:text-accent disabled:opacity-50"
        :title="t('actions.download')"
        :aria-label="t('actions.downloadItem', { name: song.name })"
        :disabled="resolving"
        @click="resolveAndDownload"
      >
        <AppIcon
          :name="resolving ? 'refresh' : 'download'"
          :size="16"
          stroke-width="2"
          :class="resolving ? 'animate-spin' : ''"
        />
      </button>
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
// One similar track: full playback on the cover (from the library, else
// streamed), and a download button straight from its video id. The row
// hands off to DownloadState, so progress, queue and retry look exactly
// like search results.
import { computed, ref } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import UiBadge from '../ui/UiBadge.vue'
import DownloadState from '../search/DownloadState.vue'
import TrackFormat from '../library/TrackFormat.vue'
import LocationBadges from '../library/LocationBadges.vue'
import '/src/styles/trackRows.css'
import SourceSongMenu from '../library/SourceSongMenu.vue'
import { formatDuration } from '/src/lib/format'
import API from '/src/model/api'
import { useDownloadManager } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import { useUi } from '/src/model/ui'
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
const library = useLibrary()
const dm = useDownloadManager()
const ui = useUi()

const resolving = ref(false)
const resolved = ref(null)

const artistName = computed(
  () =>
    (props.song.artists || []).join(', ') ||
    props.song.artist ||
    t('common.unknownArtist')
)

// Playing works like every other track row: a downloaded song plays in
// full through the built-in player (so the player shows this track),
// anything else plays its 30 s preview clip on the row itself. `props`
// goes in whole so a new song object for the row stays reactive;
// useSongPlay only reads song/queue/context.
const play = useSongPlay(props)
const overlayIcon = computed(() =>
  play.isCurrent.value && player.isPlaying.value ? 'pause' : 'play'
)

const inLibrary = computed(() =>
  library.hasSong(artistName.value, props.song.name, props.song)
)

// Every row already is a downloadable song (video id + link).
const downloadable = computed(() => !!String(props.song.song_id || '').trim())

async function resolveAndDownload() {
  if (resolving.value || resolved.value) return
  resolving.value = true
  try {
    const res = await API.search(`${artistName.value} ${props.song.name}`)
    const first = res.data?.[0]
    if (!first) {
      ui.toast(t('similar.noDownloadMatch', { name: props.song.name }), {
        kind: 'error',
      })
      return
    }
    resolved.value = first
    dm.queue(first)
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('similar.resolveFailed'), {
      kind: 'error',
    })
  } finally {
    resolving.value = false
  }
}
</script>
