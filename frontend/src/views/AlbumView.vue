<template>
  <div>
    <DetailState
      :loaded="ready"
      :found="!!album"
      icon="disc"
      :missing="t('album.notFound')"
    >
      <CollectionHero
        :playing="isThisPlaying"
        :title="album.title"
        :kicker="[releaseKicker(effectiveType, t), album.year].filter(Boolean).join(' · ')"
        :loading="sourceLoading || targetLoading"
        :cover="album.cover"
        :name="album.title"
      >
        <template #kicker><AlbumLabelKicker :text="[releaseKicker(effectiveType, t), album.year].filter(Boolean).join(' · ')" :album-id="spotifyAlbumId(edition || sourceSongs?.[0]?.album_id)" :pending="sourceLoading" /></template>
        <template #subtitle>
          <RouterLink
            v-if="album.artist"
            :to="{ name: 'Artist', query: { name: album.artist } }"
            class="font-semibold text-fg hover:underline max-md:block"
            >{{ album.artist }}</RouterLink
          >
          <!-- Phones: the facts start on their own line under the artist. -->
          <span v-for="(part, i) in facts" :key="part" class="whitespace-nowrap"
            ><span :class="i === 0 && album.artist ? 'max-md:hidden' : ''"> · </span>{{ part }}</span
          >
        </template>
        <template #actions>
          <PlayButton
            :label="t('actions.playItem', { name: album.title })"
            :playing="isThisPlaying"
            @click="togglePlay"
          />
          <UiIconButton
            icon="shuffle"
            :label="t('actions.shuffle')"
            size="lg"
            round
            :active="player.shuffle.value"
            toggle
            @click="player.toggleShuffle()"
          />
          <UiButton
            variant="ghost"
            icon="queue"
            @click="actions.enqueue(albumQueue)"
          >
            {{ t('actions.addToQueue') }}
          </UiButton>
          <UiButton
            v-if="sourceSongs && targetLoaded && !albumComplete"
            variant="ghost"
            icon="download"
            :loading="submitting"
            :disabled="!targetLoaded"
            @click="downloadAlbum"
          >
            {{ albumButtonLabel }}
          </UiButton>
          <EditionMenu
            v-if="editionOptions.length > 1"
            :model-value="edition"
            :options="editionOptions"
            :label="t('library.tracks')"
            icon="disc"
            data-album-version
            @update:model-value="selectEdition"
          />
          <UiMenu :items="menu" :label="t('common.more')" size="lg" />
        </template>
      </CollectionHero>

      <section class="mx-auto max-w-[1680px] px-4 sm:px-6 lg:px-10">
        <TrackDownPlayList
          v-if="sourceSongs"
          :songs="sourceSongs"
          :queue="albumQueue"
          :context="context"
          hide-album
          @contextmenu="openRowMenu"
        >
          <template #heart="{ song }"><LikeButton v-if="localTrack(song)" :file="localTrack(song).file" /></template>
          <template #actions="{ song }">
            <span
              v-if="localTrack(song)"
              class="flex items-center justify-end"
              @click.stop
              @dblclick.stop
            >
              <UiMenu
                :ref="(el) => (rowMenus[song.song_id || song.url] = el)"
                :items="rowMenu(song)"
                :label="t('common.more')"
                size="sm"
              />
            </span>
            <SourceSongMenu v-else :song="song" />
          </template>
        </TrackDownPlayList>
        <TrackList
          v-else
          :tracks="albumQueue"
          :context="context"
          :show-album="false"
          :show-added="false"
          :show-cover="false"
          :link-artist="false"
          numbering="track"
          :hide-menu="['album']"
        />
      </section>

      <section
        v-if="moreByArtist.length"
        class="mx-auto mt-12 flex max-w-[1680px] flex-col gap-4 px-4 sm:px-6 lg:px-10"
      >
        <div class="flex items-baseline justify-between">
          <h2 class="text-display text-xl font-semibold">
            {{ t('album.moreBy', { artist: album.artist }) }}
          </h2>
          <RouterLink
            :to="{ name: 'Artist', query: { name: album.artist } }"
            class="text-[13px] font-semibold text-muted hover:text-fg"
            >{{ t('common.seeAll') }}</RouterLink
          >
        </div>
        <div
          class="tile-grid"
        >
          <MediaTile
            v-for="other in moreByArtist"
            :key="other.key"
            :to="{
              name: 'Album',
              query: { artist: other.artist, title: other.title },
            }"
            :title="other.title"
            :release-type="other.release_type || ''"
            :subtitle="other.year"
            :cover="other.cover"
            :name="other.title"
            @play="actions.play(other.tracks, 0, albumContext(other))"
          />
        </div>
      </section>
    </DetailState>
  </div>
</template>

<script setup>
import AlbumLabelKicker from '/src/components/library/AlbumLabelKicker.vue'
import { spotifyAlbumId } from '/src/lib/albumLabel'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UiButton from '/src/components/ui/UiButton.vue'
import UiIconButton from '/src/components/ui/UiIconButton.vue'
import UiMenu from '/src/components/ui/UiMenu.vue'
import EditionMenu from '/src/components/library/EditionMenu.vue'
import CollectionHero from '/src/components/library/CollectionHero.vue'
import DetailState from '/src/components/library/DetailState.vue'
import MediaTile from '/src/components/library/MediaTile.vue'
import PlayButton from '/src/components/library/PlayButton.vue'
import TrackList from '/src/components/library/TrackList.vue'
import TrackDownPlayList from '/src/components/library/TrackDownPlayList.vue'
import SourceSongMenu from '/src/components/library/SourceSongMenu.vue'
import LikeButton from '/src/components/player/LikeButton.vue'
import { useAlbumSource, useAlbumDestination, albumEditionOptions } from '/src/model/albumSource'
import { downloadReleaseLabel, effectiveReleaseType, releaseKicker } from '/src/lib/releaseType'
import { useDownloadManager } from '/src/model/download'
import { useUi } from '/src/model/ui'
import { useLibrary } from '/src/model/library'
import { usePlayer } from '/src/model/player'
import { usePlaylistActions } from '/src/model/playlistActions'
import { useTrackActions } from '/src/model/trackActions'
import { useVisibility } from '/src/model/visibility'
import { albumKey, dedupeAlbumTracks } from '/src/lib/library'
import { openAlbumOn } from '/src/lib/sourceLinks'
import { selectedAlbumMetadata } from '/src/lib/albumRouting'
import API from '/src/model/api'
import { formatBytes, splitLength } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const library = useLibrary()
const player = usePlayer()
const actions = useTrackActions()
const playlistActions = usePlaylistActions()
const visibility = useVisibility()

const ready = ref(false)
// The album as it plays: one copy of each song (the same song can sit in
// the album folder and in a playlist folder), preferring the album folder.
const albumQueue = computed(() => dedupeAlbumTracks(album.value?.tracks || []))
const { songs: sourceSongs, editions, edition, selectEdition, releaseType, loading: sourceLoading } = useAlbumSource(route)
const effectiveType = computed(() => effectiveReleaseType(releaseType.value, album.value?.release_type))
// Labels describe versions, never provider ID suffixes.
const editionOptions = computed(() => albumEditionOptions(editions.value, t))
const { missing: missingSongs, loaded: targetLoaded, loading: targetLoading } = useAlbumDestination(sourceSongs)
const albumComplete = computed(() => targetLoaded.value && !!sourceSongs.value?.length && !missingSongs.value.length)
const dm = useDownloadManager()
const ui = useUi()
const submitting = ref(false)

async function downloadAlbum() {
  if (!targetLoaded.value || !missingSongs.value.length || submitting.value) return
  submitting.value = true
  try {
    await dm.fromSongs(missingSongs.value, {
      destination: 'album',
      downloadMode: 'missing',
    })
  } catch (err) {
    ui.toast(err?.response?.data?.detail || t('toast.actionFailed'), { kind: 'error' })
  } finally {
    submitting.value = false
  }
}

function localTrack(song) {
  return library.findTrack((song.artists || [])[0] || song.artist, song.name, song)
}

// The album folder already holds some, not all, of the album's tracks.
const albumPartlyOwned = computed(() =>
  targetLoaded.value &&
  missingSongs.value.length > 0 &&
  missingSongs.value.length < (sourceSongs.value?.length || 0)
)
const albumButtonLabel = computed(() =>
  downloadReleaseLabel(effectiveType.value, t,
    albumPartlyOwned.value ? 'partial' : 'none')
)

const rowMenus = {}
function openRowMenu(event, song) {
  rowMenus[song.song_id || song.url]?.openAt(event)
}

function rowMenu(song) {
  const track = localTrack(song)
  if (!track) return []
  const items = actions.menuFor(track, {
    list: albumQueue.value,
    index: albumQueue.value.indexOf(track),
    context: context.value,
    hide: ['album'],
  })
  const addItems = playlistActions.addMenuItems([track])
  if (addItems.length) items.splice(3, 0, { divider: true }, ...addItems)
  return items
}

async function loadAlbum() {
  ready.value = false
  await library.loadArtistTracks(String(route.query.artist || ''))
  ready.value = true
}

onMounted(loadAlbum)
watch(
  [() => route.query.artist, () => route.query.title],
  () => loadAlbum()
)

const album = computed(() => selectedAlbumMetadata(
  library.findAlbum(
    String(route.query.artist || ''),
    String(route.query.title || '')
  ), sourceSongs.value?.[0]
))

function albumContext(item, preserveOrigin = false) {
  return {
    type: 'album',
    title: item.title,
    subtitle: item.artist,
    cover: item.cover,
    route: {
      name: 'Album',
      query: {
        artist: item.artist,
        title: item.title,
        ...(edition.value ? { edition: edition.value } : {}),
        ...(preserveOrigin && route.query.playlist ? { playlist: route.query.playlist } : {}),
        ...(preserveOrigin && route.query.playlistUrl ? { playlistUrl: route.query.playlistUrl } : {}),
      },
    },
  }
}

const context = computed(() => (album.value ? albumContext(album.value, true) : null))

const facts = computed(() => {
  const a = album.value
  const songs = sourceSongs.value
  const { hours, minutes } = splitLength(
    songs ? songs.reduce((sum, song) => sum + (song.duration || 0), 0) : a.duration
  )
  const formats = [...new Set(a.tracks.map((track) => track.format))].join(', ')
  return [
    t('common.tracks', { count: songs?.length || a.tracks.length }),
    hours
      ? t('common.lengthHours', { hours, minutes })
      : t('common.lengthMinutes', { minutes }),
    formats,
    formatBytes(a.size),
  ].filter(Boolean)
})

const isThisPlaying = computed(() => {
  const current = player.currentTrack.value
  return (
    player.isPlaying.value &&
    !!current &&
    albumKey(current.albumArtist, current.album) === album.value?.key
  )
})

function togglePlay() {
  if (isThisPlaying.value) player.pause()
  else actions.play(albumQueue.value, 0, context.value)
}

const moreByArtist = computed(() => {
  const artist = library.findArtist(album.value?.artist)
  if (!artist) return []
  return artist.albums
    .filter((other) => other.key !== album.value.key)
    .slice(0, 6)
})

// Admins can put the whole album in one of their playlists (or a new one).
const addToPlaylist = computed(() =>
  playlistActions.addMenuItems(album.value?.tracks || [])
)

const albumRef = computed(() => ({
  name: album.value?.title || '',
  artist: album.value?.artist || '',
  // The matched Spotify edition, when the full tracklist came from Spotify.
  url: editions.value.find((e) => e.id === edition.value)?.url || '',
}))
const findLookups = { spotify: API.spotifyLink, youtube: API.youtubeMusicLink }
const findOpts = (missing) => ({
  lookups: findLookups,
  onMissing: () => ui.toast(t(missing), { kind: 'error' }),
})

const menu = computed(() => [
  {
    label: t('actions.playNext'),
    icon: 'play-next',
    action: () => actions.playNext(albumQueue.value),
  },
  ...(addToPlaylist.value.length
    ? [{ divider: true }, ...addToPlaylist.value, { divider: true }]
    : []),
  {
    label: t('library.downloadZip'),
    icon: 'zip',
    action: () => actions.downloadZip(album.value.tracks),
  },
  // The same album on the streaming services (its exact page, not a search).
  {
    label: t('link.findSpotify'),
    icon: 'spotify',
    action: () => openAlbumOn('spotify', albumRef.value, findOpts('link.notOnSpotify')),
  },
  {
    label: t('link.findYoutube'),
    icon: 'youtube-music',
    action: () => openAlbumOn('youtube', albumRef.value, findOpts('link.notOnYoutubeMusic')),
  },
  ...(album.value ? visibility.albumMenu(album.value) : []),
  { divider: true },
  {
    label: t('album.delete'),
    icon: 'trash',
    danger: true,
    action: async () => {
      const deleted = await actions.remove(album.value.tracks)
      if (deleted.length)
        router.push({ name: 'Library', params: { tab: 'albums' } })
    },
  },
])
</script>
