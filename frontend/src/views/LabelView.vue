<template>
  <div
    class="mx-auto flex max-w-[1680px] flex-col gap-8 px-4 pt-6 sm:px-6 md:pt-8 lg:px-10"
  >
    <PageHeader :title="label" :subtitle="t('labels.subtitle')" />
    <p class="text-sm text-muted">{{ t('labels.limited') }}</p>
    <p
      v-if="state.scanning.value && state.year.value"
      class="text-sm text-muted"
      aria-live="polite"
      data-label-scanning
    >
      {{
        t('labels.scanning', {
          count: state.releases.value.length,
          year: String(state.year.value),
        })
      }}
    </p>
    <p
      v-else-if="!state.loading.value && state.complete.value"
      class="text-sm text-muted"
      data-label-complete
    >
      {{ t('labels.loaded', { count: state.releases.value.length }) }}
    </p>
    <div
      v-else-if="!state.loading.value && state.partial.value"
      class="flex flex-wrap items-center gap-3 text-sm text-muted"
      data-label-partial
    >
      <span>{{
        t('labels.partial', {
          count: state.releases.value.length,
          years: state.failedYears.value.join(', '),
        })
      }}</span>
      <UiButton variant="ghost" icon="refresh" @click="state.load(label)">{{
        t('common.retry')
      }}</UiButton>
    </div>
    <div
      v-if="state.loading.value"
      class="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 2xl:grid-cols-6"
      aria-live="polite"
      :aria-label="t('search.searching')"
    >
      <UiSkeleton v-for="n in 6" :key="n" class="aspect-square w-full" />
    </div>
    <UiEmpty
      v-else-if="state.error.value"
      icon="alert"
      :title="t('search.failed')"
      :body="state.error.value"
    >
      <UiButton icon="refresh" @click="state.load(label)">{{
        t('common.retry')
      }}</UiButton>
    </UiEmpty>
    <UiEmpty
      v-else-if="!state.releases.value.length"
      icon="search"
      :title="t('search.noResults')"
      :body="t('labels.empty')"
    />
    <section v-else class="flex flex-col gap-4">
      <h2 class="text-display text-xl font-semibold">
        {{ t('labels.releases') }}
      </h2>
      <div class="tile-grid">
        <ReleaseCard
          v-for="release in state.releases.value"
          :key="release.album_id"
          :release="release"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '/src/components/library/PageHeader.vue'
import ReleaseCard from '/src/components/search/ReleaseCard.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import api from '/src/model/api'
import { useLabelTimeline } from '/src/lib/labels'
import { useI18n } from '/src/i18n'

const { t } = useI18n()
const route = useRoute()
const label = computed(() => String(route.params.label || '').trim())
const state = useLabelTimeline(
  async (name, year) => (await api.labelReleases(name, year)).data
)
watch(label, (name) => state.load(name), { immediate: true })
onBeforeUnmount(() => state.stop())
</script>
