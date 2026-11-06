<template>
  <Teleport to="body">
    <Transition name="now-playing">
      <div
        v-if="nowPlaying.isOpen.value && track"
        class="fixed inset-0 z-50 flex flex-col overflow-hidden bg-[#07080b] text-white [--np-side:clamp(240px,28vw,410px)]"
        role="dialog"
        aria-modal="true"
        data-now-playing
        :aria-label="t('player.nowPlaying')"
        @touchstart.passive="startDismissSwipe"
        @touchend="endDismissSwipe"
        @touchcancel="dismissStart = null"
      >
        <!-- Backdrop: the artwork, blown up and blurred. -->
        <div class="pointer-events-none absolute inset-0" aria-hidden="true">
          <div
            class="absolute inset-0 transition-colors duration-700"
            :style="{ backgroundColor: tint }"
          />
          <img
            v-if="track.hasCover"
            :src="track.cover"
            alt=""
            class="absolute inset-0 size-full scale-125 object-cover opacity-55 blur-[90px] saturate-150"
          />
          <div
            class="absolute inset-0 bg-gradient-to-b from-black/25 via-black/45 to-black/80"
          />
        </div>

        <div
          class="relative flex h-full flex-col px-5 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(1.25rem,env(safe-area-inset-bottom))] lg:px-10 lg:pt-6 lg:pb-8"
        >
          <!-- Header -->
          <header class="np-edge-aligned relative z-10 flex h-12 shrink-0 touch-pan-x items-center gap-3" data-np-swipe-surface>
            <button
              ref="closeButton"
              type="button"
              class="flex size-10 items-center justify-center rounded-full bg-white/10 transition-colors hover:bg-white/20 focus-visible:bg-white/20 focus-visible:outline-none"
              :aria-label="t('player.closeNowPlaying')"
              @click="nowPlaying.close()"
            >
              <AppIcon name="chevron-down" :size="22" />
            </button>
            <component
              :is="contextRoute ? RouterLink : 'div'"
              :to="contextRoute || undefined"
              data-np-context
              class="flex min-w-0 flex-col max-lg:flex-1 max-lg:items-center"
              @click.prevent="contextRoute && navigate(contextRoute)"
            >
              <span class="eyebrow !text-white/55">{{ contextLabel }}</span>
              <span class="max-w-full truncate text-sm font-semibold" :class="contextRoute ? 'hover:underline' : ''">{{
                contextTitle
              }}</span>
            </component>
            <div
              class="ml-auto hidden gap-1 rounded-[12px] bg-white/8 p-1 lg:flex xl:w-[var(--np-side)]"
              role="tablist"
              data-np-tabs
            >
              <button
                v-for="tab in panels"
                :key="tab.id"
                type="button"
                role="tab"
                :aria-selected="tab.id === 'queue' && !isMobile ? desktopQueueVisible : panel === tab.id"
                class="flex h-9 items-center justify-center gap-2 rounded-[9px] px-3.5 text-[13px] transition-colors xl:flex-1 xl:px-2"
                :class="
                  (tab.id === 'queue' && !isMobile ? desktopQueueVisible : panel === tab.id)
                    ? 'bg-white/15 font-semibold text-white'
                    : 'font-medium text-white/65 hover:text-white'
                "
                @click="setPanel(tab.id)"
              >
                <AppIcon :name="tab.icon" :size="16" />{{ tab.label }}
              </button>
            </div>
            <div class="lg:hidden">
            <UiMenu
              :items="trackMenu"
              :label="t('common.more')"
            >
              <template #trigger>
                <button
                  ref="mobileMoreButton"
                  type="button"
                  class="flex size-10 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('common.more')"
                >
                  <AppIcon name="more" :size="22" />
                </button>
              </template>
            </UiMenu>
            </div>
          </header>

          <!-- Body -->
          <div
            class="np-edge-aligned np-body grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] gap-6 overflow-hidden py-4 lg:items-stretch lg:gap-10 lg:py-4 xl:gap-12"
            :data-queue-visible="desktopQueueVisible" :data-central-panel="!!panel"
          >
            <!-- Artwork + title (hidden on phones while a panel is open) -->
            <div
              class="now-playing-stage flex h-full min-h-0 w-full min-w-0 max-w-full flex-col justify-center gap-4 overflow-hidden lg:gap-5"
              :class="mobilePanel ? 'max-lg:hidden' : ''"
            >
              <div class="now-playing-cover mx-auto touch-pan-x" data-np-swipe-surface>
                <CoverArt
                  :src="track.hasCover ? track.cover : ''"
                  :name="track.album || track.title"
                  rounded="rounded-[20px]"
                  :letter-size="140"
                  :icon-size="72"
                  class="aspect-square w-full min-h-0 min-w-0 transition-transform duration-500 ease-out-soft"
                  :class="player.isPlaying.value ? 'scale-100' : 'scale-[0.94] lg:scale-100'"
                />
              </div>
              <div
                class="flex w-full min-w-0 shrink-0 items-end justify-between gap-4" data-np-undercover
              >
                <div class="min-w-0 flex-1">
                  <div class="flex min-w-0 items-center gap-2.5">
                    <h2
                      class="now-playing-title text-display truncate font-bold"
                    >
                      {{ track.title }}
                    </h2>
                    <ExplicitBadge v-if="track.explicit" tone="onDark" />
                  </div>
                  <div class="mt-1 truncate text-base text-white/70">
                    <RouterLink v-if="artistRoute" :to="artistRoute" data-np-artist
                      class="hover:text-white hover:underline" @click.prevent="navigate(artistRoute)">{{ track.artist }}</RouterLink>
                    <span v-else>{{ track.artist }}</span>
                    <template v-if="albumRoute"><span> · </span><RouterLink :to="albumRoute" data-np-cover-album
                      class="hover:text-white hover:underline" @click.prevent="navigate(albumRoute)">{{ track.album }}</RouterLink></template>
                  </div>
                </div>
                <!-- Phones: format and heart right of the title block. On
                     desktop the bottom bar carries them, like the mini player. -->
                <div class="flex shrink-0 items-center gap-1 lg:hidden" data-np-cover-meta>
                  <span v-if="track.format" data-np-cover-format class="shrink-0 rounded-md border border-white/20 px-1.5 py-0.5 text-[11px] leading-none font-semibold tracking-wide text-white/75">{{ track.format }}</span>
                  <span v-if="!track?.isPodcast && !track?.stream" class="contents" data-np-cover-like>
                    <LikeButton :file="track.file" size="lg" />
                  </span>
                </div>
              </div>
              <p
                v-if="player.playError.value"
                class="flex items-center gap-2 text-sm text-danger"
              >
                <AppIcon name="alert" :size="16" />{{ t('player.cannotPlay') }}
              </p>
            </div>

            <!-- Main panel -->
            <div
              v-if="panel !== 'queue' && (panel || (!isMobile && !desktopQueueVisible))"
              data-np-central
              class="min-h-0 overflow-hidden lg:h-full"
              :class="mobilePanel ? '' : 'max-lg:hidden'"
            >
              <LyricsPanel v-if="panel === 'lyrics'" :compact="isMobile" />
              <!-- Details and equalizer start level with the cover's top. -->
              <div v-else-if="panel === 'details' || panel === 'equalizer'" class="h-full lg:flex lg:flex-col lg:justify-center">
                <div class="now-playing-aligned min-h-0" data-np-aligned>
                  <TrackDetails v-if="panel === 'details'" />
                  <EqualizerPanel v-else :palette="palette" class="lg:!justify-start" />
                </div>
              </div>
            </div>

            <!-- One frameless queue: right-hand slot on desktop, panel on phones. -->
            <aside
              v-if="isMobile ? panel === 'queue' : desktopQueueVisible"
              data-np-queue
              class="h-full min-h-0 max-h-full overflow-hidden"
            >
              <UpNextPanel />
            </aside>
          </div>

          <!-- Transport -->
          <footer class="relative z-10 shrink-0">
            <div class="flex items-center gap-3">
              <span class="tabular w-12 text-xs text-white/65">{{
                formatDuration(scrub ?? player.currentTime.value)
              }}</span>
              <WaveSeekBar
                data-np-seek
                class="min-w-0 flex-1"
                :model-value="scrub ?? player.currentTime.value"
                :max="player.duration.value || 1"
                :label="t('player.seek')"
                :value-text="formatDuration(player.currentTime.value)"
                :playing="player.isPlaying.value"
                :palette="palette"
                @update:model-value="(v) => (scrub = v)"
                @commit="commitSeek"
              />
              <span class="tabular w-12 text-right text-xs text-white/65">{{
                formatDuration(player.duration.value)
              }}</span>
            </div>

            <!-- The same bar as the mini player: title block with format and
                 heart, transport in the middle, panels/volume/collapse right. -->
            <div class="np-edge-aligned mt-3 flex items-center lg:mt-4" data-np-bar>
              <div class="hidden min-w-0 flex-1 basis-0 items-center gap-3 lg:flex">
                <div data-np-nowline class="flex min-w-0 flex-1 flex-col">
                  <div class="flex min-w-0 items-center gap-2">
                    <span class="truncate text-sm font-semibold text-white">{{ track.title }}</span>
                    <ExplicitBadge v-if="track.explicit" tone="onDark" />
                  </div>
                  <div class="truncate text-xs text-white/65">
                    <RouterLink v-if="artistRoute" :to="artistRoute" data-np-artist
                      class="hover:text-white hover:underline" @click.prevent="navigate(artistRoute)">{{ track.artist }}</RouterLink>
                    <span v-else>{{ track.artist }}</span>
                    <template v-if="albumRoute"><span> · </span><RouterLink :to="albumRoute" data-np-bottom-album
                      class="hover:text-white hover:underline" @click.prevent="navigate(albumRoute)">{{ track.album }}</RouterLink></template>
                  </div>
                </div>
              </div>

              <div
                class="flex flex-1 items-center justify-between lg:flex-none lg:justify-center lg:gap-1 xl:gap-3 2xl:gap-7"
                data-np-transport
              >
                <button
                  v-if="track?.isPodcast"
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                  :aria-label="t('podcasts.skipBack')"
                  @click="player.seekBy(-15)"
                >
                  <AppIcon name="skip-back" :size="22" />
                </button>
                <!-- Left of shuffle: tracks like this one
                     (podcasts have none). -->
                <button
                  v-if="similarArtist && similarTitle"
                  type="button"
                  class="flex size-11 items-center lg:max-xl:hidden justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                  :aria-label="t('similar.findSimilar')"
                  @click="goSimilar"
                >
                  <AppIcon name="wand" :size="22" />
                </button>
                <button
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full transition-colors hover:bg-white/10"
                  :class="
                    player.shuffle.value ? 'text-accent' : 'text-white/80'
                  "
                  :aria-label="t('player.shuffle')"
                  :aria-pressed="player.shuffle.value"
                  @click="player.toggleShuffle()"
                >
                  <AppIcon name="shuffle" :size="22" />
                </button>
                <button
                  type="button"
                  class="flex size-13 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('player.previous')"
                  @click="player.prev()"
                >
                  <AppIcon name="prev" :size="28" />
                </button>
                <button
                  type="button"
                  class="now-playing-play flex items-center justify-center rounded-full bg-white text-[#0b0c0e] shadow-[0_12px_30px_rgba(0,0,0,0.35)] transition-transform hover:scale-105 active:scale-95"
                  :aria-label="
                    player.isPlaying.value
                      ? t('player.pause')
                      : t('player.play')
                  "
                  @click="player.toggle()"
                >
                  <AppIcon
                    :name="player.isPlaying.value ? 'pause' : 'play'"
                    :size="26"
                  />
                </button>
                <button
                  type="button"
                  class="flex size-13 items-center justify-center rounded-full hover:bg-white/10"
                  :aria-label="t('player.next')"
                  @click="player.next()"
                >
                  <AppIcon name="next" :size="28" />
                </button>
                <button
                  v-if="track?.isPodcast"
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                  :aria-label="t('podcasts.skipForward')"
                  @click="player.seekBy(30)"
                >
                  <AppIcon name="skip-forward" :size="22" />
                </button>
                <button
                  v-else
                  type="button"
                  class="relative flex size-11 items-center justify-center rounded-full transition-colors hover:bg-white/10"
                  :class="
                    player.repeatMode.value !== 'off'
                      ? 'text-accent'
                      : 'text-white/80'
                  "
                  :aria-label="repeatLabel"
                  @click="player.cycleRepeat()"
                >
                  <AppIcon
                    :name="
                      player.repeatMode.value === 'one'
                        ? 'repeat-one'
                        : 'repeat'
                    "
                    :size="22"
                  />
                </button>
                <!-- Right of repeat: a stream queues its download (once -
                     while queued it spins instead), a downloaded track
                     shows a static check that does nothing. -->
                <button
                  v-if="isMobile"
                  type="button"
                  data-np-mobile-queue
                  class="flex size-11 items-center justify-center transition-colors hover:text-white"
                  :class="panel === 'queue' ? 'text-accent' : 'text-white/80'"
                  :aria-label="t('player.upNext')"
                  :aria-pressed="panel === 'queue'"
                  @click="toggleMobilePanel('queue')"
                ><AppIcon name="queue" :size="22" /></button>
                <button
                  v-else-if="showPlayerDownload"
                  type="button"
                  class="flex size-11 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10 disabled:opacity-50"
                  :aria-label="t('actions.downloadItem', { name: track.title })"
                  :disabled="downloadBusy || !pendingSong"
                  @click="downloadCurrent"
                >
                  <AppIcon
                    :name="downloadBusy ? 'refresh' : 'download'"
                    :size="22"
                    :class="downloadBusy ? 'animate-spin' : ''"
                  />
                </button>
                <!-- The heart sits where the library check used to be. -->
                <span
                  v-else-if="!track?.isPodcast && !track?.stream"
                  class="flex size-11 items-center justify-center"
                  data-np-bar-like
                ><LikeButton :file="track.file" size="lg" /></span>
              </div>

              <div class="hidden min-w-0 flex-1 basis-0 items-center justify-end gap-1 lg:flex" data-np-bar-right>
                <UiMenu
                  v-if="track?.isPodcast"
                  :items="speedMenu"
                  :label="t('podcasts.playbackSpeed')"
                >
                  <template #trigger>
                    <button
                      type="button"
                      class="flex h-10 items-center gap-2 rounded-full px-3 text-xs font-semibold text-white/75 transition-colors hover:bg-white/10"
                      :aria-label="t('podcasts.playbackSpeed')"
                    >
                      <AppIcon name="gauge" :size="20" />
                      <span class="tabular">{{ speedLabel }}</span>
                    </button>
                  </template>
                </UiMenu>
                <!-- Same row as the mini player: playing bars, elapsed / total,
                     format, volume. -->
                <EqBars v-if="player.isPlaying.value" :size="12" class="shrink-0" />
                <span data-np-clock class="tabular mx-1 inline-grid shrink-0 text-xs whitespace-nowrap text-white/65">
                  <span class="invisible col-start-1 row-start-1" aria-hidden="true">{{ clockSizer }}</span>
                  <span class="col-start-1 row-start-1 text-right"
                    >{{ formatDuration(player.currentTime.value) }} / {{ formatDuration(player.duration.value) }}</span
                  >
                </span>
                <span v-if="track.format" data-np-format class="mr-1 shrink-0 rounded-md border border-white/20 px-1.5 py-0.5 text-[11px] leading-none font-semibold tracking-wide text-white/75">{{ track.format }}</span>
                <VolumeControl
                  button-size="md"
                  :icon-px="22"
                  width="hidden w-24 2xl:flex"
                  track-class="bg-white/20"
                  fill-class="bg-white"
                  thumb-class="bg-white"
                  class="shrink-0 text-white [&_button]:shrink-0 [&_button]:text-white/80 [&_button:hover]:bg-white/10"
                />
                <!-- Same spot as the mini player's expand arrows. -->
                <button
                  type="button"
                  data-np-collapse
                  class="flex size-10 shrink-0 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                  :aria-label="t('player.closeNowPlaying')"
                  @click="nowPlaying.close()"
                ><AppIcon name="collapse" :size="20" /></button>
                <UiMenu :items="trackMenu" :label="t('common.more')" data-np-more>
                  <template #trigger>
                    <button
                      ref="desktopMoreButton"
                      type="button"
                      class="flex size-10 shrink-0 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/10"
                      :aria-label="t('common.more')"
                    >
                      <AppIcon name="more" :size="20" />
                    </button>
                  </template>
                </UiMenu>
              </div>
            </div>

            <!-- Secondary native popups share the top menu's anchor. -->
            <UiMenu ref="mobileSleepMenu" :items="sleepMenu" :label="t('player.sleepTimer')">
              <template #trigger><span class="hidden" aria-hidden="true" /></template>
            </UiMenu>
            <UiMenu v-if="isMobile && track?.isPodcast" ref="mobileSpeedMenu" :items="speedMenu" :label="t('podcasts.playbackSpeed')">
              <template #trigger><span class="hidden" aria-hidden="true" /></template>
            </UiMenu>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useMediaQuery, useNow } from '@vueuse/core'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import UiMenu from '../ui/UiMenu.vue'
import WaveSeekBar from '../player/WaveSeekBar.vue'
import VolumeControl from '../player/VolumeControl.vue'
import LikeButton from '../player/LikeButton.vue'
import LyricsPanel from '../player/LyricsPanel.vue'
import UpNextPanel from '../player/UpNextPanel.vue'
import TrackDetails from '../player/TrackDetails.vue'
import EqualizerPanel from '../player/EqualizerPanel.vue'
import { usePlayer } from '/src/model/player'
import { useDownloadManager, useProgressTracker } from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useUi } from '/src/model/ui'
import { usePlayerPrefs } from '/src/model/playerPrefs'
import { useNowPlaying } from '/src/model/ui'
import { formatDuration, hueFor, widestClock } from '/src/lib/format'
import EqBars from '../ui/EqBars.vue'
import { availablePanels, requestedPanel } from '/src/lib/panels'
import { useCoverPalette } from '/src/model/coverPalette'
import { saveName } from '/src/lib/paths'
import { openTrackOnSpotify } from '/src/lib/sourceLinks'
// Static on purpose: a dynamic import of the API client breaks the build.
import API from '/src/model/api'
import { playerArtistRoute, playerContextRoute, playerAlbumRoute } from '/src/lib/playerNavigation'
import { dismissPlayerSwipe } from '/src/lib/playerSwipe'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const library = useLibrary()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const ui = useUi()
const { showLyrics } = usePlayerPrefs()
const nowPlaying = useNowPlaying()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const isMobile = useMediaQuery('(max-width: 1023px)')
const now = useNow({ interval: 15000 })
const scrub = ref(null)
const closeButton = ref(null)
const mobileMoreButton = ref(null)
const mobileSleepMenu = ref(null)
const mobileSpeedMenu = ref(null)
const desktopMoreButton = ref(null)
// Secondary menus open where the ⋯ that offered them sits (top on
// phones, bottom bar on desktop - UiMenu flips it upwards there).
async function openMobileMenu(menu) {
  const button = isMobile.value ? mobileMoreButton.value : desktopMoreButton.value
  const rect = button?.getBoundingClientRect()
  if (!rect) return
  await nextTick()
  menu?.openAt({ preventDefault() {}, clientX: rect.right - 208, clientY: rect.bottom })
}
let dismissStart = null
function startDismissSwipe(event) {
  dismissStart = null
  if (!isMobile.value || event.touches.length !== 1 ||
      !event.target.closest('[data-np-swipe-surface]')) return
  const touch = event.touches[0]
  dismissStart = { x: touch.clientX, y: touch.clientY }
}
function endDismissSwipe(event) {
  const touch = event.changedTouches?.[0]
  const end = touch ? { x: touch.clientX, y: touch.clientY } : null
  const dismiss = dismissPlayerSwipe(dismissStart, end, isMobile.value)
  dismissStart = null
  if (dismiss) {
    event.preventDefault()
    nowPlaying.close()
  }
}

const track = computed(() => player.currentTrack.value)
const artistRoute = computed(() => playerArtistRoute(track.value))
const albumRoute = computed(() => playerAlbumRoute(track.value))

// Tracks like this one (podcasts have none): left of shuffle.
const similarArtist = computed(() => {
  if (track.value?.isPodcast) return ''
  return (track.value?.artists || [])[0] || track.value?.artist || ''
})
const similarTitle = computed(
  () => track.value?.name || track.value?.title || ''
)

function goSimilar() {
  const artist = (
    (track.value?.artists || [])[0] ||
    track.value?.artist ||
    ''
  ).trim()
  const title = (track.value?.name || track.value?.title || '').trim()
  if (!artist || !title) return
  router.push({ name: 'Similar', query: { artist, track: title } })
}
const palette = useCoverPalette(track)
const tint = computed(
  () =>
    palette.value?.background ||
    `oklch(0.3 0.06 ${hueFor(track.value?.album || track.value?.title)})`
)

const PANEL_TABS = {
  lyrics: { icon: 'lyrics', label: 'player.lyrics' },
  queue: { icon: 'queue', label: 'player.upNext' },
  details: { icon: 'info', label: 'player.details' },
  equalizer: { icon: 'equalizer', label: 'player.equalizer' },
}

const panels = computed(() =>
  availablePanels({
    lyrics: showLyrics.value,
    isPodcast: track.value?.isPodcast,
    isStream: track.value?.stream,
  }).map((id) => ({
    id,
    icon: PANEL_TABS[id].icon,
    label: t(PANEL_TABS[id].label),
  }))
)

// ?panel= picks the side panel; phones show it instead of the artwork.
const requested = computed(() =>
  requestedPanel(
    route.query.panel,
    panels.value.map((tab) => tab.id)
  )
)
// Nothing in the middle by default: lyrics, queue etc. only when picked.
const desktopQueueVisible = ref(true)
const panel = computed(() => !isMobile.value && requested.value === 'queue' ? '' : (requested.value || ''))
const mobilePanel = computed(() => isMobile.value && !!requested.value)

function setPanel(id) {
  if (id === 'queue' && !isMobile.value) {
    desktopQueueVisible.value = !desktopQueueVisible.value
    return
  }
  // Picking the open tab again closes it.
  if (requested.value === id) {
    const { panel: _panel, ...query } = route.query
    router.replace({ query })
    return
  }
  router.replace({ query: { ...route.query, panel: id } })
}

const clockSizer = computed(() => widestClock(player.duration.value))
const hasPanel = (id) => panels.value.some((tab) => tab.id === id)

function toggleMobilePanel(id) {
  if (mobilePanel.value && panel.value === id) {
    const { panel: _panel, ...query } = route.query
    router.replace({ query })
  } else {
    setPanel(id)
  }
}

const context = computed(() => player.context.value)
const contextLabel = computed(() => {
  const type = context.value?.type
  return type ? t(`player.playingFrom.${type}`) : t('player.nowPlaying')
})
const contextTitle = computed(
  () => context.value?.title || track.value?.album || t('player.queue')
)
const contextRoute = computed(() => playerContextRoute(context.value, track.value))

const repeatLabel = computed(
  () =>
    ({
      off: t('player.repeatOff'),
      all: t('player.repeatAll'),
      one: t('player.repeatOne'),
    })[player.repeatMode.value]
)

const sleepLabel = computed(() => {
  const at = player.sleepAt.value
  if (!at) return ''
  if (at === 'track') return t('player.sleepEndOfTrackShort')
  const minutes = Math.max(1, Math.ceil((at - now.value.getTime()) / 60000))
  return t('player.minutesLeft', { count: minutes })
})

const SPEEDS = [0.75, 1, 1.25, 1.5, 1.75, 2]
const speedLabel = computed(() => `${player.playbackRate.value}×`)
const speedMenu = computed(() =>
  SPEEDS.map((rate) => ({
    label: `${rate}×`,
    checked: player.playbackRate.value === rate,
    action: () => player.setPlaybackRate(rate),
  }))
)

const sleepMenu = computed(() => [
  { heading: t('player.sleepTimer') },
  ...[15, 30, 45, 60, 90].map((minutes) => ({
    label: t('player.sleepMinutes', { count: minutes }),
    action: () => player.setSleepTimer(minutes),
  })),
  {
    label: t('player.sleepEndOfTrack'),
    checked: player.sleepAt.value === 'track',
    action: () => player.setSleepTimer('track'),
  },
  { divider: true, hidden: !player.sleepAt.value },
  {
    label: t('player.sleepOff'),
    icon: 'x',
    hidden: !player.sleepAt.value,
    action: () => player.setSleepTimer(null),
  },
])

const trackMenu = computed(() => {
  const tr = track.value
  if (!tr) return []
  return [
    {
      label: t('player.goToAlbum'),
      icon: 'disc',
      hidden: !tr.album || tr.isPodcast,
      action: () =>
        navigate({
          name: 'Album',
          query: { artist: tr.albumArtist, title: tr.album },
        }),
    },
    {
      label: t('player.goToArtist'),
      icon: 'user',
      hidden: !tr.albumArtist || tr.isPodcast,
      action: () =>
        navigate({ name: 'Artist', query: { name: tr.albumArtist } }),
    },
    // The track's own Spotify page (found on its album), never a search.
    {
      label: t('link.findSpotify'),
      icon: 'spotify',
      hidden: !tr.album || tr.isPodcast || !!tr.stream,
      action: () => openTrackOnSpotify(tr, {
        lookup: API.spotifyLink,
        onMissing: () => ui.toast(t('link.notOnSpotify'), { kind: 'error' }),
      }),
    },
    {
      label: t('library.saveToDevice'),
      icon: 'download',
      hidden: !!tr.stream,
      action: () => saveFile(tr),
    },
    { divider: true },
    ...(isMobile.value ? [
      ...panels.value.filter((tab) => tab.id !== 'queue').map((tab) => ({
        label: tab.label, icon: tab.icon, checked: panel.value === tab.id,
        action: () => toggleMobilePanel(tab.id),
      })),
      { label: t('player.sleepTimer'), icon: 'timer', checked: !!player.sleepAt.value,
        action: () => openMobileMenu(mobileSleepMenu.value) },
      { label: t('podcasts.playbackSpeed'), icon: 'gauge', hidden: !tr.isPodcast,
        action: () => openMobileMenu(mobileSpeedMenu.value) },
      { label: t('actions.downloadItem', { name: tr.title }), icon: 'download',
        hidden: !showPlayerDownload.value, disabled: downloadBusy.value,
        action: downloadCurrent },
    ] : [
      { label: t('player.lyrics'), icon: 'lyrics', hidden: !hasPanel('lyrics'),
        checked: panel.value === 'lyrics', action: () => setPanel('lyrics') },
      { label: t('player.upNext'), icon: 'queue', hidden: !hasPanel('queue'),
        checked: desktopQueueVisible.value, action: () => setPanel('queue') },
      { label: t('player.details'), icon: 'info', hidden: !hasPanel('details'),
        checked: panel.value === 'details', action: () => setPanel('details') },
      { label: t('player.equalizer'), icon: 'equalizer', hidden: !hasPanel('equalizer'),
        checked: panel.value === 'equalizer', action: () => setPanel('equalizer') },
      { label: sleepLabel.value ? `${t('player.sleepTimer')} · ${sleepLabel.value}` : t('player.sleepTimer'),
        icon: 'timer', checked: !!player.sleepAt.value,
        action: () => openMobileMenu(mobileSleepMenu.value) },
    ]),
  ]
})

function navigate(to) {
  // One navigation drops np/panel and opens the target. Calling close()
  // here would race a history.back() against the link destination.
  return router.push(to)
}

function saveFile(tr) {
  const a = document.createElement('a')
  a.href = tr.url
  a.download = saveName(tr.file)
  document.body.appendChild(a)
  a.click()
  a.remove()
}

// A stream that landed in the library while playing (downloaded from
// anywhere) offers deletion instead of another download.
const streamDownloaded = computed(
  () =>
    !!track.value?.stream &&
    library.hasSong(track.value.artist, track.value.title, track.value)
)

const showPlayerDownload = computed(
  () => !!track.value?.stream && !streamDownloaded.value
)

// The playing stream as a downloadable song: the watch URL is the
// download key (so it can't be queued twice) and the known video id
// pins the exact version, like a resolved search row.
const pendingSong = computed(() => {
  const tr = track.value
  if (!tr?.stream || !tr.video_id) return null
  return {
    name: tr.title,
    artists: tr.artist ? [tr.artist] : [],
    artist: tr.artist || '',
    album_name: tr.album || '',
    cover_url: tr.cover && String(tr.cover).startsWith('http') ? tr.cover : '',
    duration: tr.duration || 0,
    url: `https://music.youtube.com/watch?v=${tr.video_id}`,
    youtube_id: tr.video_id,
  }
})

// The queued/finished job behind the button, if any - while one exists
// the button spins instead of queueing a duplicate.
const downloadJob = computed(() => {
  tracker.queueVersion.value
  return pendingSong.value ? tracker.getBySong(pendingSong.value) : null
})
const downloadBusy = computed(() => {
  const state = downloadJob.value?.state
  return state === 'queued' || state === 'active'
})

/** Queue the playing stream as a download (it keeps streaming). */
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

function commitSeek(value) {
  player.seek(value)
  scrub.value = null
}

// Nothing to show once the queue empties.
watch(track, (value) => {
  if (!value && nowPlaying.isOpen.value) nowPlaying.close()
})

watch(
  () => nowPlaying.isOpen.value,
  async (open) => {
    document.documentElement.style.overflow = open ? 'hidden' : ''
    if (open) {
      await nextTick()
      closeButton.value?.focus()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  document.documentElement.style.overflow = ''
})
</script>

<style scoped>
.now-playing-play {
  width: clamp(3rem, 7vh, 3.75rem);
  height: clamp(3rem, 7vh, 3.75rem);
}
@media (min-width: 1024px) {
  .np-body { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .np-body[data-queue-visible="true"][data-central-panel="false"] {
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  }
  .np-body[data-queue-visible="true"][data-central-panel="true"] {
    grid-template-columns: minmax(0, .9fr) minmax(0, 1fr) minmax(220px, var(--np-side));
  }
  .np-body[data-queue-visible="true"][data-central-panel="true"] .now-playing-stage {
    width: 100%;
  }
}
</style>
