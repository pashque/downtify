<template>
  <article class="tile group relative flex min-w-0 flex-col gap-2.5">
    <RouterLink :to="to" class="relative block" :aria-label="title">
      <CoverArt
        :thumb="300"
        :src="cover"
        :fallback="fallback"
        :covers="covers"
        :name="name || title"
        :round="round"
        :icon="icon"
        :symbol="symbol"
        shadow
        :letter-size="round ? 40 : 56"
        class="aspect-square w-full"
      >
        <span
          v-if="isPlaying"
          class="absolute top-2.5 left-2.5 flex h-6 items-center gap-1.5 rounded-full bg-black/55 px-2 text-[11px] font-semibold text-white backdrop-blur"
        >
          <EqBars :size="10" />{{ t('player.playing') }}
        </span>
        <span
          v-else-if="typeLabel"
          data-release-badge
          class="tile-badge absolute top-2.5 left-2.5 rounded-full bg-black/55 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur"
        >{{ typeLabel }}</span>
        <slot name="badge" />
        <span
          v-if="hiddenBy"
          class="absolute bottom-2.5 left-2.5 flex h-6 items-center gap-1.5 rounded-full bg-black/60 px-2 text-[11px] font-semibold text-white backdrop-blur"
          :title="t(`visibility.hiddenBy.${hiddenBy}`)"
        >
          <AppIcon name="eye-off" :size="12" />{{ t('visibility.hiddenShort') }}
        </span>
      </CoverArt>
    </RouterLink>
    <button
      v-if="playable"
      type="button"
      class="tile-play tile-action-glow absolute flex size-11 items-center justify-center rounded-full bg-accent text-on-accent transition-transform hover:scale-105"
      :class="round ? 'right-1 bottom-[4.25rem]' : 'right-3 bottom-[4.25rem]'"
      :aria-label="t('actions.playItem', { name: title })"
      @click="$emit('play')"
    >
      <AppIcon name="play" :size="16" />
    </button>
    <!-- Controls over the cover (e.g. a menu): outside the link, so a
    click on one doesn't also open the tile. -->
    <div v-if="$slots.overlay" class="absolute top-2 right-2">
      <slot name="overlay" />
    </div>
    <!-- Card text: artist links must not be nested inside the album link. -->
    <div class="flex min-w-0 flex-col gap-0.5" :class="round ? 'items-center text-center' : ''">
      <RouterLink :to="to" class="w-full truncate text-sm font-semibold text-fg">{{ title }}</RouterLink>
      <span class="w-full truncate text-[13px] text-muted">
        <template v-if="creditArtist">{{ subtitle.slice(0, subtitle.indexOf(creditArtist)) }}<ArtistCredits :artist="creditArtist" />{{ subtitle.slice(subtitle.indexOf(creditArtist) + creditArtist.length) }}</template>
        <RouterLink v-else :to="to">{{ subtitle }}</RouterLink>
      </span>
    </div>
  </article>
</template>

<script setup>
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import ArtistCredits from './ArtistCredits.vue'
import { useI18n } from '/src/i18n'
import { computed } from 'vue'
import { usePlayer } from '/src/model/player'
import { isPlayingTarget } from '/src/lib/nowPlaying'
import { releaseKicker } from '/src/lib/releaseType'

const props = defineProps({
  to: { type: [String, Object], required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  // null means not a release card; '' means a release of unknown type.
  releaseType: { type: String, default: null },
  artist: { type: String, default: '' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  // Shown when `cover` fails to load (see CoverArt).
  fallback: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  symbol: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  playing: { type: Boolean, default: false },
  playable: { type: Boolean, default: true },
  // Admins: the rule hiding this from users ('album', 'artist'), or ''.
  hiddenBy: { type: String, default: '' },
})
defineEmits(['play'])
const { t } = useI18n()
const player = usePlayer()
const typeLabel = computed(() => {
  if (props.round) return ''
  if (typeof props.to === 'object' && props.to.name === 'Playlist') return t('link.kind.playlist')
  return props.releaseType !== null ? releaseKicker(props.releaseType, t) : ''
})
const creditArtist = computed(() => {
  const artist = props.artist || (typeof props.to === 'object' && props.to.name === 'Album' ? String(props.to.query?.artist || '') : '')
  return artist && props.subtitle.includes(artist) ? artist : ''
})
// Every page's cards: badge the album, artist or playlist now playing.
const isPlaying = computed(() =>
  props.playing ||
  isPlayingTarget(props.to, player.currentTrack.value, player.context.value, props.title)
)
</script>
