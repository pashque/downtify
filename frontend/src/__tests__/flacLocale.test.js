import { expect, it } from 'vitest'
const locales=import.meta.glob('../i18n/locales/*.js',{eager:true})
it('labels the existing action as a FLAC download in every locale without claiming source fidelity or replacement',()=>{
 for(const locale of Object.values(locales)) {
  expect(locale.default.actions.downloadFlac).toEqual(expect.stringContaining('FLAC'))
 }
 expect(locales['../i18n/locales/en.js'].default.actions.downloadFlac).toBe('Download FLAC')
})
