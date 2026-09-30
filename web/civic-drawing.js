/* Civic sprites in the same 24-pixel-per-meter local frame as furnitureSprite.
 * This file has no imports so it can be embedded in the offline report. */
export function drawCivicObject(c,o,palette){
  const s=24,w=o.base_w*s,h=o.base_h*s;
  const fill=(x,y,ww,hh,color)=>{c.fillStyle=color;c.fillRect(x,y,ww,hh)};
  const stroke=(x,y,ww,hh,color,line=1)=>{c.strokeStyle=color;c.lineWidth=line;c.strokeRect(x,y,ww,hh)};
  const wood='#b08b62',top='#d3b38a',dark='#52645b',cream='#f1e7cf',fabric=(palette&&palette.fabric)||'#8aa486',accent=(palette&&palette.accent)||'#b48267';
  fill(2,3,w-4,h-3,'#35493520');
  switch(o.kind){
    case 'school_teacher_desk':case 'civic_staff_desk':
      fill(1,4,w-2,h-5,wood);fill(2,1,w-4,h-8,top);fill(5,4,w-10,8,cream);fill(w-18,5,10,8,'#758f80');fill(7,h-3,w-14,3,dark);break;
    case 'school_student_desk':case 'civic_cafeteria_table':
      fill(2,4,w-4,h-6,wood);fill(1,1,w-2,h-9,top);fill(6,5,w-12,7,cream);fill(w/2-2,h-3,4,3,dark);
      if(o.kind==='civic_cafeteria_table'){fill(3,0,w-6,2,fabric);fill(3,h-2,w-6,2,fabric)}break;
    case 'school_student_chair':
      fill(3,2,w-6,6,wood);fill(4,3,w-8,4,fabric);fill(3,10,w-6,9,wood);fill(5,11,w-10,6,fabric);
      fill(5,h-4,3,4,dark);fill(w-8,h-4,3,4,dark);break;
    case 'school_chalkboard':
      fill(1,1,w-2,h-2,wood);fill(4,4,w-8,h-8,'#456b61');fill(8,7,w-18,1,'#ecedcf');fill(8,11,w-24,1,'#cfdbc1');fill(8,h-6,w-16,2,top);break;
    case 'school_lab_bench':
      fill(1,5,w-2,h-6,wood);fill(2,1,w-4,h-9,'#b8c7b7');fill(5,4,w-10,8,'#d7e6d5');fill(8,5,7,6,'#89aba0');fill(w-17,4,9,8,'#e6e2ca');fill(4,h-3,w-8,3,dark);break;
    case 'school_microscope':
      fill(5,h-7,w-10,4,wood);fill(w/2-3,5,6,12,'#62796e');fill(w/2-5,3,10,4,'#b8cbb8');fill(w/2-6,15,12,3,'#d2c69f');fill(w/2-2,8,4,3,'#43564e');break;
    case 'school_model_skeleton':
      fill(w/2-1,3,2,h-7,'#e5dcc6');fill(w/2-5,3,10,3,'#e5dcc6');fill(w/2-6,8,12,2,'#e5dcc6');fill(w/2-5,12,10,2,'#e5dcc6');fill(w/2-7,h-8,3,6,'#e5dcc6');fill(w/2+4,h-8,3,6,'#e5dcc6');fill(w/2-5,5,3,2,dark);fill(w/2+2,5,3,2,dark);break;
    case 'school_physics_demo':
      fill(1,5,w-2,h-6,wood);fill(2,1,w-4,h-9,top);fill(5,4,w-10,8,'#d8e3d5');fill(7,6,6,5,'#6d8a80');fill(16,5,2,8,dark);fill(14,4,7,2,accent);fill(20,9,3,3,'#d4bb73');fill(4,h-3,w-8,3,dark);break;
    case 'school_supply_cabinet':case 'civic_locker_bank':case 'fire_gear_rack':case 'civic_archive_shelf':
      fill(1,1,w-2,h-2,wood);fill(3,3,w-6,h-5,'#8b795d');
      for(let xx=5;xx<w-5;xx+=o.kind==='civic_locker_bank'?18:12){
        if(o.kind==='civic_locker_bank'){fill(xx,4,15,h-8,'#97a99a');fill(xx+11,8,2,3,'#e4d8b9');fill(xx+4,h-9,8,1,'#788c80')}
        else if(o.kind==='fire_gear_rack'){fill(xx,5,8,12,'#b66c4d');fill(xx+1,4,6,3,'#e2c58b');fill(xx+2,17,4,3,'#726b55')}
        else {fill(xx,5,8,9,[accent,fabric,'#d2bd82'][Math.floor(xx/12)%3]);fill(xx,15,8,2,top)}
      }break;
    case 'civic_safety_station':
      fill(3,1,w-6,h-2,'#d9d7c2');stroke(3,1,w-6,h-2,'#789082',2);fill(w/2-3,4,6,10,'#b85c49');fill(w/2-1,6,2,6,cream);fill(w/2-3,8,6,2,cream);fill(6,h-5,w-12,1,dark);break;
    case 'civic_cafeteria_counter':case 'civic_reception_desk':
      fill(1,5,w-2,h-6,wood);fill(0,1,w,h-8,top);fill(4,4,w-8,8,cream);fill(w-17,4,10,9,'#7f9b8e');fill(7,h-2,w-14,2,dark);
      if(o.kind==='civic_reception_desk'){fill(w/2-5,6,10,5,'#647a70');fill(w/2-2,7,4,2,'#d3dabb')}break;
    case 'clinic_exam_table':case 'hospital_bed':
      fill(1,1,w-2,h-2,'#a88866');fill(3,4,w-6,h-8,'#e6e5d5');fill(4,7,w-8,Math.max(5,h*.28),fabric);fill(4,4,w-8,3,'#faf1dc');
      if(o.kind==='hospital_bed'){fill(2,1,w-4,3,'#87998c');fill(w-7,4,3,h-9,'#b3c2b4');fill(5,h-4,4,3,dark);fill(w-9,h-4,4,3,dark)}
      else {fill(6,h-7,w-12,2,'#b6c7b7');fill(w-7,3,3,5,'#d8dfcf')}break;
    case 'clinic_screen':
      fill(2,2,w-4,h-4,'#d5ddcf');fill(4,4,w-8,h-8,'#e6eadc');fill(3,1,2,h-2,wood);fill(w-5,1,2,h-2,wood);fill(4,h-4,w-8,1,'#b7c9b8');break;
    case 'clinic_cart':case 'civic_service_kiosk':
      fill(3,2,w-6,h-7,'#d9dfcf');stroke(3,2,w-6,h-7,'#82998b',1);fill(6,5,w-12,6,'#637f76');fill(8,6,w-16,3,'#b4d0be');fill(5,h-5,w-10,2,dark);
      if(o.kind==='clinic_cart'){fill(3,h-3,3,3,dark);fill(w-6,h-3,3,3,dark)}else{fill(7,h-8,w-14,2,top);fill(w/2-2,13,4,4,accent)}break;
    case 'hospital_bedside_stand':
      fill(2,5,w-4,h-6,wood);fill(1,2,w-2,h-9,top);fill(5,5,w-10,5,'#e2e4d5');fill(w/2-2,12,4,2,dark);fill(5,h-2,w-10,2,dark);break;
    case 'civic_waiting_bench':
      fill(2,3,w-4,5,wood);fill(1,7,w-2,7,fabric);fill(3,14,w-6,3,wood);fill(5,16,3,h-17,dark);fill(w-8,16,3,h-17,dark);break;
    case 'fire_dispatch_console':
      fill(1,5,w-2,h-6,wood);fill(1,1,w-2,h-8,'#64766d');fill(4,3,w-8,11,'#9db9aa');
      for(let xx=6;xx<w-6;xx+=9){fill(xx,5,5,5,xx%2?'#d2c581':'#7f9d83');fill(xx+1,13,3,2,'#e5dfc5')}fill(5,h-3,w-10,3,dark);break;
    case 'fire_engine_bay':
      fill(2,2,w-4,h-4,'#c3b99f');fill(5,5,w-10,h-10,'#a94f3f');fill(8,8,w-16,7,'#cfddcf');fill(10,9,w-20,4,'#8ea99d');fill(4,16,w-8,3,'#e4d9b8');
      fill(6,h-8,10,7,'#4a544e');fill(w-16,h-8,10,7,'#4a544e');fill(8,h-6,6,4,'#aeb9a8');fill(w-14,h-6,6,4,'#aeb9a8');fill(7,3,w-14,2,'#ded5bb');break;
    default:return false;
  }
  return true;
}
