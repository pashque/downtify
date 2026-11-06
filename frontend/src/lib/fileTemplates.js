export const FLAT_OUTPUT = '{artists} - {title}.{output-ext}'
export const LIBRARY_OUTPUT =
  '{albumartist}/{albumartist} - {album} ({year})/{tracknumber}. {artists} - {title}.{output-ext}'

export function defaultOutput(settings) {
  return settings.folder_structure === true ? LIBRARY_OUTPUT : FLAT_OUTPUT
}
