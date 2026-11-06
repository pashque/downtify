<template>
  <div
    v-if="track"
    class="flex h-full min-h-0 flex-col gap-5 overflow-y-auto px-2"
  >
    <dl class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-3 text-sm">
      <template v-for="row in rows" :key="row.label">
        <dt class="text-white/50">{{ row.label }}</dt>
        <dd class="min-w-0 break-words text-white/90">
          <ArtistCredits v-if="row.kind === 'artist'" :artists="track.artists" :artist="track.artist" />
          <template v-else>{{ row.value }}</template>
        </dd>
      </template>
    </dl>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import ArtistCredits from '../library/ArtistCredits.vue'
import { usePlayer } from '/src/model/player'
// Static on purpose: a dynamic import of the API client breaks the built
// app on load (see model/streamResolve.js).
import API from '/src/model/api'
import { formatBytes, formatDuration, timeAgo } from '/src/lib/format'
import { useI18n } from '/src/i18n'

const player = usePlayer()
const { t, locale } = useI18n()
const track = computed(() => player.currentTrack.value)
const audioDetails = ref({})
// Only the mounted Details panel probes, never the library/queue render.
// Scalar sources avoid repeated requests when playback updates the row object.
onMounted(() => watch(
  [() => track.value?.stream || track.value?.isStream || track.value?.podcast ? '' : track.value?.file,
    () => track.value?.size, () => track.value?.added],
  async ([file], _old, onCleanup) => {
    let active = true
    onCleanup(() => { active = false })
    audioDetails.value = {}
    if (!file || file.startsWith('stream:')) return
    try {
      const details = await API.getAudioDetails(file)
      if (active) audioDetails.value = details || {}
    } catch {
      // Missing, hidden and unsupported files must never inherit old facts.
    }
  },
  { immediate: true },
))

// One line: "MP3 · 320 kbps · 48 kHz · Joint stereo". Only measured
// facts; anything the file doesn't report is left out.
function audioSummary(format, audio) {
  const container = String(format || '').toUpperCase()
  const codec = String(audio.codec || '').toUpperCase()
  const name = container && codec && codec !== container ? `${container} (${codec})` : container || codec
  const parts = [name]
  if (audio.bitrate > 0) parts.push(`${Math.round(audio.bitrate / 1000)} kbps`)
  if (audio.lossless && audio.bit_depth > 0) parts.push(`${audio.bit_depth}-bit`)
  if (audio.sample_rate > 0) parts.push(`${Number((audio.sample_rate / 1000).toFixed(1))} kHz`)
  // Mode only when the stream states it; 2 lossless channels are plain
  // stereo, but a lossy codec's 2 channels may be joint, so just count them.
  if (audio.channel_mode) parts.push(audio.channel_mode)
  else if (audio.channels === 1) parts.push('Mono')
  else if (audio.channels === 2 && audio.lossless) parts.push('Stereo')
  else if (audio.channels > 0) parts.push(`${audio.channels} ch`)
  return parts.filter(Boolean).join(' · ')
}

const rows = computed(() => {
  const tr = track.value
  if (!tr) return []
  const audio = audioDetails.value
  return [
    { label: t('track.title'), value: tr.title },
    { label: t('track.artist'), value: tr.artist || tr.artists?.join(', '), kind: 'artist' },
    { label: t('track.album'), value: tr.album },
    { label: t('track.trackNumber'), value: tr.trackNumber || '' },
    { label: t('track.year'), value: tr.year },
    {
      label: t('track.length'),
      value: tr.duration ? formatDuration(tr.duration) : '',
    },
    { label: t('track.format'), value: audioSummary(tr.format, audio) },
    { label: t('track.size'), value: tr.size ? formatBytes(tr.size) : '' },
    {
      label: t('track.added'),
      value: tr.added ? timeAgo(tr.added, locale.value) : '',
    },
    { label: t('track.file'), value: tr.file },
  ].filter((row) => row.value !== '' && row.value !== undefined)
})
</script>
