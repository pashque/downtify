<template>
  <span class="flex min-w-0 flex-wrap items-center gap-1" @click.stop @dblclick.stop>
    <RouterLink v-for="album in albums" :key="`${album.artist}/${album.title}`"
      :to="{ name: 'Album', query: { artist: album.artist, title: album.title } }"
      data-location-kind="album" :title="`${album.artist} — ${album.title}`"
      class="max-w-full truncate rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-muted hover:bg-raised">
      {{ t('track.album') }}
    </RouterLink>
    <RouterLink v-for="playlist in playlists" :key="playlist.name"
      :to="{ name: 'Playlist', query: { name: playlist.name } }"
      data-location-kind="playlist" :title="playlist.name"
      class="max-w-full truncate rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-muted hover:bg-raised">
      {{ playlist.name }}
    </RouterLink>
  </span>
</template>
<script setup>
import { computed } from 'vue'
import { useI18n } from '/src/i18n'
const props = defineProps({ location: { type: Object, default: null }, contextKind: { type: String, default: '' } })
const { t } = useI18n()
const albums = computed(() => props.contextKind === 'album' ? [] : props.location?.albums || [])
const playlists = computed(() => props.contextKind === 'playlist' ? [] : props.location?.playlists || [])
</script>
