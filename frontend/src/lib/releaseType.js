// The hero kicker for a release: its real type (Single, EP, Compilation,
// Album) when the source says so; plain "Album" when nobody knows.
const TYPES = new Set(['album', 'single', 'ep', 'compilation'])

export function releaseKicker(type, t) {
  const kind = String(type || '').toLowerCase()
  return TYPES.has(kind) ? t(`album.kinds.${kind}`) : t('album.kicker')
}

export function effectiveReleaseType(sourceType, embeddedType) {
  const source = String(sourceType || '').toLowerCase()
  if (TYPES.has(source)) return source
  const embedded = String(embeddedType || '').toLowerCase()
  return TYPES.has(embedded) ? embedded : ''
}

/** Label by release type and completeness at the canonical album destination. */
export function downloadReleaseLabel(type, t, completeness = 'none') {
  const typeKey = String(type || '').toLowerCase()
  const kind = TYPES.has(typeKey) ? typeKey : 'album'
  const group = completeness === 'complete' ? 'downloadAgainKind'
    : completeness === 'partial' ? 'downloadFullKind' : 'downloadKind'
  return t(`album.${group}.${kind}`)
}
