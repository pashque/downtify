<template>
  <ul class="flex flex-col">
    <li v-for="item in items" :key="item.name">
      <RouterLink
        :to="{ name: 'Label', params: { label: item.name } }"
        class="flex items-center gap-3 rounded-panel px-3 py-2.5 hover:bg-raised"
        data-label-match
      >
        <CoverArt
          :src="item.image || ''"
          :name="item.name"
          icon="disc"
          :letter-size="20"
          class="size-12"
          data-label-image
        />
        <span class="flex min-w-0 flex-col gap-0.5">
          <span class="truncate text-[15px] font-semibold">{{
            item.name
          }}</span>
          <span
            v-if="item.artists && item.artists.length"
            class="truncate text-[13px] text-muted"
          >
            {{ item.artists.join(', ') }}
          </span>
        </span>
      </RouterLink>
    </li>
  </ul>
</template>

<script setup>
import CoverArt from '../ui/CoverArt.vue'

defineProps({ items: { type: Array, required: true } })
</script>
