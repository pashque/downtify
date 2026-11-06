<template>
  <FilenameTemplate
    v-model="settings.output"
    :default-template="defaultOutput(settings)"
    :format="settings.format"
  />
  <SettingRow
    :label="t('settings.folderStructure')"
    :description="t(settings.folder_structure === true ? 'settings.folderStructureOnHint' : 'settings.folderStructureOffHint')"
  >
    <UiSwitch
      :model-value="settings.folder_structure === true"
      :aria-label="t('settings.folderStructure')"
      @update:model-value="settings.folder_structure = $event"
    />
  </SettingRow>
  <SettingRow
    :label="t('settings.playlistUseLibrary')"
    :description="playlistHint"
  >
    <UiSwitch
      v-model="settings.playlist_use_library"
      :aria-label="t('settings.playlistUseLibrary')"
    />
  </SettingRow>
  <p v-if="settings.folder_structure == null" class="px-5 py-3 text-xs text-muted" role="status">
    {{ t('settings.legacyFoldersHint') }}
  </p>
</template>

<script setup>
import { computed } from 'vue'
import UiSwitch from '../ui/UiSwitch.vue'
import SettingRow from './SettingRow.vue'
import FilenameTemplate from './FilenameTemplate.vue'
import { defaultOutput } from '/src/lib/fileTemplates'
import { useI18n } from '/src/i18n'

const props = defineProps({ settings: { type: Object, required: true } })
const { t } = useI18n()
const playlistHint = computed(() => {
  if (props.settings.folder_structure === true) {
    return t(props.settings.playlist_use_library
      ? 'settings.playlistLibraryHint'
      : 'settings.playlistSeparateHint')
  }
  return t(props.settings.playlist_use_library
    ? 'settings.playlistFolderHint'
    : 'settings.playlistFlatHint')
})
</script>
