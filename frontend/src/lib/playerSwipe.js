// Deliberate vertical gestures only; a tap/sideways swipe must not close.
export function dismissPlayerSwipe(start, end, mobile) {
  if (!mobile || !start || !end) return false
  const dy = end.y - start.y
  return dy >= 80 && Math.abs(end.x - start.x) < dy * 0.6
}
