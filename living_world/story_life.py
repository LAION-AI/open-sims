"""V3 integration: appraisals, known people and concrete possessions.

Only the coordinator calls mutating methods. Observation methods return copies.
"""
from copy import deepcopy
from . import affect, careers, possessions, psychology
from .daily_life import DAILY_ACTIONS, apply_step, StepUnavailable
from .urban_life import SERVICE_ACTIONS, assigned_service_job


class StoryLife:
    def _story_actor(self,actor):
        if 'belongings' not in actor:
            wardrobes=[o for o in self.objects.values() if o['kind']=='wardrobe'
                       and o.get('household_id')==actor['household_id']]
            if actor['household_id']=='student_residence' and wardrobes:
                slot=max(0,int(actor['id'].rsplit('_',1)[-1])-45)
                wardrobe=wardrobes[min(slot,len(wardrobes)-1)]
            else:
                wardrobe=wardrobes[0] if wardrobes else None
            actor.update(possessions.initialize(actor,self.now,wardrobe['id'] if wardrobe else None))
        if 'affect' not in actor:
            actor['affect']=affect.appraise(actor,self.needs_at(actor),self.now,{'kind':'initialization','text':'Authored initial needs'},'initialization')
        actor['workplace']=assigned_service_job(actor,self.objects)
        actor['workplace_id']=actor['workplace']['workplace_id'] if actor.get('workplace') else None

    def _initialize_story(self):
        for actor in self.actors.values():self._story_actor(actor)
        for aid,patch in psychology.initialize_social_graph(self.actors,self.now).items():self.actors[aid].update(patch)
        for aid,patch in psychology.authored_friendships(self.actors,self.now).items():
            self.actors[aid]['relations'].update(patch['relations'])
        self.meta['story_systems']={'version':0,'schema':'mosswood.story/3','taxonomy':'EmoNet-Face 40',
            'truth_policy':'canonical simulation causes are not the actor self-story; no real-person inference'}

    def _migrate_story(self,saved):
        additions=[]
        for oid,obj in self.objects.items():
            if oid not in saved['objects']:
                additions.append({'collection':'objects','subject_id':oid,'component_path':'$','new_value':deepcopy(obj)})
        story={'version':0,'schema':'mosswood.story/3','migration_at':self.now,
            'truth_policy':'appraisals added without fabricated past encounters; existing biographies and actions retained'}
        self.meta['story_systems']=story
        additions.append({'collection':'world','subject_id':'story_systems','component_path':'$','new_value':deepcopy(story)})
        self.store.append(self._beat('migration.story.resources.v3',[],
            'Added city destinations; all old object IDs and existing map cells preserved.',additions))
        with self.transaction('migration.story.actors.v3',list(self.actors),
                'Added concrete belongings and multi-emotion appraisals; existing actions and biographies kept.'):
            for aid in self.actors:
                actor=self.edit('actors',aid)
                self._story_actor(actor)
                actor.setdefault('career', careers.initial(actor,self.now))
                actor.update(psychology.add_missing_ambitions(actor,self.now))
                actor['affect']=affect.appraise(actor,self.needs_at(actor),self.now,'Migration: current state, not invented history',f'beat_{self.store.sequence+1:08}')
        self.save()

    def _step_available(self,actor,obj,kind,completion=False):
        if kind in possessions.POSSESSION_ACTIONS:
            return possessions.step_available(actor,obj,kind,self.now,completion=completion)
        if kind in DAILY_ACTIONS:
            if kind=='eat_meal':
                concrete=sum(i['location']=={'type':'container','id':obj['id']} and i['state'].get('stage')=='served'
                    for a in self.actors.values() for i in a.get('belongings',[]))
                if obj.get('daily',{}).get('served_meals',0)<=concrete:return False
            try:apply_step(actor,obj,kind)
            except StepUnavailable:return False
        return True

    def _apply_possession(self,actor,action):
        kind=action['kind']
        if kind in possessions.POSSESSION_ACTIONS:
            eaten=next((item for item in actor.get('belongings',[]) if
                kind=='eat_recipe' and item['kind'] in possessions.RECIPES and
                item['location']=={'type':'container','id':action['target_id']} and
                item.get('state',{}).get('stage')=='served'),None)
            obj=self.edit('objects',action['target_id'])
            patch=possessions.apply_step(actor,obj,kind,self.now)
            obj['daily']=patch.pop('object_daily')
            actor.update(patch)
            if eaten:
                actor['last_meal']={'label':eaten['label'],'item_id':eaten['id'],'at':self.now}
        elif kind in {'clear_dishes','wash_dishes'}:
            if kind=='clear_dishes':
                target=action['target_id']
                # Transfer custody, not ownership, when clearing somebody else's plate.
                own=next((i for i in actor.get('belongings',[]) if i['kind']=='dirty_dish' and i['location']=={'type':'container','id':target}),None)
                if own is None:
                    for other in self.actors.values():
                        dish=next((i for i in other.get('belongings',[]) if i['kind']=='dirty_dish' and i['location']=={'type':'container','id':target}),None)
                        if dish:
                            other=self.edit('actors',other['id']);other['belongings'].remove(dish)
                            actor['belongings'].append(deepcopy(dish));break
            actor.update(possessions.synchronize_cleanup(actor,self.objects[action['target_id']],kind,self.now))

    def _story_inspection(self,actor):
        actor['affect']=affect.project_affect(actor,self.now)
        actor['social_graph']=affect.social_graph_projection(actor,self.actors,self.now)
        actor['appearance']={**actor['appearance'],'outfit':possessions.worn_outfit(actor)}
        return actor

    def _story_projection(self,actor):
        emotional=affect.project_affect(actor,self.now)
        return {'affect':{k:emotional.get(k) for k in ('primary','states')},
            'appearance':{**actor['appearance'],'outfit':possessions.worn_outfit(actor)},
            'portable_items':[deepcopy(i) for i in actor.get('belongings',[]) if i.get('location',{}).get('type') in {'carried','container'}]}

    def _story_invariants(self):
        errors=[];identifiers=set();items_by_id={}
        home_ids={a['home_id'] for a in self.actors.values()}
        for actor in self.actors.values():
            worn_slots=set()
            for item in actor.get('belongings',[]):
                if item['id'] in identifiers:errors.append('duplicate portable item '+item['id'])
                identifiers.add(item['id'])
                items_by_id[item['id']]=item
                if item.get('owner_id') not in self.actors:errors.append('invalid item owner '+item['id'])
                location=item.get('location',{})
                if location.get('type') not in {'worn','carried','container','consumed'}:errors.append('unknown item location '+item['id'])
                if location.get('type') in {'carried','worn'} and location.get('id')!=actor['id']:errors.append('invalid item custodian '+item['id'])
                if location.get('type')=='container' and location.get('id') not in self.objects and location.get('id') not in home_ids:errors.append('unknown item container '+item['id'])
                if location.get('type')=='worn':
                    if location.get('slot') in worn_slots:errors.append('duplicate clothing slot '+actor['id'])
                    worn_slots.add(location.get('slot'))
        for obj in self.objects.values():
            daily=obj.get('daily',{})
            for key,value in daily.items():
                if key=='oven_item_id':
                    item=items_by_id.get(value)
                    if not item or item['location']!={'type':'container','id':obj['id']} or item['state'].get('stage') not in {'heating','baked'}:
                        errors.append('invalid oven contents '+obj['id'])
                elif not isinstance(value,(int,float)) or value<0:
                    errors.append('invalid resource count '+obj['id']+':'+key)
            concrete_meals=sum(i['location']=={'type':'container','id':obj['id']} and i['state'].get('stage')=='served' for i in items_by_id.values()) if obj['kind']=='table' else 0
            if concrete_meals>daily.get('served_meals',0):errors.append('table meal counter disagrees with items '+obj['id'])
        return errors
