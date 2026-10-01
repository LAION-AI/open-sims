/* Original, code-drawn 16-bit palette. Logical footprints come from Python. */
const T=24;
const palettes=[
  {wall:'#ede0bd',roof:'#a56854',light:'#be8165',dark:'#7c5148',trim:'#d4bd92'},
  {wall:'#e3dfc9',roof:'#668781',light:'#83a096',dark:'#496b69',trim:'#b7c2a5'},
  {wall:'#f2dcae',roof:'#b48a51',light:'#cfab68',dark:'#896b43',trim:'#d6bf91'},
  {wall:'#e5d6c2',roof:'#8a849a',light:'#a39ab1',dark:'#665f7d',trim:'#c6b6ac'},
  {wall:'#d5dfc6',roof:'#6e8961',light:'#8fa476',dark:'#516d4d',trim:'#b2c09b'},
  {wall:'#ead5c7',roof:'#a4787b',light:'#c28d8a',dark:'#805c67',trim:'#cab0a1'}
];
const publicSigns={cafe:'THE DAILY CRUMB',shop:'MOSS & MARKET',school:'MOSSWOOD SCHOOL',studio:'CREATIVE STUDIO',workshop:'MOSSWOOD WORKS',gym:'MOSSWOOD FITNESS',nightclub:'LANTERN CLUB',town_hall:'TOWN HALL',hospital:'MOSSWOOD HOSPITAL',fire_station:'FIRE STATION',office_hub:'SOUTH OFFICES',supermarket:'SOUTH MARKET',shopping_center:'MOSSWOOD ARCADE'};
const hash=(x,y)=>{let n=Math.imul(x+1327,374761393)^Math.imul(y+835,668265263);n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967296};
function rect(c,x,y,w,h,color){c.fillStyle=color;c.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h))}
function line(c,x,y,x2,y2,color,width=1){c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.moveTo(x,y);c.lineTo(x2,y2);c.stroke()}
function pixelTree(c,x,y,variant=0){
  c.save();c.translate(x,y);c.scale(1.6,1.6);x=0;y=0;
  const shade=['#55784e','#5d8050','#728a50'][variant%3],mid=['#77975d','#82a061','#93a663'][variant%3],light=['#96af70','#a2b577','#b1bd7b'][variant%3];
  rect(c,x-17,y+2,39,12,'#6d89574d');rect(c,x-11,y+10,30,5,'#6b86584d');
  rect(c,x-3,y-15,8,31,'#816e49');rect(c,x,y-12,3,27,'#ac8b55');rect(c,x-8,y-16,7,6,'#816e49');
  const rows=[[ -31, -13,27],[-26,-23,43],[-17,-28,53],[-6,-24,47],[4,-16,32]];
  for(const [dy,dx,w] of rows)rect(c,x+dx,y+dy-10,w,12,shade);
  for(const [dy,dx,w] of [[-32,-12,24],[-27,-21,39],[-18,-24,42],[-9,-18,36],[-1,-10,24]])rect(c,x+dx,y+dy-11,w,9,mid);
  for(const [dx,dy,w] of [[-12,-38,15],[-20,-29,12],[4,-27,13],[-16,-17,8],[0,-39,6]])rect(c,x+dx,y+dy,w,5,light);
  rect(c,x+17,y-24,4,12,shade);rect(c,x+4,y-7,9,5,shade);rect(c,x-20,y-23,3,4,'#b4c17e');
  c.restore();
}

export function emotionGlyph(id){
  const key=String(id||'').toLowerCase();
  if(/affection|infatuation|longing|romantic|connected|lonely/.test(key))return '♥';
  if(/fear|distress|anxious|afraid|doubt|worried|helplessness/.test(key))return '!';
  if(/amusement|elation|pleasure|contentment|gratitude|triumph|pride|relief|happy|content|playful/.test(key))return '✦';
  if(/interest|awe|astonishment|surprise|hope|enthusiasm|optimism|concentration|contemplation|inspired/.test(key))return '✧';
  if(/anger|irritability|bitterness|contempt|disgust|malice|jealousy|envy|tense/.test(key))return '◆';
  if(/fatigue|exhaustion|sadness|disappointment|shame|embarrassment|numbness|pain|sad/.test(key))return '☾';
  if(/confusion|teasing|impatience|sourness/.test(key))return '?';
  return '◇';
}

export function drawPerson(c,appearance,x,y,{scale=1,walking=false,time=0,direction=0,selected=false,sleeping=false,sitting=false}={}){
  c.save();c.translate(Math.round(x),Math.round(y));c.scale(scale,scale);
  if(sleeping){c.globalAlpha=.85}
  const {shirt,skin,hair,style}=appearance;
  const outfit=appearance.outfit||{},top=outfit.top?.color||shirt||'#849c83',trousers=outfit.trousers?.color||'#464b3c',shoes=outfit.shoes?.color||'#414b4b',coat=outfit.outerwear?.color;
  rect(c,-7,-1,15,4,'#32492f40');
  const stride=walking?Math.sin(time*10)*2:0;
  if(sitting){rect(c,-9,-12,19,4,'#a4825c');rect(c,-8,-9,3,10,'#8a7154');rect(c,7,-9,3,10,'#8a7154')}
  rect(c,-5,-5+stride,4,6,trousers);rect(c,2,-5-stride,4,6,trousers);
  rect(c,-6,-1+stride,5,2,shoes);rect(c,2,-1-stride,5,2,shoes);
  rect(c,-6,-17,13,13,trousers);rect(c,-5,-17,11,11,top);
  if(sitting){rect(c,-7,-6,6,3,trousers);rect(c,2,-6,6,3,trousers)}
  rect(c,-7,-14,3,8,top);rect(c,6,-14,3,8,top);
  if(coat){rect(c,-6,-17,3,11,coat);rect(c,4,-17,3,11,coat);rect(c,-8,-14,3,8,coat);rect(c,7,-14,3,8,coat);rect(c,-1,-16,2,8,coat)}
  rect(c,-7,-7+stride,3,4,skin);rect(c,6,-7-stride,3,4,skin);
  rect(c,-1,-18,4,4,skin);rect(c,-6,-27,13,12,hair);rect(c,-7,-25,15,7,hair);
  rect(c,-5,-23,11,9,skin);rect(c,-6,-24,13,4,hair);
  rect(c,-5,-20,2,4,hair);rect(c,5,-20,2,3,hair);
  if(style===1){rect(c,-8,-24,3,14,hair);rect(c,6,-24,3,13,hair)}
  if(style===2){rect(c,-7,-27,14,4,'#d5b771');rect(c,-9,-24,18,2,'#c6a85c')}
  if(style===3){rect(c,5,-27,5,7,hair);rect(c,-3,-27,4,2,'#d5b99b')}
  if(direction!==3){rect(c,-2,-20,1,2,'#433e35');rect(c,3,-20,1,2,'#433e35');rect(c,0,-16,3,1,'#b87d63')}
  else{rect(c,-5,-22,11,6,hair)}
  rect(c,-4,-14,2,2,'#ffffff25');
  c.restore();
}

export function drawPortrait(c,appearance,x,y,{scale=2.7,emotion=null}={}){
  drawPerson(c,appearance,x,y,{scale,direction:0});
  const states=Array.isArray(emotion)?emotion:emotion?[emotion]:[];
  if(states.length){c.save();c.font='bold 15px Georgia';c.textAlign='center';states.slice(0,4).forEach((state,index)=>{
    const id=typeof state==='string'?state:state.id||state.type;
    c.fillStyle=/fear|distress|anger|sad|doubt/i.test(id)?'#a77870':'#83a074';
    c.fillText(emotionGlyph(id),x+scale*9-index*16,y-scale*27);
  });if(states.length>4){c.fillStyle='#607a62';c.font='bold 9px sans-serif';c.fillText(`+${states.length-4}`,x-scale*10,y-scale*27)}c.restore()}
}

function drawDog(c,x,y,time=0){
  c.save();c.translate(Math.round(x),Math.round(y));
  const wag=Math.sin(time*.012)>0?2:0;
  rect(c,-10,-2,22,4,'#485c4155');
  rect(c,-8,-10,16,10,'#9b7753');rect(c,-5,-12,10,7,'#b18a5f');
  rect(c,-7,-2,3,5,'#6d5546');rect(c,4,-2,3,5,'#6d5546');
  rect(c,7,-12,8,8,'#9b7753');rect(c,12,-16,4,8,'#785b49');
  rect(c,8,-16,4,6,'#785b49');rect(c,14,-9,4,3,'#d6ba8c');
  rect(c,16,-9,2,2,'#3f3c37');rect(c,12,-12,2,2,'#29352d');
  rect(c,-12,-11-wag,5,3,'#9b7753');rect(c,-15,-13-wag,4,3,'#785b49');
  rect(c,7,-5,4,2,'#b74f47');c.restore();
}

function drawCarried(c,carried,x,y){
  const has=key=>Array.isArray(carried)?carried.includes(key):Number(carried?.[key]||0)>0;
  const px=Math.round(x+10),py=Math.round(y-13);
  if(has('groceries')){rect(c,px-1,py-4,12,12,'#b78e57');rect(c,px+1,py-6,8,3,'#805d42');rect(c,px+3,py,3,3,'#8faa69')}
  else if(has('dirty_dish')){rect(c,px-1,py+2,13,4,'#777f79');rect(c,px+1,py-1,9,4,'#e0dcc6');rect(c,px+4,py,3,2,'#b38d6b')}
  else if(has('prepared_meal')||has('pizza')||has('pancake')){rect(c,px-2,py+2,14,4,'#e5e3ce');rect(c,px,py-2,10,6,'#e5e3ce');rect(c,px+2,py-1,6,3,has('pizza')?'#c96f4d':'#d9b474');rect(c,px+5,py-2,3,2,'#76955e')}
  else if(has('ingredients')||has('egg')||has('dough')||has('tomato')||has('vegetable')){rect(c,px,py+1,11,6,'#9e7754');rect(c,px+1,py-2,4,5,'#7b9a65');rect(c,px+6,py-3,4,6,'#b88154')}
  else if(has('food_scraps')){rect(c,px,py,10,8,'#9d8d67');rect(c,px+2,py-3,6,4,'#6d8761')}
}

function drawEmotion(c,actor,x,y){
  const states=actor.affect?.states?.length?actor.affect.states:[actor.emotion].filter(Boolean);
  if(!states.length)return;
  const count=Math.min(3,states.length),left=x-count*7;
  for(let index=0;index<count;index++){
    const id=typeof states[index]==='string'?states[index]:states[index].id||states[index].type;
    const px=left+index*14;
    rect(c,px,y-48,13,13,'#fff9e9d9');c.fillStyle=/fear|distress|anger|sad|doubt/i.test(id)?'#a77970':'#78986c';
    c.font='bold 10px Georgia';c.textAlign='center';c.fillText(emotionGlyph(id),px+6,y-38);
  }
  if(states.length>3){c.fillStyle='#526f58';c.font='bold 8px sans-serif';c.fillText(`+${states.length-3}`,left+count*14+7,y-38)}
}

export class NeighborhoodRenderer{
  constructor(canvas,minimap,world,onSelect,onHouse,onObject=null){
    this.canvas=canvas;this.ctx=canvas.getContext('2d',{alpha:false});this.mini=minimap;this.mctx=minimap.getContext('2d');this.world=world;
    this.objectById=new Map(world.objects.map(o=>[o.id,o]));
    this.onObject=onObject;this.selectedObject=null;
    this.onSelect=onSelect;this.onHouse=onHouse;this.mapPlan=world.planning_metadata||null;this.camera={x:(this.mapPlan?world.width/2:64)*T,y:(this.mapPlan?world.height/2:60)*T,zoom:.46};this.selected='resident_001';this.grid=false;this.roofs='auto';this.follow=false;this.state=null;this.received=performance.now();this.hitPeople=[];this.hover=null;this.fps=60;this.frameTimes=[];
    this.base=document.createElement('canvas');this.base.width=world.width*T;this.base.height=world.height*T;this.baseCtx=this.base.getContext('2d');
    this.roofCache=new Map();this.renderBase();this.buildRoofs();this.bind();
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(canvas.parentElement);this.resize();
    this.lastFrame=performance.now();this.running=true;requestAnimationFrame(t=>this.frame(t));
  }
  resize(){const r=this.canvas.getBoundingClientRect();this.width=r.width;this.height=r.height;const dpr=Math.min(window.devicePixelRatio||1,2);this.dpr=dpr;this.canvas.width=Math.round(r.width*dpr);this.canvas.height=Math.round(r.height*dpr);this.ctx.imageSmoothingEnabled=false;}
  setState(s){this.state=s;this.received=performance.now()}
  worldAt(x,y){return {x:(x-this.width/2)/this.camera.zoom+this.camera.x,y:(y-this.height/2)/this.camera.zoom+this.camera.y}}
  screenAt(x,y){return {x:(x-this.camera.x)*this.camera.zoom+this.width/2,y:(y-this.camera.y)*this.camera.zoom+this.height/2}}
  setZoom(zoom,x=this.width/2,y=this.height/2){const old=this.worldAt(x,y);this.camera.zoom=Math.max(.12,Math.min(2.7,zoom));const current=this.worldAt(x,y);this.camera.x+=old.x-current.x;this.camera.y+=old.y-current.y;this.constrain()}
  constrain(){this.camera.x=Math.max(-50,Math.min(this.world.width*T+50,this.camera.x));this.camera.y=Math.max(-50,Math.min(this.world.height*T+50,this.camera.y))}
  fit(){this.follow=false;this.camera={x:this.world.width*T/2,y:this.world.height*T/2,zoom:Math.min(this.width/(this.world.width*T+120),this.height/(this.world.height*T+120))}}
  overview(){this.follow=false;const park=this.mapPlan?.parks?.find(p=>p.name==='Clover Green')||this.mapPlan?.parks?.[0],bounds=park?.bounds;const cx=bounds?(bounds[0]+bounds[2]/2):this.mapPlan?this.world.width/2:64,cy=bounds?(bounds[1]+bounds[3]/2):this.mapPlan?this.world.height/2:60;this.camera={x:cx*T,y:cy*T,zoom:Math.max(.28,Math.min(.52,this.width/2400))}}
  focusActor(id,zoom=.95){this.selected=id;const a=this.state?.actors.find(a=>a.id===id);if(a){const p=this.actorPosition(a,performance.now());this.camera.x=p[0]*T;this.camera.y=p[1]*T;this.camera.zoom=zoom;}}
  focusHome(id){const b=this.world.buildings.find(b=>b.id===id);if(b){this.follow=false;this.camera.x=(b.x+b.w/2)*T;this.camera.y=(b.y+b.h/2)*T;this.camera.zoom=Math.min(1.65,this.width/460,this.height/400);this.openBuilding=id}}
  actorPosition(actor,time){const a=actor.action;if(a?.phase==='travel'){
    const elapsed=this.state.paused?0:Math.min(.4,(time-this.received)/1000)*this.state.speed;
    const index=Math.max(0,Math.min(a.path.length-1,this.state.clock+elapsed-a.started_at));const i=Math.floor(index),f=index-i,p=a.path[i],q=a.path[Math.min(i+1,a.path.length-1)];return [p[0]+(q[0]-p[0])*f+.5,p[1]+(q[1]-p[1])*f+.72];
  }return [actor.position[0]+.5,actor.position[1]+.72]}
  bind(){
    this.pointers=new Map();let lastPinch=null;
    this.canvas.addEventListener('pointerdown',e=>{this.canvas.setPointerCapture(e.pointerId);this.pointers.set(e.pointerId,{x:e.offsetX,y:e.offsetY});this.drag={x:e.offsetX,y:e.offsetY,startX:e.offsetX,startY:e.offsetY,moved:false};this.canvas.classList.add('dragging');if(this.pointers.size===2){const [a,b]=[...this.pointers.values()];lastPinch=Math.hypot(a.x-b.x,a.y-b.y)}});
    this.canvas.addEventListener('pointermove',e=>{
      if(this.pointers.has(e.pointerId))this.pointers.set(e.pointerId,{x:e.offsetX,y:e.offsetY});
      if(this.pointers.size===2){const[a,b]=[...this.pointers.values()],distance=Math.hypot(a.x-b.x,a.y-b.y);if(lastPinch)this.setZoom(this.camera.zoom*distance/lastPinch,(a.x+b.x)/2,(a.y+b.y)/2);lastPinch=distance;this.drag.moved=true;return}
      if(this.drag&&this.pointers.size){const dx=e.offsetX-this.drag.x,dy=e.offsetY-this.drag.y;this.camera.x-=dx/this.camera.zoom;this.camera.y-=dy/this.camera.zoom;this.drag.x=e.offsetX;this.drag.y=e.offsetY;if(Math.hypot(e.offsetX-this.drag.startX,e.offsetY-this.drag.startY)>4)this.drag.moved=true;this.follow=false;this.constrain()}
      else this.showHover(e.offsetX,e.offsetY);
    });
    this.canvas.addEventListener('pointerup',e=>{if(this.drag&&!this.drag.moved&&this.pointers.size===1)this.pick(e.offsetX,e.offsetY);this.pointers.delete(e.pointerId);this.drag=null;lastPinch=null;this.canvas.classList.remove('dragging')});
    this.canvas.addEventListener('pointercancel',e=>{this.pointers.delete(e.pointerId);this.drag=null;this.canvas.classList.remove('dragging')});
    this.canvas.addEventListener('pointerleave',()=>document.getElementById('hover-label').classList.add('hidden'));
    this.canvas.addEventListener('wheel',e=>{e.preventDefault();this.setZoom(this.camera.zoom*Math.exp(-e.deltaY*.0016),e.offsetX,e.offsetY)},{passive:false});
    this.mini.addEventListener('click',e=>{const r=this.mini.getBoundingClientRect();this.camera.x=(e.clientX-r.left)/r.width*this.world.width*T;this.camera.y=(e.clientY-r.top)/r.height*this.world.height*T;this.follow=false});
    this.keys=new Set();window.addEventListener('keydown',e=>{if(e.defaultPrevented||document.querySelector('dialog[open]')||['INPUT','TEXTAREA','SELECT','BUTTON'].includes(e.target.tagName))return;if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','w','a','s','d'].includes(e.key)){e.preventDefault();this.keys.add(e.key)}});window.addEventListener('keyup',e=>this.keys.delete(e.key));window.addEventListener('blur',()=>this.keys.clear());
  }
  objectAt(x,y){const p=this.worldAt(x,y);return this.world.objects.find(o=>{if(p.x/T<o.x||p.x/T>=o.x+o.w||p.y/T<o.y||p.y/T>=o.y+o.h)return false;const b=this.world.buildings.find(b=>b.id===o.building_id);return !b||!this.roofVisible(b)})}
  pick(x,y){const hit=this.personAt(x,y);if(hit){this.onSelect(hit.id);return}const object=this.objectAt(x,y);if(object&&this.onObject){this.onObject(object.id);return}const p=this.worldAt(x,y);const b=this.world.buildings.find(b=>p.x/T>=b.x&&p.x/T<b.x+b.w&&p.y/T>=b.y&&p.y/T<b.y+b.h);if(b){this.openBuilding=b.id;if(b.household_id&&this.world.households.some(h=>h.id===b.household_id))this.onHouse(b.household_id);else{this.camera.x=(b.x+b.w/2)*T;this.camera.y=(b.y+b.h/2)*T;this.camera.zoom=.95}}}
  personAt(x,y){return this.hitPeople.filter(p=>Math.abs(x-p.x)<Math.max(9,p.size*.5)&&y>p.y-p.size*1.4&&y<p.y+5).sort((a,b)=>Math.hypot(x-a.x,y-a.y)-Math.hypot(x-b.x,y-b.y))[0]}
  showHover(x,y){const label=document.getElementById('hover-label');const person=this.personAt(x,y);let title='',subtitle='';if(person){const a=this.state.actors.find(a=>a.id===person.id);title=a.name;subtitle=a.action?.label||'Taking a moment'}else{const object=this.objectAt(x,y);if(object){title=object.name;subtitle='Klicken: Zustand, Nutzung und Interaktionsplätze'}else{const p=this.worldAt(x,y);const b=this.world.buildings.find(b=>p.x/T>=b.x&&p.x/T<b.x+b.w&&p.y/T>=b.y&&p.y/T<b.y+b.h);if(b){title=b.name;subtitle=b.household_id?'Click to meet the household':'Click to look inside'}}}if(!title){label.classList.add('hidden');return}label.textContent=title;const small=document.createElement('small');small.textContent=subtitle;label.append(small);label.style.left=Math.min(this.width-210,x+14)+'px';label.style.top=Math.max(8,y-55)+'px';label.classList.remove('hidden')}
  renderBase(){
    const c=this.baseCtx;c.imageSmoothingEnabled=false;const {width,height,terrain}=this.world;
    rect(c,0,0,width*T,height*T,'#9eaf78');
    for(let y=0;y<height;y++)for(let x=0;x<width;x++){
      const v=terrain[y*width+x],px=x*T,py=y*T,r=hash(x,y);
      if(v===0){rect(c,px,py,T,T,r>.65?'#9faf77':r<.2?'#a4b57d':'#a1b17a');
        if(r>.35){rect(c,px+3+Math.floor(r*13),py+7,2,3,'#8ca365');rect(c,px+6+Math.floor(r*13),py+5,2,3,'#8ca365')}
        if(r<.08){rect(c,px+8,py+15,2,2,'#c8ce96');rect(c,px+10,py+13,2,2,'#d8d8a0')}
      }else if(v===1){rect(c,px,py,T,T,r>.5?'#afa995':'#b2ac98');if(r>.3)rect(c,px+7,py+15,2,1,'#bdb6a1')}
      else if(v===2){rect(c,px,py,T,T,'#d5c9a5');rect(c,px+1,py+1,T-2,T-2,r>.45?'#d9cdaa':'#d3c5a1');line(c,px,py+T-1,px+T,py+T-1,'#c3b992')}
      else if(v===3){rect(c,px,py,T,T,'#dbc6a0');line(c,px,py+T-1,px+T,py+T-1,'#c5ad8d');line(c,px+(y%2?12:0),py,px+(y%2?12:0),py+T,'#c9b38e');rect(c,px+3,py+8,13,1,'#e4d1ab')}
      else if(v===4){rect(c,px+3,py+3,T,T,'#6a6e5744');rect(c,px,py,T,T,'#bab79c');rect(c,px,py-6,T,10,'#f1e5c7');rect(c,px,py+4,T,2,'#d6cbae')}
      else if(v===5){rect(c,px,py,T,T,'#80aa9b');rect(c,px+3,py+8,9,2,'#9bc1ab');rect(c,px+12,py+16,7,2,'#a5cab2')}
    }
    if(this.mapPlan){for(const room of this.world.regions||[]){if(!room.parent||!room.bounds)continue;const [rx,ry,rw,rh]=room.bounds;
      const tone=/bathroom/i.test(room.name)?'#d8e3d2':/child|nursery/i.test(room.name)?'#ead8c9':/bedroom/i.test(room.name)?'#e9dcc6':/living|dining/i.test(room.name)?'#dcc9a7':/classroom/i.test(room.name)?'#e5d6b0':/lobby/i.test(room.name)?'#e0d6b9':'#d6c5a8';
      for(let yy=ry;yy<ry+rh;yy++)for(let xx=rx;xx<rx+rw;xx++)if(xx>=0&&yy>=0&&xx<width&&yy<height&&terrain[yy*width+xx]===3){rect(c,xx*T,yy*T,T-1,T-1,tone);if(/bathroom|hospital/i.test(room.name))rect(c,xx*T+2,yy*T+2,3,3,'#eaf0dd')}
      if(room.id==='school_classroom'){rect(c,(rx+1)*T,(ry+1)*T,7*T,4,'#607e66');rect(c,(rx+1)*T,(ry+1)*T+4,7*T,2,'#d5bc91')}
    }}
    // New maps derive markings from planning metadata; old saves retain their
    // original authored roads and crosswalks verbatim.
    if(this.mapPlan?.roads?.length){
      for(const road of this.mapPlan.roads){
        if(road.class==='pedestrian')continue;
        const [rx,ry,rw,rh]=road.bounds,hor=rw>=rh;
        if(hor){rect(c,rx*T,ry*T,rw*T,2,'#92917d');rect(c,rx*T,(ry+rh)*T-2,rw*T,2,'#92917d');if(road.class==='arterial')for(let xx=rx+2;xx<rx+rw-2;xx+=5)rect(c,xx*T,(ry+rh/2)*T,33,2,'#d6cbb0')}
        else{rect(c,rx*T,ry*T,2,rh*T,'#92917d');rect(c,(rx+rw)*T-2,ry*T,2,rh*T,'#92917d');if(road.class==='arterial')for(let yy=ry+2;yy<ry+rh-2;yy+=5)rect(c,(rx+rw/2)*T,yy*T,2,33,'#d6cbb0')}
      }
    }else for(const y of [23,47,69,93,123]){
      rect(c,0,y*T,width*T,2,'#92917d');rect(c,0,(y+3)*T-2,width*T,2,'#92917d');
      for(let x=0;x<width;x+=5)rect(c,x*T,(y+1.5)*T,35,2,'#d6cbb0');
      for(const x of (y===123?[2,42,79,123]:[2,61,123]))for(let k=0;k<5;k++)rect(c,x*T,(y+.15)*T+k*13,40,6,'#dad2b5');
    }
    // Warm garden plots and flower borders distinguish front gardens.
    for(const b of this.world.buildings.filter(b=>b.household_id)){
      const x=b.x*T,y=b.y*T,p=palettes[(b.palette??0)%palettes.length];
      rect(c,x-2,y+b.h*T,7*T,3,'#657d522c');
      for(let k=0;k<6;k++){rect(c,x+k*12+12,y+(b.h+1)*T+3,8,5,'#788e58');rect(c,x+k*12+14,y+(b.h+1)*T,3,4,k%2?'#dabb76':'#dbc29d')}
      rect(c,b.door[0]*T-5,b.door[1]*T+10,34,18,p.trim);rect(c,b.door[0]*T-8,b.door[1]*T+26,40,5,'#c2b497');
      // Only old identical floorplans use this original fixed rug/bath overlay.
      if(!this.mapPlan){rect(c,x+1*T+8,y+5*T+9,5*T-15,3*T+3,['#be9073','#9caf93','#cab18a','#b5a0a4','#c3a094'][b.palette]);
        c.strokeStyle='#efe0b94d';c.lineWidth=2;c.strokeRect(x+T+12,y+5*T+13,5*T-23,3*T-5);
        for(let yy=6;yy<10;yy++)for(let xx=9;xx<14;xx++){rect(c,x+xx*T,y+yy*T,T-1,T-1,(xx+yy)%2?'#dce0cb':'#ced6c1')}}
    }
    for(const o of this.world.objects)this.drawFurniture(c,o);
    // Small public place signs, each part of the drawn scene.
    for(const b of this.world.buildings.filter(b=>!b.household_id)){
      const x=(b.frontage?.[0]??b.x+b.w/2)*T,y=(b.frontage?.[1]??b.y+b.h+1)*T;
      const sign=publicSigns[b.id]||b.name.toUpperCase(),sw=Math.max(98,sign.length*6+10);
      rect(c,x-sw/2+3,y-6,sw,15,'#7c856449');rect(c,x-sw/2,y-9,sw,15,'#ece3c1');c.font='7px monospace';c.textAlign='center';c.fillStyle='#748362';c.fillText(sign,x,y+1);
    }
    for(const d of this.world.decorations){const x=(d.x+.5)*T,y=(d.y+.7)*T;
      if(d.kind==='tree')pixelTree(c,x,y,d.variant);
      if(d.kind==='flowers'){for(let j=0;j<10;j++){const xx=x+j*5;rect(c,xx,y,3,5,'#758d53');rect(c,xx-1,y-3,4,3,['#e4c27b','#d9a191','#d4c9a5'][d.variant])}}
      if(d.kind==='mailbox'){rect(c,x,y-4,3,16,'#9d8660');rect(c,x-5,y-12,14,9,'#65867c');rect(c,x-5,y-14,12,3,'#91ada0');rect(c,x+7,y-16,2,6,'#c78967')}
      if(d.kind==='fence'){for(let j=0;j<d.w*24;j+=9){rect(c,x+j,y-8,4,15,'#d3cfad');rect(c,x+j,y-10,3,2,'#e4ddbc')}rect(c,x,y-5,d.w*24,3,'#e1d9b8');rect(c,x,y+2,d.w*24,2,'#b8b697')}
      if(d.kind==='lamp'){rect(c,x-1,y-17,3,31,'#657467');rect(c,x-5,y-23,11,10,'#556c5d');rect(c,x-3,y-21,7,6,'#e8dbac');rect(c,x-6,y-25,13,3,'#768878');rect(c,x-4,y+12,9,3,'#75836b')}
    }
    // The original parked cars belong only to the original layout.
    for(const [x,y,color] of this.mapPlan?[]:[[30,24,'#cebe86'],[94,48,'#8a9caa'],[23,70,'#c18c70'],[111,94,'#9a9f78']]){
      rect(c,x*T,y*T,68,29,'#64745b44');rect(c,x*T-2,y*T+4,6,8,'#525d50');rect(c,x*T+53,y*T+4,6,8,'#525d50');rect(c,x*T-2,y*T+21,6,8,'#525d50');rect(c,x*T+53,y*T+21,6,8,'#525d50');rect(c,x*T,y*T,58,29,color);rect(c,x*T+14,y*T+3,24,22,'#dde0c7');rect(c,x*T+16,y*T+5,20,18,'#91aaa2');rect(c,x*T+1,y*T+4,5,6,'#e6d9a3');rect(c,x*T+1,y*T+20,5,6,'#e6d9a3');
    }
  }
  drawFurniture(c,o){
    const x=o.x*T,y=o.y*T,w=o.w*T,h=o.h*T;
    const shadow=()=>rect(c,x+3,y+5,w-2,h-2,'#5b665737');
    if(o.kind==='door'){rect(c,x+2,y+2,w-4,h-4,'#c6a075');rect(c,x+5,y+5,w-10,h-9,'#ddbd8e');rect(c,x+w-6,y+12,2,2,'#7e7759');return}
    if(o.kind==='park_marker'||o.kind.endsWith('_marker'))return;
    shadow();
    switch(o.kind){
      case 'sofa':rect(c,x+2,y+3,w-3,h-3,'#697c68');rect(c,x+3,y+1,w-6,7,'#9eaf90');rect(c,x+4,y+7,w-8,h-10,'#b0bc99');for(let i=1;i<3;i++)rect(c,x+i*T,y+7,2,h-10,'#8fa282');rect(c,x,y+5,6,h-5,'#8a9e7c');rect(c,x+w-6,y+5,6,h-5,'#8a9e7c');rect(c,x+8,y+8,11,9,'#d6c599');rect(c,x+w-21,y+8,11,9,'#b9866b');rect(c,x+4,y+h,4,3,'#7d785c');rect(c,x+w-8,y+h,4,3,'#7d785c');break;
      case 'bed':rect(c,x+1,y+1,w-2,h-1,'#9b7f63');rect(c,x+2,y+3,w-4,h-5,'#f2e7c7');rect(c,x+3,y+4,w-6,12,'#fff3d8');if(o.bed_variant==='double'){rect(c,x+w/2,y+4,2,13,'#d8cbae');rect(c,x+4,y+6,w/2-7,7,'#f7edd7');rect(c,x+w/2+4,y+6,w/2-8,7,'#f7edd7')}rect(c,x+2,y+19,w-4,h-22,'#a3b6ad');rect(c,x+2,y+20,w-4,5,'#c2d1bd');rect(c,x+5,y+27,2,h-31,'#b6c8b7');rect(c,x+2,y+h-4,w-4,3,'#92a99f');break;
      case 'wardrobe':rect(c,x+1,y+2,w-2,h-3,'#755b49');rect(c,x+3,y+1,w-6,h-5,'#b49470');rect(c,x+w/2-1,y+2,2,h-7,'#80664f');rect(c,x+6,y+5,w/2-10,h-11,'#c3a380');rect(c,x+w/2+4,y+5,w/2-10,h-11,'#c3a380');rect(c,x+w/2-7,y+11,3,5,'#e1d29d');rect(c,x+w/2+4,y+11,3,5,'#e1d29d');rect(c,x+3,y+h-5,w-6,3,'#685646');break;
      case 'side_table':rect(c,x+2,y+5,w-4,h-6,'#816953');rect(c,x+1,y+2,w-2,h-10,'#c5a47d');rect(c,x+4,y+4,w-8,2,'#e2c49a');rect(c,x+8,y+10,w-16,4,'#a78967');rect(c,x+w/2-2,y+11,4,2,'#e8d49f');break;
      case 'armchair':rect(c,x+3,y+5,w-6,h-7,'#799079');rect(c,x+4,y+2,w-8,8,'#a3b49a');rect(c,x+6,y+10,w-12,h-15,'#b6c5a6');rect(c,x+1,y+9,5,h-11,'#69816f');rect(c,x+w-6,y+9,5,h-11,'#69816f');rect(c,x+4,y+h-3,4,3,'#6e6753');rect(c,x+w-8,y+h-3,4,3,'#6e6753');break;
      case 'dining_chair':rect(c,x+3,y+4,w-6,h-7,'#94795c');rect(c,x+4,y+2,w-8,5,'#c4a177');rect(c,x+5,y+10,w-10,h-14,'#b9956b');rect(c,x+5,y+h-4,3,4,'#6e5d4b');rect(c,x+w-8,y+h-4,3,4,'#6e5d4b');break;
      case 'coat_rack':rect(c,x+10,y+3,4,h-5,'#7b6850');rect(c,x+5,y+4,14,3,'#ad906c');rect(c,x+4,y+7,4,5,'#8e7663');rect(c,x+16,y+7,4,5,'#8e7663');rect(c,x+5,y+h-4,14,3,'#685947');break;
      case 'floor_lamp':rect(c,x+11,y+8,2,h-11,'#737b68');rect(c,x+5,y+3,14,8,'#e2c997');rect(c,x+7,y+1,10,3,'#f0dba8');rect(c,x+6,y+h-4,12,3,'#6f725f');break;
      case 'hospital_bed':rect(c,x+1,y+2,w-2,h-3,'#77918f');rect(c,x+3,y+3,w-6,h-6,'#e8efdf');rect(c,x+6,y+5,Math.min(w-12,18),8,'#fcf9e6');rect(c,x+3,y+h-7,w-6,4,'#9dbbb9');break;
      case 'school_student_chair':rect(c,x+3,y+5,w-6,h-7,'#9b805f');rect(c,x+3,y+3,w-6,5,'#ccae7f');rect(c,x+5,y+h-4,3,4,'#766d57');rect(c,x+w-8,y+h-4,3,4,'#766d57');break;
      case 'school_student_desk':case 'school_desk':rect(c,x+2,y+5,w-4,h-6,'#8f7558');rect(c,x+2,y+2,w-4,h-8,'#c8a77a');rect(c,x+5,y+4,Math.min(w-10,10),Math.min(h-11,7),'#e9dfc5');rect(c,x+w-9,y+4,4,5,'#6d867a');rect(c,x+5,y+h-3,3,3,'#705f4b');rect(c,x+w-8,y+h-3,3,3,'#705f4b');break;
      case 'chalkboard':rect(c,x+2,y+2,w-4,h-5,'#836f55');rect(c,x+4,y+3,w-8,h-8,'#41675a');rect(c,x+11,y+8,Math.min(w-24,60),2,'#d8e0c7');rect(c,x+18,y+13,Math.min(w-36,42),2,'#bcd5bc');rect(c,x+4,y+h-5,w-8,3,'#b89971');rect(c,x+w-17,y+h-7,7,3,'#e5dfc4');break;
      case 'fridge':rect(c,x+2,y,w-4,h,'#d7dfcd');rect(c,x+3,y+1,w-6,h-4,'#eef0dc');rect(c,x+4,y+9,w-8,1,'#b2c5b8');rect(c,x+5,y+4,2,4,'#8fa598');rect(c,x+5,y+12,2,7,'#8fa598');break;
      case 'sink':rect(c,x,y+2,w,h-2,'#b6af92');rect(c,x,y,w,h-5,'#e3decb');rect(c,x+4,y+4,w-8,h-12,'#879d97');rect(c,x+6,y+6,w-12,h-16,'#b0c2b4');rect(c,x+10,y,3,7,'#e9eedb');break;
      case 'counter':rect(c,x,y+2,w,h-2,'#b4a587');rect(c,x,y,w,h-6,'#ded3b5');rect(c,x+6,y+3,15,13,'#9f9983');rect(c,x+8,y+5,4,4,'#5b665e');rect(c,x+15,y+11,4,4,'#5b665e');rect(c,x+32,y+6,9,8,'#ebe2c3');rect(c,x+34,y+3,5,4,'#bd8c65');break;
      case 'table':rect(c,x+4,y+5,w-5,h-1,'#9b7e56');rect(c,x+1,y,w-2,h-5,'#c3a077');rect(c,x+3,y+1,w-6,2,'#ddbb8b');rect(c,x+w-14,y+5,6,6,'#9da782');rect(c,x+w-13,y+4,4,3,'#81936a');break;
      case 'desk':rect(c,x,y+3,w,h-1,'#ab906a');rect(c,x,y,w,h-4,'#d1b587');rect(c,x+5,y+2,19,12,'#566d66');rect(c,x+7,y+3,15,8,'#a9c6bb');rect(c,x+11,y+14,9,3,'#72897b');rect(c,x+30,y+5,10,12,'#f2e9ce');rect(c,x+33,y+6,6,1,'#bfb998');rect(c,x+33,y+9,5,1,'#bfb998');rect(c,x+10,y+h+4,15,9,'#b49b72');break;
      case 'bookshelf':case 'shelf':rect(c,x,y,w,h,'#ad8c61');for(let yy=2;yy<h-2;yy+=15){rect(c,x+2,y+yy,w-4,12,'#786e52');for(let xx=3;xx<w-3;xx+=5)rect(c,x+xx,y+yy+2,3,10,['#b4ba88','#d4b080','#a1b5a3','#c18e75'][(xx+yy)%4]);rect(c,x,y+yy+12,w,3,'#c3a070')}break;
      case 'toilet':rect(c,x+5,y,w-10,8,'#f0efdd');rect(c,x+7,y+9,w-14,12,'#d8e0d2');rect(c,x+4,y+7,w-8,11,'#e9eddd');rect(c,x+7,y+10,w-14,5,'#9bb7ac');rect(c,x+15,y+2,3,2,'#a7b9ad');break;
      case 'shower':rect(c,x,y,w,h,'#bdc9ba');rect(c,x+2,y+2,w-4,h-4,'#dbe4d1');for(let yy=5;yy<h;yy+=8)rect(c,x+3,y+yy,w-6,1,'#c0d1be');rect(c,x+2,y+2,3,h-4,'#a5c4b8');rect(c,x+w-5,y+2,3,h-4,'#8db0a4');rect(c,x+7,y+2,10,3,'#839b8f');rect(c,x+11,y+4,2,8,'#afc5b6');break;
      case 'plant':rect(c,x+7,y+12,12,11,'#bb936e');rect(c,x+5,y+11,16,4,'#d4ac7e');rect(c,x+10,y+3,7,10,'#698458');rect(c,x+3,y+1,9,7,'#85a166');rect(c,x+16,y+2,7,7,'#91ac72');rect(c,x+10,y-3,6,10,'#9fb67b');break;
      case 'planter':rect(c,x,y,w,h,'#b99f76');rect(c,x+3,y+3,w-6,h-6,'#877951');for(let yy=10;yy<h-4;yy+=18)for(let xx=10;xx<w-5;xx+=18){rect(c,x+xx,y+yy,8,8,'#5d8450');rect(c,x+xx-3,y+yy,5,4,'#94ad6a');rect(c,x+xx+3,y+yy-4,5,6,'#b5c781');rect(c,x+xx+3,y+yy+4,3,3,'#bf9660')}break;
      case 'bench':rect(c,x+3,y+6,w-6,h-8,'#a6865a');rect(c,x+3,y+4,w-6,3,'#d6b784');rect(c,x+3,y+10,w-6,3,'#c5a273');rect(c,x+3,y+16,w-6,3,'#c5a273');rect(c,x+7,y+15,3,11,'#627058');rect(c,x+w-10,y+15,3,11,'#627058');rect(c,x,y+5,3,16,'#718166');rect(c,x+w-3,y+5,3,16,'#718166');break;
      case 'fountain':rect(c,x+5,y+3,w-10,h-6,'#b9c4af');rect(c,x+1,y+10,w-2,h-20,'#bdc9b5');rect(c,x+8,y+8,w-16,h-16,'#79a999');rect(c,x+12,y+12,w-24,h-24,'#a2c8b0');rect(c,x+21,y+4,6,26,'#dce5ca');rect(c,x+15,y+11,19,5,'#dce5ca');break;
      case 'cafe_counter':case 'shop_counter':rect(c,x,y,w,h,'#a4835d');rect(c,x,y,w,h-6,'#d6b584');rect(c,x+7,y+3,15,13,'#74847c');rect(c,x+9,y+5,11,6,'#bacab6');rect(c,x+31,y+5,13,8,'#e6d9af');rect(c,x+33,y+5,4,4,'#ad7c4d');rect(c,x+39,y+6,3,3,'#ad7c4d');for(let xx=55;xx<w-5;xx+=15)rect(c,x+xx,y+5,8,8,'#b0b786');break;
      case 'supermarket_checkout':case 'mall_counter':rect(c,x,y+3,w,h-3,'#937a62');rect(c,x,y,w,h-5,'#d0ad79');rect(c,x+5,y+3,14,11,'#779985');rect(c,x+7,y+5,10,7,'#c6d3b9');for(let xx=26;xx<w-5;xx+=12){rect(c,x+xx,y+5,8,7,'#b8a270');rect(c,x+xx+2,y+3,4,3,'#889b70')}break;
      case 'gym_station':case 'nightclub_floor':case 'townhall_desk':case 'hospital_desk':case 'fire_stationdesk':case 'office_station':rect(c,x,y+3,w,h-3,'#786f62');rect(c,x,y,w,h-5,o.kind==='hospital_desk'?'#d6e0d5':o.kind==='nightclub_floor'?'#977b9d':'#bba47f');for(let xx=5;xx<w-5;xx+=17){rect(c,x+xx,y+4,11,8,o.kind==='gym_station'?'#718982':o.kind==='nightclub_floor'?'#b98cb7':'#738d86');rect(c,x+xx+2,y+5,7,4,'#dce3c7')}break;
      case 'bin':rect(c,x+5,y+5,15,16,'#6f7f68');rect(c,x+4,y+3,17,4,'#8fa184');rect(c,x+7,y+9,2,9,'#8e9d80');rect(c,x+16,y+9,2,9,'#526c5c');break;
      case 'teacher_station':case 'illustrator_station':case 'designer_station':
      case 'carpenter_station':case 'tailor_station':case 'gardener_station':{
        const wood=o.kind==='teacher_station'?'#bd9d70':o.kind==='gardener_station'?'#9eae7b':'#ae8d67';
        rect(c,x,y+3,w,h-2,'#806d59');rect(c,x,y,w,h-6,wood);rect(c,x+3,y+1,w-6,2,'#dfc8a0');
        for(let i=0;i<o.anchors.length;i++){const sx=x+i*T+5;
          if(o.kind==='teacher_station'){rect(c,sx,y+5,13,8,'#e9dfbf');rect(c,sx+2,y+8,8,1,'#a1aa8c')}
          else if(o.kind==='gardener_station'){rect(c,sx+2,y+2,7,8,'#718d65');rect(c,sx+1,y+9,11,4,'#b69368')}
          else if(o.kind==='tailor_station'){rect(c,sx+2,y+4,10,6,'#c4b8a2');rect(c,sx+6,y+2,2,3,'#718a80')}
          else if(o.kind==='carpenter_station'){rect(c,sx+1,y+4,12,3,'#9c7758');rect(c,sx+5,y+2,3,8,'#687568')}
          else{rect(c,sx+1,y+3,12,8,'#5c736d');rect(c,sx+3,y+4,8,5,'#acc6b4')}
        }
        break;
      }
      default:rect(c,x+2,y+3,w-4,h-4,'#8c856d');rect(c,x+2,y+1,w-4,h-8,'#b9aa86');rect(c,x+5,y+4,Math.min(13,w-10),Math.min(8,h-10),'#d8d5b8');break;
    }
  }
  drawEverydayOverlay(c,o,daily){
    if(!daily)return;
    const x=o.x*T,y=o.y*T,w=o.w*T;
    if(o.kind==='table'){
      const served=Math.min(3,daily.served_meals||0),dirty=Math.min(3,daily.dirty_dishes||0);
      for(let i=0;i<served;i++){const px=x+Math.min(w-13,7+i*15);rect(c,px,y+3,12,10,'#eee7d0');rect(c,px+2,y+4,8,7,'#b7b38c');rect(c,px+3,y+5,6,4,'#cf9163');rect(c,px+7,y+4,3,2,'#70915a')}
      for(let i=0;i<dirty;i++){const px=x+Math.min(w-13,7+(i+served)*13);rect(c,px,y+3,11,9,'#d2d4c8');rect(c,px+2,y+4,7,5,'#8f9d91');rect(c,px+4,y+5,3,2,'#9b8064')}
    }else if(o.kind==='counter'&&daily.mess){
      const count=Math.min(4,daily.mess);for(let i=0;i<count;i++){const px=x+23+i*6;rect(c,px,y+7,5,2,'#977659');rect(c,px+2,y+5,3,2,'#ae8b65')}
      if(daily.oven_item_id){rect(c,x+8,y+6,15,10,'#4c5b56');rect(c,x+10,y+7,11,7,'#e2bf78');rect(c,x+13,y+8,5,3,'#bd604b')}
    }else if(o.kind==='counter'&&daily.oven_item_id){
      rect(c,x+8,y+6,15,10,'#4c5b56');rect(c,x+10,y+7,11,7,'#e2bf78');rect(c,x+13,y+8,5,3,'#bd604b');
    }else if(o.kind==='bin'&&daily.trash){
      rect(c,x+6,y+4,13,3,'#5f5949');rect(c,x+8,y+2,4,3,'#a08962');rect(c,x+14,y+1,3,3,'#73865a');
    }
  }
  buildRoofs(){for(const b of this.world.buildings){const padding=18,w=b.w*T,h=b.h*T,p=palettes[(b.palette??0)%palettes.length];const roof=document.createElement('canvas');roof.width=w+padding*2+10;roof.height=h+padding*2+20;const c=roof.getContext('2d');c.translate(padding,padding);c.imageSmoothingEnabled=false;
    rect(c,7,15,w+4,h+5,'#4760443b');rect(c,-3,h-54,w+6,62,p.wall);rect(c,0,h-19,w,14,p.trim);
    // Windows and shutters on the south façade.
    for(const xx of [1.5*T,w-3.6*T]){rect(c,xx-4,h-42,36,26,p.trim);rect(c,xx,h-40,28,22,'#6e9a95');rect(c,xx+2,h-39,24,8,'#bbd2be');rect(c,xx+13,h-40,2,22,'#f2e8c8');rect(c,xx,h-29,28,2,'#f2e8c8');rect(c,xx-5,h-41,4,22,p.dark);rect(c,xx+29,h-41,4,22,p.dark);rect(c,xx-4,h-17,36,4,'#a39671');for(let k=0;k<5;k++){rect(c,xx+k*6,h-17,4,4,'#6f8c55');rect(c,xx+k*6+1,h-19,3,3,k%2?'#d4af77':'#bd8b70')}}
    const dx=b.door[0]*T-b.x*T;rect(c,dx-1,h-39,26,41,p.dark);rect(c,dx+2,h-35,20,34,'#b99868');rect(c,dx+5,h-32,14,17,'#95b0a0');rect(c,dx+17,h-13,2,3,'#efe0ad');
    const rh=h-48;rect(c,-10,-8,w+20,rh+12,p.dark);rect(c,-8,-13,w+16,rh+9,p.roof);
    // Stepped hip-roof silhouette with shingle courses and central ridge.
    rect(c,2,-21,w-4,9,p.light);rect(c,13,-28,w-26,8,p.light);rect(c,22,-33,w-44,6,p.light);
    for(let yy=-8;yy<rh-5;yy+=11){rect(c,-7,yy,w+14,2,p.dark+'70');for(let xx=-5+(Math.floor(yy/11)%2)*15;xx<w;xx+=29){rect(c,xx,yy+2,1,8,p.light+'90');rect(c,xx+2,yy+3,22,1,p.light+'66')}}
    rect(c,-7,rh-2,w+14,4,p.light);rect(c,-10,rh+2,w+20,5,p.dark);
    if(b.household_id && b.palette%2===0){const wx=w*.46,wy=rh*.46;rect(c,wx-6,wy,42,31,p.dark);rect(c,wx-3,wy-3,36,29,p.wall);rect(c,wx+3,wy+3,24,17,'#96b0a1');rect(c,wx+5,wy+4,20,6,'#bed0b5');rect(c,wx+14,wy+3,2,17,'#ece3c2');rect(c,wx-8,wy-6,46,6,p.light);rect(c,wx-3,wy-10,36,4,p.light);rect(c,wx+2,wy-14,26,4,p.light)}
    // Sunlit left hip and chimney bring depth without changing logical bounds.
    c.fillStyle=p.light+'55';c.beginPath();c.moveTo(22,-32);c.lineTo(22,rh);c.lineTo(-7,rh);c.lineTo(-7,-8);c.closePath();c.fill();
    rect(c,w-58,-29,24,37,'#897862');rect(c,w-55,-29,17,34,'#bfaa84');rect(c,w-60,-32,27,7,'#dec7a0');rect(c,w-55,-29,17,3,'#726950');for(let yy=-20;yy<5;yy+=8)rect(c,w-54,yy,16,1,'#a48b70');
    if(!b.household_id){const color=b.id==='cafe'?'#d7c39a':b.id==='school'?'#bfd0bb':'#b6c4a5';for(let i=0;i<7;i++)rect(c,dx-63+i*22,h-57,22,18,i%2?color:'#f0e4bc');rect(c,dx-63,h-39,154,5,p.dark);c.font='bold 10px monospace';c.textAlign='center';c.fillStyle='#ede4c4';c.fillText(publicSigns[b.id]||b.name.toUpperCase(),w/2,rh-30)}
    this.roofCache.set(b.id,{image:roof,offset:padding});}}
  roofVisible(b){if(this.roofs==='open')return false;if(this.roofs==='closed')return true;const selected=this.state?.actors.find(a=>a.id===this.selected);if(b.id===this.openBuilding||b.id===selected?.home_id)return false;if(selected){const p=selected.position;if(p[0]>=b.x&&p[0]<b.x+b.w&&p[1]>=b.y&&p[1]<b.y+b.h)return false}return true}
  frame(time){if(!this.running)return;const delta=Math.min((time-this.lastFrame)/1000,.1);this.lastFrame=time;this.frameTimes.push(delta);if(this.frameTimes.length>60)this.frameTimes.shift();this.fps=Math.round(this.frameTimes.length/this.frameTimes.reduce((a,b)=>a+b,0));
    const move=360*delta/this.camera.zoom;if(this.keys.size){this.follow=false;if(this.keys.has('ArrowLeft')||this.keys.has('a'))this.camera.x-=move;if(this.keys.has('ArrowRight')||this.keys.has('d'))this.camera.x+=move;if(this.keys.has('ArrowUp')||this.keys.has('w'))this.camera.y-=move;if(this.keys.has('ArrowDown')||this.keys.has('s'))this.camera.y+=move;this.constrain()}
    if(this.follow){const a=this.state?.actors.find(a=>a.id===this.selected);if(a){const p=this.actorPosition(a,time);this.camera.x+=(p[0]*T-this.camera.x)*Math.min(1,delta*8);this.camera.y+=(p[1]*T-this.camera.y)*Math.min(1,delta*8)}}
    this.render(time);requestAnimationFrame(t=>this.frame(t));
  }
  render(time){const c=this.ctx,z=this.camera.zoom;document.querySelector('.neighborhood-card')?.classList.toggle('hidden',z>=.9);c.setTransform(this.dpr,0,0,this.dpr,0,0);c.imageSmoothingEnabled=false;rect(c,0,0,this.width,this.height,'#b1be90');c.save();c.translate(this.width/2-this.camera.x*z,this.height/2-this.camera.y*z);c.scale(z,z);
    const left=Math.max(0,this.camera.x-this.width/z/2),top=Math.max(0,this.camera.y-this.height/z/2),right=Math.min(this.base.width,this.camera.x+this.width/z/2),bottom=Math.min(this.base.height,this.camera.y+this.height/z/2);
    if(right>left&&bottom>top)c.drawImage(this.base,left,top,right-left,bottom-top,left,top,right-left,bottom-top);
    for(const resource of this.state?.resources||[]){
      const o=this.objectById.get(resource.id);if(!o||!resource.daily)continue;
      if(o.x*T>right||o.y*T>bottom||(o.x+o.w)*T<left||(o.y+o.h)*T<top)continue;
      this.drawEverydayOverlay(c,o,resource.daily);
    }
    if(this.grid){c.strokeStyle='#f5f5d144';c.lineWidth=1/z;for(let x=Math.floor(left/T)*T;x<right;x+=T){c.beginPath();c.moveTo(x,top);c.lineTo(x,bottom);c.stroke()}for(let y=Math.floor(top/T)*T;y<bottom;y+=T){c.beginPath();c.moveTo(left,y);c.lineTo(right,y);c.stroke()}
      for(const o of this.world.objects){c.strokeStyle='#608e88aa';c.lineWidth=1/z;c.strokeRect(o.x*T,o.y*T,o.w*T,o.h*T);for(const a of o.anchors)rect(c,a[0]*T+9,a[1]*T+9,6,6,'#ebe8a5')}}
    for(const b of this.world.buildings){if(b.x*T>right||b.y*T>bottom||(b.x+b.w)*T<left||(b.y+b.h)*T<top)continue;if(this.roofVisible(b)){const r=this.roofCache.get(b.id);c.drawImage(r.image,b.x*T-r.offset,b.y*T-r.offset)}}
    const inspected=this.objectById.get(this.selectedObject);if(inspected){const building=this.world.buildings.find(b=>b.id===inspected.building_id);if(!building||!this.roofVisible(building)){c.fillStyle='#fff2b533';c.fillRect(inspected.x*T,inspected.y*T,inspected.w*T,inspected.h*T);c.strokeStyle='#fff3b0';c.lineWidth=2/z;c.strokeRect(inspected.x*T,inspected.y*T,inspected.w*T,inspected.h*T);for(const [ax,ay] of inspected.anchors||[]){c.strokeStyle='#487d73';c.strokeRect(ax*T+4,ay*T+4,T-8,T-8)}}}
    for(const animal of this.state?.animals||[]){
      const p=animal.position;if(!Array.isArray(p)||p.length<2)continue;
      const x=(p[0]+.5)*T,y=(p[1]+.72)*T;
      if(x<left-20||x>right+20||y<top-20||y>bottom+20)continue;
      drawDog(c,x,y,this.state.paused?0:time);
    }
    // Selected trajectory uses the actual A* path accepted by the coordinator.
    const selected=this.state?.actors.find(a=>a.id===this.selected);if(selected?.action?.phase==='travel'){const path=selected.action.path;const passed=Math.max(0,this.state.clock-selected.action.started_at);c.strokeStyle='#f5f4cc9c';c.lineWidth=2/z;c.setLineDash([3/z,5/z]);c.beginPath();path.slice(passed).forEach((p,i)=>i?c.lineTo((p[0]+.5)*T,(p[1]+.6)*T):c.moveTo((p[0]+.5)*T,(p[1]+.6)*T));c.stroke();c.setLineDash([])}
    this.hitPeople=[];const people=(this.state?.actors||[]).map(a=>({actor:a,pos:this.actorPosition(a,time)})).sort((a,b)=>a.pos[1]-b.pos[1]);
    for(const {actor:a,pos} of people){const x=pos[0]*T,y=pos[1]*T;if(x<left-20||x>right+20||y<top-40||y>bottom+40)continue;const b=this.world.buildings.find(b=>pos[0]>=b.x&&pos[0]<b.x+b.w&&pos[1]>=b.y&&pos[1]<b.y+b.h);const concealed=b&&this.roofVisible(b);const isSelected=a.id===this.selected;const screen=this.screenAt(x,y);
      if(concealed){c.globalAlpha=.88;rect(c,x-4,y-5,8,8,isSelected?'#e8efba':'#f2e5bc');rect(c,x-2,y-3,4,4,a.appearance.shirt);c.globalAlpha=1;this.hitPeople.push({id:a.id,x:screen.x,y:screen.y,size:10});continue}
      if(isSelected){c.strokeStyle='#f7f1c0';c.lineWidth=2/z;c.beginPath();c.ellipse(x,y,12,6,0,0,Math.PI*2);c.stroke();const yy=y-42+Math.sin(time*.003)*2;c.fillStyle='#e2eabb';c.beginPath();c.moveTo(x,yy-6);c.lineTo(x+5,yy);c.lineTo(x,yy+7);c.lineTo(x-5,yy);c.closePath();c.fill();rect(c,x-1,yy-2,2,5,'#a1b986')}
      let direction=0;if(a.action?.phase==='travel'){const i=Math.min(a.action.path.length-2,Math.max(0,Math.floor(this.state.clock-a.action.started_at)));if(i>=0&&a.action.path[i+1][1]<a.action.path[i][1])direction=3}
      const sitting=a.action?.phase==='using'&&['eat','eat_meal','eat_recipe'].includes(a.action.kind)&&this.objectById.get(a.action.target_id)?.kind==='table';
      drawPerson(c,a.appearance,x,y,{walking:a.action?.phase==='travel'&&!this.state.paused,time:this.state.paused?0:time/1000,direction,selected:isSelected,sleeping:a.action?.kind==='sleep',sitting});
      if(a.carried)drawCarried(c,a.carried,x,y);
      if(z>.85)drawEmotion(c,a,x,y);
      if(a.action?.kind==='chat'){rect(c,x+9,y-33,16,12,'#faf7df');rect(c,x+9,y-22,4,4,'#faf7df');for(let k=0;k<3;k++)rect(c,x+12+k*4,y-28,2,2,'#9ca581')}
      if(a.action?.kind==='sleep'){c.font='10px monospace';c.fillStyle='#f6f2d0';c.fillText('z',x+10,y-35)}
      this.hitPeople.push({id:a.id,x:screen.x,y:screen.y,size:24*z});
    }
    // Night is presentation derived from the authoritative clock.
    const hour=(this.state?.clock||29700)/3600%24;const night=hour<5||hour>21?.29:hour<7||hour>19?.13:0;
    if(night){rect(c,left,top,right-left,bottom-top,`rgba(34,51,81,${night})`);for(const d of this.world.decorations.filter(d=>d.kind==='lamp')){const x=(d.x+.5)*T,y=(d.y+.7)*T;c.fillStyle='#ffe1a521';c.beginPath();c.arc(x,y,35,0,Math.PI*2);c.fill();rect(c,x-3,y-21,7,6,'#f1d18d')}}
    c.restore();
    // World lettering stays readable at neighborhood scale.
    if(z<.8){c.textAlign='center';c.fillStyle='#6e715ec9';c.font='500 8px "Segoe UI", sans-serif';
      if(this.mapPlan?.roads?.length){const named=new Map();for(const road of this.mapPlan.roads){if(!road.name||road.class==='pedestrian')continue;const existing=named.get(road.name);if(!existing||road.bounds[2]*road.bounds[3]>existing.bounds[2]*existing.bounds[3])named.set(road.name,road)}
        for(const road of named.values()){const [rx,ry,rw,rh]=road.bounds,s=this.screenAt((rx+rw/2)*T,(ry+rh/2)*T);if(s.x<0||s.x>this.width||s.y<0||s.y>this.height)continue;c.save();c.translate(s.x,s.y);if(rh>rw)c.rotate(-Math.PI/2);c.fillText(road.name.toUpperCase(),0,-4);c.restore()}
        c.fillStyle='#f3f1d7';c.font='italic 15px Georgia';for(const park of this.mapPlan.parks||[]){const [px,py,pw,ph]=park.bounds,s=this.screenAt((px+pw/2)*T,(py+ph/2)*T);if(s.x>0&&s.x<this.width&&s.y>0&&s.y<this.height)c.fillText(park.name,s.x,s.y)}
      }else{for(const [name,y] of [['W I L L O W   L A N E',24.5],['C L O V E R   S T R E E T',48.5],['M A P L E   R O W',70.5],['F E R N   W A L K',94.5]]){const s=this.screenAt(64*T,y*T);if(s.y>5&&s.y<this.height)c.fillText(name,s.x,s.y-4)}const park=this.screenAt(49*T,59*T);c.fillStyle='#f3f1d7';c.font='italic 15px Georgia';c.fillText('Clover Green',park.x,park.y)}}
    if(z>.42&&z<1){c.font='8px "Segoe UI", sans-serif';for(const b of this.world.buildings.filter(b=>b.household_id)){const s=this.screenAt((b.x+7.5)*T,(b.y+b.h+2.4)*T);if(s.x>0&&s.x<this.width&&s.y>0&&s.y<this.height){c.fillStyle='#5a7350';c.fillText(b.name.replace(' house',''),s.x,s.y)}}}
    if(z>.25&&z<.65){c.textAlign='center';c.font='600 9px "Segoe UI",sans-serif';for(const b of this.world.buildings.filter(b=>!b.household_id)){const s=this.screenAt((b.x+b.w/2)*T,(b.y+b.h+2.2)*T);if(s.x<0||s.x>this.width||s.y<0||s.y>this.height)continue;const label=b.name,w=c.measureText(label).width+12;rect(c,s.x-w/2,s.y-10,w,15,'#fffbeacb');c.fillStyle='#526f57';c.fillText(label,s.x,s.y+1)}}
    if(selected){const p=this.actorPosition(selected,time),s=this.screenAt(p[0]*T,p[1]*T);if(s.x>0&&s.x<this.width&&s.y>0&&s.y<this.height){const name=selected.name.split(' ')[0];c.font='500 10px "Segoe UI",sans-serif';const w=c.measureText(name).width+17;rect(c,s.x-w/2,s.y+9,w,18,'#fffcece8');c.fillStyle='#627b50';c.textAlign='center';c.fillText(name,s.x,s.y+21)}}
    this.renderMinimap();document.getElementById('zoom-label').textContent=Math.round(z*100)+'%';const bar=document.querySelector('.scale-bar>span');bar.style.width=10*T*z+'px';
  }
  renderMinimap(){const c=this.mctx,w=this.mini.width,h=this.mini.height;c.imageSmoothingEnabled=false;c.clearRect(0,0,w,h);c.drawImage(this.base,0,0,w,h);for(const b of this.world.buildings){const p=palettes[(b.palette??0)%palettes.length];rect(c,b.x/this.world.width*w,b.y/this.world.height*h,b.w/this.world.width*w,b.h/this.world.height*h,p.roof)}for(const a of this.state?.actors||[]){rect(c,a.position[0]/this.world.width*w,a.position[1]/this.world.height*h,2,2,a.id===this.selected?'#fff6c5':'#436b4c')}for(const a of this.state?.animals||[]){const p=a.position;if(Array.isArray(p))rect(c,p[0]/this.world.width*w,p[1]/this.world.height*h,2,2,'#b68a61')}c.strokeStyle='#faffd1';c.lineWidth=1.5;const left=(this.camera.x-this.width/this.camera.zoom/2)/(this.world.width*T)*w,top=(this.camera.y-this.height/this.camera.zoom/2)/(this.world.height*T)*h;c.strokeRect(left,top,this.width/this.camera.zoom/(this.world.width*T)*w,this.height/this.camera.zoom/(this.world.height*T)*h)}
  screenshot(){return this.canvas.toDataURL('image/png')}
}
