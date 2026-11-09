<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <template v-if="!query">
      <PageHeader :title="t('search.title')" :subtitle="t('search.subtitle')" />
      <div class="grid gap-4 md:grid-cols-3">
        <div
          v-for="tip in tips"
          :key="tip.title"
          class="flex flex-col gap-2 rounded-panel border border-line-2 bg-surface p-5"
        >
          <span
            class="flex size-10 items-center justify-center rounded-[10px]"
            :class="tip.tone"
          >
            <AppIcon :name="tip.icon" :size="20" />
          </span>
          <p class="mt-1 text-[15px] font-semibold">{{ tip.title }}</p>
          <p class="text-[13px] text-pretty text-muted">{{ tip.body }}</p>
        </div>
      </div>
      <section v-if="recent.length" class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <h2 class="text-display text-lg font-semibold">
            {{ t('search.recent') }}
          </h2>
          <button
            type="button"
            class="text-[13px] font-semibold text-muted hover:text-fg"
            @click="recent = []"
          >
            {{ t('common.clear') }}
          </button>
        </div>
        <div class="flex flex-wrap gap-2">
          <RouterLink
            v-for="term in recent"
            :key="term"
            :to="{ name: 'Search', params: { query: term } }"
            class="flex h-9 items-center gap-2 rounded-full bg-surface-2 px-3.5 text-sm text-fg-3 hover:bg-raised"
          >
            <AppIcon name="clock" :size="14" class="text-faint" />{{ term }}
          </RouterLink>
        </div>
      </section>
    </template>

    <LabelMatches v-else-if="labelQuery" :query="labelQuery" />

    <template v-else>
      <div class="flex flex-col gap-4">
        <PageHeader
          :title="t('search.resultsFor', { query })"
          :subtitle="search.loading.value ? t('search.searching') : ''"
        />
        <UiChips v-model="filter" :items="filters" />
      </div>

      <div v-if="search.loading.value" class="flex flex-col gap-2">
        <div v-for="n in 6" :key="n" class="flex h-16 items-center gap-3 px-3">
          <UiSkeleton class="size-11 !rounded-[8px]" />
          <div class="flex flex-1 flex-col gap-2">
            <UiSkeleton class="h-3.5 w-1/3" />
            <UiSkeleton class="h-3 w-1/5" />
          </div>
        </div>
      </div>

      <UiEmpty
        v-else-if="search.error.value && !search.songs.value.length"
        icon="alert"
        :title="t('search.failed')"
        :body="search.error.value"
      >
        <UiButton icon="refresh" @click="search.searchFor(query)">{{
          t('common.retry')
        }}</UiButton>
      </UiEmpty>

      <UiEmpty
        v-else-if="!hasResults"
        icon="search"
        :title="t('search.noResults')"
        :body="t('search.noResultsHint')"
      />

      <template v-else>
        <section
          v-if="show('songs') && search.songs.value.length"
          class="flex flex-col gap-3"
        >
          <h2
            v-if="filter === 'all'"
            class="text-display text-xl font-semibold"
          >
            {{ t('search.songs') }}
          </h2>
          <div class="-mx-3 flex flex-col">
            <TrackDownPlayHeader hide-album />
            <SongRow
              v-for="(song, i) in visibleSongs"
              :key="song.song_id || song.url"
              :song="song"
              :location="locationFor(song)"
              :index="i"
              :songs="visibleSongs"
            />
          </div>
          <button
            v-if="
              filter === 'all' &&
              search.songs.value.length > visibleSongs.length
            "
            type="button"
            class="self-start text-[13px] font-semibold text-muted hover:text-fg"
            @click="filter = 'songs'"
          >
            {{ t('search.showAllSongs', { count: search.songs.value.length }) }}
          </button>
        </section>

        <section
          v-if="show('artists') && search.artists.value.length"
          class="flex flex-col gap-4"
        >
          <h2
            v-if="filter === 'all'"
            class="text-display text-xl font-semibold"
          >
            {{ t('search.artists') }}
          </h2>
          <div class="tile-grid">
            <ReleaseCard
              v-for="artist in visibleArtists"
              :key="artist.artist_id || artist.url"
              :release="artist"
              round
            />
          </div>
        </section>

        <section
          v-if="show('albums') && search.albums.value.length"
          class="flex flex-col gap-4"
        >
          <h2
            v-if="filter === 'all'"
            class="text-display text-xl font-semibold"
          >
            {{ t('search.albums') }}
          </h2>
          <div class="tile-grid">
            <ReleaseCard
              v-for="album in visibleAlbums"
              :key="album.album_id || album.url"
              :release="album"
            />
          </div>
        </section>

        <section
          v-if="show('labels') && labelFinder.labels.value.length"
          class="flex flex-col gap-2"
        >
          <h2
            v-if="filter === 'all'"
            class="text-display text-xl font-semibold"
          >
            {{ t('labels.heading') }}
          </h2>
          <LabelList :items="visibleLabels" class="-mx-3" />
          <button
            v-if="
              filter === 'all' &&
              labelFinder.labels.value.length > visibleLabels.length
            "
            type="button"
            class="self-start text-[13px] font-semibold text-muted hover:text-fg"
            @click="filter = 'labels'"
          >
            {{
              t('labels.showAll', { count: labelFinder.labels.value.length })
            }}
          </button>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup>
import { useLibraryLocations } from '/src/model/libraryLocations'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useLocalStorage } from '@vueuse/core'
import AppIcon from '/src/components/ui/AppIcon.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiChips from '/src/components/ui/UiChips.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import LabelList from '/src/components/search/LabelList.vue'
import LabelMatches from '/src/components/search/LabelMatches.vue'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import TrackDownPlayHeader from '/src/components/library/TrackDownPlayHeader.vue'
import SongRow from '/src/components/search/SongRow.vue'
import { useSearch } from '/src/model/search'
import { useLibrary } from '/src/model/library'
import api from '/src/model/api'
import { labelFromQuery, useLabelFinder } from '/src/lib/labels'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const search = useSearch()
const library = useLibrary()
const { locationFor } = useLibraryLocations(computed(() => search.songs.value))
const filter = ref('all')
const recent = useLocalStorage('downtify-recent-searches', [])

watch(
  () => search.songs.value,
  (songs) => library.lookupSongs(songs)
)

const query = computed(() => String(route.params.query || '').trim())
// Labels that match ordinary search text (light lookup, no spelling fixes).
const labelFinder = useLabelFinder(
  async (text) => (await api.labelFind(text, { fuzzy: false })).data
)
const labelQuery = computed(() => labelFromQuery(query.value))

watch(
  query,
  (value) => {
    filter.value = 'all'
    if (!value) return
    if (labelFromQuery(value)) return
    if (value.length >= 3) labelFinder.load(value)
    recent.value = [
      value,
      ...recent.value.filter((term) => term !== value),
    ].slice(0, 10)
    if (value !== search.query.value || !search.songs.value.length) {
      search.searchFor(value)
    }
  },
  { immediate: true }
)

const filters = computed(() => [
  { id: 'all', label: t('search.all') },
  { id: 'songs', label: t('search.songs'), count: search.songs.value.length },
  {
    id: 'artists',
    label: t('search.artists'),
    count: search.artists.value.length,
  },
  {
    id: 'albums',
    label: t('search.albums'),
    count: search.albums.value.length,
  },
  ...(labelFinder.labels.value.length
    ? [
        {
          id: 'labels',
          label: t('labels.heading'),
          count: labelFinder.labels.value.length,
        },
      ]
    : []),
])

function show(section) {
  return filter.value === 'all' || filter.value === section
}

const hasResults = computed(
  () =>
    labelFinder.labels.value.length ||
    search.songs.value.length ||
    search.albums.value.length ||
    search.artists.value.length
)

// In "All" only close matches are previewed; the Labels chip lists the rest.
const visibleLabels = computed(() =>
  filter.value === 'all'
    ? labelFinder.labels.value.filter((item) => item.score >= 0.9).slice(0, 3)
    : labelFinder.labels.value
)

const visibleSongs = computed(() =>
  filter.value === 'all' ? search.songs.value.slice(0, 8) : search.songs.value
)
const visibleAlbums = computed(() =>
  filter.value === 'all' ? search.albums.value.slice(0, 6) : search.albums.value
)
const visibleArtists = computed(() =>
  filter.value === 'all'
    ? search.artists.value.slice(0, 6)
    : search.artists.value
)

const tips = computed(() => [
  {
    icon: 'search',
    tone: 'bg-accent/12 text-accent',
    title: t('search.tipSearchTitle'),
    body: t('search.tipSearchBody'),
  },
  {
    icon: 'spotify',
    tone: 'bg-spotify/12 text-spotify',
    title: t('search.tipSpotifyTitle'),
    body: t('search.tipSpotifyBody'),
  },
  {
    icon: 'youtube',
    tone: 'bg-src-ytm/12 text-src-ytm',
    title: t('search.tipYoutubeTitle'),
    body: t('search.tipYoutubeBody'),
  },
])
</script>
