<template>
  <ul class="flex flex-col">
    <li v-for="item in items" :key="item.name">
      <RouterLink
        :to="{ name: 'Label', params: { label: item.name } }"
        class="flex min-w-0 flex-col gap-0.5 rounded-panel px-3 py-3 hover:bg-raised"
        data-label-match
      >
        <span class="truncate text-[15px] font-semibold">{{ item.name }}</span>
        <span
          v-if="item.artists && item.artists.length"
          class="truncate text-[13px] text-muted"
        >
          {{ item.artists.join(', ') }}
        </span>
      </RouterLink>
    </li>
  </ul>
</template>

<script setup>
defineProps({ items: { type: Array, required: true } })
</script>
