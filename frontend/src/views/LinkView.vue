<template>
  <div>
    <!-- Loading -->
    <div
      v-if="loading"
      class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-10 sm:px-6 md:flex-row md:items-end lg:px-10"
    >
      <UiSkeleton
        class="size-48 self-center !rounded-[16px] sm:size-56 md:self-auto"
      />
      <div class="flex flex-1 flex-col gap-3">
        <UiSkeleton class="h-3 w-32" />
        <UiSkeleton class="h-12 w-2/3" />
        <p class="flex items-center gap-2 text-sm text-muted">
          <span
            class="size-4 animate-spin rounded-full border-2 border-accent border-r-transparent"
          />
          {{ t('link.resolving') }}
        </p>
      </div>
    </div>

    <div
      v-else-if="error"
      class="mx-auto max-w-[1680px] px-4 pt-10 sm:px-6 lg:px-10"
    >
      <UiEmpty icon="alert" :title="t('link.failed')" :body="error">
        <UiButton icon="refresh" @click="resolve">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>
    </div>

    <div v-else-if="details" class="animate-rise">
      <CollectionHero
        :playing="linkPlaying"
        :loading="albumInfoUpdating"
        :title="details.name || t('link.untitled')"
        :kicker="kicker"
        :cover="details.cover_url"
        :covers="details.cover_url ? [] : mosaic"
        :name="details.name"
        :icon="
          details.kind === 'artist'
            ? 'user'
            : details.kind === 'playlist'
              ? 'playlist'
              : 'disc'
        "
        :round="details.kind === 'artist'"
      >
        <template #subtitle>
          <!-- Exactly the library album page's lines, for every source:
               "Artist · 16 tracks · 1 h 1 min" (kicker "ALBUM · 2022"). -->
          <span v-if="heroArtists.length" class="max-md:block" data-link-artists>
            <template v-for="(name, i) in heroArtists" :key="name">
              <span v-if="i">, </span>
              <button
                type="button"
                class="font-semibold text-fg hover:underline"
                @click="openArtist(name)"
              >{{ name }}</button>
            </template>
          </span>
          <span v-else-if="details.subtitle && details.kind !== 'artist'">{{
            details.subtitle
          }}</span>
          <span
            v-for="(part, i) in heroFacts"
            :key="part"
            class="tabular"
            data-link-facts
          ><span :class="i === 0 ? 'max-md:hidden' : ''">{{ i || heroArtists.length || (details.subtitle && details.kind !== 'artist') ? ' · ' : '' }}</span>{{ part }}</span>
        </template>
        <template #actions>
          <template v-if="details.tracks.length">
            <PlayButton
              v-if="releaseInLibrary"
              data-link-play
              :label="t('actions.playItem', { name: details.name })"
              :playing="linkPlaying"
              @click="playRelease"
            />
            <UiButton
              v-if="selected.size || (details.kind === 'album' ? albumTargetLoaded : newSongs.length)"
              :variant="releaseInLibrary && !selected.size ? 'ghost' : 'primary'"
              size="lg"
              icon="download"
              :loading="submitting"
              :disabled="!selected.size && details.kind === 'album' && !albumTargetLoaded"
              :class="!releaseInLibrary || selected.size ? 'shadow-[0_10px_30px_color-mix(in_srgb,var(--c-accent)_35%,transparent)]' : ''"
              data-link-primary
              @click="selected.size ? downloadSelection() : details.kind === 'album' ? downloadAlbum() : download(newSongs)"
            >
              {{
                selected.size
                  ? `${t('link.downloadSelected')} (${selected.size})`
                  : details.kind === 'album'
                  ? albumButtonLabel
                  : newSongs.length === details.tracks.length
                    ? t('link.downloadAll', { count: newSongs.length })
                    : t('link.downloadNew', { count: newSongs.length })
              }}
            </UiButton>
            <span
              v-else-if="details.kind !== 'album'"
              class="inline-flex h-12 items-center gap-2 rounded-control bg-accent/12 px-5 text-[15px] font-semibold text-accent"
            >
              <AppIcon name="check-circle" :size="18" />{{
                t('link.allInLibrary')
              }}
            </span>
            <UiButton
              v-if="details.kind !== 'album' && newSongs.length && newSongs.length < details.tracks.length"
              variant="ghost"
              @click="download(details.tracks)"
            >
              {{ t('link.redownloadAll') }}
            </UiButton>
          </template>
          <UiButton
            v-if="watchable"
            variant="ghost"
            icon="radar"
            :loading="watching"
            @click="watch"
          >
            {{
              details.kind === 'artist'
                ? t('link.watchArtist')
                : t('link.watchPlaylist')
            }}
          </UiButton>
          <UiButton
            v-if="details.kind === 'artist'"
            variant="ghost"
            icon="trending"
            :to="{ name: 'TopSongs', query: { url } }"
          >
            {{ t('link.topSongs') }}
          </UiButton>
          <UiButton
            v-for="action in providerActions"
            :key="action.icon"
            variant="ghost"
            :icon="action.icon"
            data-link-source
            @click="action.action"
          >{{ action.label }}</UiButton>
          <EditionMenu
            v-if="details.kind === 'album' && sourceAlbumId && editionOptions.length > 1"
            :model-value="sourceAlbumId"
            :options="editionOptions"
            :label="t('library.album')"
            data-link-editions
            @update:model-value="selectEdition"
          />
          <EditionMenu
            v-if="details.kind !== 'album' && details.tracks.length && filters.length > 1"
            v-model="filter"
            :options="filterOptions"
            :label="t('link.filterAll')"
            icon="filter"
            data-link-filter
          />
          <UiMenu :items="heroMenu" :label="t('common.more')" size="lg" />
        </template>
      </CollectionHero>

      <div
        class="mx-auto flex max-w-[1680px] flex-col gap-6 px-4 sm:px-6 lg:px-10"
      >
        <!-- Tracks -->
        <template v-if="details.tracks.length">
          <ol class="-mx-3 flex flex-col">
            <TrackDownPlayHeader
              selectable
              :selected-count="selected.size"
              :hide-album="details.kind !== 'playlist'"
              @clear-selection="selected = new Set()"
            />
            <li
              v-for="row in visibleRows"
              @click="rowPlaybackClick($event) && startRowSong(row.song, { queue: playQueue, context: playContext, songs: playSongs })"
              :key="row.key"
              class="group source-track-grid source-selectable h-16 rounded-[12px] px-3 transition-colors hover:bg-surface"
              :data-track-row="row.song.song_id || row.song.url"
              :class="[selected.has(row.key) ? 'bg-accent/8' : '', { 'source-hide-album': details.kind !== 'playlist' }]"
            >
              <button
                type="button"
                role="checkbox"
                :aria-checked="selected.has(row.key)"
                :aria-label="t('library.selectTrack', { title: row.song.name })"
                class="flex size-[18px] shrink-0 items-center justify-center rounded-[5px] border-[1.5px] transition-colors"
                :class="
                  selected.has(row.key)
                    ? 'border-accent bg-accent text-on-accent'
                    : 'border-line-3 hover:border-fg-3'
                "
                @click="toggle(row.key)"
              >
                <AppIcon
                  v-if="selected.has(row.key)"
                  name="check"
                  :size="13"
                  stroke-width="3"
                />
              </button>
              <SongPlayCell
                data-column="number" class="source-number"
                :song="row.song"
                :index="row.index"
                :queue="playQueue"
                :context="playContext"
                :songs="playSongs"
              />
              <CoverArt
                :src="row.song.cover_url"
                :name="row.song.album_name || row.song.name"
                rounded="rounded-[8px]"
                :letter-size="14"
                class="source-cover size-11"
              />
              <div data-column="title" class="min-w-0 flex-1">
                <p class="truncate text-sm font-semibold">
                  {{ row.song.name }}
                </p>
                <p class="truncate text-[13px] text-muted">
                  <ArtistCredits :artists="row.song.artists" :artist="row.song.artist" />
                </p>
              </div>
              <span
                v-if="details.kind === 'playlist'" data-column="album" class="source-album truncate text-[13px] text-muted"
                >{{ row.song.album_name }}</span
              >
              <span
                data-track-duration data-column="time"
                class="source-duration tabular hidden w-12 text-right text-[13px] text-muted sm:block"
              >
                {{ row.song.duration ? formatDuration(row.song.duration) : '' }}
              </span>
              <TrackFormat data-column="format" class="source-format" :formats="locationFor(row.song)?.formats || []" />
              <div data-track-download-cell data-column="download" class="source-download flex w-28 shrink-0 max-sm:w-auto">
                <DownloadState :song="row.song" :downloaded="locationFor(row.song)?.downloaded" round />
              </div>
              <LocationBadges data-column="locations" class="source-locations" :location="locationFor(row.song)" />
              <span data-column="heart" class="source-heart"><LocalLike :song="row.song" /></span>
              <span data-column="menu" class="source-actions"><SourceSongMenu :song="row.song" /></span>
            </li>
          </ol>
          <p
            v-if="!visibleRows.length"
            class="py-10 text-center text-sm text-muted"
          >
            {{ t('library.noMatches') }}
          </p>
        </template>

        <!-- Artist releases: Albums, then Singles & EPs. -->
        <template v-else-if="details.albums.length">
          <h2 v-if="releaseGroups.length" class="text-display text-xl font-semibold">{{ t('finder.discography') }}</h2>
          <section
            v-for="group in releaseGroups"
            :key="group.id"
            class="flex flex-col gap-4"
            :data-discography="group.id"
          >
            <h2 class="text-display text-lg font-semibold">{{ group.label }}</h2>
            <div
              class="tile-grid"
            >
              <ReleaseCard
                v-for="album in group.items"
                :key="album.album_id || album.url"
                :release="album"
              />
            </div>
          </section>
        </template>

        <UiEmpty v-else icon="search" :title="t('link.empty')" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { downloadReleaseLabel, releaseKicker } from '/src/lib/releaseType'
import { rowPlaybackClick } from '/src/lib/rowPlayback'
import { useSongStarter } from '/src/model/songPlay'
import ArtistCredits from '/src/components/library/ArtistCredits.vue'
import LocalLike from '/src/components/library/LocalLike.vue'
import { computed, ref, watch as watchValue } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '/src/components/ui/AppIcon.vue'
import CoverArt from '/src/components/ui/CoverArt.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'

import UiMenu from '/src/components/ui/UiMenu.vue'
import EditionMenu from '/src/components/library/EditionMenu.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import { songProvider, openYouTubeMusic, openAlbumOn } from '/src/lib/sourceLinks'
import { groupAlbumEditions, albumEditionOptions } from '/src/lib/albumEditions'
import { discographySections, inspectDiscography } from '/src/lib/discography'
import { isPlayingRelease } from '/src/lib/nowPlaying'
import { usePlayer } from '/src/model/player'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import DownloadState from '/src/components/search/DownloadState.vue'
import LocationBadges from '/src/components/library/LocationBadges.vue'
import SourceSongMenu from '/src/components/library/SourceSongMenu.vue'
import TrackDownPlayHeader from '/src/components/library/TrackDownPlayHeader.vue'
import TrackFormat from '/src/components/library/TrackFormat.vue'
import { useLibraryLocations } from '/src/model/libraryLocations'
import '/src/styles/trackRows.css'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import SongPlayCell from '/src/components/library/SongPlayCell.vue'
import API from '/src/model/api'
import monitorAPI from '/src/model/monitor'
import {
  jobSongKey,
  useDownloadManager,
  useProgressTracker,
} from '/src/model/download'
import { useLibrary } from '/src/model/library'
import { useAlbumDestination } from '/src/model/albumSource'
import { albumRowSong } from '/src/lib/albumRouting'
import { destinationAvailable, songDownloadState } from '/src/lib/downloadState'
import { useUi } from '/src/model/ui'
import { classifyInput } from '/src/lib/input'
import { playableQueue } from '/src/lib/topSongs'
import { formatDuration, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const startRowSong = useSongStarter()
const route = useRoute()
const router = useRouter()
const dm = useDownloadManager()
const tracker = useProgressTracker()
const library = useLibrary()
const ui = useUi()
const player = usePlayer()

const details = ref(null)
const { locationFor, refresh: refreshLocations } = useLibraryLocations(computed(() => details.value?.tracks || []))
const albumSongs = computed(() => details.value?.kind === 'album' ? details.value.tracks : null)
const { missing: missingAlbumSongs, loaded: albumTargetLoaded, loading: albumTargetLoading } = useAlbumDestination(albumSongs)
const albumComplete = computed(() => albumTargetLoaded.value && !!albumSongs.value?.length && !missingAlbumSongs.value.length)
const loading = ref(false)
const error = ref('')
const submitting = ref(false)
const watching = ref(false)
const filter = ref('all')
const selected = ref(new Set())

const url = computed(() => String(route.query.url || ''))
const kind = computed(() => classifyInput(url.value))

const editions = ref([])
const editionsLoading = ref(false)
const albumInfoUpdating = computed(() => editionsLoading.value || albumTargetLoading.value || releasesLoading.value)
const sourceAlbumId = computed(() => {
  if (kind.value.source !== 'spotify' || kind.value.kind !== 'album') return ''
  try {
    const parsed = new URL(kind.value.url)
    if (parsed.hostname !== 'open.spotify.com') return ''
    return /^\/album\/([A-Za-z0-9]{22})\/?$/.exec(parsed.pathname)?.[1] || ''
  } catch { return '' }
})
const editionGroups = computed(() => groupAlbumEditions(editions.value, sourceAlbumId.value))
const editionOptions = computed(() => albumEditionOptions(editionGroups.value, t))
let resolveRequest = 0
function clearSource() {
  details.value = null
  selected.value = new Set()
  editions.value = []
  editionsLoading.value = false
  filter.value = 'all'
  error.value = ''
}
function selectEdition(id) {
  const edition = editionGroups.value.find(item => item.id === id)
  if (!edition || id === sourceAlbumId.value || !/^[A-Za-z0-9]{22}$/.test(id)) return
  // Invalidate immediately, even before the router's reactive update.
  resolveRequest++
  clearSource()
  loading.value = true
  router.replace({ query: { ...route.query, url: `https://open.spotify.com/album/${id}` } })
}
async function discoverEditions(id, current) {
  editionsLoading.value = true
  try {
    const res = await API.getSpotifyAlbumEditions(id)
    if (current === resolveRequest) {
      editions.value = res.data?.editions || []
      await library.lookupSongs(details.value?.tracks || [])
      if (current !== resolveRequest) return
      void refreshLocations()
    }
  } catch { /* Optional choices must not prevent opening the exact source. */ }
  finally { if (current === resolveRequest) editionsLoading.value = false }
}
async function resolve() {
  const current = ++resolveRequest
  const requestedUrl = url.value
  const query = { ...route.query }
  clearSource()
  loading.value = !!requestedUrl
  if (!requestedUrl) return
  try {
    const res = await API.resolveUrl(requestedUrl)
    if (current !== resolveRequest) return
    details.value = res.data
    if (res.data?.kind === 'album') {
      details.value.tracks = (res.data.tracks || []).map((song) => albumRowSong(song, query))
      if (sourceAlbumId.value) void discoverEditions(sourceAlbumId.value, current)
      await library.lookupSongs(details.value.tracks)
    } else {
      await library.lookupSongs(res.data?.tracks || [], {
        destination: true,
        playlist_name: res.data?.kind === 'playlist' ? res.data.name : '',
      })
    }
  } catch (err) {
    if (current === resolveRequest) error.value = err?.response?.data?.detail || err?.message || ''
  } finally {
    if (current === resolveRequest) loading.value = false
  }
}

watchValue(url, resolve, { immediate: true, flush: 'sync' })

const SOURCE_LABELS = {
  spotify: () => t('link.openSpotify'),
  youtube: () => t('link.openYoutube'),
  deezer: () => t('link.openDeezer'),
}
// The service's own logo on its button (not a generic arrow).
const sourceIcon = computed(() => ({ spotify: 'spotify', youtube: 'youtube-music', deezer: 'deezer' })[kind.value.source] || 'arrow-up-right')
const sourceLabel = computed(() =>
  (SOURCE_LABELS[kind.value.source] || SOURCE_LABELS.youtube)()
)

const kicker = computed(() => {
  // Where the link is from, then the library album line: "SPOTIFY · ALBUM · 2022".
  const d = details.value
  const names = { spotify: 'Spotify', youtube: 'YouTube Music', deezer: 'Deezer' }
  const source = names[kind.value.source] || kind.value.source || ''
  const label = d?.kind === 'album' ? releaseKicker(d.release_type, t) : t(`link.kind.${d?.kind || 'track'}`)
  return [source, label, d?.kind === 'artist' ? '' : d?.year].filter(Boolean).join(' · ')
})

// Playing a downloaded song from here queues the list's other downloaded
// songs after it, in the list's order; the rest stream in full.
const playQueue = computed(() =>
  playableQueue(details.value?.tracks || [], library.findTrack)
)
// The whole list for a mixed queue: downloaded rows from the library,
// the rest streamed, played through to the end.
const playSongs = computed(() => visibleRows.value.map((row) => row.song))
const playContext = computed(() =>
  details.value
    ? {
        type: details.value.kind === 'playlist' ? 'playlist' : 'album',
        title: details.value.name || '',
        subtitle: details.value.subtitle || '',
        cover: details.value.cover_url || '',
        route: { name: 'Link', query: { ...route.query, url: url.value } },
      }
    : null
)

// Playlist Monitor has no Deezer support: watching a Deezer playlist or
// artist for updates isn't offered, only downloading what's there now.
const watchable = computed(
  () =>
    (details.value?.kind === 'playlist' || details.value?.kind === 'artist') &&
    kind.value.source !== 'deezer'
)

const mosaic = computed(() =>
  [
    ...new Set(
      (details.value?.tracks || [])
        .map((song) => song.cover_url)
        .filter(Boolean)
    ),
  ].slice(0, 4)
)

const lengthLabel = computed(() => {
  const total = (details.value?.tracks || []).reduce(
    (sum, song) => sum + (song.duration || 0),
    0
  )
  if (!total) return ''
  const { hours, minutes } = splitLength(total)
  return hours
    ? t('common.lengthHours', { hours, minutes })
    : t('common.lengthMinutes', { minutes })
})

function keyOf(song, index) {
  return jobSongKey(song) || `row-${index}`
}

function statusOf(song) {
  tracker.queueVersion.value
  const artist = (song.artists || [])[0] || song.artist
  const item = tracker.getBySong(song)
  const state = songDownloadState(
    item,
    details.value?.kind === 'album'
      ? library.hasSong(artist, song.name, song)
      : destinationAvailable(song, item, library.hasSong(artist, song.name, song))
  )
  // Every queue state shows the same neutral chip here; a song that is
  // neither queued nor in the library is downloadable.
  return state === 'library' || state === 'new' ? state : 'queue'
}

const rows = computed(() =>
  (details.value?.tracks || []).map((song, index) => ({
    song,
    index,
    key: keyOf(song, index),
    status: statusOf(song),
  }))
)

const newSongs = computed(() =>
  rows.value.filter((row) => row.status === 'new').map((row) => row.song)
)

const filters = computed(() => {
  const count = (status) =>
    rows.value.filter((row) => row.status === status).length
  return [
    { id: 'all', label: t('link.filterAll'), count: rows.value.length },
    { id: 'new', label: t('link.filterNew'), count: count('new') },
    { id: 'library', label: t('link.filterLibrary'), count: count('library') },
    { id: 'queue', label: t('link.filterQueue'), count: count('queue') },
  ].filter((item) => item.id === 'all' || item.count)
})

// Album/track artists are clickable: the library artist page when the
// artist is in the library, otherwise their full Spotify discography.
const heroArtists = computed(() => {
  const d = details.value
  if (!d || !['album', 'track'].includes(d.kind)) return []
  const lead = d.tracks?.[0]
  const names = d.kind === 'album' && lead?.album_artist
    ? [lead.album_artist]
    : lead?.artists || []
  return [...new Set(names.map((n) => String(n || '').trim()).filter(Boolean))]
})

async function openArtist(name) {
  try {
    await library.ensureArtists()
  } catch {
    // Without the library index, fall back to the Spotify discography.
  }
  const local = library.findArtist(name)
  if (local && (local.tracks?.length || local.track_count || local.trackCount)) {
    router.push({ name: 'Artist', query: { name, tab: 'albums' } })
    return
  }
  try {
    const res = await API.getArtistSpotifyId(name)
    router.push({ name: 'Link', query: { url: `https://open.spotify.com/artist/${res.data.id}` } })
  } catch {
    ui.toast(t('artist.notFound'), { kind: 'error' })
  }
}

const inspectedReleases = ref([])
const releasesLoading = ref(false)
let inspectedArtistName = ''
let releaseInspectionRequest = 0
watchValue(() => {
  tracker.queueVersion.value
  return JSON.stringify([
    details.value?.kind, details.value?.name,
    (details.value?.albums || []).map(release => release.album_id || release.url),
    tracker.downloadQueue.value.filter(item => item.state === 'done').map(item => item.filename),
  ])
}, async () => {
  const current = ++releaseInspectionRequest
  const d = details.value
  if (inspectedArtistName !== (d?.kind === 'artist' ? d.name : '')) {
    inspectedReleases.value = []
    inspectedArtistName = d?.kind === 'artist' ? d.name : ''
  }
  releasesLoading.value = false
  if (d?.kind !== 'artist') return
  releasesLoading.value = true
  try {
   try {
    await library.ensureArtists()
    // The light artist index has no per-release tracks. Load this artist's
    // visible files before deciding which unique release needs verification.
    await library.loadArtistTracks?.(d.name)
  } catch { /* Keep unknown releases available. */ }
  if (current !== releaseInspectionRequest) return
  const localAlbums = library.findArtist(d.name)?.albums || []
  const inspected = await inspectDiscography(d.albums || [], localAlbums, API)
  if (current === releaseInspectionRequest) inspectedReleases.value = inspected
  } finally { if (current === releaseInspectionRequest) releasesLoading.value = false }
}, { immediate: true })
const releaseGroups = computed(() =>
  discographySections(inspectedReleases.value, [], {
    albums: t('library.albums'),
    singles: t('artist.singlesAndEps'),
  })
)

const filterOptions = computed(() =>
  // The former chips as one button-styled select in the hero action row.
  filters.value.map((item) => ({ value: item.id, label: `${item.label} (${item.count})` }))
)

// Only actions that matter for a resolved link page.
const heroMenu = computed(() => {
  const d = details.value
  if (!d) return []
  const lead = d.tracks?.[0]
  const artist = d.kind === 'artist' ? '' : lead?.album_artist || (lead?.artists || [])[0] || ''
  // Album/playlist/track pages from another source: open the matching
  // YouTube Music album (or the track for a single-song link).
  const ytmKind = d.kind === 'track' ? 'track' : d.kind === 'album' ? 'album' : ''
  const ytmItem = d.kind === 'track' ? lead : { name: d.name, artist }
  const albumItem = { name: d.name, artist, url: songProvider({ url: url.value }) === 'spotify' ? url.value : '' }
  const toastMissing = (key) => () => ui.toast(t(key), { kind: 'error' })
  const lookups = { spotify: API.spotifyLink, youtube: API.youtubeMusicLink }
  return [
    // Every album page, whatever the link's source: find it on both services.
    ...(d.kind === 'album'
      ? [
          {
            label: t('link.findSpotify'), icon: 'spotify',
            action: () => openAlbumOn('spotify', albumItem, { lookups, onMissing: toastMissing('link.notOnSpotify') }),
          },
          {
            label: t('link.findYoutube'), icon: 'youtube-music',
            action: () => openAlbumOn('youtube', { ...albumItem, url: songProvider({ url: url.value }) === 'youtube' ? url.value : '' }, { lookups, onMissing: toastMissing('link.notOnYoutubeMusic') }),
          },
        ]
      : [
          {
            label: sourceLabel.value, icon: sourceIcon.value,
            action: () => window.open(url.value, '_blank', 'noopener'),
          },
          {
            label: t('link.openYoutube'), icon: 'youtube-music',
            hidden: songProvider({ url: url.value }) === 'youtube' || !ytmKind || !ytmItem,
            action: () => openYouTubeMusic(ytmItem, ytmKind, {
              lookup: API.youtubeMusicLink,
              onMissing: toastMissing('link.notOnYoutubeMusic'),
            }),
          },
        ]),
    {
      label: t('monitor.copyLink'), icon: 'copy',
      action: async () => {
        try {
          await navigator.clipboard.writeText(url.value)
          ui.toast(t('monitor.linkCopied'))
        } catch {
          ui.toast(t('toast.actionFailed'), { kind: 'error' })
        }
      },
    },
  ]
})

// Reuse the menu's direct resolvers: no search links or duplicate lookup logic.
const providerActions = computed(() => [{
  label: sourceLabel.value, icon: sourceIcon.value,
  action: () => window.open(url.value, '_blank', 'noopener'),
}])

// The primary button downloads the ticked tracks while any are ticked,
// then clears the ticks.
async function downloadSelection() {
  await download(selectedSongs.value)
  selected.value = new Set()
}

const visibleRows = computed(() =>
  filter.value === 'all'
    ? rows.value
    : rows.value.filter((row) => row.status === filter.value)
)

const selectedSongs = computed(() =>
  rows.value.filter((row) => selected.value.has(row.key)).map((row) => row.song)
)

function toggle(key) {
  const next = new Set(selected.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  selected.value = next
}

function downloadAlbum() {
  if (!albumTargetLoaded.value || submitting.value) return
  return albumComplete.value
    ? download(details.value.tracks, 'redownload')
    : download(missingAlbumSongs.value, 'missing')
}

// The album folder already holds some, not all, of the album's tracks.
const albumPartlyOwned = computed(() =>
  albumTargetLoaded.value &&
  missingAlbumSongs.value.length > 0 &&
  missingAlbumSongs.value.length < (albumSongs.value?.length || 0)
)

const albumButtonLabel = computed(() =>
  downloadReleaseLabel(details.value?.release_type, t,
    albumComplete.value ? 'complete' : albumPartlyOwned.value ? 'partial' : 'none')
)

// Physical presence is independent of the canonical download destination.
const releaseInLibrary = computed(() => details.value?.kind === 'album' &&
  !!details.value.tracks.length && (albumComplete.value ||
    details.value.tracks.every(song => locationFor(song)?.downloaded === true)))
function playRelease() {
  if (!releaseInLibrary.value) return
  if (linkPlaying.value) return player.pause()
  return startRowSong(details.value.tracks[0], {
    queue: playQueue.value, context: playContext.value, songs: details.value.tracks,
  })
}

// The album on this link is what is playing (a downloaded copy of it).
const linkPlaying = computed(() =>
  details.value?.kind === 'album' && player.isPlaying.value &&
  isPlayingRelease({ name: details.value.name, artist: details.value.tracks?.[0]?.album_artist || (details.value.tracks?.[0]?.artists || [])[0] }, player.currentTrack.value)
)

// After the artist, as on the library album page: "16 tracks · 1 h 1 min".
const heroFacts = computed(() => {
  const d = details.value
  if (!d) return []
  if (d.tracks.length) {
    return [t('common.tracks', { count: d.tracks.length }), lengthLabel.value].filter(Boolean)
  }
  return d.albums.length ? [t('link.releases', { count: d.albums.length })] : []
})

async function download(songs, mode) {
  const downloadMode = mode || (songs === details.value.tracks ? 'redownload' : 'missing')
  if (!songs.length) return
  submitting.value = true
  try {
    const isPlaylist = details.value.kind === 'playlist'
    // Keep the playlist's own order for the M3U even when only some
    // tracks are sent.
    const withOrder = songs.map((song) => ({
      ...song,
      downtify_track_order: details.value.tracks.indexOf(song),
    }))
    const count = await dm.fromSongs(withOrder, {
      playlistUrl: isPlaylist ? url.value : '',
      ...(details.value.kind === 'album' ? { destination: 'album' } : {}),
      downloadMode,
    })
    selected.value = new Set()
    ui.toast(t('toast.queuedTracks', { count, name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.queue'),
        run: () => router.push({ name: 'Queue' }),
      },
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    submitting.value = false
  }
}

async function watch() {
  watching.value = true
  try {
    await monitorAPI.addMonitoredPlaylist(url.value, 360)
    ui.toast(t('toast.watching', { name: details.value.name }), {
      kind: 'success',
      action: {
        label: t('nav.monitor'),
        run: () =>
          router.push({
            name: 'Monitor',
            params: {
              tab: details.value.kind === 'artist' ? 'artists' : 'playlists',
            },
          }),
      },
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), {
      kind: 'error',
    })
  } finally {
    watching.value = false
  }
}
</script>
