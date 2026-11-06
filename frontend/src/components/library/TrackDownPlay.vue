<template>
  <div
    class="group source-track-grid h-16 rounded-[12px] px-3 transition-colors"
    :data-track-row="song.song_id || song.url || song.file"
    :class="
      [selected ? 'bg-accent/8' : highlighted ? 'bg-surface' : 'hover:bg-surface', { 'source-selectable': selectable, 'source-hide-album': hideAlbum }]
    "
    :data-marked="marked || undefined"
    @click="onRowClick"
    @dblclick="rowPlaybackClick($event) && ensurePlaying()"
    @contextmenu="emit('contextmenu', $event)"
  >
    <button
      v-if="selectable"
      type="button"
      role="checkbox"
      :aria-checked="selected"
      :aria-label="t('library.selectTrack', { title: song.name })"
      class="flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border-[1.5px] transition-colors"
      :class="
        selected
          ? 'border-accent bg-accent text-on-accent'
          : 'border-line-3 hover:border-fg-3'
      "
      @click.stop="emit('toggle')"
      @dblclick.stop
    >
      <AppIcon v-if="selected" name="check" :size="13" stroke-width="3" />
    </button>
    <span
      data-column="number" class="source-number flex w-6 items-center justify-center text-[13px] text-faint max-sm:hidden"
    >
      <EqBars v-if="isCurrent" :size="12" :playing="player.isPlaying.value" />
      <!-- A stream being resolved, where the number was. -->
      <AppIcon
        v-else-if="loading"
        name="refresh"
        :size="14"
        class="animate-spin text-fg"
      />
      <template v-else>
        <span class="tabular" :class="playable ? 'group-hover:hidden' : ''">{{
          index === null ? '' : index + 1
        }}</span>
        <button
          v-if="playable"
          type="button"
          class="hidden text-fg group-hover:block"
          :aria-label="playLabel"
          @click.stop="toggle"
        >
          <AppIcon name="play" :size="14" />
        </button>
      </template>
    </span>

    <button
      v-if="playable"
      type="button"
      class="source-cover shrink-0"
      :aria-label="playLabel"
      @click.stop="toggle"
    >
      <CoverArt
        :src="cover"
        :name="song.album_name || song.name"
        rounded="rounded-[8px]"
        :letter-size="14"
        class="size-11"
      />
    </button>
    <CoverArt
      v-else
      :src="cover"
      :name="song.album_name || song.name"
      rounded="rounded-[8px]"
      :letter-size="14"
      class="source-cover size-11"
    />

    <div data-column="title" class="min-w-0 flex-1">
      <p class="flex items-center gap-1.5">
        <RouterLink
          v-if="to"
          :to="to"
          class="truncate text-sm font-semibold hover:underline"
          :class="highlighted ? 'text-accent' : ''"
          @click.stop
          @dblclick.stop
          >{{ song.name }}</RouterLink
        >
        <span
          v-else
          class="truncate text-sm font-semibold"
          :class="highlighted ? 'text-accent' : ''"
          >{{ song.name }}</span
        >
        <ExplicitBadge v-if="song.explicit" />
      </p>
      <p class="truncate text-[13px] text-muted">
        <ArtistCredits :artists="song.artists" :artist="song.artist || t('common.unknownArtist')" /><span v-if="song.album_name && !hideAlbum" class="lg:hidden">
          · {{ song.album_name }}</span
        >
      </p>
    </div>
    <span
      v-if="!hideAlbum"
      data-column="album" class="source-album truncate text-[13px] text-muted"
      >{{ song.album_name }}</span
    >
    <span
      data-track-duration data-column="time"
      class="source-duration tabular hidden w-12 text-right text-[13px] text-muted sm:block"
    >
      {{ song.duration ? formatDuration(song.duration) : '' }}
    </span>
    <TrackFormat data-column="format" class="source-format" :formats="location?.formats || []" />
    <!-- A reserved download cell keeps checks, downloads and progress aligned. -->
    <div
      data-track-download-cell data-column="download"
      class="source-download flex w-28 shrink-0 items-center max-sm:w-auto"
      @click.stop
      @dblclick.stop
    >
      <DownloadState :song="song" :downloaded="location?.downloaded" round />
    </div>
    <LocationBadges data-column="locations" class="source-locations" :location="location" :context-kind="locationContext" />
    <div data-column="heart" class="source-heart"><slot name="heart" :song="song"><LocalLike :song="song" /></slot></div>
    <div data-column="menu" class="source-actions"><slot name="actions" :song="song"><SourceSongMenu :song="song" /></slot></div>
  </div>
</template>

<script setup>
import { rowPlaybackClick } from '/src/lib/rowPlayback'
import ArtistCredits from '/src/components/library/ArtistCredits.vue'
import LocalLike from './LocalLike.vue'
// One song as a row that downloads, then plays: minimal like a search
// result (SongRow), with the play affordances TrackList has on an album page
// once the song is in the library (the number turns into a play button on
// hover, the cover plays, a double click plays, a tap plays on a touch
// screen). On the right it shows the download state - the button, its
// progress, or the "In library" label - the way a search result does.
//
// Until the song is downloaded the same affordances stream it in full
// from YouTube, always shown in the built-in player - see
// model/songPlay.js and model/stream.js.
//
// Deliberately standalone: it borrows the look of SongRow and the behaviour
// of TrackList without importing or editing either, so neither grid can be
// affected by it. It takes a *song* (what a search or link result is), not a
// library track, and finds the file behind it once it has been downloaded.
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import ExplicitBadge from '../ui/ExplicitBadge.vue'
import DownloadState from '../search/DownloadState.vue'
import SourceSongMenu from './SourceSongMenu.vue'
import LocationBadges from './LocationBadges.vue'
import TrackFormat from './TrackFormat.vue'
import '/src/styles/trackRows.css'
import { usePlayer } from '/src/model/player'
import { useSongPlay } from '/src/model/songPlay'
import { deezerImage } from '/src/lib/deezerImage'
import { formatDuration } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const props = defineProps({
  // A song from a search/link/top-songs result.
  song: { type: Object, required: true },
  location: { type: Object, default: null },
  locationContext: { type: String, default: '' },
  // Its position in the list, shown as the number; `null` hides it.
  index: { type: Number, default: null },
  // The library tracks playing this song starts a queue from (typically the
  // list's other downloaded songs, in order). Without it, just this song.
  queue: { type: Array, default: () => [] },
  // The whole song list, for a mixed queue (downloaded rows from the
  // library, the rest streamed) the player works through to the end.
  songs: { type: Array, default: null },
  // Where the queue comes from, for the player's "playing from".
  context: { type: Object, default: null },
  // Off by default: a caller doing multi-select (e.g. a "download selected"
  // list) turns this on and owns the actual selection state itself - this
  // row only shows the checkbox and reports clicks on it via `toggle`.
  selectable: { type: Boolean, default: false },
  // Whether this row is currently selected. Ignored unless `selectable`.
  selected: { type: Boolean, default: false },
  // Makes the title a link to this route location (e.g. a page about the
  // song); a plain title when unset.
  to: { type: [String, Object], default: null },
  // Highlights the row like the one playing - for a caller pointing at
  // one song in the list (the Finder's, for the track it was opened on).
  marked: { type: Boolean, default: false },
  // Leaves out the album column (and the album after the artists on a
  // narrow screen) - for a list that is all one album anyway.
  hideAlbum: { type: Boolean, default: true },
})

const emit = defineEmits(['toggle', 'contextmenu'])

const { t } = useI18n()
const player = usePlayer()
const {
  isCurrent,
  loading,
  playable,
  highlighted: playing,
  playLabel,
  toggle,
  ensurePlaying,
} = useSongPlay(props)

// A Deezer cover at its medium size, for the 44px thumbnail - display only:
// the song's own `cover_url` is what its download embeds.
const cover = computed(() => deezerImage(props.song.cover_url))
// Lit up while it plays, and when the caller points at it.
const highlighted = computed(() => props.marked || playing.value)

// On a touch screen a tap on the row plays it (a double click can't).
function onRowClick(event) {
  if (rowPlaybackClick(event)) ensurePlaying()
}
</script>
