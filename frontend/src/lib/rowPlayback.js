// Controls and navigation retain their own action; only plain row space plays.
export function rowPlaybackClick(event) {
  if (!event || event.defaultPrevented || event.button > 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return false
  if (event.target?.closest?.('a, button, input, select, textarea, label, [role="button"], [role="checkbox"], [role="slider"], [contenteditable="true"]')) return false
  if (typeof window !== 'undefined' && window.getSelection?.()?.toString()) return false
  return true
}
