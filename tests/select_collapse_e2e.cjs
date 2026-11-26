'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const js=fs.readFileSync('ytdl_manager/app-2.js','utf8');
const marker='/* YTDL_SELECT_COLLAPSE_V2 */';
assert.equal(js.split(marker).length,2);
const source=js.split(marker)[1];
function scenario({label='Select video',disabled=false,initial='old',next='new',isResult=true}){
 let callback,scheduled=[];
 const panel={open:true};const input={value:initial};
 const button={textContent:label,disabled};
 const results={addEventListener(type,fn,capture){assert.equal(type,'click');assert.equal(capture,true);callback=fn;},contains(x){return isResult&&x===button;}};
 const elements={'ytdl-search-panel':panel,'ys-results':results,'url':input};
 vm.runInNewContext(source,{document:{getElementById:id=>elements[id]},setTimeout:fn=>scheduled.push(fn)});
 callback({target:{closest:()=>button}});
 input.value=next;
 for(const fn of scheduled)fn();
 return {open:panel.open,callbacks:scheduled.length};
}
assert.equal(scenario({}).open,false,'successful selection collapses');
assert.equal(scenario({next:'old'}).open,true,'unchanged URL keeps open');
assert.equal(scenario({next:''}).open,true,'empty URL keeps open');
assert.equal(scenario({label:'Search',next:'new'}).open,true,'other buttons keep open');
assert.equal(scenario({disabled:true}).open,true,'disabled button keeps open');
assert.equal(scenario({isResult:false}).open,true,'external button keeps open');
console.log('PASS: 6 deterministic browser-event scenarios (mock DOM, no network)');
