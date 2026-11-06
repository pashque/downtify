<template>
  <UiMenu :items="items" :label="t('common.more')" size="sm" />
</template>
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import UiMenu from '../ui/UiMenu.vue'
import { songProvider, openYouTubeMusic } from '/src/lib/sourceLinks'
import API from '/src/model/api'
import { useUi } from '/src/model/ui'
import { useI18n } from '/src/i18n'
const props = defineProps({ song: { type: Object, required: true } })
const router = useRouter()
const { t } = useI18n()
const ui = useUi()
const open = (url) => window.open(url, '_blank', 'noopener')
const LABELS = { spotify: 'link.openSpotify', deezer: 'link.openDeezer', youtube: 'link.openYoutube' }
const items = computed(() => {
  const provider = songProvider(props.song)
  const url = String(props.song.url || '')
  return [{
    // The song's own page, named after where it really goes.
    label: t(LABELS[provider] || 'search.openSource'),
    icon: ({ spotify: 'spotify', youtube: 'youtube-music', deezer: 'deezer' })[provider] || 'arrow-up-right',
    hidden: !/^https?:\/\//.test(url),
    action: () => open(url),
  }, {
    label: t('link.openYoutube'), icon: 'youtube-music',
    hidden: provider === 'youtube' || !props.song.name,
    // The real YouTube Music track, never a search page.
    action: () => openYouTubeMusic(props.song, 'track', {
      lookup: API.youtubeMusicLink,
      onMissing: () => ui.toast(t('link.notOnYoutubeMusic'), { kind: 'error' }),
    }),
  }, {
    label: t('similar.findSimilar'), icon: 'wand',
    hidden: !((props.song.artists || [])[0] || props.song.artist) || !props.song.name,
    action: () => router.push({ name: 'Similar', query: { artist: (props.song.artists || [])[0] || props.song.artist, track: props.song.name } }),
  }]
})
</script>
