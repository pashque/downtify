<template>
  <div class="flex h-full min-h-0 flex-col">
    <div class="flex items-center justify-between gap-3 px-2 pb-3">
      <div class="min-w-0">
        <p class="text-sm font-semibold text-white">{{ t('player.upNext') }}</p>
        <p class="truncate text-xs text-white/55">
          {{ summary }}
        </p>
      </div>
      <button
        v-if="upcoming.length"
        type="button"
        class="shrink-0 rounded-control px-2.5 py-1.5 text-xs font-semibold text-white/70 hover:bg-white/10 hover:text-white"
        @click="player.clearUpcoming()"
      >
        {{ t('player.clearUpcoming') }}
      </button>
    </div>

    <div
      ref="scroller"
      class="min-h-0 flex-1 overflow-y-auto overscroll-contain pr-1 [scrollbar-width:thin] [overflow-anchor:none]"
    >
      <!-- Already played: kept so the user can go back to them. -->
      <ol v-if="played.length" data-queue-played>
        <li
          v-for="item in played"
          @click="rowPlaybackClick($event) && player.playAt(item.index)"
          :key="`played-${item.track.file}-${item.index}`"
          class="group flex h-14 items-center gap-3 rounded-[10px] px-2.5 opacity-55 transition-[opacity,background-color] hover:bg-white/8 hover:opacity-100"
        >
          <button
            type="button"
            class="shrink-0 text-left"
            @click="player.playAt(item.index)"
          >
            <CoverArt
              :thumb="150"
              :src="item.track.hasCover ? item.track.cover : ''"
              :name="item.track.album || item.track.title"
              rounded="rounded-[6px]"
              :letter-size="12"
              :icon-size="14"
              class="size-10"
            />
          </button>
          <div class="min-w-0 flex-1">
            <button type="button" class="block max-w-full truncate text-left text-sm font-medium text-white" @click="player.playAt(item.index)">{{ item.track.title }}</button>
            <p class="truncate text-xs text-white/55"><ArtistCredits :artists="item.track.artists" :artist="item.track.artist" /></p>
          </div>
          <span class="tabular text-xs text-white/45">
            {{ item.track.duration ? formatDuration(item.track.duration) : '' }}
          </span>
        </li>
      </ol>
      <div
        v-if="current"
        ref="currentRow"
        @click="rowPlaybackClick($event) && player.play()"
        class="mb-1 flex h-14 items-center gap-3 rounded-[10px] bg-white/10 px-2.5"
      >
        <CoverArt
          :thumb="150"
          :src="current.hasCover ? current.cover : ''"
          :name="current.album || current.title"
          rounded="rounded-[6px]"
          :letter-size="12"
          :icon-size="14"
          class="size-10"
        />
        <div class="min-w-0 flex-1">
          <p class="flex items-center gap-1.5">
            <span class="truncate text-sm font-semibold text-accent">{{
              current.title
            }}</span>
            <ExplicitBadge v-if="current.explicit" tone="onDark" />
          </p>
          <p class="truncate text-xs text-white/55"><ArtistCredits :artists="current.artists" :artist="current.artist" /></p>
        </div>
        <EqBars :size="12" :playing="player.isPlaying.value" />
      </div>

      <ol>
        <li
          v-for="(item, position) in upcoming"
          @click="rowPlaybackClick($event) && player.playAt(item.index)"
          :key="`${item.track.file}-${item.index}`"
          class="group flex h-14 items-center gap-3 rounded-[10px] px-2.5 transition-colors hover:bg-white/8"
          :class="dragOver === position ? 'bg-white/12' : ''"
          :draggable="!player.shuffle.value"
          @dragstart="onDragStart($event, item.index)"
          @dragover.prevent="dragOver = position"
          @dragleave="dragOver = -1"
          @drop.prevent="onDrop(item.index)"
          @dragend="dragOver = -1"
        >
          <button
            type="button"
            class="shrink-0 text-left"
            @click="player.playAt(item.index)"
          >
            <CoverArt
              :thumb="150"
              :src="item.track.hasCover ? item.track.cover : ''"
              :name="item.track.album || item.track.title"
              rounded="rounded-[6px]"
              :letter-size="12"
              :icon-size="14"
              class="size-10"
            />
          </button>
          <div class="min-w-0 flex-1">
            <button type="button" class="flex max-w-full items-center gap-1.5 text-left" @click="player.playAt(item.index)">
              <span class="truncate text-sm font-medium text-white">{{ item.track.title }}</span>
              <ExplicitBadge v-if="item.track.explicit" tone="onDark" />
            </button>
            <p class="truncate text-xs text-white/55"><ArtistCredits :artists="item.track.artists" :artist="item.track.artist" /></p>
          </div>
          <span class="tabular text-xs text-white/45 group-hover:hidden">
            {{ item.track.duration ? formatDuration(item.track.duration) : '' }}
          </span>
          <button
            type="button"
            class="hidden size-8 items-center justify-center rounded-full text-white/60 hover:bg-white/10 hover:text-white group-hover:flex"
            :aria-label="t('player.removeFromQueue')"
            @click="player.removeAt(item.index)"
          >
            <AppIcon name="x" :size="16" />
          </button>
          <AppIcon
            v-if="!player.shuffle.value"
            name="grip"
            :size="16"
            class="hidden cursor-grab text-white/35 sm:block"
          />
        </li>
      </ol>

      <p
        v-if="!upcoming.length"
        class="px-2 py-8 text-center text-sm text-white/50"
      >
        {{ t('player.queueEnds') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { rowPlaybackClick } from '/src/lib/rowPlayback'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { revealScrollTop } from '/src/lib/revealRow'
import AppIcon from '../ui/AppIcon.vue'
import ArtistCredits from '../library/ArtistCredits.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import { usePlayer } from '/src/model/player'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { t } = useI18n()
const dragOver = ref(-1)
let dragFrom = -1

const current = computed(() => player.currentTrack.value)
const played = computed(() => player.played.value)
const scroller = ref(null)
const currentRow = ref(null)
// Open on the playing track; the played ones are just above it.
function showCurrent() {
  nextTick(() => {
    if (scroller.value && currentRow.value) {
      scroller.value.scrollTop = Math.max(0, currentRow.value.offsetTop - scroller.value.offsetTop - 8)
    }
  })
}
onMounted(showCurrent)
// On a track change (shuffle jumps anywhere) keep the playing row in
// sight: if it is already fully visible nothing moves, otherwise only this
// list glides to it - never the page around it.
function revealCurrent() {
  nextTick(() => {
    const view = scroller.value
    const row = currentRow.value
    if (!view || !row) return
    const top = revealScrollTop({
      scrollTop: view.scrollTop,
      viewHeight: view.clientHeight,
      rowTop: row.getBoundingClientRect().top - view.getBoundingClientRect().top + view.scrollTop,
      rowHeight: row.offsetHeight,
      maxScroll: view.scrollHeight - view.clientHeight,
    })
    if (top !== null) view.scrollTo({ top, behavior: 'smooth' })
  })
}
watch(() => player.currentIndex.value, revealCurrent)
// Long queues render the first stretch only; the rest is still queued.
const upcoming = computed(() => player.upcoming.value.slice(0, 200))

const summary = computed(() => {
  const rest = player.upcoming.value
  const length = splitLength(
    rest.reduce((sum, item) => sum + (item.track.duration || 0), 0)
  )
  const parts = [t('common.tracks', { count: rest.length })]
  if (length.hours || length.minutes) {
    parts.push(
      length.hours
        ? t('common.lengthHours', length)
        : t('common.lengthMinutes', length)
    )
  }
  return parts.join(' · ')
})

function onDragStart(event, index) {
  dragFrom = index
  event.dataTransfer.effectAllowed = 'move'
}

function onDrop(index) {
  if (dragFrom >= 0 && dragFrom !== index) player.moveTrack(dragFrom, index)
  dragFrom = -1
  dragOver.value = -1
}
</script>
