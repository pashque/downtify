// Where to scroll a list so its playing row shows, or null when it is
// already fully visible (then nothing moves). An off-screen row lands about
// a third of the way down, so the played tracks above stay in sight.
export function revealScrollTop({ scrollTop, viewHeight, rowTop, rowHeight, maxScroll }) {
  if (rowTop >= scrollTop && rowTop + rowHeight <= scrollTop + viewHeight) return null
  const target = Math.round(rowTop - viewHeight / 3)
  return Math.max(0, Math.min(Math.max(0, maxScroll), target))
}
