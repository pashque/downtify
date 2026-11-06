<template>
  <div ref="root" role="table" class="-mx-3" :aria-rowcount="tracks.length">
    <!-- Column headings (desktop) -->
    <div
      v-if="header"
      role="row"
      class="grid h-9 items-center gap-3 border-b border-line px-3 text-[11px] font-semibold tracking-[0.06em] text-faint uppercase"
      :class="gridClass"
    >
      <span v-if="selectable" role="columnheader">
        <Checkbox
          :checked="allSelected"
          :indeterminate="someSelected"
          :label="t('library.selectAll')"
          @toggle="toggleAll"
        />
      </span>
      <span data-column="number" role="columnheader" class="source-number text-center">#</span>
      <button
        type="button"
        role="columnheader"
        data-column="title" class="text-left uppercase"
        :class="showCover ? 'pl-14' : ''"
        @click="sortBy('title')"
      >
        {{ t('track.title') }}<SortMark field="title" />
      </button>
      <button
        v-if="showAlbum"
        type="button"
        role="columnheader"
        data-column="album" class="source-album text-left uppercase"
        @click="sortBy('album')"
      >
        {{ t('track.album') }}<SortMark field="album" />
      </button>
      <button
        type="button"
        role="columnheader"
        data-column="time" class="source-duration text-right uppercase"
        @click="sortBy('duration')"
      >
        {{ t('track.time') }}<SortMark
          field="duration"
        />
      </button>
      <span role="columnheader" data-column="format" class="source-format">{{
        t('track.format')
      }}</span>
      <button
        v-if="showAdded"
        type="button"
        role="columnheader"
        data-column="added" class="source-added text-left uppercase"
        @click="sortBy('added')"
      >
        {{ t('track.added') }}<SortMark field="added" />
      </button>
      <span data-column="download" role="columnheader" class="source-download">{{ t('track.library') }}</span>
      <span data-column="locations" class="source-locations" />
      <span data-column="heart" class="source-heart" />
      <span data-column="menu" class="source-actions" />
    </div>

    <div
      class="relative"
      :style="virtual ? { height: `${totalSize}px` } : undefined"
      role="rowgroup"
    >
      <div
        v-for="row in rows"
        :key="row.track.file"
        :data-track-row="row.track.file"
        role="row"
        class="group grid h-16 items-center gap-3 rounded-[12px] px-3 transition-colors select-none"
        :class="[
          gridClass,
          virtual ? 'absolute inset-x-0 top-0' : '',
          isSelected(row.track)
            ? 'bg-accent/10'
            : isCurrent(row.track)
              ? 'bg-surface'
              : 'hover:bg-surface',
        ]"
        :style="
          virtual ? { transform: `translateY(${row.start}px)` } : undefined
        "
        @click="onRowClick($event, row)"
        @dblclick="rowPlaybackClick($event) && playRow(row)"
        @contextmenu="openMenu($event, row)"
      >
        <span v-if="selectable" class="source-selection" @click.stop>
          <Checkbox
            :checked="isSelected(row.track)"
            :label="t('library.selectTrack', { title: row.track.title })"
            @toggle="toggleRow($event, row)"
          />
        </span>
        <span
          data-column="number" class="source-number flex w-6 items-center justify-center text-[13px] text-faint"
        >
          <EqBars
            v-if="isCurrent(row.track)"
            :size="12"
            :playing="player.isPlaying.value"
          />
          <template v-else>
            <span class="tabular group-hover:hidden">{{
              numbering === 'track'
                ? row.track.trackNumber || '–'
                : row.index + 1
            }}</span>
            <button
              type="button"
              class="hidden text-fg group-hover:block"
              :aria-label="t('actions.playItem', { name: row.track.title })"
              @click.stop="playRow(row)"
            >
              <AppIcon name="play" :size="14" />
            </button>
          </template>
        </span>
        <div data-column="title" class="flex min-w-0 items-center gap-3">
          <button
            v-if="showCover"
            type="button"
            class="relative shrink-0"
            :aria-label="t('actions.playItem', { name: row.track.title })"
            @click.stop="playRow(row)"
          >
            <CoverArt
              :thumb="150"
              :src="row.track.hasCover ? row.track.cover : ''"
              :name="row.track.album || row.track.title"
              rounded="rounded-[6px]"
              :letter-size="13"
              :icon-size="16"
              class="size-11"
            />
            <span
              v-if="isSelected(row.track)"
              class="absolute inset-0 flex items-center justify-center rounded-[6px] bg-accent/80 text-on-accent md:hidden"
            >
              <AppIcon name="check" :size="18" stroke-width="3" />
            </span>
          </button>
          <div class="min-w-0">
            <p class="flex items-center gap-1.5">
              <span
                class="truncate text-sm font-semibold"
                :class="isCurrent(row.track) ? 'text-accent' : 'text-fg'"
                >{{ row.track.title }}</span
              >
              <ExplicitBadge v-if="row.track.explicit" />
              <span
                v-if="row.track.hiddenBy && auth.isAdmin.value"
                class="shrink-0 text-faint"
                role="img"
                :title="t(`visibility.hiddenBy.${row.track.hiddenBy}`)"
                :aria-label="t(`visibility.hiddenBy.${row.track.hiddenBy}`)"
              >
                <AppIcon name="eye-off" :size="14" />
              </span>
            </p>
            <p class="truncate text-[13px] text-muted">
              <span
                class="mr-1.5 inline-block rounded-[4px] border border-line-3 px-1 text-[10px] font-semibold text-faint md:hidden"
                >{{ row.track.format }}</span
              >
              <ArtistCredits :artists="row.track.artists" :artist="row.track.artist" />
            </p>
          </div>
        </div>
        <span
          v-if="showAlbum"
          data-column="album" class="source-album truncate text-[13px] text-muted"
        >
          <RouterLink
            v-if="row.track.album"
            :to="albumRoute(row.track, context)"
            class="hover:text-fg hover:underline"
            @click.stop
            >{{ row.track.album }}</RouterLink
          >
        </span>
        <span data-track-duration data-column="time" class="tabular text-right text-[13px] text-muted source-duration">
          {{ row.track.duration ? formatDuration(row.track.duration) : '' }}
        </span>
        <span data-track-format data-column="format" class="source-format">
          <span
            class="rounded-[5px] border border-line-3 px-1.5 py-0.5 text-[11px] font-semibold text-muted"
            >{{ row.track.format }}</span
          >
        </span>
        <span
          v-if="showAdded"
          data-column="added" class="source-added truncate text-[13px] text-faint"
        >
          {{ row.track.added ? timeAgo(row.track.added, locale) : '' }}
        </span>
        <span data-track-download-cell data-column="download" class="source-download" @click.stop>
          <span role="img" :aria-label="t('search.inLibrary')" :title="t('search.inLibrary')" class="flex size-9 items-center justify-center text-muted"><AppIcon name="check" :size="16" stroke-width="3" /></span>
        </span>
        <LocationBadges data-column="locations" class="source-locations" :location="locationFor(row.track)" :context-kind="context?.type || ''" />
        <span data-column="heart" class="source-heart" @click.stop><LikeButton :file="row.track.file" /></span>
        <span data-column="menu" class="source-actions" @click.stop>
          <UiMenu
            :ref="(el) => (menus[row.track.file] = el)"
            :items="menuItems(row)"
            :label="t('common.more')"
            size="sm"
          />
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { rowPlaybackClick } from '/src/lib/rowPlayback'
import ArtistCredits from '/src/components/library/ArtistCredits.vue'
import { computed, defineComponent, h, onMounted, ref, watch } from 'vue'
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import UiMenu from '../ui/UiMenu.vue'
import LikeButton from '../player/LikeButton.vue'
import LocationBadges from './LocationBadges.vue'
import { useLibraryLocations } from '/src/model/libraryLocations'
import { useAuth } from '/src/model/auth'
import { usePlayer } from '/src/model/player'
import { useTrackActions } from '/src/model/trackActions'
import { usePlaylistActions } from '/src/model/playlistActions'
import { formatDuration, timeAgo } from '/src/lib/format'
import { useI18n } from '/src/i18n'
import '/src/styles/trackRows.css'
import { albumRoute } from '/src/lib/albumRouting'

const props = defineProps({
  tracks: { type: Array, required: true },
  context: { type: Object, default: null },
  selected: { type: Set, default: null },
  showAlbum: { type: Boolean, default: false },
  showAdded: { type: Boolean, default: false },
  showCover: { type: Boolean, default: true },
  linkArtist: { type: Boolean, default: true },
  numbering: { type: String, default: 'index' },
  header: { type: Boolean, default: true },
  sort: { type: Object, default: null },
  hideMenu: { type: Array, default: () => [] },
})
const { locationFor } = useLibraryLocations(computed(() => props.tracks))
const emit = defineEmits(['update:selected', 'update:sort'])

const auth = useAuth()
const player = usePlayer()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const { t, locale } = useI18n()
const root = ref(null)
const menus = {}
const scrollMargin = ref(0)
let anchor = -1

const selectable = computed(() => props.selected !== null)
const selectionMode = computed(() => (props.selected?.size || 0) > 0)

const gridClass = computed(() => ['library-track-grid', {
  'source-selectable': selectable.value,
  'source-hide-album': !props.showAlbum,
  'source-show-added': props.showAdded,
}])

// Big lists only render what's on screen.
const VIRTUAL_THRESHOLD = 120
const ROW_HEIGHT = 64
const virtual = computed(() => props.tracks.length > VIRTUAL_THRESHOLD)

const virtualizer = useWindowVirtualizer(
  computed(() => ({
    count: props.tracks.length,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
    scrollMargin: scrollMargin.value,
  }))
)

function measureOffset() {
  if (!root.value) return
  scrollMargin.value = root.value.getBoundingClientRect().top + window.scrollY
}
onMounted(measureOffset)
watch(
  () => props.tracks.length,
  () => requestAnimationFrame(measureOffset)
)

const totalSize = computed(() => virtualizer.value.getTotalSize())

const rows = computed(() => {
  if (!virtual.value) {
    return props.tracks.map((track, index) => ({ track, index, start: 0 }))
  }
  return virtualizer.value.getVirtualItems().map((item) => ({
    track: props.tracks[item.index],
    index: item.index,
    start: item.start - scrollMargin.value,
  }))
})

function isCurrent(track) {
  return player.currentTrack.value?.file === track.file
}

function isSelected(track) {
  return !!props.selected?.has(track.file)
}

const allSelected = computed(
  () => props.tracks.length > 0 && props.selected?.size === props.tracks.length
)
const someSelected = computed(
  () => (props.selected?.size || 0) > 0 && !allSelected.value
)

function setSelected(next) {
  emit('update:selected', next)
}

function toggleAll() {
  setSelected(
    allSelected.value
      ? new Set()
      : new Set(props.tracks.map((track) => track.file))
  )
}

function toggleRow(event, row) {
  const next = new Set(props.selected)
  if (event?.shiftKey && anchor >= 0) {
    const [from, to] = [anchor, row.index].sort((a, b) => a - b)
    for (let i = from; i <= to; i++) next.add(props.tracks[i].file)
  } else if (next.has(row.track.file)) {
    next.delete(row.track.file)
  } else {
    next.add(row.track.file)
  }
  anchor = row.index
  setSelected(next)
}

function playRow(row) {
  actions.play(props.tracks, row.index, props.context)
}

function onRowClick(event, row) {
  if (event.target?.closest('a, button, input, select, [role="checkbox"]')) return
  // Selection mode/modifiers keep their existing multi-select behavior.
  if (
    selectable.value &&
    (selectionMode.value || event.ctrlKey || event.metaKey || event.shiftKey)
  ) {
    toggleRow(event, row)
    return
  }
  if (rowPlaybackClick(event)) playRow(row)
}

function openMenu(event, row) {
  menus[row.track.file]?.openAt(event)
}

function menuItems(row) {
  const items = actions.menuFor(row.track, {
    list: props.tracks,
    index: row.index,
    context: props.context,
    hide: props.hideMenu,
  })
  const addItems = playlistActions.addMenuItems([row.track])
  if (addItems.length) {
    const queueAt = items.findIndex((item) => item.icon === 'queue')
    const at = queueAt >= 0 ? queueAt + 1 : 3
    items.splice(at, 0, { divider: true }, ...addItems)
  }
  if (props.context?.manual && props.context?.playlistName) {
    const playlist = playlistActions
      .manuals()
      .find((item) => item.name === props.context.playlistName)
    if (playlist) {
      const trashAt = items.findIndex((item) => item.danger)
      items.splice(trashAt >= 0 ? trashAt : items.length, 0, {
        label: t('playlists.removeTrack'),
        icon: 'x',
        action: () => playlistActions.removeFiles(playlist, [row.track]),
      })
    }
  }
  if (selectable.value) {
    items.splice(3, 0, {
      label: isSelected(row.track)
        ? t('library.deselect')
        : t('library.select'),
      icon: 'check',
      action: () => toggleRow(null, row),
    })
  }
  return items
}

function sortBy(field) {
  if (!props.sort) return
  const same = props.sort.key === field
  emit('update:sort', {
    key: field,
    dir: same && props.sort.dir === 'asc' ? 'desc' : 'asc',
  })
}

const SortMark = defineComponent({
  props: { field: String },
  setup(markProps) {
    return () =>
      props.sort?.key === markProps.field
        ? h(
            'span',
            { class: 'ml-1 text-fg-3' },
            props.sort.dir === 'asc' ? '↑' : '↓'
          )
        : null
  },
})

const Checkbox = defineComponent({
  props: { checked: Boolean, indeterminate: Boolean, label: String },
  emits: ['toggle'],
  setup(boxProps, { emit: emitBox }) {
    return () =>
      h(
        'button',
        {
          type: 'button',
          role: 'checkbox',
          'aria-checked': boxProps.indeterminate
            ? 'mixed'
            : String(boxProps.checked),
          'aria-label': boxProps.label,
          class: [
            'flex size-[18px] items-center justify-center rounded-[5px] border-[1.5px] transition-colors',
            boxProps.checked || boxProps.indeterminate
              ? 'border-accent bg-accent text-on-accent'
              : 'border-line-3 hover:border-fg-3',
          ],
          onClick: (event) => emitBox('toggle', event),
        },
        boxProps.checked
          ? [h(AppIcon, { name: 'check', size: 13, strokeWidth: 3 })]
          : boxProps.indeterminate
            ? [h('span', { class: 'h-0.5 w-2 rounded bg-on-accent' })]
            : []
      )
  },
})
</script>
