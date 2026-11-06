import { beforeEach, expect, it, vi } from 'vitest'
const http = vi.hoisted(() => ({ get:vi.fn(async()=>({data:{}})), post:vi.fn(async()=>({data:{}})), interceptors:{response:{use:vi.fn()}} }))
vi.mock('axios',()=>({default:{create:()=>http}}))
vi.mock('/src/config.js',()=>({default:{PROTOCOL:'http:',BACKEND:'localhost',PORT:'1',BASEURL:''}}))
vi.hoisted(() => {
  vi.stubGlobal('WebSocket', undefined)
  vi.stubGlobal('localStorage', { getItem:()=>null, setItem:()=>{} })
})
import API from '../model/api'
beforeEach(()=>{http.get.mockClear();http.post.mockClear()})
it('discovers choices for the exact Spotify album ID', async () => {
 await API.getSpotifyAlbumEditions('A'.repeat(22))
 expect(http.get).toHaveBeenCalledWith('/api/spotify/album/editions', {params:{album_id:'A'.repeat(22)}})
})
it('uses the exact local album source endpoint without a guessed provider URL',async()=>{
 await API.getLibraryAlbumSource('Drake','Demo')
 expect(http.get).toHaveBeenCalledWith('/api/library/album/source',{params:{artist:'Drake',title:'Demo'}})
})
it('sends all single-song hints intact, including forced album or explicit origin playlist context',async()=>{
 const song={url:'https://source/track',name:'One',downtify_destination:'album',downtify_download_mode:'missing'}
 await API.download(song)
 expect(http.post).toHaveBeenCalledWith('/api/download/url',song,{params:{url:song.url,client_id:expect.any(String)}})
 const origin={url:song.url,downtify_playlist_name:'Chosen',downtify_playlist_url:'https://source/playlist'}
 await API.download(origin)
 expect(http.post.mock.calls[1][1]).toEqual(origin)
 expect(http.post.mock.calls[1][1]).not.toHaveProperty('downtify_destination')
})
