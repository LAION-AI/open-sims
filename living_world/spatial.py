"""One-meter terrain, separate multi-cell objects, regions and deterministic A*."""
from array import array
from collections import deque
import heapq
import random
from copy import deepcopy

WIDTH, HEIGHT = 128, 220
GRASS, ROAD, PATH, FLOOR, WALL, WATER = range(6)
SURNAMES = ["Bennett", "Rivera", "Chen", "Okafor", "Laurent", "Park", "Novak", "Shah", "Rossi", "Brooks", "Silva", "Patel", "Reed", "Kim", "Meyer", "Santos", "Morgan", "Ito", "Ali", "Dubois"]


class SpatialService:
    def __init__(self, seed=42):
        self.width, self.height = WIDTH, HEIGHT
        self.cells = array("B", [GRASS]) * (WIDTH * HEIGHT)
        self.objects = {}
        self.buildings = []
        self.households = []
        self.regions = [{"id": "mosswood", "name": "Mosswood", "bounds": [0, 0, WIDTH, HEIGHT], "parent": None}]
        self.decorations = []
        self.blocked = set()
        self.path_queries = 0
        self._cache = {}
        self._generate(seed)

    def rect(self, x, y, w, h, terrain):
        for yy in range(y, y+h):
            for xx in range(x, x+w):
                if 0 <= xx < self.width and 0 <= yy < self.height:
                    self.cells[yy*self.width+xx] = terrain

    def add_object(self, kind, name, x, y, w=1, h=1, anchors=None, household=None, building=None, blocking=True, capacity=1):
        oid = f"object_{len(self.objects)+1:04}"
        anchors = anchors or [[x, y+h]]
        obj = {"id": oid, "kind": kind, "name": name, "x": x, "y": y, "w": w, "h": h,
               "orientation": 0, "anchors": anchors, "household_id": household, "building_id": building,
               "blocking": blocking, "capacity": capacity, "condition": 1.0, "mass_kg": {"sofa": 65, "bed": 45}.get(kind, 20),
               "reservations": {}, "version": 0}
        self.objects[oid] = obj
        if blocking:
            self.blocked.update((xx, yy) for yy in range(y,y+h) for xx in range(x,x+w))
        return oid

    def building(self, bid, name, x, y, w, h, palette, household=None):
        self.rect(x, y, w, h, WALL)
        self.rect(x+1,y+1,w-2,h-2,FLOOR)
        door = [x+w//2, y+h-1]
        self.rect(*door,1,1,PATH)
        self.buildings.append({"id": bid, "name": name, "x": x,"y": y,"w":w,"h":h,"door":door,"palette":palette,"household_id":household})
        self.regions.append({"id": bid,"name":name,"bounds":[x,y,w,h],"parent":"mosswood"})
        self.add_object("door", "Front door", *door, anchors=[door], household=household, building=bid, blocking=False)
        return door

    def _generate(self, seed):
        rng = random.Random(seed)
        for y in (23,47,69,93):
            self.rect(0,y-1,WIDTH,1,PATH)
            self.rect(0,y,WIDTH,3,ROAD)
            self.rect(0,y+3,WIDTH,1,PATH)
        for x in (1,125):
            self.rect(x,0,2,HEIGHT,PATH)
        for row,y in enumerate((6,30,76,100)):
            for col in range(5):
                i=row*5+col
                x=6+24*col
                hid=f"household_{i+1:02}"
                bid=f"home_{i+1:02}"
                name=f"{SURNAMES[i]} house"
                door=self.building(bid,name,x,y,15,11,i%6,hid)
                self.rect(door[0],door[1]+1,2,3,PATH)
                # Actual walls split two rooms; each has a one-meter doorway.
                self.rect(x+8,y+1,1,8,WALL)
                self.rect(x+8,y+6,1,1,FLOOR)
                self.rect(x+9,y+5,5,1,WALL)
                self.rect(x+11,y+5,1,1,FLOOR)
                self.regions.extend([
                    {"id":bid+"_living","name":"Living room & kitchen","bounds":[x+1,y+1,7,9],"parent":bid},
                    {"id":bid+"_bedroom","name":"Bedroom","bounds":[x+9,y+1,5,4],"parent":bid},
                    {"id":bid+"_bathroom","name":"Bathroom","bounds":[x+9,y+6,5,4],"parent":bid}])
                specs=[("fridge","Kitchen pantry",1,1,1,1,[[1,2]]),
                       ("sink","Kitchen sink",2,1,1,1,[[2,2]]),
                       ("counter","Kitchen counter",3,1,2,1,[[3,2]]),
                       ("sofa","Three-seat sofa",1,4,3,1,[[1,5],[2,5],[3,5]]),
                       ("table","Coffee table",2,6,2,1,[[2,7]]),
                       ("bookshelf","Bookcase",6,1,1,2,[[6,3]]),
                       ("desk","Writing desk",5,4,2,1,[[5,5]]),
                       ("bed","Single bed",9,1,1,2,[[9,3]]),
                       ("bed","Single bed",11,1,1,2,[[11,3]]),
                       ("bed","Single bed",13,1,1,2,[[13,3]]),
                       ("toilet","Toilet",13,6,1,1,[[12,6]]),
                       ("shower","Shower",13,8,1,2,[[12,8]]),
                       ("plant","House plant",1,8,1,1,[[2,8]])]
                for kind,label,dx,dy,w,h,anchors in specs:
                    self.add_object(kind,label,x+dx,y+dy,w,h,[[x+a,y+b] for a,b in anchors],hid,bid,capacity=3 if kind=="sofa" else 1)
                self.add_object("planter","Vegetable patch",x+17,y+5,2,3,[[x+16,y+6]],hid)
                self.households.append({"id":hid,"name":SURNAMES[i],"building_id":bid,"address":f"{i+1} {['Willow Lane','Clover Street','Maple Row','Fern Walk'][row]}","members":[],"palette":i%6})
                self.decorations.extend([
                    {"kind":"tree","x":x+18,"y":y+1,"variant":i%3},
                    {"kind":"flowers","x":x+1,"y":y+12,"variant":i%3},
                    {"kind":"mailbox","x":x+9,"y":y+12,"variant":i%3},
                    {"kind":"fence","x":x,"y":y+13,"w":6,"variant":0},
                    {"kind":"fence","x":x+10,"y":y+13,"w":10,"variant":0}])
        # The central green is a destination, with paths connecting both sides.
        self.rect(3,54,122,13,PATH)
        self.rect(33,53,61,15,GRASS)
        self.rect(61,52,3,17,PATH)
        self.rect(33,60,61,2,PATH)
        self.rect(70,54,9,4,WATER)
        self.regions.append({"id":"park","name":"Clover Green","bounds":[33,52,61,17],"parent":"mosswood"})
        self.building("cafe","The Daily Crumb",7,54,19,11,2)
        self.building("shop","Moss & Market",101,54,19,11,4)
        self.add_object("cafe_counter","Café kitchen",9,55,4,1,[[10,56],[12,56]],building="cafe",capacity=2)
        self.add_object("shop_counter","Market workbench",103,55,5,1,[[104,56],[106,56]],building="shop",capacity=2)
        for x in (11,17,23):
            self.add_object("table","Café table",x,59,1,1,[[x,60]],building="cafe")
        for x in (110,115):
            self.add_object("shelf","Market shelves",x,56,2,1,[[x,57]],building="shop")
        for x,y in ((39,56),(52,56),(82,56),(40,64),(54,64),(82,64)):
            self.add_object("bench","Park bench",x,y,3,1,[[x+1,y+1]],capacity=1)
        self.add_object("fountain","Drinking fountain",63,59,2,2,[[65,60],[63,61]],capacity=2)
        for x,y in ((36,62),(58,57),(88,63),(85,59)):
            self.add_object("park_marker","Clover Green",x,y,1,1,[[x,y]],blocking=False,capacity=4)
        for x,y in ((35,53),(44,54),(90,54),(35,65),(74,65),(90,65),(5,52),(97,52)):
            self.decorations.append({"kind":"tree","x":x,"y":y,"variant":rng.randrange(3)})
        for y in (23,47,69,93):
            for x in (4,30,58,83,122):
                self.decorations.append({"kind":"lamp","x":x,"y":y-1,"variant":0})
        # The civic strip is appended after the original neighborhood so that all
        # existing object IDs and terrain coordinates retain their meaning.
        self.rect(0,122,WIDTH,1,PATH)
        self.rect(0,123,WIDTH,3,ROAD)
        self.rect(0,126,WIDTH,1,PATH)
        self.rect(1,118,2,36,PATH)
        self.rect(125,118,2,36,PATH)
        self.rect(1,149,125,1,PATH)
        for x in (42,79):
            self.rect(x,126,2,24,PATH)
        workplaces=(
            ("school","Mosswood School",7,128,32,18,3),
            ("studio","Mosswood Creative Studio",47,128,27,18,5),
            ("workshop","Mosswood Works",84,128,34,18,1),
        )
        for bid,name,x,y,w,h,palette in workplaces:
            door=self.building(bid,name,x,y,w,h,palette)
            self.rect(door[0],door[1]+1,1,5,PATH)
        # Workstations are physical resources with one anchor per possible worker.
        # Distinct departments make assignment and coworker identity explicit.
        stations=(
            ("teacher_station","School staff workroom",12,131,6,"school",[12,13,14,15,16,17]),
            ("illustrator_station","Illustration studio",50,131,5,"studio",[50,51,52,53,54]),
            ("designer_station","Design studio",60,131,5,"studio",[60,61,62,63,64]),
            ("carpenter_station","Carpentry workshop",87,131,5,"workshop",[87,88,89,90,91]),
            ("tailor_station","Textile workshop",96,131,5,"workshop",[96,97,98,99,100]),
            ("gardener_station","Parks crew depot",105,131,6,"workshop",[105,106,107,108,109,110]),
        )
        for kind,name,x,y,w,bid,slots in stations:
            self.add_object(kind,name,x,y,w,1,[[slot,y+1] for slot in slots],building=bid,capacity=len(slots))
        # Bins add household waste state without obstructing or renumbering the
        # preexisting kitchen furniture and its interaction anchors.
        for household in self.households:
            building=next(b for b in self.buildings if b["id"]==household["building_id"])
            x,y=building["x"]+4,building["y"]+3
            self.add_object("bin","Kitchen bin",x,y,anchors=[[x,y]],household=household["id"],building=building["id"],blocking=False)
        # South service extension. Existing terrain y<154 and object IDs 1..349
        # stay unchanged; all new public destinations are appended here.
        for road_y in (155,185,216):
            self.rect(0,road_y-1,WIDTH,1,PATH)
            self.rect(0,road_y,WIDTH,3,ROAD)
            self.rect(0,road_y+3,WIDTH,1,PATH)
        services=(
            ("gym","Mosswood Fitness","gym_station","Exercise floor",3,160,8),
            ("nightclub","Lantern Club","nightclub_floor","Dance floor",34,160,16),
            ("town_hall","Mosswood Town Hall","townhall_desk","Public service desk",65,160,4),
            ("hospital","Mosswood Hospital","hospital_desk","Hospital reception",96,160,6),
            ("fire_station","Mosswood Fire Station","fire_stationdesk","Fire dispatch desk",3,190,4),
            ("office_hub","South Office Hub","office_station","Office workstations",34,190,12),
            ("supermarket","South Market","supermarket_checkout","Supermarket checkouts",65,190,8),
            ("shopping_center","Mosswood Arcade","mall_counter","Shopping arcade counter",96,190,10),
        )
        for bid,name,kind,label,x,y,capacity in services:
            door=self.building(bid,name,x,y,27,18,(x//31+y//30)%6)
            self.rect(door[0],door[1]+1,1,8,PATH)
            station_x,station_y=x+4,y+3
            self.add_object(kind,label,station_x,station_y,6,1,
                            [[station_x+i,station_y+1] for i in range(6)],
                            building=bid,capacity=capacity)
        self.blocked.update((i%WIDTH,i//WIDTH) for i,t in enumerate(self.cells) if t in (WALL,WATER))
        # Decorative trees are also real navigation obstacles (trunk only).
        for d in self.decorations:
            if d["kind"]=="tree":
                self.blocked.add((d["x"],d["y"]))
        self._validate_anchors()

    def _validate_anchors(self):
        for obj in self.objects.values():
            for anchor in obj["anchors"]:
                if not self.walkable(tuple(anchor)):
                    raise ValueError(f"Blocked interaction anchor for {obj['id']}: {anchor}")

    def walkable(self, p):
        return 0 <= p[0] < self.width and 0 <= p[1] < self.height and p not in self.blocked

    def path(self, start, goal):
        start,goal=tuple(start),tuple(goal)
        if not self.walkable(start) or not self.walkable(goal):
            return None
        key=(start,goal)
        if key in self._cache:
            return self._cache[key]
        self.path_queries += 1
        prefer_paths=bool(getattr(self,'planning_metadata',{}).get('layout_id'))
        frontier=[(0,0,start)]
        previous={start:None}
        costs={start:0}
        while frontier:
            _,cost,current=heapq.heappop(frontier)
            if current==goal:
                result=[]
                while current is not None:
                    result.append(list(current))
                    current=previous[current]
                result.reverse()
                if len(self._cache)>4096:
                    self._cache.clear()
                self._cache[key]=result
                return result
            if cost!=costs[current]:
                continue
            x,y=current
            for nxt in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if not self.walkable(nxt):
                    continue
                terrain=self.cells[nxt[1]*self.width+nxt[0]]
                # New districts prefer sidewalks and paths over cutting through
                # lawns or walking along traffic lanes. Travel time still uses
                # the actual returned one-metre path, not this preference cost.
                step_cost=({GRASS:6,ROAD:3}.get(terrain,1) if prefer_paths else 1)
                new_cost=cost+step_cost
                if new_cost < costs.get(nxt,10**9):
                    costs[nxt]=new_cost
                    previous[nxt]=current
                    heapq.heappush(frontier,(new_cost+abs(goal[0]-nxt[0])+abs(goal[1]-nxt[1]),new_cost,nxt))
        return None

    def regions_at(self, pos):
        return [r for r in self.regions if r["bounds"][0]<=pos[0]<r["bounds"][0]+r["bounds"][2] and r["bounds"][1]<=pos[1]<r["bounds"][1]+r["bounds"][3]]

    def visible(self, start, end, radius=7):
        x0,y0=start; x1,y1=end
        if (x1-x0)**2+(y1-y0)**2>radius**2:
            return False
        steps=max(abs(x1-x0),abs(y1-y0),1)
        for i in range(1,steps):
            x=round(x0+(x1-x0)*i/steps); y=round(y0+(y1-y0)*i/steps)
            if not (0<=x<self.width and 0<=y<self.height) or self.cells[y*self.width+x]==WALL:
                return False
        return True

    def public_data(self):
        return {"width":self.width,"height":self.height,"cell_size_m":1,"tile_pixels":24,
                "terrain":list(self.cells),"buildings":self.buildings,"households":self.households,
                "objects":list(self.objects.values()),"decorations":self.decorations,"regions":self.regions,
                "planning_metadata":deepcopy(getattr(self,'planning_metadata',{}))}

    def blueprint(self):
        """Freeze the actual layout; reload never silently regenerates its houses."""
        data=deepcopy(self.public_data())
        data.pop('objects')  # Canonical object records are stored once by World.
        data['blocked']=[list(cell) for cell in sorted(self.blocked)]
        data['park_patrol']=deepcopy(getattr(self,'park_patrol',[]))
        return data

    @classmethod
    def from_blueprint(cls, data, objects):
        result=cls.__new__(cls)
        result.width,result.height=data['width'],data['height']
        if len(data['terrain'])!=result.width*result.height:
            raise ValueError('Saved map terrain has an invalid size')
        result.cells=array('B',data['terrain'])
        for key in ('buildings','households','decorations','regions','planning_metadata','park_patrol'):
            setattr(result,key,deepcopy(data.get(key,{} if key=='planning_metadata' else [])))
        result.objects=deepcopy(objects)
        result.blocked={tuple(cell) for cell in data['blocked']}
        result.path_queries=0
        result._cache={}
        result._validate_anchors()
        return result
