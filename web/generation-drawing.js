/* Original meter-aware furniture sprites. Also embedded in the offline report. */
import {drawBedVariant} from './bed-variants-drawing.js';
import {drawCivicObject} from './civic-drawing.js';
const fill=(c,x,y,w,h,color)=>{c.fillStyle=color;c.fillRect(x,y,w,h)};
const stroke=(c,x,y,w,h,color,line=1)=>{c.strokeStyle=color;c.lineWidth=line;c.strokeRect(x,y,w,h)};
const randomTile=(x,y)=>((Math.imul(x+81,73856093)^Math.imul(y+31,19349663))>>>0)%100;

export function furnitureSprite(c,o,palette){
  if(o.procedural_sprite){for(const p of o.procedural_sprite){c.fillStyle=p.color;c.fillRect(p.x,p.y,p.w,p.h)}return}
  if(drawBedVariant(c,o,palette)||drawCivicObject(c,o,palette))return;
  const s=24,w=o.base_w*s,h=o.base_h*s,x=0,y=0;
  const wood='#b08b62',top='#d3b38a',dark='#697563',cream='#f1e7cf',fabric=palette.fabric;
  fill(c,3,4,w-2,h-2,'#4e5b492b');
  const table=()=>{fill(c,2,3,w-4,h-4,wood);fill(c,1,0,w-2,h-6,top);fill(c,3,1,w-6,2,'#e3c89f')};
  switch(o.kind){
    case 'sofa':case 'armchair':
      fill(c,2,3,w-4,h-3,'#61715d');fill(c,2,0,w-4,7,fabric);fill(c,5,8,w-10,h-11,fabric);fill(c,5,8,w-10,2,'#ffffff30');
      for(let xx=24;xx<w;xx+=24)fill(c,xx,8,2,h-11,'#42513a30');fill(c,0,4,6,h-5,fabric);fill(c,w-6,4,6,h-5,fabric);fill(c,9,8,9,8,palette.accent);if(w>48)fill(c,w-22,8,9,8,'#ddd2ab');break;
    case 'coffee_table':case 'side_table':case 'child_table':case 'dining_table':case 'large_dining_table':
      table();fill(c,6,5,11,8,cream);fill(c,w-13,5,6,6,'#929d71');fill(c,w-11,3,2,4,'#73895d');
      if(o.kind==='dining_table'||o.kind==='large_dining_table'){for(let xx=8;xx<w-6;xx+=22){fill(c,xx,-4,11,5,fabric);fill(c,xx,h-2,11,6,fabric);fill(c,xx+1,7,8,8,cream);fill(c,xx+1,h-19,8,8,cream)}}break;
    case 'tv':
      table();fill(c,6,1,w-12,14,'#4e6058');fill(c,8,3,w-16,9,'#8caaa4');fill(c,9,4,w-18,2,'#bdc9b4');fill(c,w/2-4,15,8,3,'#62736c');fill(c,3,h-7,w-6,2,'#977e5c');break;
    case 'double_bed':case 'single_bed':
      fill(c,0,0,w,h,'#aa8c6b');fill(c,2,2,w-4,h-5,cream);fill(c,3,20,w-6,h-24,fabric);fill(c,3,20,w-6,6,'#ffffff3d');
      for(let xx=4;xx<w-8;xx+=22){fill(c,xx,5,16,11,'#faf2dc');fill(c,xx,15,16,2,'#d7cdb5')}fill(c,5,29,2,h-36,'#ffffff26');break;
    case 'bookshelf':case 'toy_storage':case 'wardrobe':case 'cabinet':case 'shoe_rack':case 'coat_rack':
      fill(c,1,1,w-2,h-1,wood);fill(c,2,0,w-4,3,'#dbc29a');fill(c,3,5,w-6,h-9,'#897754');
      if(o.kind==='wardrobe'||o.kind==='cabinet'){fill(c,3,4,w/2-4,h-7,'#c7a881');fill(c,w/2+1,4,w/2-4,h-7,'#bea078');fill(c,w/2-4,12,2,4,'#806f50');fill(c,w/2+3,12,2,4,'#806f50')}
      else if(o.kind==='coat_rack'){fill(c,6,6,4,12,palette.fabric);fill(c,14,7,5,13,palette.accent)}
      else for(let xx=5;xx<w-6;xx+=6){fill(c,xx,7,4,10,[palette.fabric,palette.accent,'#c8be82','#d8caba'][xx%4]);fill(c,xx,8,4,1,'#ffffff40')}break;
    case 'desk':
      table();fill(c,5,2,18,12,'#566960');fill(c,7,3,14,8,'#9cb9af');fill(c,11,15,8,3,'#667d70');fill(c,30,5,10,11,cream);fill(c,32,8,6,1,'#b8b095');fill(c,32,11,4,1,'#b8b095');fill(c,8,h-2,16,5,fabric);break;
    case 'fridge':
      fill(c,2,0,w-4,h,'#b7c9bf');fill(c,3,1,w-6,h-4,'#e4e8d6');fill(c,4,9,w-8,1,'#9eb5a9');fill(c,w-8,3,2,4,'#809c90');fill(c,w-8,13,2,6,'#809c90');break;
    case 'sink':case 'basin':
      table();fill(c,4,4,w-8,h-12,'#829b92');fill(c,6,6,w-12,h-16,'#b1cbbd');fill(c,w/2-1,0,3,7,'#ebefdc');break;
    case 'stove':
      table();fill(c,3,2,w-6,h-7,'#ddd8c0');for(const xx of [5,13])for(const yy of [4,11]){fill(c,xx,yy,5,5,'#778077');fill(c,xx+1,yy+1,3,3,'#a7ad94')}break;
    case 'counter':case 'bar':
      table();fill(c,7,3,14,12,cream);fill(c,10,7,8,2,'#b79a6a');fill(c,w-14,3,5,9,'#91a37f');fill(c,w-12,1,2,3,'#73936f');if(o.kind==='bar'){fill(c,26,6,7,5,'#b99470');fill(c,40,6,7,5,'#c7bd8d')}break;
    case 'shower':
      fill(c,1,1,w-2,h-2,'#bacbbb');fill(c,3,3,w-6,h-6,'#dce5d0');for(let yy=10;yy<h;yy+=10)fill(c,3,yy,w-6,1,'#bfd1be');fill(c,2,1,3,h-2,'#95bcb2');fill(c,w-5,1,3,h-2,'#86ada1');fill(c,8,3,8,3,'#778e83');fill(c,12,5,2,7,'#b1c2ad');break;
    case 'toilet':
      fill(c,5,1,w-10,7,'#ececda');fill(c,4,8,w-8,10,'#e8edda');fill(c,8,10,w-16,5,'#9bb9ac');fill(c,8,18,w-16,4,'#c8d6c8');break;
    case 'washing_machine':
      fill(c,1,0,w-2,h,'#dce1cf');fill(c,3,3,w-6,3,'#b6c8ba');fill(c,6,9,w-12,11,'#89a59c');fill(c,8,11,w-16,7,'#b5d0be');break;
    case 'aquarium':
      fill(c,1,4,w-2,h-4,wood);fill(c,2,1,w-4,h-7,'#527c74');fill(c,4,3,w-8,h-12,'#85b8ad');fill(c,5,4,w-10,2,'#c6e1cf');fill(c,9,10,6,3,'#dbb677');fill(c,28,7,5,3,'#d7a28b');fill(c,w-10,9,3,7,'#6d9566');break;
    case 'stereo':
      table();fill(c,3,3,10,14,'#626b60');fill(c,w-13,3,10,14,'#626b60');fill(c,6,6,4,7,'#9aa18c');fill(c,w-10,6,4,7,'#9aa18c');fill(c,17,4,w-34,11,'#818f7e');fill(c,19,6,w-38,3,'#adbc94');break;
    case 'plant':
      fill(c,7,13,11,9,'#b88760');fill(c,5,11,15,4,'#d2a780');fill(c,9,2,6,12,'#648358');fill(c,3,4,7,6,'#8eaa6f');fill(c,14,1,7,8,'#a2bb7d');break;
    case 'floor_lamp':
      fill(c,8,16,9,5,'#998669');fill(c,11,5,3,13,'#998669');fill(c,5,2,15,9,'#ddd2ab');fill(c,7,1,11,3,'#f0e6c5');break;
    case 'bench':
      for(let yy=3;yy<20;yy+=6)fill(c,1,yy,w-2,4,top);fill(c,5,19,3,4,'#7b785c');fill(c,w-8,19,3,4,'#7b785c');break;
    case 'sideboard':case 'dresser':case 'buffet':case 'filing_cabinet':case 'tool_cabinet':
      table();for(let xx=4;xx+14<=w-3;xx+=17){fill(c,xx,7,14,6,o.kind==='tool_cabinet'?'#8caaa1':wood);fill(c,xx,15,14,5,o.kind==='filing_cabinet'?'#92a597':'#c3a078');fill(c,xx+5,9,5,2,'#6f725c');fill(c,xx+5,16,5,2,'#6f725c')}
      if(o.kind==='buffet'){fill(c,7,1,12,6,cream);fill(c,29,2,8,6,'#a8bbae')}else if(o.kind==='sideboard'){fill(c,w-14,1,7,5,palette.accent);fill(c,w-12,-1,3,4,'#7e9261')}break;
    case 'display_cabinet':
      fill(c,1,1,w-2,h-1,wood);fill(c,3,2,w-6,h-6,'#759590');fill(c,5,3,w-10,h-9,'#b6cfc3');for(let xx=8;xx<w-7;xx+=12){fill(c,xx,7,7,8,cream);fill(c,xx+2,4,3,5,'#d4be8c')}fill(c,w/2,2,2,h-4,wood);fill(c,3,16,w-6,2,'#a6bcb0');break;
    case 'kitchen_island':
      table();fill(c,3,2,w-6,h-7,'#e9dfc5');fill(c,9,4,21,12,'#bcb18a');fill(c,12,6,14,2,'#738b62');fill(c,w-22,5,12,10,'#97b3a3');fill(c,w-19,3,3,4,'#e6e9d3');break;
    case 'dishwasher':
      fill(c,1,0,w-2,h,'#c6d4c5');fill(c,3,2,w-6,4,'#839b91');fill(c,4,8,w-8,2,'#6f867e');fill(c,4,12,w-8,h-14,'#e4e7d7');fill(c,w-6,3,2,2,'#dab579');break;
    case 'microwave_cart':
      table();fill(c,2,1,w-4,16,'#e0e1ce');fill(c,4,3,12,10,'#587770');fill(c,6,5,8,6,'#8ca69b');fill(c,18,4,2,3,'#b6a477');fill(c,18,10,2,2,'#779586');break;
    case 'coffee_station':
      table();fill(c,3,2,12,16,'#546e63');fill(c,5,3,8,5,'#93aea0');fill(c,7,10,5,5,cream);fill(c,17,9,5,6,cream);fill(c,18,8,3,2,'#927a5a');fill(c,4,18,11,2,'#758a7b');break;
    case 'pantry_shelf':case 'storage_rack':case 'baby_storage':
      fill(c,1,1,w-2,h-2,wood);fill(c,3,3,w-6,h-6,'#807d5b');
      for(let xx=5;xx<w-6;xx+=11){fill(c,xx,5,8,12,[palette.accent,palette.fabric,'#d0bf84'][Math.floor(xx/11)%3]);fill(c,xx+1,4,6,2,'#e3d6ad');fill(c,xx+2,10,4,3,cream)}
      fill(c,2,h-5,w-4,3,top);if(o.kind==='baby_storage'){fill(c,8,5,4,4,'#d6b974');fill(c,30,5,5,5,'#a4bb9a')}break;
    case 'freezer':
      fill(c,1,1,w-2,h-1,'#a9c0b3');fill(c,2,0,w-4,h-5,'#e2e8d7');stroke(c,4,2,w-8,h-10,'#b7cabc');fill(c,w/2-5,h-8,10,2,'#7d998c');break;
    case 'produce_crate':
      table();fill(c,4,3,w-8,h-10,'#967b53');for(const [xx,yy,col] of [[5,4,'#9aaa65'],[12,5,'#cb8664'],[6,12,'#d4bc74'],[14,12,'#9cac71']])fill(c,xx,yy,5,5,col);fill(c,2,17,w-4,3,wood);break;
    case 'vanity':
      table();fill(c,8,0,w-16,12,'#a08b6c');fill(c,10,1,w-20,9,'#b6d1c8');fill(c,11,2,6,6,'#e2eee0');fill(c,4,12,5,5,palette.accent);fill(c,w-10,13,5,4,'#aab895');fill(c,w/2-7,h-1,14,5,fabric);break;
    case 'luggage_rack':
      table();fill(c,6,3,w-12,h-7,'#947e61');fill(c,9,4,w-18,h-10,palette.fabric);fill(c,w/2-5,0,10,3,'#647764');fill(c,13,4,3,h-10,'#cfb98e');fill(c,w-16,4,3,h-10,'#cfb98e');break;
    case 'crib':
      fill(c,2,1,w-4,h-2,wood);fill(c,5,5,w-10,h-10,cream);fill(c,6,16,w-12,h-24,fabric);fill(c,7,7,w-14,7,'#fbf0dc');
      for(let yy=4;yy<h-3;yy+=7){fill(c,1,yy,4,4,'#d9c19c');fill(c,w-5,yy,4,4,'#d9c19c')}fill(c,2,1,w-4,3,'#ead6af');fill(c,2,h-4,w-4,3,'#ead6af');break;
    case 'changing_table':
      table();fill(c,4,2,w-18,h-7,'#f1e5c7');fill(c,6,4,w-22,h-11,'#bbcfb5');fill(c,w-12,3,7,5,cream);fill(c,w-11,12,4,6,'#90b8b0');fill(c,7,7,5,6,'#ead6a8');break;
    case 'rocking_chair':
      fill(c,2,3,3,h-3,wood);fill(c,w-5,3,3,h-3,wood);fill(c,4,2,w-8,6,fabric);fill(c,6,9,w-12,h-13,fabric);fill(c,0,h-4,8,3,'#967b5b');fill(c,w-8,h-4,8,3,'#967b5b');fill(c,7,10,8,5,cream);break;
    case 'bathtub':
      fill(c,2,1,w-4,h-2,'#c0cfc2');fill(c,4,2,w-8,h-5,'#f0edda');fill(c,9,5,w-18,h-12,'#afd0c5');fill(c,13,6,w-26,2,'#d5e6d6');fill(c,3,9,8,3,'#839c90');fill(c,w-13,8,4,4,'#97bcae');break;
    case 'towel_rack':
      fill(c,2,4,w-4,2,'#7b8f81');fill(c,4,6,w-8,h-10,cream);fill(c,7,6,9,h-12,fabric);fill(c,7,h-9,9,2,'#f4e6c7');fill(c,3,6,2,h-3,'#9aa68a');fill(c,w-5,6,2,h-3,'#9aa68a');break;
    case 'laundry_basket':
      fill(c,4,3,w-8,h-5,'#bda278');fill(c,6,1,w-12,7,cream);fill(c,9,3,8,6,fabric);for(let yy=10;yy<h-2;yy+=4)fill(c,4,yy,w-8,1,'#e0c59d');for(let xx=6;xx<w-4;xx+=5)fill(c,xx,9,1,h-12,'#e0c59d');break;
    case 'dryer':
      fill(c,1,0,w-2,h,'#e7e2cb');fill(c,3,2,w-6,5,'#b9cbb9');fill(c,6,10,w-12,h-13,'#9bad98');fill(c,8,11,w-16,h-16,'#dac89f');fill(c,9,12,4,4,cream);fill(c,w-7,3,3,3,'#8ca18d');break;
    case 'ironing_board':
      fill(c,4,7,w-8,10,'#8d9a83');fill(c,8,4,w-16,15,'#b9d0be');fill(c,1,8,8,7,'#b9d0be');fill(c,12,4,w-25,2,'#e3ebd0');fill(c,w-14,7,8,6,cream);fill(c,w-12,5,5,3,'#72988c');break;
    case 'drying_rack':
      fill(c,3,2,3,h-4,'#a7b7a3');fill(c,w-6,2,3,h-4,'#a7b7a3');
      for(let yy=5;yy<h-4;yy+=10){fill(c,4,yy,w-8,2,'#f1ecd6');fill(c,10,yy,12,7,yy%20===5?fabric:cream);fill(c,26,yy,10,7,palette.accent)}break;
    case 'utility_sink':
      table();fill(c,3,3,w-6,h-8,'#adc3b4');fill(c,5,5,w-20,h-12,'#708e83');fill(c,7,6,w-24,h-15,'#c3d7c5');fill(c,11,0,3,7,'#e2e6d3');fill(c,w-12,6,6,9,'#b9b888');break;
    case 'printer_stand':
      table();fill(c,3,4,w-6,14,'#9aafa0');fill(c,5,0,w-10,9,cream);fill(c,5,9,w-10,3,'#5f7a6b');fill(c,7,12,w-14,7,'#eee9d2');fill(c,9,14,w-18,1,'#b1bda5');break;
    case 'office_desk':case 'gaming_desk':
      table();fill(c,4,1,20,12,'#496d64');fill(c,6,3,16,8,'#a2c7b8');fill(c,27,1,17,12,'#496d64');fill(c,29,3,13,8,o.kind==='gaming_desk'?'#b69cba':'#a8c4af');fill(c,10,15,24,4,'#d4d6bf');fill(c,36,15,4,4,'#7c9587');fill(c,15,h-1,16,5,fabric);
      if(w>48){fill(c,49,4,15,11,cream);fill(c,51,7,10,1,'#b5b998');fill(c,51,10,8,1,'#b5b998')}else{fill(c,8,8,4,2,'#dbd79f');fill(c,33,5,6,3,'#d7c6c2')}break;
    case 'reading_table':
      table();for(const [xx,yy,col] of [[6,5,palette.fabric],[27,24,palette.accent]]){fill(c,xx,yy,15,15,col);fill(c,xx+2,yy+2,11,11,cream);fill(c,xx+7,yy+2,1,11,'#b7ac8d')}fill(c,6,h-2,12,5,fabric);fill(c,w-18,-3,12,5,fabric);break;
    case 'piano':case 'synthesizer':
      fill(c,1,1,w-2,h-1,o.kind==='piano'?'#81694f':'#63786e');fill(c,3,2,w-6,7,o.kind==='piano'?'#a98b69':'#a1b7a2');fill(c,4,11,w-8,10,cream);
      for(let xx=6;xx<w-5;xx+=5){fill(c,xx,11,1,10,'#bcb99e');if(xx%15!==1)fill(c,xx-1,11,3,6,'#4a5a50')}fill(c,w/2-10,h+1,20,4,wood);break;
    case 'guitar_stand':
      fill(c,6,h-4,13,3,'#667b68');fill(c,11,0,3,13,'#8a765a');fill(c,9,10,7,4,palette.accent);fill(c,6,14,13,7,palette.accent);fill(c,10,14,5,4,'#6a6d50');fill(c,12,1,1,20,'#dcc79a');break;
    case 'drum_kit':
      fill(c,20,28,8,17,'#73846c');fill(c,14,37,20,7,wood);
      for(const [xx,yy,ww,hh,col] of [[14,12,22,19,cream],[4,21,12,12,palette.accent],[33,20,12,12,palette.accent],[8,3,12,12,cream],[27,3,12,12,cream],[0,2,10,7,'#c7b478'],[37,3,10,7,'#c7b478']]){fill(c,xx,yy,ww,hh,'#8e8c70');fill(c,xx+2,yy+2,ww-4,hh-4,col)}break;
    case 'treadmill':
      fill(c,1,2,w-2,h-4,'#7d9282');fill(c,5,11,w-10,h-16,'#4f6b60');for(let yy=15;yy<h-6;yy+=6)fill(c,6,yy,w-12,1,'#738c7a');fill(c,1,2,w-2,10,'#a9bba3');fill(c,7,4,w-14,5,'#5c9083');fill(c,1,13,3,h-20,'#c6d4bd');fill(c,w-4,13,3,h-20,'#c6d4bd');break;
    case 'exercise_bike':
      fill(c,9,7,6,h-10,'#7d9382');fill(c,5,7,w-10,16,'#abbba1');fill(c,9,9,6,12,'#5a7a6b');fill(c,2,3,w-4,3,'#5b7265');fill(c,7,0,w-14,7,'#b5cab2');fill(c,5,h-16,w-10,9,fabric);fill(c,2,h-6,w-4,3,'#667b69');break;
    case 'weight_bench':
      fill(c,5,10,w-10,h-15,'#6c8271');fill(c,7,12,w-14,h-20,fabric);fill(c,1,5,w-2,3,'#d4ddc6');fill(c,1,0,5,14,'#677b6e');fill(c,w-6,0,5,14,'#677b6e');fill(c,8,h-10,8,4,'#8a9d85');break;
    case 'dumbbell_rack':
      table();fill(c,3,4,w-6,h-9,'#9dab94');for(let xx=6;xx<w-7;xx+=13){fill(c,xx,10,11,3,'#c6d1b9');fill(c,xx,6,4,11,'#5a7164');fill(c,xx+8,6,4,11,'#5a7164')}break;
    case 'punching_bag':
      fill(c,4,2,w-8,h-4,'#697b67');fill(c,2,5,w-4,h-10,'#697b67');fill(c,7,1,w-14,h-4,palette.accent);fill(c,5,5,w-10,h-12,palette.accent);fill(c,9,4,3,h-10,'#ffffff32');fill(c,6,11,w-12,3,'#765f53');break;
    case 'workbench':
      table();fill(c,5,3,26,12,'#d7c7a0');fill(c,9,9,16,3,'#7e8170');fill(c,22,5,6,10,'#8d9d8b');fill(c,37,7,23,4,'#997956');fill(c,51,2,8,11,'#82988a');fill(c,w-9,2,4,15,'#557b6c');break;
    case 'sewing_table':
      table();fill(c,7,11,23,8,cream);fill(c,8,2,22,12,'#abc2af');fill(c,13,6,10,7,top);fill(c,9,3,16,3,'#e0e9d1');fill(c,9,5,3,9,'#d5e0ca');fill(c,33,3,10,13,fabric);fill(c,20,0,3,3,palette.accent);break;
    case 'easel':
      fill(c,5,3,3,h-4,wood);fill(c,w-8,3,3,h-4,wood);fill(c,2,7,w-4,h-18,'#b99c70');fill(c,4,9,w-8,h-22,cream);fill(c,5,10,w-10,9,'#9bbfb3');fill(c,5,19,w-10,9,'#a8b881');fill(c,8,16,5,10,'#749e7a');fill(c,2,h-11,w-4,3,wood);break;
    case 'potting_bench':
      table();fill(c,4,4,19,12,'#8b7752');fill(c,6,6,15,7,'#687c52');fill(c,28,10,9,8,'#bd8c65');fill(c,30,5,6,9,'#84a169');fill(c,39,2,4,15,'#68856d');break;
    case 'planter_box':case 'plant_shelf':
      table();fill(c,4,3,w-8,h-9,'#8a7954');for(let xx=6;xx<w-9;xx+=14){fill(c,xx+2,10,8,9,'#bd936c');fill(c,xx,5,12,6,'#789d65');fill(c,xx+4,1,6,9,'#a0b878');fill(c,xx+1,4,4,4,palette.accent)}
      if(o.kind==='plant_shelf')fill(c,2,h-5,w-4,3,'#d7bd90');break;
    case 'chess_table':
      table();for(let yy=0;yy<8;yy++)for(let xx=0;xx<8;xx++)fill(c,4+xx*2,2+yy*2,2,2,(xx+yy)%2?'#7a8065':'#e4d7b4');fill(c,5,3,2,3,'#faf0d3');fill(c,14,12,2,3,'#4d6456');fill(c,7,-3,10,4,fabric);fill(c,7,h-2,10,5,fabric);break;
    case 'arcade':
      fill(c,1,0,w-2,h,'#4e7066');fill(c,3,1,w-6,4,palette.accent);fill(c,4,7,w-8,10,'#324e45');fill(c,6,9,4,3,'#9bbc8b');fill(c,13,11,4,3,'#d6b482');fill(c,3,18,w-6,5,'#809b85');fill(c,6,17,2,5,'#e0cba0');fill(c,15,19,3,2,palette.accent);break;
    case 'pool_table':
      fill(c,0,0,w,h,'#94734f');fill(c,5,5,w-10,h-10,'#6b9274');stroke(c,3,3,w-6,h-6,'#c3a175',2);
      for(const xx of [2,w/2-2,w-6])for(const yy of [2,h-6])fill(c,xx,yy,4,4,'#3e6653');fill(c,16,24,3,3,cream);for(const [xx,yy,col] of [[44,17,'#e7c580'],[48,20,'#c88d75'],[44,23,'#d7ddd0'],[48,26,'#8db5b4']])fill(c,xx,yy,3,3,col);fill(c,12,h-3,w-24,1,'#e6cf9d');break;
    case 'foosball_table':
      table();fill(c,4,3,w-8,h-8,'#819b70');for(const [yy,col] of [[7,palette.accent],[15,'#6b9394']]){fill(c,-3,yy,w+6,1,'#d5d9bf');for(const xx of [12,24,36])fill(c,xx,yy-2,4,5,col)}fill(c,23,11,2,2,cream);break;
    case 'pingpong_table':
      fill(c,0,0,w,h,'#779d9d');stroke(c,2,2,w-4,h-4,'#e6edcf',1);fill(c,w/2,2,1,h-4,'#d9e5c4');fill(c,-2,h/2,w+4,2,'#607c70');fill(c,0,h/2-2,w,1,'#f0edcd');fill(c,10,8,5,7,palette.accent);fill(c,12,14,2,5,wood);fill(c,w-18,h-14,5,7,cream);fill(c,w-16,h-8,2,4,wood);fill(c,23,15,2,2,cream);break;
  }
}

function drawObject(c,o,palette,unit,originX=0,originY=0){
  c.save();c.translate(originX+o.x*unit,originY+o.y*unit);c.scale(unit/24,unit/24);c.imageSmoothingEnabled=false;
  const q=o.orientation||0,bw=o.base_w*24,bh=o.base_h*24;
  if(q===1){c.translate(bh,0);c.rotate(Math.PI/2)}else if(q===2){c.translate(bw,bh);c.rotate(Math.PI)}else if(q===3){c.translate(0,bw);c.rotate(-Math.PI/2)}
  furnitureSprite(c,o,palette);c.restore();
}

export function paintRoom(c,room,x,y,unit,{overlay=false,labels=false,selected=null,walls=true}={}){
  const w=room.width*unit,h=room.height*unit,p=room.palette;
  fill(c,x+5,y+7,w,h,'#35493516');fill(c,x,y,w,h,p.floor);
  for(let yy=0;yy<room.height;yy++)for(let xx=0;xx<room.width;xx++){
    const v=randomTile(xx+room.seed,yy);fill(c,x+xx*unit,y+yy*unit,unit,unit,v<40?'#ffffff0b':'#00000004');
    if(['bathroom','laundry','pantry','conservatory'].includes(room.kind)){fill(c,x+xx*unit+1,y+yy*unit+1,unit-2,unit-2,(xx+yy)%2?'#d6deca':'#e1e6d4')}
    else if(room.kind==='gym'){fill(c,x+xx*unit+1,y+yy*unit+1,unit-2,unit-2,(xx+yy)%2?'#a8b5a0':'#b1bda7')}
    else{fill(c,x+xx*unit,y+(yy+1)*unit-1,unit,1,'#9f886329');fill(c,x+(xx+.5*(yy%2))*unit,y+yy*unit,1,unit,'#ab926326')}
  }
  if(['living','bedroom','child','teen','party','guest','nursery','library','office','music'].includes(room.kind)){
    const table=room.kind==='living'?room.objects.find(o=>o.kind==='coffee_table'):null,rotated=table&&table.orientation%2;
    const rugW=Math.min(rotated?3:4,room.width-2)*unit,rugH=Math.min(rotated?4:3,room.height-2)*unit;
    const centerX=table?(table.x+table.w/2)*unit:w/2,centerY=table?(table.y+table.h/2)*unit:h/2;
    const rx=x+Math.max(unit*.5,Math.min(w-rugW-unit*.5,centerX-rugW/2)),ry=y+Math.max(unit*.5,Math.min(h-rugH-unit*.5,centerY-rugH/2));
    fill(c,rx,ry,rugW,rugH,p.rug);stroke(c,rx+5,ry+5,rugW-10,rugH-10,'#f5e9ca80',2)
  }
  if(overlay){for(const z of room.zones)for(const [xx,yy] of z.cells)fill(c,x+xx*unit+1,y+yy*unit+1,unit-2,unit-2,'#eec97d55');for(const o of room.objects)for(const [xx,yy] of o.clearance)fill(c,x+xx*unit+2,y+yy*unit+2,unit-4,unit-4,'#7cbaaa50')}
  for(const o of room.objects)drawObject(c,o,p,unit,x,y);
  if(overlay){for(let xx=0;xx<=room.width;xx++)fill(c,x+xx*unit,y,1,h,'#fff8e337');for(let yy=0;yy<=room.height;yy++)fill(c,x,y+yy*unit,w,1,'#fff8e337')}
  if(walls){const wall=unit*.22;fill(c,x-wall,y-wall,w+wall*2,wall,p.wall);fill(c,x-wall,y,wall,h+wall,p.wall);fill(c,x+w,y,wall,h+wall,p.wall);fill(c,x,y+h,w,wall,p.wall);fill(c,x-wall,y-wall-2,w+wall*2,2,'#f9f0d9');
    for(const door of room.doors){const [dx,dy]=door.cell;if(door.side==='north'||door.side==='south'){fill(c,x+dx*unit,y+(door.side==='north'?-wall:h),unit,wall,'#c7b58d');fill(c,x+dx*unit+3,y+(door.side==='north'?0:h-unit),2,unit,'#9e8967')}else{fill(c,x+(door.side==='west'?-wall:w),y+dy*unit,wall,unit,'#c7b58d');fill(c,x+(door.side==='west'?0:w-unit),y+dy*unit+3,unit,2,'#9e8967')}}
    for(const win of room.windows){for(const [wx,wy] of win.cells){if(win.side==='north'||win.side==='south'){fill(c,x+wx*unit+1,y+(win.side==='north'?-wall:h)+1,unit-2,wall-2,'#8eadac')}else{fill(c,x+(win.side==='west'?-wall:w)+1,y+wy*unit+1,wall-2,unit-2,'#8eadac')}}}
  }
  if(selected){const o=room.objects.find(o=>o.id===selected);if(o){stroke(c,x+o.x*unit-2,y+o.y*unit-2,o.w*unit+4,o.h*unit+4,'#355f4c',2);for(const [ax,ay] of o.clearance)stroke(c,x+ax*unit+2,y+ay*unit+2,unit-4,unit-4,'#457f72',1)}}
  if(labels&&unit>18){c.font=`${Math.max(10,Math.min(14,unit*.3))}px 'Segoe UI',sans-serif`;c.textAlign='center';c.fillStyle='#6d674dcc';c.fillText(room.name,x+w/2,y+h-7)}
}

export function paintHouseFloor(c,house,level,x,y,unit,options={}){
  const floor=house.floors[level],w=house.width*unit,h=house.height*unit;
  fill(c,x+6,y+8,w,h,'#35493515');
  const unbuilt=floor.elevation<0?'#d1cbb8':floor.elevation>0?'#e3e9d9':'#d4dfc5';
  for(let yy=0;yy<house.height;yy++)for(let xx=0;xx<house.width;xx++){
    const cell=floor.terrain[yy*house.width+xx],px=x+xx*unit,py=y+yy*unit;
    fill(c,px,py,unit,unit,cell===0?unbuilt:cell===2?'#ccb78f':'#e5dcc0');
    if(cell===0&&floor.elevation===0&&randomTile(xx,yy)<8)fill(c,px+unit*.45,py+unit*.5,Math.max(1,unit*.12),Math.max(1,unit*.12),'#aac395');
  }
  for(const room of floor.rooms){
    paintRoom(c,room,x+room.origin[0]*unit,y+room.origin[1]*unit,unit,{...options,walls:false});
    for(const window of room.windows)for(const [wx,wy] of window.cells){const px=x+(room.origin[0]+wx)*unit,py=y+(room.origin[1]+wy)*unit;
      if(window.side==='north'||window.side==='south')fill(c,px+1,py+(window.side==='north'?-.7:1.3)*unit,unit-2,.4*unit,'#91b6b0');
      else fill(c,px+(window.side==='west'?-.7:1.3)*unit,py+1,.4*unit,unit-2,'#91b6b0');
    }
  }
  for(const p of floor.portal_geometry){const px=x+p.x*unit,py=y+p.y*unit;if(p.kind==='stairs'){fill(c,px,py,p.w*unit,p.h*unit,'#a4a691');for(let k=0;k<9;k++){fill(c,px+3,py+k*p.h*unit/9,p.w*unit-6,p.h*unit/9-2,'#dedbc4')}fill(c,px+1,py,2,p.h*unit,'#7b8972');fill(c,px+p.w*unit-3,py,2,p.h*unit,'#7b8972');c.font=`${unit*.7}px sans-serif`;c.textAlign='center';c.fillStyle='#7a8a71';c.fillText('↑',px+p.w*unit/2,py+p.h*unit*.6)}else{fill(c,px,py,p.w*unit,p.h*unit,'#8eaaa2');fill(c,px+3,py+3,p.w*unit-6,p.h*unit-6,'#c0d0c3');fill(c,px+p.w*unit/2,py+4,1,p.h*unit-8,'#879d8c');fill(c,px+unit*.6,py+p.h*unit-6,unit*.8,3,'#788d7d');c.font=`${unit*.48}px sans-serif`;c.textAlign='center';c.fillStyle='#5a7968';c.fillText('↕',px+p.w*unit/2,py+unit*.8)}}
  paintPerimeterWalls(c,floor,x,y,unit);
}

function paintPerimeterWalls(c,floor,x,y,unit){
  const terrain=floor.terrain,fw=floor.width,fh=floor.height,wall=Math.max(1,unit*.13);
  const empty=(xx,yy)=>xx<0||yy<0||xx>=fw||yy>=fh||terrain[yy*fw+xx]===0;
  for(let yy=0;yy<fh;yy++)for(let xx=0;xx<fw;xx++){
    const cell=terrain[yy*fw+xx];if(!cell)continue;
    const px=x+xx*unit,py=y+yy*unit,edge='#818d77';
    if(empty(xx,yy-1))fill(c,px,py,unit,wall,edge);
    if(empty(xx,yy+1))fill(c,px,py+unit-wall,unit,wall,edge);
    if(empty(xx-1,yy)&&!(cell===2&&xx===0))fill(c,px,py,wall,unit,edge);
    if(empty(xx+1,yy))fill(c,px+unit-wall,py,wall,unit,edge);
  }
  for(const room of floor.rooms)for(const window of room.windows)for(const [wx,wy] of window.cells){
    const px=x+(room.origin[0]+wx)*unit,py=y+(room.origin[1]+wy)*unit;
    if(window.side==='north'||window.side==='south')fill(c,px+1,py+(window.side==='north'?.03:.86)*unit,unit-2,.12*unit,'#83b1ad');
    else fill(c,px+(window.side==='west'?.03:.86)*unit,py+1,.12*unit,unit-2,'#83b1ad');
  }
}

export function paintDistrict(c,block,x,y,unit){
  fill(c,x,y,block.width*unit,block.height*unit,'#c9d5ac');const nodes=Object.fromEntries(block.nodes.map(n=>[n.id,n.position]));
  for(const edge of block.edges){const a=nodes[edge.from],b=nodes[edge.to];c.lineCap='square';c.strokeStyle='#e7dfc4';c.lineWidth=(edge.width_m+edge.sidewalk_m*2)*unit;c.beginPath();c.moveTo(x+a[0]*unit,y+a[1]*unit);c.lineTo(x+b[0]*unit,y+b[1]*unit);c.stroke();c.strokeStyle='#b2ae98';c.lineWidth=edge.width_m*unit;c.stroke();c.setLineDash([3*unit,3*unit]);c.strokeStyle='#e7dcbc';c.lineWidth=.25*unit;c.stroke();c.setLineDash([])}
  const colors={sage:'#819c76',terracotta:'#bb8b71',coastal:'#829da2',plum:'#9d8b9f'};
  for(const p of block.plots){const [px,py,pw,ph]=p.bounds;stroke(c,x+px*unit,y+py*unit,pw*unit,ph*unit,'#f5f0d67a',1);const [bx,by,bw,bh]=p.building;const[a,b]=p.footpath;c.strokeStyle='#e6d5ad';c.lineWidth=p.footpath_width_m*unit;c.beginPath();c.moveTo(x+a[0]*unit,y+a[1]*unit);c.lineTo(x+b[0]*unit,y+b[1]*unit);c.stroke();fill(c,x+(bx+.5)*unit,y+(by+1)*unit,bw*unit,bh*unit,'#526c452b');fill(c,x+bx*unit,y+by*unit,bw*unit,bh*unit,colors[p.style]);for(let yy=2;yy<bh;yy+=2)fill(c,x+bx*unit,y+(by+yy)*unit,bw*unit,.3*unit,'#ffffff1a');fill(c,x+bx*unit,y+(by+bh-1)*unit,bw*unit,unit,'#ecdfbc');c.textAlign='center';c.fillStyle='#fff7df';c.font=`${Math.max(9,Math.min(14,unit*3))}px 'Segoe UI',sans-serif`;c.fillText(`${p.levels} Etagen`,x+(bx+bw/2)*unit,y+(by+bh/2)*unit)}
}
