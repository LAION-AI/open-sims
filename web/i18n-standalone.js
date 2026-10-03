import {initI18n,onLocaleChange,translate} from './i18n.js';

const header=document.querySelector('body > header');
if(header){
  const switcher=document.createElement('div');
  switcher.className='language-switch';
  switcher.setAttribute('role','group');
  switcher.setAttribute('aria-label','Language');
  switcher.innerHTML='<button type="button" data-language="en" aria-pressed="true">EN</button><button type="button" data-language="de" aria-pressed="false">DE</button>';
  header.append(switcher);
}
initI18n();
onLocaleChange(()=>{document.title=translate(document.title)});
