"""Append a traversable campus and exploded, portal-linked dormitory floors.

Every coordinate remains a one-meter tile. Upper floors are drawn as separate
cutaway slabs south of the street, while stair portals are the only graph edges
between them. This keeps the existing 2-D renderer and saved coordinates intact.
"""
from array import array

from .spatial import GRASS, ROAD, PATH, FLOOR, WALL

HEIGHT = 326
VERSION = 1


def _room(sp, bid, key, name, bounds, floor):
    sp.regions.append({'id': f'{bid}_{key}', 'name': name, 'bounds': list(bounds),
                       'parent': bid, 'floor': floor})


def _object(sp, bid, kind, name, x, y, w=1, h=1, *, anchor=None, household=None,
            capacity=1, blocking=True, floor=0, **extra):
    oid = sp.add_object(kind, name, x, y, w, h,
                        anchors=anchor or [[x, y + h]], household=household, building=bid,
                        capacity=capacity, blocking=blocking)
    sp.objects[oid]['floor'] = floor
    sp.objects[oid].update(extra)
    return oid


def _divider(sp, x, y, length, *, horizontal=True, door=None):
    if horizontal:
        sp.rect(x, y, length, 1, WALL)
        if door is not None:
            sp.rect(door, y, 1, 1, FLOOR)
    else:
        sp.rect(x, y, 1, length, WALL)
        if door is not None:
            sp.rect(x, door, 1, 1, FLOOR)


def _campus_university(sp):
    bid, x, y, w, h = 'university', 5, 220, 68, 25
    door = sp.building(bid, 'Mosswood University', x, y, w, h, 3)
    sp.buildings[-1].update(service_kind='university', floor=0,
                            campus_program='teaching, research, library, dining, administration')
    _divider(sp, x+1, y+10, w-2)
    _divider(sp, x+1, y+14, w-2)
    top = [(x+1, x+25, 'lecture', 'Lecture theatre'),
           (x+26, x+38, 'seminar', 'Seminar room'),
           (x+39, x+53, 'biology_lab', 'Biology laboratory'),
           (x+54, x+w-1, 'physics_lab', 'Physics laboratory')]
    bottom = [(x+1, x+21, 'cafeteria', 'Campus cafeteria'),
              (x+22, x+32, 'library', 'University library'),
              (x+33, x+43, 'lobby', 'Admissions and entrance'),
              (x+44, x+55, 'administration', 'Administrative offices'),
              (x+56, x+w-1, 'toilets', 'Campus toilets')]
    for sections, start, height, wall_y in ((top,y+1,9,y+10),(bottom,y+15,9,y+14)):
        for left,right,key,label in sections:
            _room(sp,bid,key,label,(left,start,right-left,height),0)
            center=(left+right)//2
            sp.rect(center,wall_y,1,1,FLOOR)
        for _,right,_,_ in sections[:-1]:
            sp.rect(right,start,1,height,WALL)
    # The entrance crosses the lobby without passing through a workstation.
    sp.rect(door[0],y+14,1,1,FLOOR)
    _object(sp,bid,'lecture_screen','Lecture screen',x+3,y+1,5,1,anchor=[[x+8,y+2]])
    _object(sp,bid,'lectern','Lecture lectern',x+11,y+1,2,1,anchor=[[x+12,y+2]])
    for row in range(4):
        for col in range(5):
            xx,yy=x+3+4*col,y+2+2*row
            _object(sp,bid,'lecture_desk',f'Lecture desk {row*5+col+1}',xx,yy,
                    anchor=[[xx,yy+1]])
            _object(sp,bid,'lecture_seat',f'Lecture seat {row*5+col+1}',xx,yy+1,
                    anchor=[[xx,yy+1]],blocking=False)
    _object(sp,bid,'seminar_table','Seminar discussion table',x+29,y+3,6,2,
            anchor=[[x+29+i,y+5] for i in range(6)]+[[x+30,y+2],[x+33,y+2]],capacity=8)
    for label,xx in (('Biology',x+42),('Physics',x+57)):
        key='biology_bench' if label=='Biology' else 'physics_bench'
        _object(sp,bid,key,label+' experiment bench',xx,y+3,4,1,
                anchor=[[xx+1,y+4],[xx+2,y+4]],capacity=2)
        _object(sp,bid,'lab_cabinet',label+' safety cabinet',xx,y+1,2,1,
                anchor=[[xx,y+2]])
    for i in range(3):
        xx=x+3+5*i
        _object(sp,bid,'cafeteria_table',f'Campus dining table {i+1}',xx,y+17,2,1,
                anchor=[[xx,y+18],[xx+1,y+18],[xx,y+16],[xx+1,y+16]],capacity=4)
    _object(sp,bid,'cafe_counter','Campus cafeteria counter',x+3,y+22,7,1,
            anchor=[[x+4,y+21],[x+6,y+21],[x+8,y+21]],capacity=3)
    _object(sp,bid,'bookshelf','Academic bookshelves',x+28,y+16,3,1,
            anchor=[[x+29,y+17]])
    _object(sp,bid,'library_desk','Study desks',x+28,y+19,3,1,
            anchor=[[x+28,y+20],[x+29,y+20],[x+30,y+20],[x+29,y+18]],capacity=4)
    _object(sp,bid,'university_desk','Admissions desk',x+39,y+17,3,1,
            anchor=[[x+40,y+18],[x+41,y+18]],capacity=2)
    _object(sp,bid,'office_station','Campus administration workstations',x+49,y+17,5,1,
            anchor=[[x+49+i,y+18] for i in range(5)],capacity=5)
    for i in range(2):
        _object(sp,bid,'toilet',f'Campus toilet {i+1}',x+62+3*i,y+17,
                anchor=[[x+62+3*i,y+18]])
    return door


def _dorm_ground(sp):
    bid,x,y,w,h='student_dorm',81,220,38,25
    resident='student_residence'
    door=sp.building(bid,'Willow Hall student residence',x,y,w,h,1)
    sp.buildings[-1].update(service_kind='student_dorm',floor=0,
                            floor_ids=['student_dorm','student_dorm_floor_1','student_dorm_floor_2'])
    _divider(sp,x+1,y+10,w-2)
    _divider(sp,x+1,y+14,w-2)
    for split in (x+13,x+25):
        sp.rect(split,y+1,1,9,WALL)
        sp.rect(split,y+15,1,9,WALL)
    for xx,key,label in ((x+7,'kitchen','Shared kitchen'),(x+19,'party','Common party room'),
                         (x+31,'gym','Residence gym')):
        sp.rect(xx,y+10,1,1,FLOOR)
        _room(sp,bid,key,label,(xx-6,y+1,11,9),0)
    for xx,key,label in ((x+7,'lounge','Resident lounge'),(x+19,'lobby','Stair lobby'),
                         (x+31,'laundry','Laundry and storage')):
        sp.rect(xx,y+14,1,1,FLOOR)
        _room(sp,bid,key,label,(xx-6,y+15,11,9),0)
    _object(sp,bid,'fridge','Shared refrigerator',x+2,y+2,anchor=[[x+2,y+3]],household=resident)
    _object(sp,bid,'sink','Shared kitchen sink',x+4,y+2,anchor=[[x+4,y+3]],household=resident)
    _object(sp,bid,'counter','Shared cooking counter',x+6,y+2,2,1,
            anchor=[[x+6,y+3],[x+7,y+3]],capacity=2,household=resident)
    _object(sp,bid,'table','Shared dining table',x+3,y+6,3,1,
            anchor=[[x+3,y+7],[x+4,y+7],[x+5,y+7],
                    [x+3,y+5],[x+4,y+5],[x+5,y+5]],capacity=6,household=resident)
    _object(sp,bid,'party_speaker','Common room speaker',x+16,y+2,2,1,
            anchor=[[x+16,y+3]])
    _object(sp,bid,'sofa','Party room sofa',x+16,y+6,3,1,
            anchor=[[x+16,y+7],[x+17,y+7],[x+18,y+7]],capacity=3)
    _object(sp,bid,'gym_station','Residence training area',x+28,y+4,3,2,
            anchor=[[x+28,y+5],[x+29,y+5],[x+30,y+5]],capacity=3,blocking=False)
    _object(sp,bid,'sofa','Residence lounge sofa',x+3,y+17,3,1,
            anchor=[[x+3,y+18],[x+4,y+18],[x+5,y+18]],capacity=3)
    _object(sp,bid,'table','Study and supper table',x+5,y+21,2,1,
            anchor=[[x+5,y+20],[x+6,y+20],[x+5,y+22],[x+6,y+22]],
            capacity=4,household=resident)
    _object(sp,bid,'laundry_machine','Shared washing machines',x+28,y+17,3,1,
            anchor=[[x+28,y+18],[x+29,y+18]],capacity=2,household=resident)
    stair=(x+19,y+19)
    _object(sp,bid,'stairs','Dormitory staircase, ground floor',*stair,
            anchor=[list(stair)],blocking=False)
    return stair


def _dorm_upper(sp,floor,y):
    bid=f'student_dorm_floor_{floor}'
    resident='student_residence'
    x,w,h=81,38,24
    door=sp.building(bid,f'Willow Hall · Floor {floor}',x,y,w,h,1)
    sp.buildings[-1].update(service_kind='student_dorm',floor=floor,
                            parent_building='student_dorm',frontage=list(door))
    _divider(sp,x+1,y+10,w-2)
    _divider(sp,x+1,y+14,w-2)
    for split in (x+13,x+25):
        sp.rect(split,y+1,1,9,WALL)
        sp.rect(split,y+15,1,8,WALL)
    for row,start,wall in ((0,y+1,y+10),(1,y+15,y+14)):
        for col in range(3):
            left=x+1+col*12
            middle=left+6
            key=f'room_{row}_{col}'
            if row==1 and col==1:
                _room(sp,bid,'landing','Stair landing',(left,start,11,8),floor)
                sp.rect(middle,wall,1,1,FLOOR)
                continue
            _room(sp,bid,key,f'Student room {floor}-{row*3+col+1}',(left,start,11,9 if row==0 else 8),floor)
            sp.rect(middle,wall,1,1,FLOOR)
            _object(sp,bid,'bed',f'Single student bed {floor}-{row*3+col+1}',
                    left+1,start+1,1,2,anchor=[[left+1,start+3]],floor=floor,
                    bed_variant='single',household=resident)
            _object(sp,bid,'desk','Study desk',left+4,start+1,2,1,
                    anchor=[[left+4,start+2]],floor=floor,household=resident)
            _object(sp,bid,'wardrobe','Lockable student wardrobe',left+8,start+1,1,2,
                    anchor=[[left+7,start+2]],floor=floor,lockable=True,locked=False,
                    household=resident)
            _object(sp,bid,'room_door','Lockable room door',middle,wall,
                    anchor=[[middle,wall]],blocking=False,floor=floor,
                    lockable=True,locked=False,room_id=f'{bid}_{key}')
    _object(sp,bid,'stairs',f'Dormitory staircase, floor {floor}',*door,
            anchor=[list(door)],blocking=False,floor=floor)
    return door


def extend_campus(sp, seed=0):
    """Idempotent appended migration for existing neighborhood blueprints."""
    metadata=getattr(sp,'planning_metadata',{})
    if metadata.get('campus_version')==VERSION:
        return False
    if metadata.get('layout_id')!='neighborhood-v1':
        raise ValueError('Campus requires the living neighborhood map')
    if sp.height>HEIGHT:
        raise ValueError('Unexpected existing map extent')
    sp.cells.extend(array('B',[GRASS])*(sp.width*(HEIGHT-sp.height)))
    sp.height=HEIGHT
    sp.regions[0]['bounds'][3]=HEIGHT
    sp.rect(0,212,sp.width,3,ROAD)
    sp.rect(0,211,sp.width,1,PATH)
    sp.rect(0,215,sp.width,1,PATH)
    sp.rect(1,202,2,51,PATH)
    sp.rect(125,202,2,51,PATH)
    metadata['roads'].append({'name':'Campus Avenue','class':'local','bounds':[0,212,sp.width,3]})
    metadata['districts']=metadata.get('districts',[])+[
        {'id':'campus','name':'Mosswood Campus','bounds':[0,211,sp.width,39]}]
    metadata['campus_version']=VERSION
    metadata['runtime_floors']=[0,1,2]
    metadata['scope']='Ground streets plus exploded, portal-linked residence floors'
    # Isolate the drawn upper slabs from ordinary outdoor walking. The only
    # access edges are the explicit two-way stair portals below.
    upper_bounds=((81,262,38,24),(81,294,38,24))
    for yy in range(254,HEIGHT):
        for xx in range(sp.width):
            if not any(bx<=xx<bx+bw and by<=yy<by+bh
                       for bx,by,bw,bh in upper_bounds):
                sp.blocked.add((xx,yy))
    _campus_university(sp)
    ground_stair=_dorm_ground(sp)
    first=_dorm_upper(sp,1,262)
    second=_dorm_upper(sp,2,294)
    sp.households.append({'id':'student_residence','name':'Willow Hall',
                          'building_id':'student_dorm','address':'Willow Hall · Campus Avenue',
                          'members':[],'palette':1,'household_kind':'student_residence'})
    metadata['portals']=[{'kind':'stairs','from':list(ground_stair),'to':list(first),'seconds':8},
                         {'kind':'stairs','from':list(first),'to':list(second),'seconds':8}]
    for building in sp.buildings:
        if building['id'] in {'university','student_dorm'}:
            door=building['door']
            sp.rect(door[0],215,1,door[1]-215,PATH)
            building['frontage']=[door[0],214]
    # Internal partition walls were set after building(), so synchronize blocked.
    for yy in range(216,HEIGHT):
        for xx in range(sp.width):
            if sp.cells[yy*sp.width+xx]==WALL:
                sp.blocked.add((xx,yy))
            elif any(bx<=xx<bx+bw and by<=yy<by+bh
                     for bx,by,bw,bh in upper_bounds):
                sp.blocked.discard((xx,yy))
    sp._cache.clear()
    sp._validate_anchors()
    return True
