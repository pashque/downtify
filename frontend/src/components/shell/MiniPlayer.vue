<template>
  <Transition name="now-playing">
    <div
      v-if="track && !nowPlaying.isOpen.value"
      data-mini-bar
      @click="openFromBar"
      class="relative flex cursor-pointer flex-col overflow-hidden rounded-[16px] border border-line-3 bg-glass px-2 pb-1 shadow-float backdrop-blur-xl md:rounded-[18px] md:pr-5 md:pl-3"
    >
      <div class="flex h-[60px] items-center gap-2 md:h-[68px] md:gap-4">

      <!-- Equal flexible sides keep the transport in the middle; the
           title takes all of the left side. -->
      <div class="flex min-w-0 flex-1 basis-0 items-center gap-1">
        <!-- The cover (and any empty space beside the text) opens the
             full player; artists and album are links. -->
        <div class="flex min-w-0 flex-1 items-center gap-3 self-stretch text-left">
          <button
            type="button"
            data-mini-open
            class="shrink-0 rounded-[10px]"
            :aria-label="t('player.openNowPlaying')"
            @click.stop="nowPlaying.open()"
          >
            <CoverArt
              :thumb="150"
              :src="track.hasCover ? track.cover : ''"
              :name="track.album || track.title"
              rounded="rounded-[10px]"
              :letter-size="18"
              :icon-size="18"
              class="size-11 md:size-[52px]"
            />
          </button>
          <span class="flex min-w-0 flex-col" data-mini-titles>
            <span class="flex min-w-0 items-center gap-1.5 md:gap-2" data-mini-titleline>
              <span class="truncate text-sm font-semibold" data-mini-title>{{ track.title }}</span>
              <ExplicitBadge v-if="track.explicit" />
            </span>
            <span class="truncate text-xs text-muted" data-mini-artist>
              <ArtistCredits
                v-if="!track.isPodcast"
                :artists="track.artists || []"
                :artist="track.artist || ''"
              /><template v-else>{{ track.artist }}</template
              ><span v-if="track.album" class="hidden landscape:inline md:inline">
                ·
                <RouterLink
                  v-if="albumRoute"
                  :to="albumRoute"
                  class="hover:text-fg hover:underline"
                  @click.stop
                  >{{ track.album }}</RouterLink
                ><template v-else>{{ track.album }}</template></span
              >
            </span>
          </span>
        </div>
      </div>

      <div class="flex shrink-0 items-center justify-center gap-1 lg:gap-2" data-mini-controls>
        <UiIconButton
          round
          v-if="canSimilar"
          icon="wand"
          :label="t('similar.findSimilar')"
          class="max-md:!hidden"
          @click="goSimilar"
        />
        <UiIconButton
          round
          icon="shuffle"
          :label="t('player.shuffle')"
          :active="player.shuffle.value"
          toggle
          class="max-md:portrait:!hidden"
          @click="player.toggleShuffle()"
        />
        <UiIconButton
          round
          icon="prev"
          :label="t('player.previous')"
          @click="player.prev()"
        />
        <button
          type="button"
          class="flex size-12 items-center justify-center rounded-full bg-invert text-on-invert transition-transform hover:scale-105 md:size-11"
          data-mini-play
          :aria-label="
            player.isPlaying.value ? t('player.pause') : t('player.play')
          "
          @click="player.toggle()"
        >
          <span
            v-if="player.isBuffering.value && player.isPlaying.value"
            class="size-4 animate-spin rounded-full border-2 border-current border-r-transparent"
          />
          <AppIcon
            v-else
            :name="player.isPlaying.value ? 'pause' : 'play'"
            :size="18"
          />
        </button>
        <UiIconButton
          round
          icon="next"
          :label="t('player.next')"
          @click="player.next()"
        />
        <UiIconButton
          round
          :icon="player.repeatMode.value === 'one' ? 'repeat-one' : 'repeat'"
          :label="repeatLabel"
          :active="player.repeatMode.value !== 'off'"
          toggle
          class="max-md:portrait:!hidden"
          @click="player.cycleRepeat()"
        />
        <UiIconButton
          round
          v-if="showPlayerDownload"
          :icon="downloadBusy ? 'refresh' : 'download'"
          :label="t('actions.downloadItem', { name: trackTitle })"
          :disabled="downloadBusy || !pendingSong"
          :class="downloadBusy ? '[&_svg]:animate-spin' : ''"
          @click="downloadCurrent"
        />
        <!-- The heart sits where the library check used to be. -->
        <span
          v-if="!track?.isPodcast && !track?.stream"
          class="contents"
          data-mini-like
          ><LikeButton :file="track.file"
        /></span>
      </div>

      <div class="hidden min-w-0 flex-1 basis-0 items-center justify-end gap-1 landscape:flex md:flex" data-mini-right>
        <!-- Same row as the full player: playing bars, elapsed / total,
             format, volume. The invisible widest clock keeps the width
             fixed, so nothing shifts as the time ticks. -->
        <EqBars v-if="player.isPlaying.value" :size="10" class="mr-1 shrink-0" />
        <span
          data-mini-clock
          class="tabular mr-1 inline-grid shrink-0 text-xs whitespace-nowrap text-muted"
        >
          <span class="invisible col-start-1 row-start-1" aria-hidden="true">{{ clockSizer }}</span>
          <span class="col-start-1 row-start-1 text-right"
            >{{ formatDuration(player.currentTime.value) }} / {{ formatDuration(player.duration.value) }}</span
          >
        </span>
        <span
          v-if="track.format"
          data-mini-format
          class="mr-1 shrink-0 rounded-md border border-line-3 px-1.5 py-0.5 text-[11px] leading-none font-semibold tracking-wide text-muted"
          >{{ track.format }}</span
        >
        <VolumeControl class="hidden min-w-0 lg:flex" width="hidden w-16 xl:flex" />
        <UiIconButton
          round
          icon="expand"
          :label="t('player.openNowPlaying')"
          size="sm"
          @click="nowPlaying.open()"
        />
        <!-- Close: stops playback, clears the queue and hides the player. -->
        <UiIconButton
          round
          icon="x"
          :label="t('common.close')"
          size="sm"
          data-player-close
          class="shrink-0 max-md:portrait:!hidden"
          @click="player.stop()"
        />
      </div>
      </div>
      <!-- The full player's wave progress, slimmer; drag or tap to seek. -->
      <WaveSeekBar
        compact
        data-mini-progress
        class="mx-1 -mt-1.5 md:mx-0 md:mt-0"
        :model-value="scrub ?? player.currentTime.value"
        :max="player.duration.value || 1"
        :label="t('player.seek')"
        :value-text="formatDuration(player.currentTime.value)"
        :playing="player.isPlaying.value"
        :palette="palette"
        track-color="rgb(128 128 128 / 0.28)"
        @update:model-value="(v) => (scrub = v)"
        @commit="commitSeek"
      />
    </div>
  </Transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import UiIconButton from '../ui/UiIconButton.vue'
import LikeButton from '../player/LikeButton.vue'
import ArtistCredits from '../library/ArtistCredits.vue'
import { RouterLink } from 'vue-router'
import { playerAlbumRoute } from '/src/lib/playerNavigation'
import WaveSeekBar from '../player/WaveSeekBar.vue'
import { useCoverPalette } from '/src/model/coverPalette'
import VolumeControl from '../player/VolumeControl.vue'
import { usePlayer } from '/src/model/player'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useNowPlaying, useUi } from '/src/model/ui'
import { formatDuration, widestClock } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const nowPlaying = useNowPlaying()
const { t } = useI18n()
const router = useRouter()
const library = useLibrary()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const ui = useUi()
const scrub = ref(null)

const track = computed(() => player.currentTrack.value)
const albumRoute = computed(() => playerAlbumRoute(track.value))

const trackArtist = computed(
  () =>
    (track.value?.artists || [])[0] ||
    track.value?.artist ||
    t('common.unknownArtist')
)
const trackTitle = computed(() => track.value?.name || track.value?.title || '')

const canSimilar = computed(() => {
  if (track.value?.isPodcast) return false
  const artist = (track.value?.artists || [])[0] || track.value?.artist || ''
  const title = track.value?.name || track.value?.title || ''
  return !!artist.trim() && !!title.trim()
})

function goSimilar() {
  const artist = (track.value?.artists || [])[0] || track.value?.artist || ''
  const title = track.value?.name || track.value?.title || ''
  if (!artist.trim() || !title.trim()) return
  router.push({ name: 'Similar', query: { artist, track: title } })
}

// A stream that isn't in the library yet can be queued from here; while
// queued it spins instead of queueing a duplicate.
const streamDownloaded = computed(
  () =>
    !!track.value?.stream &&
    library.hasSong(trackArtist.value, trackTitle.value, track.value)
)
// Same rule as the full player: any stream not in the library shows the
// button; it works once the stream's video id is known.
const showPlayerDownload = computed(
  () => !!track.value?.stream && !streamDownloaded.value
)
const pendingSong = computed(() => {
  const tr = track.value
  if (!showPlayerDownload.value || !tr?.video_id) return null
  return {
    name: trackTitle.value,
    artists: tr.artist ? [tr.artist] : [],
    artist: tr.artist || '',
    album_name: tr.album || '',
    cover_url: tr.cover && String(tr.cover).startsWith('http') ? tr.cover : '',
    duration: tr.duration || 0,
    url: `https://music.youtube.com/watch?v=${tr.video_id}`,
    youtube_id: tr.video_id,
  }
})
const downloadJob = computed(() => {
  tracker.queueVersion.value
  return pendingSong.value ? tracker.getBySong(pendingSong.value) : null
})
const downloadBusy = computed(() => {
  const state = downloadJob.value?.state
  return state === 'queued' || state === 'active'
})

function downloadCurrent() {
  const song = pendingSong.value
  if (!song || downloadBusy.value) return
  if (downloadJob.value?.state === 'failed') dm.retry(song)
  else {
    dm.queue(song)
    ui.toast(t('toast.queuedTracks', { count: 1, name: song.name }), {
      kind: 'success',
    })
  }
}

const clockSizer = computed(() => widestClock(player.duration.value))

// Same cover colours as the full player's waves.
const palette = useCoverPalette(track)


const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

// Any empty spot of the bar opens the full player; buttons, links, the
// seek bar and menus keep their own job.
function openFromBar(event) {
  // The path is captured at dispatch: a toggle that re-renders its icon
  // (repeat, shuffle, heart) leaves a detached target behind.
  const hit = event.composedPath().some((el) =>
    el instanceof Element && el.matches('button, a, input, [role="slider"], [role="menu"], [data-mini-progress]'))
  if (hit || !event.target.isConnected) return
  nowPlaying.open()
}

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}
</script>
