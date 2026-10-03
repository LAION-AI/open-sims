"""One authoritative, event-driven world. Rendering never advances simulation.

Needs are analytical segments; movement is a grid trajectory with an arrival event.
Only decision, arrival, interruption and completion boundaries wake an actor.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import heapq
import json
import math
import random
import time

from .ledger import BeatStore
from .rules import RuleRegistry
from .spatial import SpatialService
from .life_simulation import LifeSystems
from .story_life import StoryLife
from . import affect, possessions
from .urban_life import SERVICE_ACTIONS, SERVICE_JOBS, service_available
from . import psychology
from . import careers
from .daily_life import DAILY_ACTIONS, StepUnavailable, apply_step, assigned_workplace, coworkers_at_work
from .urban_life import assigned_service_job
from .campus_life import CAMPUS_ACTIONS, campus_available
from . import work_life, leisure_drama, storyteller, percentile
from .speech import SpeechLibrary

FIRST_NAMES=["Maya","Elliot","Sofia","Leo","Jun","Nora","Theo","Amara","Daniel","Camille","Louis","Hana","Felix","Petra","Arjun","Meera","Luca","Isla","Oliver","Ruby","Rafael","Clara","Asha","Nikhil","Willow","Finn","Min","Jae","Emilia","Oscar","Ines","Mateo","Avery","Robin","Yuki","Ren","Layla","Omar","Chloe","Hugo","Ada","Miles","Zoe","Jules","Samira","Noah","Elif","Tariq","Mira","Jonas","Lina","Pavel","Nia","Kiran"]
SERVICE_ACTIONS={**SERVICE_ACTIONS,**CAMPUS_ACTIONS}
JOBS=["Illustrator","Carpenter","Baker","Teacher","Designer","Gardener","Bookseller","Tailor"]+list(SERVICE_JOBS)+["Physician","Chef","Mechanic","Programmer","Civic planner","Kindergarten educator","Lifeguard","Bartender","Club DJ","Professor","Researcher","University administrator"]
SHIRTS=["#cb775c","#6b9ca4","#d7b861","#83996b","#9684af","#b87390","#6686b0","#bba480"]
SKIN=["#e9ba94","#c78e67","#996342","#f0cfad","#734a37"]
HAIR=["#574338","#352f32","#a56b3f","#d4b372","#847d75"]


def clamp(value):
    return max(0.0,min(1.0,value))


def clock_label(seconds):
    return f"{seconds//3600%24:02}:{seconds//60%60:02}"


class RejectedProposal(ValueError):
    pass


class World(StoryLife,LifeSystems):
    def __init__(self, seed=42, database=":memory:", layout='legacy'):
        self.rules=RuleRegistry()
        self.store=BeatStore(database)
        speech_database = ':memory:' if database == ':memory:' else str(__import__('pathlib').Path(database).with_name(__import__('pathlib').Path(database).stem+'-speech.sqlite3'))
        self.speech=SpeechLibrary(speech_database)
        saved=self.store.checkpoint()
        self.seed=saved["seed"] if saved else seed
        self.layout=saved.get('layout','legacy') if saved else layout
        if self.layout not in {'legacy','neighborhood-v1'}:
            self.store.close()
            raise ValueError('Unknown world layout: '+str(self.layout))
        if saved and saved.get('map_blueprint'):
            self.spatial=SpatialService.from_blueprint(saved['map_blueprint'],saved['objects'])
        elif self.layout=='neighborhood-v1':
            from .neighborhood import LivingNeighborhood
            self.spatial=LivingNeighborhood(self.seed)
        else:self.spatial=SpatialService(self.seed)
        self.actors={}
        self.objects=self.spatial.objects
        self.meta={"environment":{"weather":"Clear","temperature_c":21,"version":0},"economy":{"earned":0,"spent":0,"version":0}}
        if self.layout!='legacy':
            self.meta['map']={'version':0,'layout':self.layout,'seed':self.seed,
                'name':'Mosswood — Lindenviertel','planning':deepcopy(self.spatial.planning_metadata)}
        self.now=8*3600+15*60
        self.queue=[]
        self.queue_serial=0
        self.epoch=1
        self.paused=False
        self.speed=10
        self.fault=None
        self.metrics={"events_processed":0,"decisions":0,"completed_actions":0,"interrupted_actions":0,"declined_chats":0,"last_advance_ms":0.0}
        self._transaction=None
        if saved:
            if saved["rule_hash"] not in (self.rules.hash, self.rules.legacy_hash,self.rules.v2_hash,self.rules.v3_hash,self.rules.v31_hash,self.rules.v32_hash):
                raise ValueError("Saved world uses another rule package; use a different --database or migrate explicitly.")
            self.actors=saved["actors"]
            self.objects.update(saved["objects"])
            self.meta=saved["meta"]
            self.now=saved["now"]
            self.queue=saved["queue"]
            heapq.heapify(self.queue)
            self.queue_serial=saved["queue_serial"]
            self.epoch=saved["epoch"]
            self.metrics=saved["metrics"]
            self.paused=saved.get('paused',False)
            self.speed=saved.get('speed',10)
            self._restore_households()
            if self.layout=='neighborhood-v1' and not self.spatial.planning_metadata.get('campus_version'):
                from .campus import extend_campus
                from .neighborhood import LivingNeighborhood
                self.migration_backup=self.store.migration_backup('campus-v1')
                prior_objects=set(self.objects)
                extend_campus(self.spatial,self.seed)
                LivingNeighborhood._validate_connections(self.spatial)
                # Populate the newly opened residence with six freshly
                # initialized students. Existing biographies remain untouched.
                template=World(seed=self.seed,layout='neighborhood-v1')
                try:
                    wardrobe_ids=[o['id'] for o in self.objects.values()
                                  if o['kind']=='wardrobe' and o.get('household_id')=='student_residence']
                    newcomers=[]
                    for slot in range(6):
                        aid=f'resident_{45+slot:03}'
                        if aid in self.actors:
                            raise ValueError('Campus student ID already exists in old save')
                        actor=deepcopy(template.actors[aid])
                        actor['needs_at']=self.now
                        actor['emotion']['since']=self.now
                        actor['thought']={'text':'I have just moved into Willow Hall.',
                                          'trigger':'campus_migration','since':self.now}
                        actor['beliefs']=[{'id':aid+'_campus_knowledge',
                            'proposition':'I know my residence and the university.',
                            'confidence':'high','evidence':['campus-v1 migration'],
                            'valid_from':self.now}]
                        actor['memories']=[]
                        actor['perceptions']=[]
                        actor.pop('belongings',None)
                        actor.update(possessions.initialize(actor,self.now,wardrobe_ids[slot]))
                        actor['affect']=affect.appraise(actor,actor['needs'],self.now,
                            {'kind':'initialization','text':'Moved into Willow Hall'},
                            f'beat_{self.store.sequence+1:08}')
                        for ambition in actor.get('psychology',{}).get('ambitions',[]):
                            ambition['updated_at']=self.now
                        actor['schedule']['day']=self.now//86400
                        actor['last_beat']=f'beat_{self.store.sequence+1:08}'
                        self.actors[aid]=actor
                        newcomers.append(aid)
                        self.schedule(self.now+slot,'decision',aid,0)
                    for aid in newcomers:
                        self.actors[aid]['social_status']=storyteller.social_status(self.actors[aid],self.actors)
                    next(h for h in self.spatial.households if h['id']=='student_residence')['members']=newcomers
                finally:
                    template.close()
                map_state=self.meta['map']
                map_state['planning']=deepcopy(self.spatial.planning_metadata)
                map_state['version']=map_state.get('version',0)+1
                changes=[{'collection':'objects','subject_id':oid,'component_path':'$',
                          'new_value':deepcopy(self.objects[oid]),'expected_prior_version':None,
                          'operation':'set','scope':'canonical','effective_time':self.now,
                          'microstep':i,'evidence_ids':['campus-v1 migration']}
                         for i,oid in enumerate(self.objects) if oid not in prior_objects]
                changes.append({'collection':'world','subject_id':'map','component_path':'$',
                                'new_value':deepcopy(map_state),'expected_prior_version':map_state['version']-1,
                                'operation':'set','scope':'canonical','effective_time':self.now,
                                'microstep':len(changes),'evidence_ids':['campus-v1 migration']})
                changes.extend({'collection':'actors','subject_id':aid,'component_path':'$',
                                'new_value':deepcopy(self.actors[aid]),'expected_prior_version':None,
                                'operation':'set','scope':'canonical','effective_time':self.now,
                                'microstep':len(changes)+index,'evidence_ids':['campus-v1 migration']}
                               for index,aid in enumerate(newcomers))
                self.store.append(self._beat('migration.campus.v1',newcomers,
                    'Mosswood Campus opened and six students moved into the stair-linked residence.',changes,
                    ['Existing coordinates, residents and object identities preserved']))
                self.save()
            if saved["rule_hash"] == self.rules.legacy_hash:
                self.migration_backup = self.store.migration_backup()
                self._migrate_life(saved)
                self._migrate_story({'objects':deepcopy(self.objects)})
            elif saved['rule_hash']==self.rules.v2_hash:
                self.migration_backup=self.store.migration_backup('story-v3')
                self._migrate_story(saved)
            elif saved['rule_hash']==self.rules.v3_hash:
                with self.transaction('migration.rules.v3_1', list(self.actors),
                        'Wardrobe actions and future career goals are available; this saved floor plan stays unchanged.',
                        ['existing object IDs, positions, and personal histories preserved']):
                    self.edit('world','story_systems')['rule_contract_version']='3.1.0'
                    for aid in self.actors:
                        actor = self.edit('actors', aid)
                        actor.setdefault('career', careers.initial(actor, self.now))
                        actor.update(psychology.add_missing_ambitions(actor, self.now))
                self.save()
            elif saved['rule_hash']==self.rules.v31_hash:
                self.migration_backup=self.store.migration_backup('rules-v3_2')
                with self.transaction('migration.rules.v3_2',list(self.actors),
                        'New leisure, work and optional decision tools are available; existing homes and histories remain intact.'):
                    self.edit('world','story_systems')['rule_contract_version']='3.2.0'
                    for aid in self.actors:
                        self.edit('actors',aid)['appearance']['age']=self.actors[aid]['age']
                self.save()
            elif saved['rule_hash']==self.rules.v32_hash:
                with self.transaction('migration.rules.v3_3',list(self.actors),
                        'Campus opportunities and W100 task grading became available; no earlier action was rerolled.'):
                    self.edit('world','story_systems')['rule_contract_version']='3.3.0'
                    for aid in self.actors:
                        actor=self.edit('actors',aid)
                        actor.setdefault('education',{'university_student':18<=actor['age']<=25,
                                                      'progress_hours':0.0})
                self.save()
            missing=[aid for aid, actor in self.actors.items()
                     if 'drive' not in actor.get('psychology', {}).get('social_style', {}) or 'social_status' not in actor]
            if missing:
                self.migration_backup=self.store.migration_backup('storyteller-social-v1')
                with self.transaction('migration.social_style.v1',missing,
                        'Added individual social tendencies and current standing; no past encounters were inferred.',
                        ['Current state only; existing relationships and histories preserved']):
                    for aid in missing:
                        actor=self.edit('actors',aid)
                        actor.update(psychology.migrate_existing_actor(actor,self.rng(aid,0,'psychology'),self.now))
                        actor['social_status']=storyteller.social_status(actor,self.actors)
                self.save()
            missing_aptitudes=[aid for aid, actor in self.actors.items()
                               if actor.get('aptitudes', {}).get('version') != 1]
            if missing_aptitudes:
                if not hasattr(self,'migration_backup'):
                    self.migration_backup=self.store.migration_backup('percentile-v1')
                with self.transaction('migration.percentile.v1',missing_aptitudes,
                        'Added seeded W100 abilities; earlier events were not rerolled.'):
                    for aid in missing_aptitudes:
                        actor=self.edit('actors',aid)
                        actor['aptitudes']=percentile.initial(actor,self.rng(aid,0,'percentile_initial'))
                self.save()
            missing_education=[aid for aid, actor in self.actors.items() if 'education' not in actor]
            if missing_education:
                with self.transaction('migration.campus_education.v1',missing_education,
                        'Campus study eligibility became available to young adults; prior studies were not inferred.'):
                    self.edit('world','story_systems')['rule_contract_version']='3.3.0'
                    for aid in missing_education:
                        actor=self.edit('actors',aid)
                        actor['education']={'university_student':18<=actor['age']<=25,
                                            'progress_hours':0.0}
                self.save()
        else:
            self._initialize()
            self.save()

    def rng(self, actor_id, decision, purpose):
        key=f"{self.seed}|{actor_id}|{decision}|{self.rules.hash}|{purpose}"
        return random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest()[:16],"big"))

    def _restore_households(self):
        for h in self.spatial.households:
            h["members"]=[a["id"] for a in self.actors.values() if a["household_id"]==h["id"]]

    def _initialize(self):
        i=0
        for hi,household in enumerate(self.spatial.households):
            building=next(b for b in self.spatial.buildings if b["id"]==household["building_id"])
            for member in range(10 if household['id']=='student_residence' else 3 if hi%5==2 else 2):
                aid=f"resident_{i+1:03}"
                rng=self.rng(aid,0,"initialization")
                prefs={p:round(rng.uniform(.2,1),2) for p in ("cooking","relaxing","reading","gardening","craft","socializing","walking")}
                needs={k:round(rng.uniform(.14,.56),4) for k in self.rules.rates}
                needs["fatigue"]=rng.uniform(.08,.25)
                position=[building["x"]+4+member,building["y"]+8]
                # These are authored opening positions, not invented past journeys.
                if i<2:
                    position=[56+i,61]
                    needs["social"]=.7
                if i in (10,20,30):
                    position=[39+(i//10)*9,62]
                if self.layout!='legacy':
                    position=list(self.spatial.spawn_for(household['id'],member))
                    if i<2:position=list(self.spatial.park_patrol[i])
                interests=sorted(prefs,key=prefs.get,reverse=True)[:2]
                job=JOBS[i%len(JOBS)] if i%9!=8 else "Independent artist"
                actor={"id":aid,"kind":"human","name":f"{FIRST_NAMES[i]} {household['name']}","age":rng.randrange(22,65),
                       "household_id":household["id"],"home_id":building["id"],"position":position,
                       "appearance":{"shirt":SHIRTS[i%8],"skin":SKIN[i%5],"hair":HAIR[i%5],"style":i%4},
                       "profile":{"job":job,"interests":interests,"traits":["Curious" if prefs["reading"]>.6 else "Practical","Outgoing" if prefs["socializing"]>.6 else "Reserved","Green-fingered" if prefs["gardening"]>.65 else "Creative"]},
                       "preferences":prefs,"needs":needs,"needs_at":self.now,"need_rates":{k:v/3600 for k,v in self.rules.rates.items()},
                       "money":rng.randrange(140,360),"inventory":{"phone":1,"house_key":1},"skills":{"cooking":round(rng.uniform(.1,.6),3),"craft":round(rng.uniform(.1,.7),3),"gardening":round(rng.uniform(.1,.6),3)},
                       "schedule":{"start":9*3600,"end":17*3600,"work_target_seconds":4*3600,"work_seconds":0,"day":0},
                       "goals":[{"id":"wellbeing","title":"Take care of myself","kind":"ongoing","progress":0},
                                {"id":"work","title":"Finish today's work","kind":"daily","progress":0},
                                {"id":"hobby","title":f"Make time for {interests[0]}","kind":"daily","progress":0}],
                       "relations":{},"perceptions":[],"memories":[],"beliefs":[{"id":aid+"_knowledge","proposition":"I know my home, work hours, and the public neighborhood facilities.","confidence":"high","evidence":["initialization"],"valid_from":self.now}],
                       "emotion":{"type":"Content","valence":.5,"arousal":.2,"intensity":.3,"cause":"Initialized morning state","since":self.now,"expires_at":None},
                       "thought":{"text":"A new day in Mosswood. What shall I do first?","trigger":"initialization","since":self.now},
                       "action":None,"decision_id":0,"last_decision":None,"cooldowns":{},"effects":[],"owner":"procedural","owner_epoch":1,"version":0,"last_beat":None}
                self.actors[aid]=actor
                household["members"].append(aid)
                i+=1
        for household in self.spatial.households:
            for aid in household["members"]:
                self.actors[aid]["relations"]={other:{"closeness":.65,"trust":.75,"last_interaction":None,"kind":"Housemate"} for other in household["members"] if other!=aid}
        self._life_components(new_world=True)
        self._initialize_story()
        for actor in self.actors.values():
            actor['social_status']=storyteller.social_status(actor,self.actors)
            actor['aptitudes']=percentile.initial(actor,self.rng(actor['id'],0,'percentile_initial'))
            actor['education']={'university_student':18<=actor['age']<=25,
                                'progress_hours':0.0}
        changes=[]
        for collection,records in (("actors",self.actors),("objects",self.objects),("world",self.meta)):
            for rid,record in records.items():
                changes.append({"collection":collection,"subject_id":rid,"component_path":"$","new_value":deepcopy(record),"expected_prior_version":None,"operation":"set","scope":"canonical","effective_time":self.now,"microstep":len(changes),"evidence_ids":["initialization"]})
        self.store.append(self._beat("initialization",[],
            "Morning arrives in Mosswood. Residents begin their day across twenty homes and a ten-room student residence." if self.layout!='legacy' else
            "Morning arrives in Mosswood. Forty-four residents begin their day across twenty homes.",changes))
        for i,aid in enumerate(self.actors):
            self.schedule(self.now+i%29,"decision",aid,0)
        self.schedule((self.now//86400+1)*86400,"midnight",None,0)
        self.schedule(self.now+60,"animal_tick",None,0)

    def _beat(self, rule, participants, text, changes, reasons=None, causal=None):
        return {"field_id":None,"producer":"procedural","owner_epoch":self.epoch,"event_ids":[],"interval":[self.now,self.now],
                "base_snapshot_version":self.store.sequence,"participants":participants,
                "resolution":{"level":"L2","temporal_precision_seconds":1,"overrides":{"emotions":"bounded appraisal"}},
                "coverage":self.rules.data["coverage"],"changes":changes,"inbound_message_ids":[],"outbound_messages":[],
                "causal_parent_ids":causal or [],"unresolved_detail_constraints":["Verbatim dialogue and recursive higher-order beliefs are unmodeled; first-order social estimates are uncertain."],
                "model_and_rule_versions":self.rules.manifest(),"rule_id":rule,"seed":self.seed,"status":"committed",
                "validation_receipt":{"accepted":True,"single_coordinator":True,"microsteps_ordered":True},"narration":text,"reasons":reasons or []}

    @contextmanager
    def transaction(self, rule, participants, text, reasons=None):
        if self._transaction is not None:
            raise RuntimeError("Nested world transaction")
        tx={"before":{},"rule":rule,"participants":list(participants),"text":text,"reasons":reasons or [],"queue":list(self.queue),"serial":self.queue_serial}
        self._transaction=tx
        try:
            yield tx
            changes=[]
            bid=f"beat_{self.store.sequence+1:08}"
            for (collection,rid),old in tx["before"].items():
                new=self.collection(collection)[rid]
                new["version"]=old.get("version",0)+1
                if collection=="actors":
                    new["last_beat"]=bid
                for key,value in new.items():
                    if key not in old or old[key]!=value:
                        changes.append({"collection":collection,"subject_id":rid,"component_path":key,"new_value":deepcopy(value),"expected_prior_version":old.get("version",0),"operation":"set","scope":"subjective" if key in ("beliefs","perceptions","memories","emotion","thought") else "canonical","effective_time":self.now,"microstep":len(changes),"evidence_ids":tx["reasons"]})
            parents=sorted({old["last_beat"] for (coll,_),old in tx["before"].items() if coll=="actors" and old.get("last_beat")})
            beat=self._beat(tx["rule"],tx["participants"],tx["text"],changes,tx["reasons"],parents)
            beat["event_ids"]=[a["action"]["id"] for aid in tx["participants"] if (a:=self.actors.get(aid)) and a["action"]]
            self.store.append(beat)
        except BaseException:
            for (collection,rid),old in tx["before"].items():
                self.collection(collection)[rid]=old
            self.queue=tx["queue"]
            self.queue_serial=tx["serial"]
            raise
        finally:
            self._transaction=None

    def collection(self, name):
        return {"actors":self.actors,"objects":self.objects,"world":self.meta}[name]

    def edit(self, collection, rid):
        if self._transaction is None:
            raise RuntimeError("World writes require a coordinator transaction")
        record=self.collection(collection)[rid]
        self._transaction["before"].setdefault((collection,rid),deepcopy(record))
        return record

    def schedule(self, due, kind, aid, token):
        self.queue_serial+=1
        heapq.heappush(self.queue,[int(due),self.queue_serial,kind,aid,token])

    def needs_at(self, actor, at=None):
        elapsed=(self.now if at is None else at)-actor["needs_at"]
        return {k:clamp(value+actor["need_rates"][k]*elapsed) for k,value in actor["needs"].items()}

    def materialize(self, actor):
        actor["needs"]=self.needs_at(actor)
        actor["needs_at"]=self.now

    def position_at(self, actor, at=None):
        action=actor["action"]
        if action and action["phase"]=="travel":
            t=self.now if at is None else at
            index=max(0,min(len(action["path"])-1,t-action["started_at"]))
            return action["path"][int(index)]
        return actor["position"]

    def _known_objects(self, actor):
        # Public destinations and one's own home are initialized knowledge.
        return [o for o in self.objects.values() if o["household_id"] in (None,actor["household_id"])]

    def candidates(self, actor):
        needs=self.needs_at(actor)
        pos=self.position_at(actor)
        candidates=[]
        rejected=[]
        minute=self.now%86400
        day=self.now//86400
        objects=self._known_objects(actor)
        for kind,definition in self.rules.actions.items():
            if kind in ("chat","wait") or kind in DAILY_ACTIONS or kind in possessions.POSSESSION_ACTIONS:
                continue
            if kind in SERVICE_ACTIONS and not service_available({**actor,'needs':needs},kind,self.now):continue
            if kind in CAMPUS_ACTIONS and not campus_available(actor,kind,self.now):continue
            if actor.get('age',30)<18 and kind in {'work','dance_club','visit_bar','job_search'}:
                continue
            if actor["cooldowns"].get(kind,0)>self.now:
                continue
            options=[o for o in objects if o["kind"] in definition["object_kinds"] and o["condition"]>.1]
            if kind == "eat":
                # The old fridge-eat contract remains only for active v1 saves.
                options = [o for o in options if o["kind"] == "cafe_counter"]
            if kind=="work":
                workplace = actor.get("workplace") or {}
                options = [o for o in options if o["id"] == workplace.get("target_id")]
            if actor['household_id']=='student_residence' and kind in {'sleep','change_outfit'}:
                own=[o for o in options if o.get('household_id')=='student_residence'
                     and o['kind']==('bed' if kind=='sleep' else 'wardrobe')]
                slot=max(0,int(actor['id'].rsplit('_',1)[-1])-45)
                options=own[slot:slot+1] if own else []
            if kind=='job_search' and actor['profile']['job']!='Unemployed':
                continue
            if kind=='visit_patient' and not any(other['id']!=actor['id'] and other.get('action')
                    and other['action']['kind']=='visit_clinic' for other in self.actors.values()):
                continue
            if kind.startswith('leisure_'):
                activity=definition['leisure_activity']
                tags=leisure_drama.LEISURE_ACTIVITIES[activity]['tags']
                if activity in {'host_party','watch_movie','relax_at_home'}:
                    options=[o for o in options if o.get('household_id')==actor['household_id']]
                if activity=='visit_museum':
                    continue  # No museum affordance has been built yet.
                if actor.get('age',30)<18 and activity in {'ask_on_date','go_on_date','attend_party','karaoke','see_live_music'}:
                    continue
                if actor.get('age',30)<7 and activity=='swim':continue
                if 'party' in tags and not (self.now%86400>=17*3600 or self.now%86400<2*3600):
                    continue
            free=[]
            for obj in options:
                if definition["cost"]>actor["money"]:
                    continue
                if len(obj["reservations"])>=obj["capacity"]:
                    continue
                reserved={tuple(r["anchor"]) for r in obj["reservations"].values()}
                for anchor in obj["anchors"]:
                    if tuple(anchor) not in reserved:
                        distance=abs(pos[0]-anchor[0])+abs(pos[1]-anchor[1])
                        free.append((distance,obj["id"],anchor))
            if not free:
                if options:
                    rejected.append({"kind":kind,"reason":"Known resources are reserved or unaffordable"})
                continue
            distance,oid,anchor=min(free,key=lambda o:(o[0],o[1],o[2]))
            relief=sum(needs[n]**2*min(1,amount)*1.8 for n,amount in definition["relief"].items())
            preference=actor["preferences"].get(definition["preference"],.3)*.12
            time_cost=distance*.0015+definition["duration"]/3600*.025
            commitment=0
            if kind=="work":
                schedule=actor["schedule"]
                if schedule["start"]-300<=minute<schedule["end"] and schedule["work_seconds"]<schedule["work_target_seconds"]:
                    commitment=.65
                else:
                    commitment=-1
            if kind=='job_search':
                commitment=.45 if actor['profile']['job']=='Unemployed' else -1
            if kind in {'school_day','kindergarten_day'}:
                commitment=(.9 if actor['schedule']['work_seconds']<actor['schedule']['work_target_seconds']
                            else -.7)
            if kind in {'attend_lecture','attend_seminar','run_lab'}:
                if actor['profile']['job']=='Student':
                    commitment=.95 if actor['schedule']['work_seconds']<actor['schedule']['work_target_seconds'] and 9*3600<=minute<15*3600 else -.5
                else:
                    commitment=.38 if actor.get('education',{}).get('university_student') and 9*3600<=minute<16*3600 else -.2
            if kind=="sleep":
                commitment=.35 if minute>=22*3600 or minute<6*3600 else -.28
            critical=max([needs[n] for n in definition["relief"] if n in ("hunger","thirst","bladder","fatigue","hygiene")] or [0])
            urgency=2 if critical>=self.rules.data["selection"]["critical_threshold"] else 0
            personality = self._life_bias(actor, kind)
            if kind.startswith('leisure_'):
                activity=definition['leisure_activity']
                activity_weight=next(row['weight'] for row in leisure_drama.leisure_actions(actor) if row['activity']==activity)
                personality+=min(.38,(activity_weight-1)*.3)
                score_bonus=.25 if needs['fun']>.4 else .02
            else:score_bonus=0
            score=relief+preference+commitment+urgency-time_cost+personality+score_bonus
            candidates.append({"kind":kind,"target_id":oid,"anchor":anchor,"distance":distance,"score":round(score,5),
                               "terms":{"need_relief":round(relief,4),"preference":round(preference,4),"commitment":commitment,"critical":urgency,"personality":personality,"travel_and_time_cost":round(time_cost,4)}})
        # Only visible, socially available people are possible partners.
        if actor["cooldowns"].get("chat",0)<=self.now:
            others=[]
            for other in self.actors.values():
                if other["id"]==actor["id"] or other["owner"]!="procedural":
                    continue
                action=other["action"]
                if action and (action["phase"]!="using" or action["kind"] not in ("wait","relax","stroll")):
                    continue
                opos=self.position_at(other)
                if self.spatial.visible(pos,opos,radius=4):
                    distance=abs(opos[0]-pos[0])+abs(opos[1]-pos[1])
                    other_view={**other,'social_status':storyteller.social_status(other,self.actors),
                                'needs':self.needs_at(other)}
                    others.append((psychology.partner_priority(actor,other_view,distance,self.now),other["id"]))
            if others:
                projected = {**actor, "needs": needs}
                for partner_priority,other in sorted(others,key=lambda row:(-row[0],row[1]))[:3]:
                    workplace=actor.get('workplace_id')
                    at_work=bool(workplace) and workplace in {r['id'] for r in self.spatial.regions_at(pos)}
                    projected_other={**self.actors[other], 'needs':self.needs_at(self.actors[other]),
                        'social_status':storyteller.social_status(self.actors[other],self.actors)}
                    allowed=[row for row in psychology.social_candidates(projected,projected_other,self.now)
                             if row['allowed'] and (row['category']!='undermine' or at_work)]
                    exploratory=allowed[2:]
                    picked=self.rng(actor['id'],actor['decision_id'],
                        'social_explore:'+other).choices(exploratory,
                        weights=[max(.01,row['score']) for row in exploratory],k=1)[0] if exploratory else None
                    shortlist=allowed[:2]+([picked] if picked else [])
                    for social in shortlist:
                        score=(needs["social"]**2*2.15+actor["preferences"]["socializing"]*.20+.12
                               +(social["score"]-.5)*.4+self._life_bias(actor,"chat")+partner_priority*.18)
                        candidates.append({"kind":"chat","social_category":social["category"],"topic":social.get('topic'),
                                           "target_id":other,"anchor":list(pos),"distance":0,"score":round(score,5),
                                           "terms":{"need_relief":round(needs["social"]**2*1.9,4),
                                                    "category_affinity":social["score"],"partner_priority":partner_priority,
                                                    "personality":self._life_bias(actor,"chat")}})
            if actor.get('age', 30) >= 10 and needs['social'] >= .28 and 8*3600 <= minute < 23*3600:
                contacts=[]
                for other_id,relation in actor.get('relations',{}).items():
                    other=self.actors.get(other_id)
                    if not other or other['owner']!='procedural' or other_id==actor['id']:
                        continue
                    opposite=self.position_at(other)
                    if self.spatial.visible(pos,opposite,radius=4):
                        continue
                    ongoing=other.get('action')
                    if ongoing and (ongoing['phase']!='using' or ongoing['kind'] not in ('wait','relax','stroll')):
                        continue
                    score=float(relation.get('closeness',0))*.5+float(relation.get('trust',0))*.2
                    if relation.get('last_interaction') is not None and self.now-relation['last_interaction']<4*3600:
                        score-=.35
                    contacts.append((score,other_id))
                if contacts:
                    contacts.sort(key=lambda row:(-row[0],row[1]))
                    best=contacts[:5]
                    chosen_contact=self.rng(actor['id'],actor['decision_id'],'outreach').choices(
                        best,weights=[max(.05,.3+row[0]) for row in best],k=1)[0]
                    other=self.actors[chosen_contact[1]]
                    social=next((row for row in psychology.social_candidates(
                        {**actor,'needs':needs},
                        {**other,'needs':self.needs_at(other)},self.now)
                        if row['category']=='phone_call' and row['allowed']),None)
                    if social:
                        score=needs['social']**2*1.8+actor['preferences']['socializing']*.18
                        score+=.08+(social['score']-.5)*.3+self._life_bias(actor,'chat')
                        candidates.append({'kind':'chat','social_category':'phone_call','topic':None,
                            'target_id':other['id'],'anchor':list(pos),'distance':0,'score':round(score,5),
                            'terms':{'outreach':True,'social_need':round(needs['social'],4),
                                     'relationship':round(chosen_contact[0],4)}})
        candidates.extend(self._routine_candidates(actor, needs, pos))
        candidates.append({"kind":"wait","target_id":None,"anchor":list(pos),"distance":0,"score":-.15,"terms":{"fallback":True}})
        return sorted(candidates,key=lambda c:(-c["score"],c["kind"],c.get("social_category","")))[:self.rules.data['selection']['candidate_limit']],rejected

    def choose(self, actor, candidates):
        decision=actor["decision_id"]+1
        rng=self.rng(actor["id"],decision,"action_choice")
        temperature=self.rules.data["selection"]["temperature"]
        top=max(c["score"] for c in candidates)
        # Twenty conversation options must not make socializing twenty times
        # likelier merely because that action family has a richer vocabulary.
        family=lambda c: 'leisure' if c['kind'].startswith('leisure_') else c['kind']
        counts = {kind: sum(family(c) == kind for c in candidates) for kind in {family(c) for c in candidates}}
        weights=[math.exp((c["score"]-top)/temperature)/counts[family(c)] for c in candidates]
        draw=rng.random()
        running=0
        for candidate,weight in zip(candidates,weights):
            running+=weight/sum(weights)
            if draw<=running:
                return candidate,draw
        return candidates[-1],draw

    @staticmethod
    def _matches_recommendation(candidate, recommendation):
        return (candidate['kind'] == recommendation['action']
                and candidate.get('target_id') == recommendation.get('target_id')
                and candidate.get('social_category') == recommendation.get('social_category'))

    def recommend(self, aid, payload):
        actor = self.actors[aid]
        if actor['owner'] != 'procedural':
            raise RejectedProposal('Only procedural residents can receive player recommendations')
        if actor['version'] != payload['expected_version']:
            raise RejectedProposal('Stale actor component version')
        candidates, _ = self.candidates(actor)
        if not any(self._matches_recommendation(candidate, payload) for candidate in candidates):
            explicit = self._explicit_social_candidate(actor, payload) or self._explicit_place_candidate(actor, payload)
            if not explicit:
                raise RejectedProposal('That action is not currently feasible and known to this resident')
        ttl = int(payload.get('ttl_seconds', 1800))
        if not 60 <= ttl <= 3600:
            raise RejectedProposal('Recommendation must expire within 1–60 world minutes')
        with self.transaction('player.recommend.v1', [aid],
                              f"A player suggests a possible next step to {actor['name']}.",
                              ['Advisory utility bias only; action preconditions and consent remain authoritative']):
            actor = self.edit('actors', aid)
            actor['player_recommendation'] = {
                'id': f'recommendation_{aid}_{self.store.sequence + 1}',
                'action': payload['action'], 'target_id': payload.get('target_id'),
                'social_category': payload.get('social_category'),
                'created_at': self.now, 'expires_at': self.now + ttl, 'status': 'pending'}
        return deepcopy(actor['player_recommendation'])

    def cancel_recommendation(self, aid, expected_version):
        actor = self.actors[aid]
        if actor['version'] != expected_version:
            raise RejectedProposal('Stale actor component version')
        if actor.get('player_recommendation', {}).get('status') != 'pending':
            raise RejectedProposal('No pending recommendation')
        with self.transaction('player.recommend.cancel.v1', [aid],
                              f"The suggestion to {actor['name']} is withdrawn."):
            actor = self.edit('actors', aid)
            actor['player_recommendation']['status'] = 'cancelled'
            actor['player_recommendation']['resolved_at'] = self.now
        return deepcopy(actor['player_recommendation'])

    def _resolve_recommendation(self, actor, chosen, candidates):
        recommendation = actor.get('player_recommendation')
        if not recommendation or recommendation['status'] != 'pending':
            return
        if self.now >= recommendation['expires_at']:
            status = 'expired'
        elif not any(self._matches_recommendation(c, recommendation) for c in candidates):
            status = 'unavailable'
        elif self._matches_recommendation(chosen, recommendation):
            status = 'followed'
        else:
            status = 'considered'
        recommendation['status'] = status
        recommendation['resolved_at'] = self.now

    def _explicit_social_candidate(self, actor, request):
        """Validate a named partner without treating utility shortlist as authority."""
        if request.get('action') != 'chat' or actor['cooldowns'].get('chat', 0) > self.now:
            return None
        other = self.actors.get(request.get('target_id'))
        if not other or other['id'] == actor['id'] or other['owner'] != 'procedural':
            return None
        action = other['action']
        if action and (action['phase'] != 'using' or action['kind'] not in ('wait', 'relax', 'stroll')):
            return None
        pos = self.position_at(actor)
        opposite = self.position_at(other)
        category = request.get('social_category') or 'small_talk'
        if category != 'phone_call' and not self.spatial.visible(pos, opposite, radius=4):
            return None
        projected = {**actor, 'needs': self.needs_at(actor)}
        social = next((row for row in psychology.social_candidates(projected,
                       {**other,'social_status':storyteller.social_status(other,self.actors),
                        'needs':self.needs_at(other)}, self.now)
                       if row['category'] == category and row['allowed']), None)
        if not social:
            return None
        if category=='undermine' and actor.get('workplace_id') not in {r['id'] for r in self.spatial.regions_at(pos)}:
            return None
        distance = abs(opposite[0] - pos[0]) + abs(opposite[1] - pos[1])
        priority = psychology.partner_priority(actor,
            {**other,'social_status':storyteller.social_status(other,self.actors),
             'needs':self.needs_at(other)}, distance, self.now)
        score = (projected['needs']['social']**2 * 1.9
                 + actor['preferences']['socializing'] * .16
                 + (social['score'] - .5) * .4
                 + self._life_bias(actor, 'chat') + priority * .18)
        return {'kind': 'chat', 'social_category': category, 'topic': social.get('topic'),
                'target_id': other['id'], 'anchor': list(pos), 'distance': 0,
                'score': round(score, 5), 'terms': {'explicit_feasibility_check': True}}

    def _explicit_place_candidate(self, actor, request, *, verify_route=True):
        """Validate a player-chosen destination, independently of the utility shortlist."""
        kind = request.get('action')
        if kind not in {'community_meet', 'visit_pool', 'visit_bar', 'browse_mall',
                        'visit_townhall', 'exercise_gym', 'dance_club', 'read',
                        'garden', 'stroll'} and not (isinstance(kind, str) and kind.startswith('leisure_')):
            return None
        definition = self.rules.actions.get(kind)
        obj = self.objects.get(request.get('target_id'))
        if not definition or not obj or obj.get('household_id') not in (None, actor['household_id']):
            return None
        if obj['kind'] not in definition['object_kinds'] or obj['condition'] <= .1:
            return None
        if actor['cooldowns'].get(kind, 0) > self.now or definition['cost'] > actor['money']:
            return None
        if kind in SERVICE_ACTIONS and not service_available({**actor, 'needs': self.needs_at(actor)}, kind, self.now):
            return None
        age = actor.get('age', 30)
        if age < 18 and kind in {'visit_bar', 'dance_club'}:
            return None
        if kind.startswith('leisure_'):
            activity = definition['leisure_activity']
            tags = leisure_drama.LEISURE_ACTIVITIES[activity]['tags']
            if activity in {'host_party', 'watch_movie', 'relax_at_home'} and obj.get('household_id') != actor['household_id']:
                return None
            if activity == 'visit_museum' or age < 18 and activity in {
                    'ask_on_date', 'go_on_date', 'attend_party', 'karaoke', 'see_live_music'}:
                return None
            if age < 7 and activity == 'swim':
                return None
            minute = self.now % 86400
            if 'party' in tags and not (minute >= 17 * 3600 or minute < 2 * 3600):
                return None
        if len(obj['reservations']) >= obj['capacity']:
            return None
        pos = self.position_at(actor)
        reserved = {tuple(row['anchor']) for row in obj['reservations'].values()}
        free_anchors = [anchor for anchor in obj['anchors'] if tuple(anchor) not in reserved
                        and self.spatial.walkable(tuple(anchor))]
        if not free_anchors:
            return None
        free_anchors.sort(key=lambda anchor: (abs(pos[0]-anchor[0])+abs(pos[1]-anchor[1]),anchor))
        if verify_route:
            route = None
            for candidate_anchor in free_anchors:
                candidate_path = self.spatial.path(pos, candidate_anchor)
                if candidate_path is not None:
                    route = (candidate_path, candidate_anchor)
                    break
            if route is None:
                return None
            path, anchor = route
            distance = len(path)-1
        else:
            anchor = free_anchors[0]
            distance = abs(pos[0]-anchor[0])+abs(pos[1]-anchor[1])
        needs = self.needs_at(actor)
        relief = sum(needs[n] ** 2 * min(1, amount) * 1.8
                     for n, amount in definition['relief'].items())
        score = relief + actor['preferences'].get(definition['preference'], .3) * .12
        if kind.startswith('leisure_'):
            score += .12 if needs['fun'] > .5 else -.12
        score += self._life_bias(actor, kind) - distance * .0015
        return {'kind': kind, 'target_id': obj['id'], 'anchor': anchor,
                'distance': distance, 'score': round(score, 5),
                'terms': {'explicit_feasibility_check': verify_route}}

    def intervention_options(self, aid):
        actor = self.actors[aid]
        pos = self.position_at(actor)
        contacts = []
        projected = {**actor, 'needs': self.needs_at(actor)}
        at_work = actor.get('workplace_id') in {row['id'] for row in self.spatial.regions_at(pos)}
        for other in self.actors.values():
            if other['id'] == aid or other['owner'] != 'procedural':
                continue
            nearby = self.spatial.visible(pos, self.position_at(other), radius=4)
            if not nearby and other['id'] not in actor.get('relations', {}):
                continue
            ongoing = other.get('action')
            if (actor['cooldowns'].get('chat', 0) > self.now or ongoing and
                    (ongoing['phase'] != 'using' or ongoing['kind'] not in ('wait', 'relax', 'stroll'))):
                continue
            other_view = {**other, 'needs': self.needs_at(other),
                          'social_status': storyteller.social_status(other, self.actors)}
            categories = [row['category'] for row in psychology.social_candidates(projected, other_view, self.now)
                          if row['allowed'] and (nearby or row['category'] == 'phone_call')
                          and (row['category'] != 'undermine' or at_work)]
            if categories:
                relation = actor.get('relations', {}).get(other['id'], {})
                contacts.append({'id': other['id'], 'name': other['name'],
                                 'nearby': nearby, 'relationship': relation.get('kind', 'acquaintance'),
                                 'categories': categories})
        contacts.sort(key=lambda row: (not row['nearby'], row['name']))
        places = []
        for obj in self._known_objects(actor):
            if not obj.get('building_id') or obj.get('household_id') not in (None, actor['household_id']):
                continue
            for kind in ('community_meet', 'visit_pool', 'visit_bar', 'browse_mall',
                         'visit_townhall', 'exercise_gym', 'dance_club', 'read',
                         'garden', 'stroll'):
                if self._explicit_place_candidate(actor, {'action': kind, 'target_id': obj['id']}, verify_route=False):
                    places.append({'action': kind, 'target_id': obj['id'],
                                   'object': obj['name'], 'building_id': obj['building_id'],
                                   'label': self.rules.actions[kind]['label']})
        return {'actor_id': aid, 'version': actor['version'], 'owner': actor['owner'],
                'fault': self.fault,
                'contacts': contacts, 'places': places}

    def decide(self, aid, requested=None, *, provider_fallback=False):
        actor=self.actors[aid]
        if actor["action"] or actor["owner"]!="procedural" and requested is None and not provider_fallback:
            return
        self._repair_routine(aid)
        self._check_fears(aid)
        candidates,rejected=self.candidates(actor)
        if requested and requested.get('action') == 'chat' and not any(
                c['kind'] == 'chat' and c['target_id'] == requested.get('target_id')
                and (not requested.get('social_category') or c.get('social_category') == requested['social_category'])
                for c in candidates):
            explicit = self._explicit_social_candidate(actor, requested)
            if explicit:
                candidates.append(explicit)
        recommendation=actor.get('player_recommendation')
        if (requested is None and recommendation and recommendation['status']=='pending'
                and self.now < recommendation['expires_at']):
            if not any(self._matches_recommendation(c, recommendation) for c in candidates):
                explicit = (self._explicit_social_candidate(actor, recommendation)
                            or self._explicit_place_candidate(actor, recommendation))
                if explicit:
                    candidates.append(explicit)
            for candidate in candidates:
                if self._matches_recommendation(candidate,recommendation):
                    candidate['score']=round(candidate['score']+.65,5)
                    candidate['terms']['player_recommendation']=.65
        chosen,draw=self.choose(actor,candidates)
        if requested:
            possible=[c for c in candidates if c["kind"]==requested["action"] and (not requested.get("target_id") or c["target_id"]==requested["target_id"]) and (not requested.get("social_category") or c.get("social_category")==requested["social_category"])]
            if not possible:
                raise RejectedProposal("Requested action has no feasible, known and available target")
            chosen=possible[0]
            draw=None
        pos=self.position_at(actor)
        path=[list(pos)] if chosen["kind"] in ("chat","wait") else self.spatial.path(pos,chosen["anchor"])
        if path is None:
            rejected.append({"kind":chosen["kind"],"reason":"No walkable route"})
            chosen=next(c for c in candidates if c["kind"]=="wait")
            path=[list(pos)]
        kind=chosen["kind"]
        definition=self.rules.actions[kind]
        needs=self.needs_at(actor)
        primary=max(definition["relief"],key=lambda n:needs[n]) if definition["relief"] else None
        reason=f"{primary.capitalize()} pressure is {needs[primary]:.0%}" if primary else "No higher-value available activity"
        if kind=="work":
            reason="Work hours are active and today's work goal is unfinished"
        if kind=="chat":
            return self._start_chat(aid,chosen,candidates,rejected,draw,reason,provider_fallback)
        activity_label=(leisure_drama.scene_for(definition['leisure_activity'],
            self.rng(aid,actor['decision_id']+1,'leisure_scene'))
            if kind.startswith('leisure_') else definition['label'])
        narration=f"{actor['name']} chose {activity_label.lower()}. {reason}."
        with self.transaction("decision.utility.v1",[aid],narration,[reason]) as tx:
            actor=self.edit("actors",aid)
            self.materialize(actor)
            actor["decision_id"]+=1
            self._resolve_recommendation(actor,chosen,candidates)
            actor["last_decision"]={"at":self.now,"id":actor["decision_id"],"chosen":kind,"candidates":candidates,"rejected":rejected,"random_draw":draw,"policy":"procedural fallback while model stays opted in" if provider_fallback else "stable named softmax draw" if draw is not None else "validated external intent"}
            actor["thought"]={"text":definition["thought"],"trigger":f"decision_{actor['decision_id']}","since":self.now}
            duration=definition["duration"]
            travel=len(path)-1
            event_id=f"action_{aid}_{actor['decision_id']}"
            actor["action"]={"id":event_id,"kind":kind,"label":activity_label,"target_id":chosen["target_id"],"phase":"travel" if travel else "using","started_at":self.now,"arrives_at":self.now+travel,"ends_at":self.now+travel+duration,"duration":duration,"path":path,"reason":reason,"definition_version":self.rules.version,"reservation_id":event_id if chosen["target_id"] else None,"partner_id":None}
            self._say(actor,{'action_kind':'party' if kind.startswith('leisure_') and 'party' in kind else 'hobby' if kind.startswith('leisure_') else kind,
                             'job':actor['profile']['job'],'affect':actor['emotion']['type']})
            self._start_routine(actor, chosen)
            if chosen["target_id"]:
                obj=self.edit("objects",chosen["target_id"])
                if len(obj["reservations"])>=obj["capacity"]:
                    raise RejectedProposal("Resource became unavailable")
                obj["reservations"][event_id]={"actor_id":aid,"anchor":chosen["anchor"],"start":self.now,"end":actor["action"]["ends_at"]}
            if travel:
                self.schedule(actor["action"]["arrives_at"],"arrival",aid,event_id)
            else:
                self._begin_use(actor)
            self._schedule_urgent(actor)
        self.metrics["decisions"]+=1

    def _begin_use(self, actor):
        action=actor["action"]
        definition=self.rules.actions[action["kind"]]
        if action["kind"] in DAILY_ACTIONS:
            if not self._step_available(actor,self.objects[action['target_id']],action['kind']):raise RejectedProposal('Household item is unavailable')
            apply_step(actor, self.objects[action["target_id"]], action["kind"])
        if action['kind'] in possessions.POSSESSION_ACTIONS and not self._step_available(actor,self.objects[action['target_id']],action['kind']):
            raise RejectedProposal('Concrete item precondition changed')
        self.materialize(actor)
        actor["position"]=action["path"][-1]
        action["phase"]="using"
        if action['kind']=='work':
            coworkers=coworkers_at_work(actor,self.actors,self.objects)
            plan=work_life.build_shift_plan(actor,coworkers,action['duration'],self.rng(actor['id'],actor['decision_id'],'shift_plan'))
            action['work_plan']=plan['steps']
            action['work_step_index']=0
            if plan['steps']:
                first=plan['steps'][0]
                action['label']=first['task']
                action['current_microtask']=first['task']
                self.schedule(self.now+first['duration_seconds'],'work_step',actor['id'],action['id'])
                self._say(actor,{'action_kind':'work','job':actor['profile']['job']})
        actor["need_rates"]={k:rate/3600-definition["relief"].get(k,0)/action["duration"] for k,rate in self.rules.rates.items()}
        if action['kind']=='eat_recipe':
            # Concrete meals satisfy hunger only when that exact item is consumed.
            actor['need_rates']={k:rate/3600 for k,rate in self.rules.rates.items()}
        if action["kind"]=="chat":
            scale=min(1,action["duration"]/480)
            tone=psychology.SOCIAL_CATEGORIES.get(action.get("social_category","small_talk"),{}).get("tone")
            relief={"social":.56*scale,"fun":(.4 if tone=="play" else .16)*scale}
            actor["need_rates"]={k:rate/3600-relief.get(k,0)/action["duration"] for k,rate in self.rules.rates.items()}
        if definition["cost"]:
            if actor["money"]<definition["cost"]:
                raise RejectedProposal("Cannot afford start cost")
            actor["money"]-=definition["cost"]
            self.edit("world","economy")["spent"]+=definition["cost"]
        self.schedule(action["ends_at"],"complete",actor["id"],action["id"])
        action['needs_when_started']=self.needs_at(actor)
        self._appraise(actor,{'kind':'activity_started','category':action['kind'],'text':'Beginning '+action['label']})

    def _schedule_urgent(self, actor):
        needs=self.needs_at(actor)
        action=actor["action"]
        affected=self.rules.actions[action["kind"]]["relief"]
        physical=("hunger","thirst","bladder","fatigue","hygiene")
        preparing_food=action["kind"] in ({"buy_groceries","stock_fridge","fetch_ingredients","prepare_meal","serve_meal","eat_meal"}|set(possessions.POSSESSION_ACTIONS)-{'change_outfit'})
        critical=[key for key in physical if needs[key]>=.939 and not(key=="hunger" and preparing_food)]
        covered=[key for key in critical if key in affected]
        # A resident may have several critical needs at once.  Let the action
        # already addressing one of them finish; otherwise bladder and fatigue
        # can interrupt each other every second and neither receives relief.
        if covered:
            # Short concrete relief (notably a toilet visit) is atomic enough
            # to finish.  A long action such as sleep is rechecked only after
            # its covered critical need has clearly recovered below .90, so it
            # cannot ignore another critical need for its whole duration.
            if action["duration"]>900:
                recovery=[]
                for key in covered:
                    rate=actor["need_rates"][key]
                    if rate<0 and needs[key]>.90:
                        recovery.append(max(1,math.ceil((needs[key]-.90)/-rate)))
                if recovery:
                    due=self.now+min(recovery)
                    if due<action["ends_at"]:
                        self.schedule(due,"urgent",actor["id"],action["id"])
            return
        times=[]
        for key in physical:
            if key == "hunger" and preparing_food:
                continue  # Eating requires preparation; do not interrupt it every second.
            rate=actor["need_rates"][key]
            if rate>0:
                times.append(max(1,math.ceil((.94-needs[key])/rate)))
        if times and actor["action"]:
            due=self.now+min(times)
            if due<actor["action"]["ends_at"]:
                self.schedule(due,"urgent",actor["id"],actor["action"]["id"])

    def _start_chat(self, aid, chosen, candidates, rejected, draw, reason, provider_fallback=False):
        actor=self.actors[aid]
        other=self.actors[chosen["target_id"]]
        category=chosen.get("social_category", "small_talk")
        social = next(s for s in psychology.social_candidates({**actor,"needs":self.needs_at(actor)},
                       {**other,'social_status':storyteller.social_status(other,self.actors),
                        'needs':self.needs_at(other)},self.now) if s["category"]==category)
        if not social["allowed"]:
            raise RejectedProposal(social["reason"])
        if category=='undermine' and actor.get('workplace_id') not in {r['id'] for r in self.spatial.regions_at(self.position_at(actor))}:
            raise RejectedProposal('Workplace rivalry requires both residents to meet at work')
        label=psychology.SOCIAL_CATEGORIES[category].get("label",category.replace("_"," "))
        topic=chosen.get('topic') or social.get('topic')
        topic_phrase=f" about {topic}" if topic else ''
        # Recipient decides from its own needs and willingness, with one named draw.
        willingness=min(.97,social["willingness"]+self.needs_at(other)["social"]*.25)
        accepted=max(self.needs_at(other).values())<.91 and self.rng(other["id"],f"{aid}:{actor['decision_id']+1}","chat_consent").random()<willingness
        if not accepted:
            with self.transaction("social.decline.v1",[aid,other["id"]],f"{other['name']} is not ready to chat. {actor['name']} respects that and reconsiders.",["Recipient willingness check declined"]):
                actor=self.edit("actors",aid)
                actor["decision_id"]+=1
                self._resolve_recommendation(actor,chosen,candidates)
                actor["cooldowns"]["chat"]=self.now+900
                other=self.edit("actors",other["id"])
                self._social_complete(actor,other,category,"declined")
                actor.update(psychology.update_fears(actor,"social_rejected",self.now,f"beat_{self.store.sequence+1:08}"))
                self._appraise(actor,"Recipient declined")
                self._appraise(other,"Expressed a social boundary")
                actor["last_decision"]={"at":self.now,"id":actor["decision_id"],"chosen":"chat","social_category":category,"candidates":candidates,"rejected":rejected,"random_draw":draw,"policy":"recipient declined; procedural provider fallback" if provider_fallback else "recipient declined; no shared action executed"}
                self._perceive(actor,f"{other['name']} declined a conversation.",other["id"],"hearing")
                self.schedule(self.now+1,"decision",aid,actor["decision_id"])
            self.metrics["declined_chats"]+=1
            return
        with self.transaction("social.accept.v2",[aid,other["id"]],f"{actor['name']} and {other['name']} agree: {label}{topic_phrase}.",[reason,"Recipient accepted the request",category]):
            actor=self.edit("actors",aid)
            other=self.edit("actors",other["id"])
            self._resolve_recommendation(actor,chosen,candidates)
            if other["action"]:
                self._release(other)
            for person,partner in ((actor,other),(other,actor)):
                self.materialize(person)
                person["decision_id"]+=1
                event_id=f"action_{aid}_{actor['decision_id']}" if person is actor else actor["action"]["id"]
                duration=social["duration_seconds"]
                person["action"]={"id":event_id,"kind":"chat","social_category":category,"topic":topic,
                                  "label":f"{label}{topic_phrase} · {partner['name'].split()[0]}","target_id":partner["id"],"phase":"using","started_at":self.now,"arrives_at":self.now,"ends_at":self.now+duration,"duration":duration,"path":[list(person["position"])],"reason":"Both participants accepted this interaction","definition_version":self.rules.version,"reservation_id":None,"partner_id":partner["id"]}
                person["thought"]={"text":f"I would like to spend a moment with {partner['name'].split()[0]}{topic_phrase}.","trigger":"accepted conversation","since":self.now}
                self._begin_use(person)
                self._say(person,{'social_category':category,'action_kind':'date' if category=='ask_date' else 'hobby'})
                self._perceive(person,f"{partner['name']} agreed to spend time talking with me.",partner["id"],"hearing")
                self._schedule_urgent(person)
            actor["last_decision"]={"at":self.now,"id":actor["decision_id"],"chosen":"chat","social_category":category,"candidates":candidates,"rejected":rejected,"random_draw":draw,"policy":"procedural provider fallback plus recipient consent" if provider_fallback else "utility choice plus recipient consent"}
        self.metrics["decisions"]+=1

    def _perceive(self, actor, content, source, modality):
        bid=f"beat_{self.store.sequence+1:08}"
        pid=f"perception_{actor['id']}_{self.store.sequence+1}_{len(actor['perceptions'])}"
        perception={"id":pid,"observer":actor["id"],"at":self.now,"modality":modality,"content":content,"source_entity":source,"source_beat":bid,"reliability":"direct"}
        actor["perceptions"]=(actor["perceptions"]+[perception])[-16:]
        actor["memories"]=(actor["memories"]+[{"id":"memory_"+pid,"at":self.now,"content":content,"source_percepts":[pid],"salience":.6,"retention":"retained"}])[-16:]
        actor["beliefs"]=(actor["beliefs"]+[{"id":"belief_"+pid,"proposition":content,"confidence":"high","evidence":[pid],"valid_from":self.now}])[-16:]
        if source in self.actors and source != actor["id"]:
            actor.update(psychology.observe(actor, source, content, self.now, bid, modality))

    def _release(self, actor):
        action=actor["action"]
        if not action:
            return
        self.materialize(actor)
        actor["position"]=list(self.position_at(actor))
        if action["reservation_id"] and action["target_id"] in self.objects:
            obj=self.edit("objects",action["target_id"])
            obj["reservations"].pop(action["reservation_id"],None)
        actor["need_rates"]={k:v/3600 for k,v in self.rules.rates.items()}
        actor["action"]=None

    def _appraise(self, actor, cause):
        needs=self.needs_at(actor)
        source=cause if isinstance(cause,dict) else {'kind':'appraisal','text':cause}
        cause=source.get('text',source['kind'])
        evidence=f'beat_{self.store.sequence+1:08}'
        actor['affect']=affect.appraise(actor,needs,self.now,source,evidence)
        peak=max(needs.values())
        mean=sum(needs.values())/len(needs)
        label="Uncomfortable" if peak>.85 else "Restless" if needs["fun"]>.67 else "Lonely" if needs["social"]>.65 else "Content" if mean>.28 else "Happy"
        social=actor.get("psychology",{}).get("social_appraisal")
        if social and social['expires_at']>self.now:
            actor['affect']=affect.appraise(actor,needs,self.now,{
                **social,'kind':'romantic_affection' if social.get('adult_relation') else 'social_interaction',
                'text':f"{social['category']}: {social['outcome']}"},social['evidence_id'])
        if social and social["expires_at"]>self.now and peak < .9:
            label=social["type"]
            cause=f"{social['category']}: {social['outcome']} · evidence {social['evidence_id']}"
        fear=actor.get("psychology",{}).get("active_fear")
        if fear and fear["expires_at"] > self.now:
            actor['affect']=affect.appraise(actor,needs,self.now,{
                'kind':'dog_encounter' if fear['kind']=='dogs' else 'work_warning',
                'text':fear['event'],'expires_at':fear['expires_at']},fear['evidence_id'])
            label="Afraid" if fear["kind"]=="dogs" else "Worried"
            cause=f"{fear['event']} · evidence {fear['evidence_id']}"
        actor["emotion"]={"type":label,"valence":round(1-mean*1.6,3),"arousal":round(max(.1,peak*.6),3),"intensity":round(max(.2,abs(.5-mean)),3),"cause":cause,"since":self.now,"expires_at":None}
        if label in {"Afraid","Worried","Tense","Disappointed"}:
            actor["emotion"].update(valence=-.35,arousal=.75 if label=="Afraid" else .5,intensity=.6,
                expires_at=fear["expires_at"] if fear and fear["expires_at"]>self.now else social.get("expires_at") if social else None)
        actor["goals"][0]["progress"]=round(1-mean,3)
        actor["goals"][1]["progress"]=min(1,actor["schedule"]["work_seconds"]/max(1,actor["schedule"]["work_target_seconds"]))

    def _say(self, actor, context):
        actor['speech']={'text':self.speech.choose(context,self.rng(actor['id'],actor['decision_id'],
            'speech:'+str(self.now)+':'+str(context))), 'since':self.now,'expires_at':self.now+480}

    def _work_step(self, aid):
        actor=self.actors[aid]
        action=actor['action']
        if not action or action['kind']!='work':return
        index=action.get('work_step_index',0)
        plan=action.get('work_plan',[])
        if index>=len(plan):return
        step=plan[index]
        outcome=work_life.resolve_work_step(actor,step,self.rng(aid,actor['decision_id'],'work_step:'+str(index)))
        check=percentile.resolve(actor,step['task'],
            self.rng(aid,actor['decision_id'],'percentile_work:'+str(index)),
            context={'at':self.now,'environment':8 if outcome['mishap'] else 0})
        coworker=outcome.get('colleague_id')
        if coworker and (coworker not in self.actors or not self.actors[coworker].get('action')
                or self.actors[coworker]['action'].get('kind')!='work'
                or self.actors[coworker]['action'].get('phase')!='using'
                or self.actors[coworker].get('workplace_id')!=actor.get('workplace_id')):
            coworker=None
            outcome['interaction']=None
        participant_ids=[aid]+([coworker] if coworker in self.actors else [])
        narrative=f"{actor['name']} completed {step['task'].lower()}."
        if outcome['interaction'] and coworker in self.actors:
            narrative+=f" {actor['name']} and {self.actors[coworker]['name']} {outcome['interaction'].replace('_',' ')} at work."
        if outcome['mishap']:narrative+=f" A {outcome['mishap'].replace('_',' ')} changed the result."
        narrative+=f" W100 {check['roll']}/{check['threshold']}: {check['grade']}."
        with self.transaction('work.microtask.v1',participant_ids,narrative,['seeded profession-specific outcome']):
            actor=self.edit('actors',aid)
            self.materialize(actor)
            action=actor['action']
            career=actor['career']
            career['performance']=clamp(career.get('performance',.5)+outcome['performance_delta'])
            career['performance']=clamp(career['performance']+
                {'excellent':.016,'success':.006,'mixed':-.006,'setback':-.019}[check['grade']])
            actor['aptitudes']['last_check']=check
            if check['grade'] in {'excellent','success'}:
                skill=check['skill']
                actor['skills'][skill]=round(min(1,actor['skills'].get(skill,.15)+.0007),4)
            actor['needs']['fun']=clamp(actor['needs']['fun']-outcome['fun_delta'])
            actor['action']['work_step_index']=index+1
            if index+1<len(plan):
                following=plan[index+1]
                action['label']=following['task']
                action['current_microtask']=following['task']
                self.schedule(self.now+following['duration_seconds'],'work_step',aid,action['id'])
            self._say(actor,{'event':'failure' if outcome['mishap'] else '', 'action_kind':'work_microtask','job':actor['profile']['job']})
            if coworker in self.actors and outcome['interaction']:
                colleague=self.edit('actors',coworker)
                self._social_complete(actor,colleague,
                    'coordinate_work' if outcome['interaction']!='small_talk' else 'small_talk',
                    'negative' if outcome['interaction']=='disagree' else 'positive')
                colleague['speech']={'text':self.speech.choose({'relationship':'coworker'},self.rng(coworker,colleague['decision_id'],'coworker:'+str(self.now))),
                    'since':self.now,'expires_at':self.now+360}
                self._perceive(colleague,f"{actor['name']} {outcome['interaction'].replace('_',' ')} with me at work.",aid,'workplace')
            self._appraise(actor,{'kind':'work_progress','text':narrative})

    def complete(self, aid):
        actor=self.actors[aid]
        action=deepcopy(actor["action"])
        participants=[aid]
        partner=action.get("partner_id")
        if partner:
            participants.append(partner)
        shared=[]
        social_sites={'community_meet','visit_bar','visit_pool','dance_club','exercise_gym','visit_clinic',
                      'school_day','kindergarten_day','attend_lecture','attend_seminar',
                      'run_lab','study_library','campus_lunch','dorm_party'}
        if action['kind'] in social_sites or action['kind'].startswith('leisure_'):
            here=self.objects.get(action.get('target_id'),{}).get('building_id')
            if here:
                available=[other for other in self.actors.values() if other['id']!=aid
                    and other.get('action') and other['action'].get('phase')=='using'
                    and (other['action']['kind'] in social_sites or other['action']['kind'].startswith('leisure_'))
                    and self.objects.get(other['action'].get('target_id'),{}).get('building_id')==here
                    and self.spatial.visible(self.position_at(actor),self.position_at(other),radius=5)
                    and actor['cooldowns'].get('shared:'+other['id'],0)<=self.now]
                if available:
                    scene_rng=self.rng(aid,actor['decision_id'],'shared_activity:'+action['id'])
                    scene_rng.shuffle(available)
                    for other in available:
                        relation=actor.get('relations',{}).get(other['id'],{})
                        interest=max(.04,min(.88,.18+.32*other.get('psychology',{}).get('big_five',{}).get('extraversion',.5)
                            +.16*other.get('needs',{}).get('social',.3)+.16*relation.get('closeness',.2)
                            -.22*relation.get('tension',0)))
                        if scene_rng.random()<interest:
                            shared.append(other['id'])
                            participants.append(other['id'])
                        if len(shared)>=3:break
        definition=self.rules.actions[action["kind"]]
        if action['kind'] in possessions.POSSESSION_ACTIONS and not self._step_available(actor,self.objects[action['target_id']],action['kind'],completion=True):
            self.interrupt(aid,'Concrete item precondition changed before completion')
            return
        if action["kind"] in DAILY_ACTIONS:
            if not self._step_available(actor,self.objects[action['target_id']],action['kind']):
                self.interrupt(aid,'Household item precondition changed');return
            try:
                apply_step(actor,self.objects[action["target_id"]],action["kind"])
            except StepUnavailable as exc:
                self.interrupt(aid,f"Household precondition changed: {exc}")
                return
        finished_label=psychology.SOCIAL_CATEGORIES[action.get("social_category","small_talk")]["label"] if partner else action.get('label',definition['label'])
        with self.transaction("action.complete.v1",participants,f"{actor['name']} finished {finished_label.lower()}.",[action["reason"]]) as tx:
            person=self.edit("actors",aid)
            self.materialize(person)
            self._daily_complete(person, action)
            if action['kind']=='eat_recipe':
                for key,amount in definition['relief'].items():person['needs'][key]=clamp(person['needs'][key]-amount)
                if person.get('last_meal',{}).get('at')==self.now:
                    tx['text']+=f" On the plate: {person['last_meal']['label']}."
            if action["kind"]=="work":
                shift=careers.complete_shift(person,action['duration'],self.now,
                    f"beat_{self.store.sequence+1:08}",definition['income'])
                person['career'],person['skills']=shift['career'],shift['skills']
                person["money"]+=shift['income']
                self.edit("world","economy")["earned"]+=shift['income']
                person["schedule"]["work_seconds"]+=action["duration"]
                security=work_life.evaluate_job_security(person,person['career']['performance'],
                    self.rng(aid,person['decision_id'],'job_security'))
                if security['event']=='fired':
                    person['profile']['job']='Unemployed'
                    person['career']['job']='Unemployed'
                    person['workplace']=None
                    person['workplace_id']=None
                    person['schedule']['work_target_seconds']=0
                    person['goals'][1].update(title='Find a new job',progress=0)
                    self._say(person,{'event':'fired'})
                    tx['text']+=f" {person['name']} was dismissed and can now seek a new job."
                elif security['event']=='job_warning':
                    person['thought']={'text':'My work is under review; I should pay attention.',
                        'trigger':'job_warning','since':self.now}
                    tx['text']+=f" {person['name']} received a work warning."
            if action['kind']=='job_search':
                openings=work_life.search_jobs(person,seed=self.rng(aid,person['decision_id'],'job_search'),limit=5)
                if openings:
                    search_rng=self.rng(aid,person['decision_id'],'job_opening')
                    choice=search_rng.choices(openings,weights=[row['success_probability'] for row in openings],k=1)[0]
                    proposal=work_life.evaluate_hire(person,choice['job'],
                        self.rng(aid,person['decision_id'],'hiring'))
                    if proposal['event']=='hired':
                        person['profile']['job']=proposal['job']
                        person['career']=careers.initial(person,self.now)
                        person['workplace']=assigned_service_job(person,self.objects) or assigned_workplace(person,self.objects)
                        person['workplace_id']=person['workplace']['workplace_id'] if person['workplace'] else None
                        person['schedule'].update(start=person['career']['schedule_start'],
                            end=person['career']['schedule_start']+8*3600,work_target_seconds=4*3600)
                        person['goals'][1].update(title="Finish today's work",progress=0)
                        self._say(person,{'event':'hired'})
                        tx['text']+=f" {person['name']} was hired as {proposal['job']}."
                    else:
                        self._say(person,{'event':'failure'})
                        tx['text']+=f" {person['name']}'s application was declined."
                person['cooldowns']['job_search']=self.now+3600
            if action['kind'] in {'school_day','kindergarten_day'}:
                person['schedule']['work_seconds']+=action['duration']
                tx['text']+=f" {person['name']} attended their scheduled learning day."
            if action['kind'] in {'attend_lecture','attend_seminar','run_lab','study_library'}:
                check=percentile.resolve(person,action['kind'],
                    self.rng(aid,person['decision_id'],'percentile_campus:'+action['id']),
                    skill='analysis' if action['kind']=='run_lab' else 'teaching' if action['kind']=='attend_seminar' else 'reading',
                    context={'at':self.now,'environment':7 if action['kind']=='run_lab' else 0})
                person['aptitudes']['last_check']=check
                person.setdefault('education',{'university_student':False,'progress_hours':0.0})
                person['education']['progress_hours']=round(person['education']['progress_hours']+
                    action['duration']/3600*(1.2 if check['grade']=='excellent' else .4 if check['grade']=='setback' else 1),3)
                if person['profile']['job']=='Student':
                    person['schedule']['work_seconds']+=action['duration']
                tx['text']+=f" Campus learning: W100 {check['roll']}/{check['threshold']} ({check['grade']})."
            if action['kind'].startswith('leisure_'):
                activity=definition['leisure_activity']
                event=leisure_drama.resolve_social_event(person,None,activity,{},
                    self.rng(aid,person['decision_id'],'leisure_event'))
                person['last_leisure_event']={'at':self.now,'activity':activity,
                                              'scene':action.get('label', definition['label']),
                                              'kind':event['kind']}
                if event['kind'] not in {'quiet','good_time'}:
                    self._say(person,{'event':'fight' if event['kind']=='fight' else 'failure' if event['kind'] in {'minor_mishap','awkward_moment'} else 'party_started' if 'party' in activity else '',
                                      'action_kind':'party' if 'party' in activity else 'hobby'})
                    self._perceive(person,f"During {activity.replace('_',' ')}: {event['kind'].replace('_',' ')}.",aid,'participation')
                    tx['text']+=f" A {event['kind'].replace('_',' ')} followed."
            if shared:
                context_kind='seminar debate' if action['kind']=='attend_seminar' else (
                    'party banter' if action['kind']=='dorm_party' else 'shared conversation')
                scene_members=[aid]+shared
                person['last_group_scene']={'at':self.now,'kind':context_kind,
                                            'participant_ids':scene_members}
                for other_id in shared:
                    companion=self.edit('actors',other_id)
                    category='play_together' if person['age']<18 or companion['age']<18 else (
                        'share_interest' if action['kind'] in {'attend_seminar','run_lab'} else 'tell_joke')
                    check=percentile.resolve(person,category,
                        self.rng(aid,person['decision_id'],'group_check:'+action['id']+':'+other_id),
                        social=True,target=companion,
                        context={'at':self.now,'actor_id':aid,'environment':4 if action['kind']=='dorm_party' else 0})
                    outcome='negative' if check['grade']=='setback' else 'neutral' if check['grade']=='mixed' else 'positive'
                    self._social_complete(person,companion,category,outcome)
                    person['cooldowns']['shared:'+other_id]=self.now+1800
                    companion['cooldowns']['shared:'+aid]=self.now+1800
                    companion['last_group_scene']={'at':self.now,'kind':context_kind,
                                                   'participant_ids':scene_members,'outcome':outcome}
                    if check['grade']=='setback':
                        self._appraise(companion,{'kind':'story_argument',
                            'text':f"A joke or disagreement with {person['name']} landed badly.",
                            'subject_id':aid})
                    self._say(companion,{'social_category':'joke' if outcome!='negative' else 'set_boundary'})
                    tx['text']+=f" {companion['name']} joined {context_kind} ({outcome}; W100 {check['roll']}/{check['threshold']})."
                cross=storyteller.group_dynamic(person,[self.actors[oid] for oid in shared],
                    self.rng(aid,person['decision_id'],'group_dynamic:'+action['id']))
                if cross:
                    first=self.edit('actors',cross['first_id'])
                    second=self.edit('actors',cross['second_id'])
                    self._social_complete(first,second,cross['category'],cross['outcome'])
                    for member in (first,second):
                        member['last_group_scene']['cross_turn']=cross['kind']
                        self._perceive(member,cross['text'],aid,'participation')
                    if cross['kind']=='mediated_disagreement':
                        storyteller.adapt_style(person,'unexpected_support')
                    tx['text']+=' '+cross['text']
                self._say(person,{'social_category':'joke'})
            incident=storyteller.incident_for(person,action,
                self.rng(aid,person['decision_id'],'storyteller:'+action['id'])) if not partner else None
            if incident:
                evidence=f"beat_{self.store.sequence+1:08}"
                transfer=storyteller.apply_incident(person,incident,self.now,evidence,action['kind'])
                economy=self.edit('world','economy')
                economy['earned' if transfer>=0 else 'spent']+=abs(transfer)
                storyteller.adapt_style(person,incident['id'])
                person['social_status']=storyteller.social_status(person,self.actors)
                tx['rule']='storyteller.activity.v1'
                tx['text']+=f" {incident['text']}"
                tx['reasons'].append('Incident resolved only after '+action['kind']+' completed')
                self._perceive(person,incident['text'],action['target_id'] or aid,'participation')
            pref=definition["preference"]
            if pref in person["skills"]:
                person["skills"][pref]=min(1,person["skills"][pref]+.003)
            if pref in person["profile"]["interests"]:
                person["goals"][2]["progress"]=min(1,person["goals"][2]["progress"]+action["duration"]/3600)
            if action["target_id"] in self.objects:
                obj=self.edit("objects",action["target_id"])
                obj["condition"]=max(.2,obj["condition"]-.0001*action["duration"]/600)
            if partner:
                category=action.get("social_category","small_talk")
                if not action.get("social_effects_applied"):
                    other=self.edit("actors",partner)
                    social_turn=storyteller.social_turn(person,other,category,
                        self.rng(aid,person['decision_id'],'storyteller_social:'+action['id']))
                    check=percentile.resolve(person,category,
                        self.rng(aid,person['decision_id'],'percentile_social:'+action['id']),
                        social=True,target=other,context={'at':self.now,'actor_id':aid})
                    person['aptitudes']['last_check']=check
                    tx['text']+=f" W100 {check['roll']}/{check['threshold']}: {check['grade']}."
                    # A resolved bilateral encounter changes both directions once.
                    outcome="negative" if psychology.SOCIAL_CATEGORIES[category]["tone"]=="conflict" or social_turn and social_turn['kind']=='argument' else "positive"
                    if check['grade']=='setback' and category in {'tell_joke','compliment','flirt','gossip','undermine','challenge'}:
                        outcome='negative'
                    elif check['grade']=='mixed' and outcome=='positive':
                        outcome='neutral'
                    self._social_complete(person,other,category,outcome)
                    if social_turn:
                        kind=social_turn['kind']
                        if kind=='rumor':
                            subject=social_turn['subject_id']
                            storyteller.remember_rumor(other,subject,aid,self.now,f"beat_{self.store.sequence+1:08}")
                            social_turn['text']=social_turn['text'].replace(subject,self.actors[subject]['name'])
                        elif kind in {'argument','sabotage','sabotage_backfire','friendly_rivalry'}:
                            for participant,rival_id in ((person,partner),(other,aid)):
                                edge=participant['relations'][rival_id]
                                edge['rivalry']=clamp(edge.get('rivalry',0)+(.04 if kind=='friendly_rivalry' else .12))
                                if kind!='friendly_rivalry':
                                    edge['tension']=clamp(edge.get('tension',0)+(.10 if kind=='argument' else .13))
                                    edge['trust']=clamp(edge.get('trust',.35)-(.035 if kind=='sabotage' else .08))
                            if kind=='sabotage':
                                other['career']['performance']=clamp(other['career'].get('performance',.5)-.04)
                            if kind=='sabotage_backfire':
                                person['career']['performance']=clamp(person['career'].get('performance',.5)-.025)
                        storyteller.adapt_style(person,kind)
                        storyteller.adapt_style(other,kind)
                        person['last_social_incident']={'kind':kind,'with':partner,'at':self.now}
                        other['last_social_incident']={'kind':kind,'with':aid,'at':self.now}
                        tx['text']+=' '+social_turn['text']
                        tx['reasons'].append('Both participants completed '+category+' before social consequence')
                        self._perceive(person,social_turn['text'],partner,'participation')
                        self._perceive(other,social_turn['text'],aid,'participation')
                        if kind in {'argument','sabotage_backfire','sabotage'}:
                            for participant in (person,other):
                                self._appraise(participant,{'kind':'story_argument' if kind=='argument' else 'story_sabotage_backfire',
                                    'text':social_turn['text'],'subject_id':partner if participant is person else aid})
                    person['social_status']=storyteller.social_status(person,self.actors)
                    other['social_status']=storyteller.social_status(other,self.actors)
                    relation=person.get('social_graph',{}).get(partner) or person.get('relations',{}).get(partner,{})
                    romantic=(category=='express_affection' and person['age']>=18 and other['age']>=18
                        and person.get('family',{}).get('partner_id')==partner
                        and other.get('family',{}).get('partner_id')==aid
                        and relation.get('layers',{}).get('family',{}).get('status') in (None,'none','unknown'))
                    context={'tension':relation.get('tension',0),'closeness':relation.get('closeness',0),
                        'both_adults':person['age']>=18 and other['age']>=18,
                        'non_kin':romantic,'mutual_consent':romantic,'romantic':romantic,
                        'committed':romantic,'trying_for_child':False,
                        'private_at_home':romantic and person['home_id']==other['home_id']
                            and any('bedroom' in region['name'].lower()
                                for region in self.spatial.regions_at(person['position']))}
                    drama=leisure_drama.resolve_social_event(person,other,
                        'date' if romantic else 'work_chat' if category=='coordinate_work' else 'make_friends',
                        context,self.rng(aid,person['decision_id'],'social_event'))
                    if drama['kind'] not in {'quiet','good_time'}:
                        for participant,other_id in ((person,partner),(other,aid)):
                            graph=participant.get('social_graph',{})
                            edge=graph.get(other_id) or participant.get('relations',{}).get(other_id)
                            if edge:
                                effects=drama['effects']
                                edge['closeness']=clamp(edge.get('closeness',.5)+sum(effects.get('relationship',(0,0)))/200)
                                edge['tension']=clamp(edge.get('tension',0)+sum(effects.get('tension',(0,0)))/200)
                                edge['attraction']=clamp(edge.get('attraction',0)+sum(effects.get('romance',(0,0)))/200)
                            participant['last_social_event']={'at':self.now,'with':other_id,'kind':drama['kind']}
                            self._say(participant,{'event':'fight' if drama['kind']=='fight' else '',
                                'action_kind':'kiss' if drama['kind']=='kiss' else 'argument' if drama['kind'] in {'argument','shouting_match','fight'} else 'date' if romantic else 'hobby'})
                        tx['text']+=f" {person['name']} and {other['name']} had a {drama['kind'].replace('_',' ')}."
                    if other["action"] and other["action"]["id"]==action["id"]:
                        other["action"]["social_effects_applied"]=True
                topic=f" about {action['topic']}" if action.get('topic') else ''
                self._perceive(person,f"We completed {category.replace('_',' ')}{topic} with {self.actors[partner]['name']}.",partner,"participation")
            else:
                self._perceive(person,f"I finished {definition['label'].lower()}.",action["target_id"] or aid,"participation")
            self._release(person)
            person['social_status']=storyteller.social_status(person,self.actors)
            person["cooldowns"][action["kind"]]=self.now+(600 if action["kind"]=="chat" else 30)
            if action['kind'] in SERVICE_ACTIONS:person['cooldowns'][action['kind']]=self.now+(86400 if action['kind'].startswith('visit_') else 7200)
            relief={k:round(value-person['needs'][k],4) for k,value in action.get('needs_when_started',{}).items()
                    if value-person['needs'][k]>.05 and definition['relief'].get(k,0)>0}
            self._appraise(person,{'kind':'activity_completed','category':action['kind'],'text':f"Completed {action['kind']}"})
            if incident:
                adverse=incident['money']<0 or sum(incident['needs'].values())>0
                self._appraise(person,{'kind':'story_bad' if adverse else 'story_good',
                    'text':incident['text'],'category':incident['id']})
            if relief:
                self._appraise(person,{'kind':'need_relief','category':max(relief,key=relief.get),'relief':relief,
                    'text':'Actual need relief: '+', '.join(f'{k} {v:.0%}' for k,v in relief.items())})
            self.schedule(self.now+1,"decision",aid,person["decision_id"])
        self.metrics["completed_actions"]+=1
        # Administrative appointments are occasional, not a repeating comfort loop.

    def interrupt(self, aid, reason, schedule=True):
        actor=self.actors[aid]
        if not actor["action"]:
            return
        partner=actor["action"].get("partner_id")
        ids=[aid]+([partner] if partner and self.actors[partner]["action"] and self.actors[partner]["action"]["id"]==actor["action"]["id"] else [])
        with self.transaction("action.interrupt.v1",ids,f"{actor['name']} stopped {actor['action']['label'].lower()}. {reason}.",[reason]):
            for person_id in ids:
                person=self.edit("actors",person_id)
                previous=person["action"]["kind"]
                self._release(person)
                person["cooldowns"][previous]=self.now+120
                person["thought"]={"text":reason,"trigger":"interruption","since":self.now}
                self._appraise(person,reason)
                if schedule:
                    self.schedule(self.now+1,"decision",person_id,person["decision_id"])
        self.metrics["interrupted_actions"]+=1

    def advance(self, seconds):
        if not isinstance(seconds,int) or seconds<0:
            raise ValueError("Advance requires nonnegative integer world seconds")
        start=time.perf_counter()
        target=self.now+seconds
        events=0
        while self.queue and self.queue[0][0]<=target:
            due,serial,kind,aid,token=heapq.heappop(self.queue)
            self.now=due
            events+=1
            if events>1000000:
                raise RuntimeError("Scheduler budget exceeded; time has not skipped pending events")
            if kind=="animal_tick":
                self._animal_tick()
                continue
            if kind=="midnight":
                with self.transaction("calendar.day.v1",list(self.actors),"A new day begins. Daily work and hobby goals start afresh."):
                    for actor_id in self.actors:
                        actor=self.edit("actors",actor_id)
                        actor["schedule"]["day"]=self.now//86400
                        actor["schedule"]["work_seconds"]=0
                        actor["goals"][1]["progress"]=0
                        actor["goals"][2]["progress"]=0
                    self.schedule(self.now+86400,"midnight",None,0)
                continue
            actor=self.actors[aid]
            if kind=="decision":
                if actor["decision_id"]==token:
                    self.decide(aid)
                continue
            action=actor["action"]
            if not action or action["id"]!=token:
                continue
            if kind=="arrival":
                obj=self.objects[action["target_id"]]
                if obj["condition"]<=.1 or action["id"] not in obj["reservations"]:
                    self.interrupt(aid,"The reserved object is no longer usable")
                    continue
                if not self._step_available(actor,obj,action['kind']):
                    self.interrupt(aid,'Object or portable item precondition changed');continue
                if action["kind"] in DAILY_ACTIONS:
                    try:
                        apply_step(actor,obj,action["kind"])
                    except StepUnavailable as exc:
                        self.interrupt(aid,f"Household precondition changed: {exc}")
                        continue
                with self.transaction("travel.arrive.v1",[aid],f"{actor['name']} reached {obj['name'].lower()} and began {action['label'].lower()}.",["Walkable path completed","Reservation revalidated"]):
                    actor=self.edit("actors",aid)
                    self._begin_use(actor)
                    self._schedule_urgent(actor)
            elif kind=="complete":
                self.complete(aid)
            elif kind=='work_step':
                self._work_step(aid)
            elif kind=="urgent":
                needs=self.needs_at(actor)
                affected=self.rules.actions[action["kind"]]["relief"]
                preparing_food=action["kind"] in ({"buy_groceries","stock_fridge","fetch_ingredients","prepare_meal","serve_meal","eat_meal"}|set(possessions.POSSESSION_ACTIONS)-{'change_outfit'})
                urgent=[k for k in ("hunger","thirst","bladder","fatigue","hygiene") if needs[k]>=.939 and k not in affected and not(k=="hunger" and preparing_food)]
                # Do not preempt a presently critical need's own relief with a
                # second critical need.  Completion is the arbitration boundary
                # and the next decision then handles the remaining pressure.
                serving_critical=any(needs[k]>=.939 and k in affected for k in ("hunger","thirst","bladder","fatigue","hygiene"))
                if urgent and not serving_critical:
                    self.interrupt(aid,f"Urgent {urgent[0]} needs attention")
                elif actor["action"] and actor["action"]["id"]==token:
                    # A recovery recheck may occur before another need has
                    # crossed the urgent threshold. Recalculate its future
                    # crossing instead of leaving a long action unmonitored.
                    self._schedule_urgent(actor)
        self.now=target
        self.metrics["events_processed"]+=events
        self.metrics["last_advance_ms"]=round((time.perf_counter()-start)*1000,3)
        # Bound obsolete timers from interrupted actions, preserving stable sequence keys.
        if len(self.queue)>len(self.actors)*8:
            self.queue=[e for e in self.queue if e[2] in ("midnight","animal_tick") or (e[2]=="decision" and self.actors[e[3]]["decision_id"]==e[4]) or (e[2] not in ("decision","midnight","animal_tick") and self.actors[e[3]]["action"] and self.actors[e[3]]["action"]["id"]==e[4])]
            heapq.heapify(self.queue)

    def inspect(self, aid):
        actor=deepcopy(self.actors[aid])
        actor["needs"]=self.needs_at(self.actors[aid])
        actor['social_status']=storyteller.social_status(self.actors[aid],self.actors)
        actor["position"]=list(self.position_at(self.actors[aid]))
        actor["locations"]=self.spatial.regions_at(actor["position"])
        actor["coverage"]=self.rules.data["coverage"]
        actor["clock"]=self.now
        action=actor["action"]
        actor["intentions"]=[]
        if action:
            actor["intentions"].append({"text":f"{action['label']} until about {clock_label(action['ends_at'])}","status":"committed","target_id":action["target_id"],"deadline":action["ends_at"],"prerequisites":["Reach interaction anchor","Hold reservation"] if action["reservation_id"] else ["Remain available"]})
        candidates,_=self.candidates(self.actors[aid])
        for c in candidates[:3]:
            actor["intentions"].append({"text":self.rules.actions[c["kind"]]["label"],"status":"possible next action, not a promise","score":c["score"]})
        actor['recommendation_options'] = [
            {'action': c['kind'], 'target_id': c.get('target_id'),
             'social_category': c.get('social_category'), 'topic': c.get('topic'),
             'label': self.rules.actions[c['kind']]['label'], 'score': c['score']}
            for c in candidates[:12] if c['kind'] != 'wait']
        return self._life_inspection(actor)

    def snapshot(self):
        people=[]
        for a in self.actors.values():
            needs=self.needs_at(a)
            action=a["action"]
            carried={k:v for k,v in a["inventory"].items() if k in {"ingredients","prepared_meal","dirty_dish","food_scraps","groceries"}}
            people.append({"id":a["id"],"name":a["name"],"household_id":a["household_id"],"home_id":a["home_id"],"position":self.position_at(a),"appearance":a["appearance"],"emotion":a["emotion"]["type"],"wellbeing":round(1-sum(needs.values())/len(needs),3),"action":deepcopy(action),"speech":a.get('speech') if a.get('speech',{}).get('expires_at',0)>self.now else None,"carried":carried,"version":a["version"],**self._story_projection(a)})
        counts={}
        for a in people:
            kind=a["action"]["kind"] if a["action"] else "idle"
            counts[kind]=counts.get(kind,0)+1
        return {"name":"Mosswood","seed":self.seed,"clock":self.now,"day":self.now//86400+1,"time":clock_label(self.now),"version":self.store.sequence,"paused":self.paused,"speed":self.speed,"fault":self.fault,
                "actors":people,"population":len(people),"households":len(self.spatial.households),"environment":self.meta["environment"],"activity_counts":counts,
                "wellbeing":round(sum(p["wellbeing"] for p in people)/len(people),3),"metrics":{**self.metrics,"queue_size":len(self.queue),"path_queries":self.spatial.path_queries,"beat_count":self.store.sequence},
                "animals":deepcopy(self.meta.get("animals",{}).get("dogs",[])),
                "resources":[{"id":o["id"],"condition":o["condition"],"reservations":o["reservations"],"daily":o.get("daily",{})} for o in self.objects.values() if o["reservations"] or o.get("daily")]}

    def perspective(self, aid):
        """The agent packet intentionally excludes other people's private components."""
        actor=self.inspect(aid)
        visible=[{"id":o["id"],"name":o["name"],"position":self.position_at(o)} for o in self.actors.values() if o["id"]!=aid and self.spatial.visible(actor["position"],self.position_at(o))]
        candidates,_=self.candidates(self.actors[aid])
        # The actor's self-story is not privileged access to unconscious causes.
        actor.pop('social_graph',None)
        actor['affect']={k:v for k,v in actor.get('affect',{}).items() if k in {'primary','self_narrative','updated_at'}}
        return {"protocol":"lwm.procedural-bridge/0.1","world_time":self.now,"snapshot_version":self.store.sequence,"authority_scope":{"actor_id":aid,"owner":actor["owner"],"owner_epoch":actor["owner_epoch"]},
                "rule_manifest":self.rules.manifest(),"self":actor,"visible_people":visible,
                "available_actions":candidates,"pending_boundaries":[e for e in self.queue if e[3]==aid],
                "omissions":["Other actors' private needs, beliefs, memories and intentions","Exact dialogue","Multi-field synchronization is not implemented"],
                "output_contract":{"actor_id":aid,"owner_epoch":actor["owner_epoch"],"expected_version":actor["version"],"action":"one available action kind","target_id":"optional available target"}}

    def submit_intent(self, payload):
        actor=self.actors[payload["actor_id"]]
        if payload["owner_epoch"]!=actor["owner_epoch"]:
            raise RejectedProposal("Stale ownership epoch")
        if payload["expected_version"]!=actor["version"]:
            raise RejectedProposal("Stale actor component version")
        if actor["action"]:
            raise RejectedProposal("Actor is busy; submit at a decision boundary")
        self.decide(actor["id"],payload)
        return {"accepted":True,"beat_id":actor["last_beat"],"snapshot_version":self.store.sequence}

    def transfer(self, aid, owner, expected_epoch):
        actor=self.actors[aid]
        if actor["owner_epoch"]!=expected_epoch:
            raise RejectedProposal("Stale ownership epoch")
        with self.transaction("authority.transfer.v1",[aid],f"Decision authority for {actor['name']} transferred to {owner}.",["Active mechanics and reservations preserved"]):
            actor=self.edit("actors",aid)
            actor["owner_epoch"]+=1
            actor["owner"]=owner
            if owner=="procedural" and not actor["action"]:
                self.schedule(self.now+1,"decision",aid,actor["decision_id"])
        return self.perspective(aid)

    def set_decision_provider(self, aid, model, expected_version):
        actor=self.actors[aid]
        if actor['version']!=expected_version:
            raise RejectedProposal('Stale actor component version')
        if model is None and not actor.get('decision_provider'):
            raise RejectedProposal('This resident has no active decision provider')
        with self.transaction('authority.provider.v1',[aid],
                f"{actor['name']} {'chose '+model+' for future decisions' if model else 'returned to procedural decisions'}.",
                ['Player opt-in; existing action and reservations preserved']):
            actor=self.edit('actors',aid)
            actor['owner_epoch']+=1
            actor['owner']='external' if model else 'procedural'
            actor['decision_provider']={'model':model,'enabled_at':self.now,'status':'ready','failures':0} if model else None
            actor['decision_provider_error']=None
            if model is None and not actor['action']:
                self.schedule(self.now+1,'decision',aid,actor['decision_id'])
        return {'actor_id':aid,'model':model,'enabled':bool(model),
                'owner_epoch':actor['owner_epoch'],'version':actor['version']}

    def invariants(self):
        errors=self._story_invariants()
        for actor in self.actors.values():
            if not self.spatial.walkable(tuple(self.position_at(actor))):
                errors.append(f"{actor['id']} occupies a blocked cell")
            if any(not 0<=v<=1 for v in self.needs_at(actor).values()):
                errors.append(f"{actor['id']} need out of bounds")
            action=actor["action"]
            if action and action["reservation_id"]:
                if action["id"] not in self.objects[action["target_id"]]["reservations"]:
                    errors.append(f"{actor['id']} has no reservation")
            if actor["money"]<0:
                errors.append(f"{actor['id']} has negative money")
            if any(not isinstance(v, (int, float)) or v < 0 for v in actor["inventory"].values()):
                errors.append(f"{actor['id']} has invalid inventory")
            for rel in actor.get("relations",{}).values():
                if any(not 0 <= rel.get(k,0) <= 1 for k in ("closeness","trust","respect","attraction","tension")):
                    errors.append(f"{actor['id']} relationship out of bounds")
        for obj in self.objects.values():
            if any(isinstance(v,(int,float)) and v<0 for v in obj.get("daily",{}).values()):
                errors.append(f"{obj['id']} has invalid household state")
            if len(obj["reservations"])>obj["capacity"]:
                errors.append(f"{obj['id']} over capacity")
            anchors=[]
            for rid,r in obj["reservations"].items():
                actor=self.actors[r["actor_id"]]
                if not actor["action"] or actor["action"]["id"]!=rid:
                    errors.append(f"{obj['id']} has leaked reservation")
                anchors.append(tuple(r["anchor"]))
            if len(set(anchors))!=len(anchors):
                errors.append(f"{obj['id']} duplicates an interaction slot")
        return errors

    def save(self):
        payload={"seed":self.seed,"rule_hash":self.rules.hash,"now":self.now,"actors":self.actors,"objects":self.objects,"meta":self.meta,"queue":self.queue,"queue_serial":self.queue_serial,"epoch":self.epoch,"metrics":self.metrics,
            'layout':self.layout,'paused':self.paused,'speed':self.speed}
        if self.layout!='legacy':payload['map_blueprint']=self.spatial.blueprint()
        try:self.store.save_checkpoint(payload)
        except Exception as exc:
            # SQLite has rolled back the uncommitted ledger tail. Never later
            # checkpoint an advanced RAM state whose supporting Beats were lost.
            self.paused=True
            self.fault=f'Write failed; returning to last durable checkpoint: {type(exc).__name__}: {exc}'
            durable=self.store.checkpoint()
            if durable:
                self.actors=durable['actors']
                self.objects.clear()
                self.objects.update(durable['objects'])
                self.meta=durable['meta']
                self.now=durable['now']
                self.queue=durable['queue']
                heapq.heapify(self.queue)
                self.queue_serial=durable['queue_serial']
                self.epoch=durable['epoch']
                self.metrics=durable['metrics']
                self._restore_households()
            self.fault=f'Write failed; restored last durable checkpoint: {type(exc).__name__}: {exc}'
            raise

    def canonical_state(self):
        return {"actors":self.actors,"objects":self.objects,"world":self.meta}

    def close(self):
        try:self.save()
        finally:
            self.store.close()
            self.speech.close()
