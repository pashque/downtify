<template>
  <LikeButton v-if="file" :file="file" />
</template>
<script setup>
// Heart for a source/search row once the same song exists in the library.
import { computed } from 'vue'
import LikeButton from '../player/LikeButton.vue'
import { useLibrary } from '/src/model/library'
const props = defineProps({ song: { type: Object, required: true } })
const library = useLibrary()
const file = computed(() => library.findTrack((props.song.artists || [])[0] || props.song.artist, props.song.name, props.song)?.file || '')
</script>
