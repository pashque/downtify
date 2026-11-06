<template>
  <header
    class="relative isolate flex flex-col justify-end overflow-hidden"
    :class="banner ? 'min-h-[300px] sm:min-h-[380px] lg:min-h-[440px]' : ''"
  >
    <img
      v-if="banner"
      :src="banner"
      alt=""
      class="absolute inset-0 -z-20 size-full object-cover object-[center_20%]"
    />
    <div
      class="absolute inset-0 -z-10"
      :class="banner ? '' : 'opacity-70'"
      :style="{
        background: banner
          ? 'linear-gradient(180deg, rgba(11,12,14,0.05) 0%, rgba(11,12,14,0.55) 65%, rgba(11,12,14,0.92) 100%)'
          : `linear-gradient(180deg, ${tint} 0%, transparent 100%)`,
      }"
      aria-hidden="true"
    />
    <span
      v-if="loading && banner"
      data-hero-loading
      role="status"
      :aria-label="t(loadingLabel)"
      :title="t(loadingLabel)"
      class="pointer-events-none absolute right-4 bottom-4 z-10 flex size-10 items-center justify-center rounded-full bg-black/55 text-white/75 backdrop-blur"
    >
      <AppIcon name="refresh" :size="18" class="animate-spin" />
    </span>
    <button
      v-if="bannerEditable"
      type="button"
      :title="t('artistArt.editArtist')"
      :aria-label="t('artistArt.editArtist')"
      class="absolute top-4 right-4 z-10 flex size-10 items-center justify-center rounded-full border border-line-2 bg-black/55 text-white backdrop-blur transition-colors hover:bg-black/70"
      @click="$emit('edit-banner')"
    >
      <AppIcon name="pencil" :size="16" />
    </button>
    <!-- Phones: cover left, details right, buttons underneath. -->
    <div
      class="mr-auto flex max-w-[1680px] flex-col gap-6 px-4 pt-6 pb-6 sm:px-6 lg:flex-row lg:items-end lg:gap-8 lg:pt-10 lg:px-10"
      :class="banner ? '' : 'max-lg:grid max-lg:w-full max-lg:grid-cols-[120px_minmax(0,1fr)] max-lg:items-center max-lg:gap-x-4 max-lg:gap-y-4'"
      data-hero-layout
    >
      <div
        v-if="!banner"
        class="group/cover relative size-48 shrink-0 self-center max-lg:size-[120px] max-lg:self-auto lg:size-[232px]"
      >
        <CoverArt
          :src="cover"
          :fallback="coverFallback"
          :covers="covers"
          :name="name || title"
          :round="round"
          :icon="icon"
          :symbol="symbol"
          shadow
          :letter-size="96"
          :icon-size="64"
          rounded="rounded-[16px]"
          class="size-full shadow-[0_24px_60px_rgba(0,0,0,0.45)]"
        />
        <!-- The same "Playing" badge as the cards, on the page's own cover. -->
        <span
          v-if="playing"
          data-hero-playing
          class="pointer-events-none absolute top-3 left-3 flex h-6 items-center gap-1.5 rounded-full bg-black/55 px-2 text-[11px] font-semibold text-white backdrop-blur"
        >
          <EqBars :size="10" />{{ t('player.playing') }}
        </span>
        <!-- While the full tracklist loads: grey spinning arrows in the
             corner where the cards show their play button. -->
        <span
          v-if="loading && !banner"
          data-hero-loading
          role="status"
          :aria-label="t(loadingLabel)"
          :title="t(loadingLabel)"
          class="pointer-events-none absolute right-3 bottom-3 flex size-10 items-center justify-center rounded-full bg-black/55 text-white/75 backdrop-blur max-lg:right-2 max-lg:bottom-2 max-lg:size-8"
        >
          <AppIcon name="refresh" :size="18" class="animate-spin" />
        </span>
        <button
          v-if="photoEditable"
          type="button"
          class="absolute inset-0 flex items-center justify-center rounded-[16px] bg-black/0 text-white opacity-0 transition-all group-hover/cover:bg-black/45 group-hover/cover:opacity-100"
          :class="round ? 'rounded-full' : ''"
          @click="$emit('edit-photo')"
        >
          <span class="flex items-center gap-2 text-base font-semibold">
            <AppIcon name="pencil" :size="17" />{{ t('artistArt.editPhoto') }}
          </span>
        </button>
      </div>
      <div
        class="flex min-w-0 flex-col gap-3"
        :class="banner ? 'max-lg:items-center max-lg:text-center' : 'max-lg:contents'"
      >
        <div class="flex min-w-0 flex-col gap-3 max-lg:gap-1.5" :class="banner ? 'max-lg:items-center' : ''">
        <span
          class="eyebrow"
          :class="banner ? '!text-white/70' : '!text-fg-3'"
          >{{ kicker }}</span
        >
        <h1
          class="text-display line-clamp-2 text-4xl leading-[1.05] font-bold text-balance break-words max-lg:text-[26px] lg:text-5xl xl:text-[64px]"
          :class="banner ? 'text-white' : 'text-fg'"
        >
          {{ title }}
        </h1>
        <p class="text-[15px]" :class="banner ? 'text-white/75' : 'text-fg-3'">
          <slot name="subtitle" />
        </p>
        </div>
        <div
          class="hero-actions mt-3 flex min-h-14 flex-wrap items-center gap-2.5"
          :class="banner ? 'max-lg:justify-center' : 'max-lg:col-span-2 max-lg:mt-0 max-lg:justify-start'"
        >
          <slot name="actions" />
        </div>
        <div v-if="$slots.status" class="max-lg:col-span-2">
          <slot name="status" />
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '../ui/AppIcon.vue'
import CoverArt from '../ui/CoverArt.vue'
import EqBars from '../ui/EqBars.vue'
import { hueFor } from '/src/lib/format'
import { useCoverPalette } from '/src/model/coverPalette'
import { useI18n } from '/src/i18n'

const props = defineProps({
  title: { type: String, required: true },
  kicker: { type: String, default: '' },
  // Spinning arrows on the cover while more of the release loads.
  loading: { type: Boolean, default: false },
  loadingLabel: { type: String, default: 'album.loadingTracks' },
  name: { type: String, default: '' },
  cover: { type: String, default: '' },
  // Shown when `cover` fails to load (see CoverArt) - for a `cover` that
  // may not exist, like an artist photo from the proxy.
  coverFallback: { type: String, default: '' },
  covers: { type: Array, default: () => [] },
  icon: { type: String, default: 'disc' },
  symbol: { type: Boolean, default: false },
  round: { type: Boolean, default: false },
  // Optional background photo (artist page only - see ArtistView) and
  // whether each hover "edit photo/banner" affordance is shown at all -
  // each mirrors its own settings toggle independently. When a banner
  // is set, the round photo (and its own edit affordance) is hidden
  // entirely to de-clutter the header - ArtistArtModal's "Profile" tab
  // is still reachable from the banner's edit button.
  banner: { type: String, default: '' },
  photoEditable: { type: Boolean, default: false },
  bannerEditable: { type: Boolean, default: false },
  // This album/playlist is what is playing now.
  playing: { type: Boolean, default: false },
})
defineEmits(['edit-photo', 'edit-banner'])

const { t } = useI18n()

// Share the player's cached artwork extraction; playlist mosaics use their
// first visible cover. Missing/unreadable artwork keeps the stable name tint.
const paletteTrack = computed(() => {
  const cover = props.banner || (props.symbol ? '' : props.cover || props.covers.find(Boolean) || props.coverFallback)
  return { hasCover: !!cover, cover }
})
const palette = useCoverPalette(paletteTrack)
const tint = computed(
  () => palette.value?.primary
    ? `${palette.value.primary}8c`
    : `oklch(0.45 0.08 ${hueFor(props.name || props.title)} / 0.55)`
)
</script>
