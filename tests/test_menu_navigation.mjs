import {test} from 'node:test';
import assert from 'node:assert/strict';
import {MenuNavigation} from '../next-stage/menu-navigation.mjs';
function setup(hash=''){
 const host=new EventTarget(),calls=[],writes=[];let state='HOME';
 host.location={pathname:'/rythem_game/next-stage/',search:'?v=keep',hash};
 host.history={state:{existing:true},pushState(data,title,url){writes.push(['push',url]);host.location.hash=url.slice(url.indexOf('#'));},replaceState(data,title,url){writes.push(['replace',url]);host.location.hash=url.slice(url.indexOf('#'));}};
 const nav=new MenuNavigation({host,canNavigate:()=>state==='HOME',onChange:(...args)=>calls.push(args)});
 return {host,calls,writes,nav,setState:s=>state=s};
}
test('initial empty/unknown route replaces, direct gacha survives and query/path stay',()=>{
 for(const hash of ['','#/bad','#/gacha']){const x=setup(hash);x.nav.mount();assert.equal(x.nav.menuScreen,hash==='#/gacha'?'gacha':'library');assert.equal(x.writes.length,hash==='#/gacha'?0:1);if(x.writes.length)assert.deepEqual(x.writes[0],['replace','/rythem_game/next-stage/?v=keep#/library']);}
});
test('only changed menus push and duplicate mounting does not add handlers',()=>{
 const x=setup();x.nav.mount();x.nav.mount();x.nav.navigate('gacha');x.nav.navigate('gacha');assert.equal(x.calls.length,2);assert.equal(x.writes.filter(w=>w[0]==='push').length,1);
});
test('popstate + hashchange apply one route and never push from history',()=>{
 const x=setup();x.nav.mount();x.host.location.hash='#/gacha';x.host.dispatchEvent(new Event('popstate'));x.host.dispatchEvent(new Event('hashchange'));assert.equal(x.calls.length,2);assert.equal(x.writes.length,1);
 x.host.location.hash='#/library';x.host.dispatchEvent(new Event('popstate'));assert.equal(x.calls.length,3);
});
test('all non HOME states reject clicks/history without calling adapters',()=>{
 for(const state of ['LOADING','COUNTDOWN','PLAY','PAUSED','CLEAR','RESULT']){const x=setup();x.nav.mount();x.setState(state);assert.equal(x.nav.navigate('gacha'),false);x.host.location.hash='#/gacha';x.host.dispatchEvent(new Event('hashchange'));assert.equal(x.host.location.hash,'#/library');assert.equal(x.calls.length,1);}
});
test('rapid navigation is synchronous and final choice wins; invalid intent is ignored',()=>{
 const x=setup();x.nav.mount();for(let i=0;i<100;i++)x.nav.navigate(i%2?'library':'gacha');assert.equal(x.nav.menuScreen,'library');assert.equal(x.calls.at(-1)[0],'library');assert.equal(x.nav.navigate('<script>'),false);
});
test('teardown removes history listeners and rejects future actions',()=>{
 const x=setup();x.nav.mount();x.nav.destroy();x.host.location.hash='#/gacha';x.host.dispatchEvent(new Event('hashchange'));x.host.dispatchEvent(new Event('popstate'));assert.equal(x.nav.navigate('gacha'),false);assert.equal(x.calls.length,1);
});
test('game home replaces route and can refresh the adapter without extra history',()=>{
 const x=setup('#/gacha');x.nav.mount();x.nav.navigate('library',{replace:true,force:true,restore:false});assert.equal(x.writes[0][0],'replace');assert.equal(x.calls.at(-1)[2].restore,false);assert.equal(x.nav.menuScreen,'library');
});
