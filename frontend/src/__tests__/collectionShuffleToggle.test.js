import {expect,it} from 'vitest'
import {readFileSync} from 'node:fs'
import {parse} from '@vue/compiler-sfc'
import {baseParse} from '@vue/compiler-dom'
it.each(['AlbumView','PlaylistView'])('%s shuffle changes mode without starting a collection',name=>{
 const text=readFileSync(new URL(`../views/${name}.vue`,import.meta.url),'utf8')
 const root=baseParse(parse(text).descriptor.template.content)
 let shuffle
 function visit(n){if(n.tag==='UiIconButton' && n.props.some(p=>p.name==='icon'&&p.value?.content==='shuffle'))shuffle=n;for(const c of n.children||[])visit(c)}
 visit(root)
 const bound=(directive,arg)=>shuffle.props.find(p=>p.name===directive&&p.arg?.content===arg)?.exp?.content
 expect(bound('on','click')).toBe('player.toggleShuffle()')
 expect(bound('bind','active')).toBe('player.shuffle.value')
 expect(shuffle.props.some(p=>p.name==='toggle')).toBe(true)
})
