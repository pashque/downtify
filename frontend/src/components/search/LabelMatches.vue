<template>
  <section class="flex flex-col gap-4" data-label-matches>
    <PageHeader
      :title="t('labels.matchesTitle', { query })"
      :subtitle="
        finder.loading.value
          ? t('search.searching')
          : finder.fuzzy.value
            ? t('labels.matchesFuzzy')
            : t('labels.matchesHint')
      "
    />
    <div v-if="finder.loading.value" class="flex flex-col gap-2">
      <div v-for="n in 4" :key="n" class="flex h-14 items-center px-3">
        <UiSkeleton class="h-4 w-1/3" />
      </div>
    </div>
    <UiEmpty
      v-else-if="finder.error.value"
      icon="alert"
      :title="t('search.failed')"
      :body="finder.error.value"
    >
      <UiButton icon="refresh" @click="finder.load(query)">{{
        t('common.retry')
      }}</UiButton>
    </UiEmpty>
    <UiEmpty
      v-else-if="!finder.labels.value.length"
      icon="search"
      :title="t('search.noResults')"
      :body="t('labels.matchesEmpty')"
    />
    <LabelList v-else :items="finder.labels.value" />
  </section>
</template>

<script setup>
import { watch } from 'vue'
import LabelList from '/src/components/search/LabelList.vue'
import PageHeader from '/src/components/library/PageHeader.vue'
import UiButton from '/src/components/ui/UiButton.vue'
import UiEmpty from '/src/components/ui/UiEmpty.vue'
import UiSkeleton from '/src/components/ui/UiSkeleton.vue'
import api from '/src/model/api'
import { useLabelFinder } from '/src/lib/labels'
import { useI18n } from '/src/i18n'

const props = defineProps({ query: { type: String, required: true } })
const { t } = useI18n()
const finder = useLabelFinder(async (q) => (await api.labelFind(q)).data)
watch(
  () => props.query,
  (q) => finder.load(q),
  { immediate: true }
)
</script>
