import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {translate,getLocale,setLocale,speechBubble,STORAGE_KEY} from './i18n.js';

test('English is the default without a saved language',()=>{
  assert.equal(getLocale(),'en');
  assert.equal(STORAGE_KEY,'mosswood.language');
});

test('main navigation and dynamic menus translate in both directions',()=>{
  assert.equal(translate('Objekte','en'),'Objects');
  assert.equal(translate('Sozial','en'),'Social');
  assert.equal(translate('Kontakt & Ausflug planen','en'),'Plan contact & outing');
  assert.equal(translate('Was soll als Nächstes passieren?','en'),'What should happen next?');
  assert.equal(translate('Objects','de'),'Objekte');
  assert.equal(translate('View relationships','de'),'Beziehungsnetz ansehen');
  assert.equal(translate('What should happen next?','de'),'Was soll als Nächstes passieren?');
});

test('live data labels and names remain readable',()=>{
  assert.equal(translate('Zustand 85%','en'),'Condition 85%');
  assert.equal(translate('Eifersucht und Neid','en'),'Jealousy & Envy');
  assert.equal(translate('Maya Kinderbrook','en'),'Maya Kinderbrook');
  assert.equal(translate('Contentment','de'),'Zufriedenheit');
});

test('German speech catalog has a deterministic English presentation',()=>{
  const actor={id:'sim_1',action:{kind:'work'},speech:{text:'Kaffee rettet mich ☕'}};
  const english=speechBubble(actor,'en');
  assert.match(english,/^[^äöüß]+$/i);
  assert.equal(speechBubble(actor,'en'),english);
  assert.equal(speechBubble(actor,'de'),'Kaffee rettet mich ☕');
});

test('all game views load the shared language controls',()=>{
  const main=readFileSync(new URL('./index.html',import.meta.url),'utf8');
  assert.match(main,/data-language="en"/);
  assert.match(main,/data-language="de"/);
  for(const name of ['atelier','workshop','city']){
    const html=readFileSync(new URL(`./${name}.html`,import.meta.url),'utf8');
    assert.match(html,/i18n-standalone\.js/);
    assert.match(html,/i18n-standalone\.css/);
  }
});

test('switching language persists without touching the simulation',()=>{
  const oldDocument=globalThis.document,oldStorage=globalThis.localStorage,oldFilter=globalThis.NodeFilter;
  const saved=new Map();
  globalThis.localStorage={setItem:(key,value)=>saved.set(key,value)};
  globalThis.NodeFilter={SHOW_ELEMENT:1,SHOW_TEXT:4};
  globalThis.document={nodeType:9,documentElement:{lang:'en'},createTreeWalker:()=>({nextNode:()=>false}),querySelectorAll:()=>[]};
  try{
    setLocale('de');assert.equal(getLocale(),'de');assert.equal(saved.get(STORAGE_KEY),'de');assert.equal(document.documentElement.lang,'de');
    setLocale('en');assert.equal(getLocale(),'en');assert.equal(saved.get(STORAGE_KEY),'en');
  }finally{
    globalThis.document=oldDocument;globalThis.localStorage=oldStorage;globalThis.NodeFilter=oldFilter;
  }
});
