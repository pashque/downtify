import { expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
const src=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8')
it('album card subtitle artists are independent links, not inside the album link',()=>{
  const s=src('components/library/MediaTile.vue')
  expect(s).toContain('<ArtistCredits')
  expect(s).toContain('creditArtist')
  expect(s.indexOf('</RouterLink>',s.indexOf('<!-- Card text'))).toBeLessThan(s.indexOf('<ArtistCredits'))
})
it('search/discovery release artist credits link separately from the release title',()=>{
  const s=src('components/search/ReleaseCard.vue')
  expect(s).toContain('<ArtistCredits :artists="release.artists" :artist="release.artist"')
})
it('artists not grouped in the Library resolve to their catalog artist page on click only',()=>{
  const s=src('views/ArtistView.vue')
  expect(s).toContain('API.getArtistSpotifyId(name)')
  expect(s).toContain("route.query.name !== name")
  expect(s).toContain("router.replace({ name: 'Link'")
})
it('Link and playlist native source rows link each artist',()=>{
  for(const file of ['views/LinkView.vue','views/PlaylistView.vue']) expect(src(file)).toContain('<ArtistCredits')
})
